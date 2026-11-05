from django.db.models import Q
from rest_framework.decorators import api_view
from .models import PromptTemplate, PromptVersion
from .serializers import (
    PromptTemplateListSerializer, PromptTemplateDetailSerializer,
    PromptPreviewSerializer, PromptVersionSerializer,
)
from accounts.views import make_response
from accounts.models import User
from services.default_flag import set_default_atomically
from services.pagination import parse_paging
from services.search import search_filter

# ── Template CRUD ─────────────────────────────────────

@api_view(["GET", "POST"])
def template_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    if request.method == "GET":
        qs = PromptTemplate.objects.select_related("created_by").order_by("-is_default", "-updated_at")
        skill = request.GET.get("skill")
        if skill:
            qs = qs.filter(skill=skill)
        keyword = request.GET.get("keyword")
        if keyword:
            qs = search_filter(qs, keyword, "prompt")
        page, size = parse_paging(request)
        total = qs.count()
        data = qs[(page - 1) * size: page * size]
        return make_response(data={
            "list": PromptTemplateListSerializer(data, many=True).data,
            "total": total, "page": page, "pageSize": size,
        })
    # POST
    ser = PromptTemplateListSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    tmpl = ser.save(created_by=request.user)
    # 首次保存也创建版本记录
    PromptVersion.objects.create(
        template=tmpl, version=1, content=tmpl.content,
        variables=tmpl.variables, change_note="初始版本",
        created_by=request.user,
    )
    if tmpl.is_default:
        set_default_atomically(tmpl, scope={"skill": tmpl.skill})
    return make_response(data=PromptTemplateDetailSerializer(tmpl).data)


@api_view(["GET", "PUT", "DELETE"])
def template_detail(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        tmpl = PromptTemplate.objects.get(pk=pk)
    except PromptTemplate.DoesNotExist:
        return make_response(code=404, message="模板不存在", http_status=404)
    if request.method == "GET":
        return make_response(data=PromptTemplateDetailSerializer(tmpl).data)
    elif request.method == "PUT":
        old_content = tmpl.content
        ser = PromptTemplateDetailSerializer(tmpl, data=request.data, partial=True)
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        tmpl = ser.save()
        # 内容变了 → 版本号 +1 + 创建历史
        if tmpl.content != old_content:
            tmpl.version += 1
            tmpl.save(update_fields=["version"])
            PromptVersion.objects.create(
                template=tmpl, version=tmpl.version, content=tmpl.content,
                variables=tmpl.variables, change_note=request.data.get("change_note", ""),
                created_by=request.user,
            )
        if tmpl.is_default:
            set_default_atomically(tmpl, scope={"skill": tmpl.skill})
        return make_response(data=PromptTemplateDetailSerializer(tmpl).data)
    else:
        tmpl.delete()
        return make_response(message="删除成功")


# ── Preview / Versions / Rollback ─────────────────────

@api_view(["POST"])
def template_preview(request, pk):
    """Jinja2 渲染预览"""
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        tmpl = PromptTemplate.objects.get(pk=pk)
    except PromptTemplate.DoesNotExist:
        return make_response(code=404, message="模板不存在", http_status=404)
    ser = PromptPreviewSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    variables = ser.validated_data.get("variables", {})
    try:
        from jinja2 import Template
        rendered = Template(tmpl.content).render(**variables)
    except Exception as e:
        return make_response(code=400, message=f"渲染失败: {str(e)}", http_status=400)
    return make_response(data={"rendered": rendered, "variables": variables})


@api_view(["GET"])
def template_versions(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        tmpl = PromptTemplate.objects.get(pk=pk)
    except PromptTemplate.DoesNotExist:
        return make_response(code=404, message="模板不存在", http_status=404)
    versions = tmpl.versions.all()
    return make_response(data=PromptVersionSerializer(versions, many=True).data)


@api_view(["POST"])
def template_rollback(request, pk):
    """回滚到指定版本"""
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        tmpl = PromptTemplate.objects.get(pk=pk)
    except PromptTemplate.DoesNotExist:
        return make_response(code=404, message="模板不存在", http_status=404)
    version_id = request.data.get("version_id")
    if not version_id:
        return make_response(code=400, message="请指定 version_id", http_status=400)
    try:
        pv = PromptVersion.objects.get(template=tmpl, id=version_id)
    except PromptVersion.DoesNotExist:
        return make_response(code=404, message="版本不存在", http_status=404)
    tmpl.content = pv.content
    tmpl.variables = pv.variables
    tmpl.version += 1
    tmpl.save()
    PromptVersion.objects.create(
        template=tmpl, version=tmpl.version, content=tmpl.content,
        variables=tmpl.variables,
        change_note=f"回滚到 v{pv.version} — {pv.change_note}",
        created_by=request.user,
    )
    return make_response(data=PromptTemplateDetailSerializer(tmpl).data)


@api_view(["PUT"])
def template_set_default(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        tmpl = PromptTemplate.objects.get(pk=pk)
    except PromptTemplate.DoesNotExist:
        return make_response(code=404, message="模板不存在", http_status=404)
    # 按 skill 互斥：同一技能下至多一条默认模板。行锁 + 事务避免并发产生 0/2 条默认
    set_default_atomically(tmpl, scope={"skill": tmpl.skill})
    return make_response(data=PromptTemplateDetailSerializer(tmpl).data)
