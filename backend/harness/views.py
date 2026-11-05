from rest_framework.decorators import api_view
from .models import RAGPipeline, TraceLog
from .serializers import (
    RAGPipelineListSerializer, RAGPipelineDetailSerializer, TraceLogSerializer,
)
from accounts.views import make_response
from accounts.models import User
from services.default_flag import set_default_atomically
from services.pagination import parse_paging


# ── Pipeline CRUD ─────────────────────────────────────

@api_view(["GET", "POST"])
def pipeline_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    if request.method == "GET":
        qs = RAGPipeline.objects.select_related(
            "prompt_template", "context_strategy", "agent_config", "created_by"
        ).order_by("-is_default", "-updated_at")
        page, size = parse_paging(request)
        total = qs.count()
        data = qs[(page - 1) * size: page * size]
        return make_response(data={
            "list": RAGPipelineListSerializer(data, many=True).data,
            "total": total, "page": page, "pageSize": size,
        })
    ser = RAGPipelineListSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    pipeline = ser.save(created_by=request.user)
    if pipeline.is_default:
        set_default_atomically(pipeline)
    return make_response(data=RAGPipelineDetailSerializer(pipeline).data)


@api_view(["GET", "PUT", "DELETE"])
def pipeline_detail(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        pipeline = RAGPipeline.objects.select_related(
            "prompt_template", "context_strategy", "agent_config"
        ).get(pk=pk)
    except RAGPipeline.DoesNotExist:
        return make_response(code=404, message="管道不存在", http_status=404)
    if request.method == "GET":
        return make_response(data=RAGPipelineDetailSerializer(pipeline).data)
    elif request.method == "PUT":
        ser = RAGPipelineListSerializer(pipeline, data=request.data, partial=True)
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        pipeline = ser.save()
        if pipeline.is_default:
            set_default_atomically(pipeline)
        return make_response(data=RAGPipelineDetailSerializer(pipeline).data)
    else:
        pipeline.delete()
        return make_response(message="删除成功")


@api_view(["PUT"])
def pipeline_set_default(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        pipeline = RAGPipeline.objects.get(pk=pk)
    except RAGPipeline.DoesNotExist:
        return make_response(code=404, message="管道不存在", http_status=404)
    # 全局互斥：行锁 + 事务避免并发产生 0 条或 2 条默认
    set_default_atomically(pipeline)
    return make_response(data=RAGPipelineDetailSerializer(pipeline).data)


# ── Trace Log ─────────────────────────────────────────

def _parse_paging(request, default_size=50):
    """分页参数安全解析：非数字/越界回退，不再让 pageSize=abc 直接 500。"""
    def _int(name, default, minimum, maximum):
        try:
            value = int(request.GET.get(name, default))
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, value))

    return _int('page', 1, 1, 10 ** 9), _int('pageSize', default_size, 1, 200)


@api_view(["GET"])
def trace_list(request):
    """链路追踪列表。

    教师只能看到**自己任教课程**的会话追踪。旧实现任何教师都能翻出全校
    学生的提问与回答，属于越权读取他人对话数据。
    """
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    qs = TraceLog.objects.select_related("session", "session__course", "pipeline").order_by("-created_at")
    if request.user.role != User.Role.ADMIN:
        qs = qs.filter(session__course__teacher_id=request.user.id)
    session_id = request.GET.get("session_id")
    if session_id:
        qs = qs.filter(session_id=session_id)
    phase = request.GET.get("phase")
    if phase:
        qs = qs.filter(phase=phase)
    page, size = _parse_paging(request)
    total = qs.count()
    data = qs[(page - 1) * size: page * size]
    return make_response(data={
        "list": TraceLogSerializer(data, many=True).data,
        "total": total, "page": page, "pageSize": size,
    })


@api_view(["GET"])
def trace_detail(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        trace = TraceLog.objects.select_related("session", "session__course", "pipeline").get(pk=pk)
    except TraceLog.DoesNotExist:
        return make_response(code=404, message="追踪记录不存在", http_status=404)
    if request.user.role != User.Role.ADMIN:
        if getattr(trace.session.course, "teacher_id", None) != request.user.id:
            return make_response(code=403, message="无权限", http_status=403)
    return make_response(data=TraceLogSerializer(trace).data)
