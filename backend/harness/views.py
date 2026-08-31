from rest_framework.decorators import api_view
from .models import RAGPipeline, TraceLog
from .serializers import (
    RAGPipelineListSerializer, RAGPipelineDetailSerializer, TraceLogSerializer,
)
from accounts.views import make_response
from accounts.models import User


# ── Pipeline CRUD ─────────────────────────────────────

@api_view(["GET", "POST"])
def pipeline_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    if request.method == "GET":
        qs = RAGPipeline.objects.select_related(
            "prompt_template", "context_strategy", "agent_config", "created_by"
        ).order_by("-is_default", "-updated_at")
        page = int(request.GET.get("page", 1))
        size = int(request.GET.get("pageSize", 20))
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
        RAGPipeline.objects.exclude(pk=pipeline.pk).update(is_default=False)
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
            RAGPipeline.objects.exclude(pk=pipeline.pk).update(is_default=False)
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
    RAGPipeline.objects.all().update(is_default=False)
    pipeline.is_default = True
    pipeline.save(update_fields=["is_default"])
    return make_response(data=RAGPipelineDetailSerializer(pipeline).data)


# ── Trace Log ─────────────────────────────────────────

@api_view(["GET"])
def trace_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    qs = TraceLog.objects.select_related("session", "pipeline").order_by("-created_at")
    session_id = request.GET.get("session_id")
    if session_id:
        qs = qs.filter(session_id=session_id)
    phase = request.GET.get("phase")
    if phase:
        qs = qs.filter(phase=phase)
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("pageSize", 50))
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
        trace = TraceLog.objects.select_related("session", "pipeline").get(pk=pk)
    except TraceLog.DoesNotExist:
        return make_response(code=404, message="追踪记录不存在", http_status=404)
    return make_response(data=TraceLogSerializer(trace).data)
