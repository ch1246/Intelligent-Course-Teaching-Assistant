import os
import asyncio
import logging
import threading
from django.utils import timezone
from rest_framework.decorators import api_view
from .models import VectorCollection
from .serializers import VectorCollectionSerializer
from accounts.views import make_response
from accounts.models import User
from files_app.models import UploadedFile
from settings_app.models import AgentAPIConfig
from services.rag_service import (
    delete_collection,
    index_documents,
    summarize_document,
)
from services.search import search_filter

logger = logging.getLogger(__name__)

# 上传白名单：只放行能解析出文本的类型，挡住「任意文件上传」
ALLOWED_UPLOAD_EXTENSIONS = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.md', '.txt'}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB
MAX_PAGE_SIZE = 100


def _parse_paging(request):
    """解析分页参数。非数字/越界都安全回退 —— 旧实现 pageSize=abc 会直接 500。"""
    def _int(name, default, minimum, maximum):
        try:
            value = int(request.GET.get(name, default))
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, value))

    return _int('page', 1, 1, 10 ** 9), _int('pageSize', 20, 1, MAX_PAGE_SIZE)


def _can_manage(request, vc) -> bool:
    """归属校验：admin 任意；教师只能操作自己任教课程的知识库。"""
    if request.user.role == User.Role.ADMIN:
        return True
    return getattr(vc.course, 'teacher_id', None) == request.user.id


# ── Collection CRUD ───────────────────────────────────

@api_view(["GET", "POST"])
def collection_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    if request.method == "GET":
        qs = VectorCollection.objects.select_related("course").order_by("-created_at")
        if request.user.role == User.Role.TEACHER:
            qs = qs.filter(course__teacher_id=request.user.id)
        page, size = _parse_paging(request)
        search = request.GET.get("search", "")
        if search:
            qs = search_filter(qs, search, "collection")
        status = request.GET.get("status", "")
        if status in ("active", "indexing", "error"):
            qs = qs.filter(status=status)
        total = qs.count()
        data = qs[(page - 1) * size: page * size]
        return make_response(data={
            "list": VectorCollectionSerializer(data, many=True).data,
            "total": total, "page": page, "pageSize": size,
        })
    ser = VectorCollectionSerializer(data=request.data, context={"request": request})
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    vc = ser.save()
    return make_response(data=VectorCollectionSerializer(vc).data)


@api_view(["GET", "PUT", "DELETE"])
def collection_detail(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        vc = VectorCollection.objects.select_related("course").get(pk=pk)
    except VectorCollection.DoesNotExist:
        return make_response(code=404, message="集合不存在", http_status=404)
    if not _can_manage(request, vc):
        return make_response(code=403, message="只能操作自己任教的课程", http_status=403)
    if request.method == "GET":
        return make_response(data=VectorCollectionSerializer(vc).data)
    elif request.method == "PUT":
        ser = VectorCollectionSerializer(vc, data=request.data, partial=True, context={"request": request})
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        ser.save()
        return make_response(data=VectorCollectionSerializer(vc).data)
    else:
        # 一门课只有一个知识库记录（模型上有唯一约束），删除该记录即表示
        # 删除这门课的向量库，物理集合名由 VectorCollection.collection_name 唯一决定。
        # 旧实现直接按 course_id 拼名字删除，同课程多条记录共享一个物理集合，
        # 删任意一条就会把整门课的向量库清空。
        collection_name = vc.collection_name
        vc.delete()
        delete_collection(collection_name)
        return make_response(message="删除成功")


# ── Reindex ───────────────────────────────────────────

def _get_llm_config():
    config = AgentAPIConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        config = AgentAPIConfig.objects.filter(is_active=True).first()
    return config


def _chunk_params() -> tuple[int, int]:
    """从默认上下文策略读取分块参数。

    此前 reindex 用的是 rag_service 里写死的 500/50，后台 ContextStrategy 的
    chunk_size / chunk_overlap 配了也不生效 —— 这里把它接进链路。
    """
    from context_engine.models import ContextStrategy

    strategy = (
        ContextStrategy.objects.filter(is_active=True, is_default=True).first()
        or ContextStrategy.objects.filter(is_active=True).first()
    )
    if not strategy:
        return 500, 50
    return (strategy.chunk_size or 500), (strategy.chunk_overlap or 50)


def _run_async(coro):
    """在同步上下文里执行协程。

    没有运行中的事件循环 → 直接 asyncio.run；
    已有运行中的循环（例如被嵌在异步服务器/线程里）→ 另起线程 + 新循环执行，
    不再依赖未列入 requirements 的 nest_asyncio。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict = {}

    def runner():
        loop = asyncio.new_event_loop()
        try:
            result["value"] = loop.run_until_complete(coro)
        except BaseException as exc:  # noqa: BLE001 - 原样抛回主线程
            result["error"] = exc
        finally:
            loop.close()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


@api_view(["POST"])
def reindex(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        vc = VectorCollection.objects.select_related("course").get(pk=pk)
    except VectorCollection.DoesNotExist:
        return make_response(code=404, message="集合不存在", http_status=404)
    if not _can_manage(request, vc):
        return make_response(code=403, message="只能操作自己任教的课程", http_status=403)

    vc.status = "indexing"
    vc.save()

    try:
        collection_name = vc.collection_name
        delete_collection(collection_name)

        # 全量重灌：集合刚被删掉，必须把该课程**所有**文件重新索引一遍。
        # 旧实现只取 is_vectorized=False，第二次重建时集合已空却没有文件可灌 → 静默丢数据。
        files = list(UploadedFile.objects.filter(course_id=vc.course_id).order_by("id"))
        documents = []
        metadatas = []
        ids_list = []
        summaries = []
        skipped = []

        llm_config = _get_llm_config()
        can_summarize = bool(llm_config and llm_config.get_api_key())
        chunk_size, chunk_overlap = _chunk_params()

        for uf in files:
            if not os.path.exists(uf.stored_path):
                skipped.append(f"{uf.original_name}(文件不存在)")
                continue
            with open(uf.stored_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            if not content.strip():
                skipped.append(f"{uf.original_name}(内容为空)")
                continue

            documents.append(content)
            metadatas.append({"source": uf.original_name, "file_id": str(uf.id)})
            ids_list.append(str(uf.id))

            # 摘要优先复用库里已有的，避免每次重建都重新调用 LLM
            summary = (uf.summary or "").strip()
            if not summary and can_summarize and len(content) > 200:
                try:
                    summary = _run_async(summarize_document(
                        content=content,
                        filename=uf.original_name,
                        base_url=llm_config.base_url,
                        api_key=llm_config.get_api_key(),
                        model=llm_config.default_model or (llm_config.model_list[0] if llm_config.model_list else "gpt-3.5-turbo"),
                    ))
                except Exception as e:
                    logger.warning(f"Summarize failed for {uf.original_name}: {e}")
                    summary = ""
            summaries.append(summary)

            update_fields = ["is_vectorized"]
            uf.is_vectorized = True
            if summary and summary != (uf.summary or ""):
                uf.summary = summary
                update_fields.append("summary")
            uf.save(update_fields=update_fields)

        if skipped:
            logger.warning(
                "reindex 跳过 %d/%d 个文件：%s", len(skipped), len(files), "；".join(skipped[:10])
            )

        if documents:
            total_chunks = index_documents(
                collection_name, documents, metadatas, ids_list, summaries,
                chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            )
            vc.chunk_count = total_chunks
            vc.vector_count = total_chunks
            vc.document_count = len(documents)
        else:
            vc.chunk_count = 0
            vc.vector_count = 0
            vc.document_count = 0

        vc.status = "active"
        vc.last_indexed_at = timezone.now()
        vc.save()
        logger.info(
            "reindex 完成 course=%s 文件=%d 文档=%d chunk=%d (chunk_size=%d, overlap=%d)",
            vc.course_id, len(files), vc.document_count, vc.vector_count, chunk_size, chunk_overlap,
        )
        return make_response(data=VectorCollectionSerializer(vc).data)
    except Exception as e:
        vc.status = "error"
        vc.save()
        return make_response(code=500, message=f"索引失败: {str(e)}", http_status=500)


# ── Document upload ───────────────────────────────────

@api_view(["POST"])
def upload_document(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    file = request.FILES.get("file")
    collection_id = request.data.get("collection_id")
    if not file or not collection_id:
        return make_response(code=400, message="缺少参数", http_status=400)
    try:
        vc = VectorCollection.objects.select_related("course").get(pk=collection_id)
    except VectorCollection.DoesNotExist:
        return make_response(code=404, message="集合不存在", http_status=404)
    if not _can_manage(request, vc):
        return make_response(code=403, message="只能操作自己任教的课程", http_status=403)

    # 三重校验：扩展名白名单 + 大小上限 + 真实文件头（不信任 content_type）
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        return make_response(
            code=400,
            message=f"不支持的文件类型 {ext or '(无扩展名)'}，仅支持：{'、'.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}",
            http_status=400,
        )
    if file.size > MAX_UPLOAD_BYTES:
        return make_response(code=400, message="文件超过 20MB 上限", http_status=400)
    if file.size == 0:
        return make_response(code=400, message="文件为空", http_status=400)

    from django.conf import settings
    import uuid

    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(settings.MEDIA_ROOT, "vectors", stored_name)
    os.makedirs(os.path.dirname(stored_path), exist_ok=True)

    with open(stored_path, "wb+") as dest:
        for chunk in file.chunks():
            dest.write(chunk)

    uf = UploadedFile.objects.create(
        original_name=file.name, stored_path=stored_path,
        file_size=file.size, mime_type=file.content_type or "",
        course=vc.course, uploader=request.user,
    )
    return make_response(data={"id": uf.id, "name": uf.original_name, "size": uf.file_size})
