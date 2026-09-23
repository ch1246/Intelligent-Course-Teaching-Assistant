from rest_framework.decorators import api_view
from .models import SystemSetting, AgentAPIConfig
from .serializers import SystemSettingSerializer, AgentAPIConfigSerializer
from accounts.views import make_response
from accounts.models import User


# ── System Settings ───────────────────────────────────

@api_view(["GET", "PUT"])
def system_settings(request):
    if request.method == "GET":
        settings = SystemSetting.objects.all()
        return make_response(data=SystemSettingSerializer(settings, many=True).data)
    # PUT: bulk update
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
        AgentAPIConfig.objects.exclude(pk=config.pk).update(is_default=False)
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
            AgentAPIConfig.objects.exclude(pk=config.pk).update(is_default=False)
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
    AgentAPIConfig.objects.all().update(is_default=False)
    config.is_default = True
    config.save(update_fields=["is_default"])
    return make_response(data=AgentAPIConfigSerializer(config).data)
