from rest_framework.decorators import api_view
from .models import SystemSetting, AgentAPIConfig
from .serializers import SystemSettingSerializer, AgentAPIConfigSerializer
from accounts.views import make_response
from accounts.models import User
from services.default_flag import set_default_atomically


# ── System Settings ───────────────────────────────────

# 安全：非管理员读取系统设置时只返回这些「公开配置」，避免把可能存放凭证/密钥的项暴露出去。
# 新增敏感配置项（如 SMTP 密码）不要加进这个集合。
PUBLIC_SETTING_KEYS = {
    "site_name",
    "site_description",
    "default_language",
    "max_upload_size_mb",
    "maintenance_mode",
    "enable_registration",
}


@api_view(["GET", "PUT"])
def system_settings(request):
    is_admin = request.user.role == User.Role.ADMIN

    if request.method == "GET":
        # 读：管理员拿全量；其他登录用户只拿公开白名单
        qs = SystemSetting.objects.all()
        if not is_admin:
            qs = qs.filter(key__in=PUBLIC_SETTING_KEYS)
        return make_response(data=SystemSettingSerializer(qs, many=True).data)

    # PUT: bulk update —— 安全：只有管理员可以修改系统配置
    if not is_admin:
        return make_response(code=403, message="无权限", http_status=403)
    data = request.data
    if isinstance(data, list):
        for item in data:
            key = item.get("key")
            value = item.get("value", "")
            if key:
                SystemSetting.objects.update_or_create(key=key, defaults={"value": value})
    elif isinstance(data, dict):
        for key, value in data.items():
            SystemSetting.objects.update_or_create(key=key, defaults={"value": str(value)})
    settings = SystemSetting.objects.all()
    return make_response(data=SystemSettingSerializer(settings, many=True).data)


# ── Agent API Configs ─────────────────────────────────

@api_view(["GET", "POST"])
def agent_api_config_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    if request.method == "GET":
        qs = AgentAPIConfig.objects.all().order_by("-is_default", "-created_at")
        return make_response(data=AgentAPIConfigSerializer(qs, many=True).data)
    # POST
    ser = AgentAPIConfigSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    config = ser.save(created_by=request.user)
    if config.is_default:
        set_default_atomically(config)
    return make_response(data=AgentAPIConfigSerializer(config).data)


@api_view(["GET", "PUT", "DELETE"])
def agent_api_config_detail(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        config = AgentAPIConfig.objects.get(pk=pk)
    except AgentAPIConfig.DoesNotExist:
        return make_response(code=404, message="配置不存在", http_status=404)
    if request.method == "GET":
        return make_response(data=AgentAPIConfigSerializer(config).data)
    elif request.method == "PUT":
        # If api_key is explicitly provided as empty string, remove it to keep old value
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if "api_key" in data and data["api_key"] == "":
            del data["api_key"]
        # Guard: if someone accidentally sends the masked key back, strip it
        if "api_key" in data and isinstance(data["api_key"], str) and data["api_key"].startswith("sk-****"):
            del data["api_key"]
        ser = AgentAPIConfigSerializer(config, data=data, partial=True)
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        config = ser.save()
        if config.is_default:
            set_default_atomically(config)
        return make_response(data=AgentAPIConfigSerializer(config).data)
    else:
        config.delete()
        return make_response(message="删除成功")


@api_view(["PUT"])
def set_default_config(request, pk):
    """Set this config as the default."""
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        config = AgentAPIConfig.objects.get(pk=pk)
    except AgentAPIConfig.DoesNotExist:
        return make_response(code=404, message="配置不存在", http_status=404)
    # 全局互斥：行锁 + 事务避免并发产生 0 条或 2 条默认
    set_default_atomically(config)
    return make_response(data=AgentAPIConfigSerializer(config).data)
