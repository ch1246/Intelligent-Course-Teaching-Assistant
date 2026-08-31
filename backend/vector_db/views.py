import os
import asyncio
from django.utils import timezone
from rest_framework.decorators import api_view
from .models import VectorCollection
from .serializers import VectorCollectionSerializer
from accounts.views import make_response
from accounts.models import User
from files_app.models import UploadedFile
from settings_app.models import AgentAPIConfig
from services.rag_service import index_documents, delete_collection, summarize_document


# ── Collection CRUD ───────────────────────────────────

@api_view(["GET", "POST"])
def collection_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    if request.method == "GET":
        qs = VectorCollection.objects.select_related("course").order_by("-created_at")
        page = int(request.GET.get("page", 1))
        size = int(request.GET.get("pageSize", 20))
        search = request.GET.get("search", "")
        if search:
            qs = qs.filter(name__icontains=search)
        status = request.GET.get("status", "")
        if status in ("active", "indexing", "error"):
            qs = qs.filter(status=status)
        total = qs.count()
        data = qs[(page - 1) * size: page * size]
        return make_response(data={
            "list": VectorCollectionSerializer(data, many=True).data,
            "total": total, "page": page, "pageSize": size,
        })
    ser = VectorCollectionSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    vc = ser.save()
    return make_response(data=VectorCollectionSerializer(vc).data)


@api_view(["GET", "PUT", "DELETE"])
def collection_detail(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        vc = VectorCollection.objects.get(pk=pk)
    except VectorCollection.DoesNotExist:
        return make_response(code=404, message="集合不存在", http_status=404)
    if request.method == "GET":
        return make_response(data=VectorCollectionSerializer(vc).data)
    elif request.method == "PUT":
        ser = VectorCollectionSerializer(vc, data=request.data, partial=True)
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        ser.save()
        return make_response(data=VectorCollectionSerializer(vc).data)
    else:
        collection_name = f"course_{vc.course_id}"
        delete_collection(collection_name)
        vc.delete()
        return make_response(message="删除成功")


# ── Reindex ───────────────────────────────────────────

def _get_llm_config():
    config = AgentAPIConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        config = AgentAPIConfig.objects.filter(is_active=True).first()
    return config


def _run_async(coro):
    """Run an async coroutine in a sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


@api_view(["POST"])
def reindex(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        vc = VectorCollection.objects.get(pk=pk)
    except VectorCollection.DoesNotExist:
        return make_response(code=404, message="集合不存在", http_status=404)

    vc.status = "indexing"
    vc.save()

    try:
        collection_name = f"course_{vc.course_id}"
        delete_collection(collection_name)

        files = UploadedFile.objects.filter(course_id=vc.course_id, is_vectorized=False)
        documents = []
        metadatas = []
        ids_list = []
        summaries = []

        llm_config = _get_llm_config()
        can_summarize = llm_config and llm_config.get_api_key()

        for uf in files:
            file_path = uf.stored_path
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                documents.append(content)
                metadatas.append({"source": uf.original_name, "file_id": str(uf.id)})
                ids_list.append(str(uf.id))
                uf.is_vectorized = True

                # ── AI 摘要 ──────────────────────────
                if can_summarize and len(content) > 200:
                    try:
                        summary = _run_async(summarize_document(
                            content=content,
                            filename=uf.original_name,
                            base_url=llm_config.base_url,
                            api_key=llm_config.get_api_key(),
                            model=llm_config.default_model or (llm_config.model_list[0] if llm_config.model_list else "gpt-3.5-turbo"),
                        ))
                        uf.summary = summary
                        summaries.append(summary)
                    except Exception as e:
                        logger = __import__("logging").getLogger(__name__)
                        logger.warning(f"Summarize failed for {uf.original_name}: {e}")
                        summaries.append("")
                else:
                    summaries.append("")

                uf.save(update_fields=["is_vectorized", "summary"])

        if documents:
            total_chunks = index_documents(
                collection_name, documents, metadatas, ids_list, summaries
            )
            vc.chunk_count = total_chunks
            vc.vector_count = total_chunks
            vc.document_count = len(documents)

        vc.status = "active"
        vc.last_indexed_at = timezone.now()
        vc.save()
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
        vc = VectorCollection.objects.get(pk=collection_id)
    except VectorCollection.DoesNotExist:
        return make_response(code=404, message="集合不存在", http_status=404)

    from django.conf import settings
    import uuid
    ext = os.path.splitext(file.name)[1]
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
