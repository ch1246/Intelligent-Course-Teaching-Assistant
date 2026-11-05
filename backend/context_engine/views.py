from rest_framework.decorators import api_view
from .models import ContextStrategy
from .serializers import ContextStrategySerializer
from accounts.views import make_response
from accounts.models import User
from services.default_flag import set_default_atomically
from services.pagination import parse_paging


@api_view(["GET", "POST"])
def strategy_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    if request.method == "GET":
        qs = ContextStrategy.objects.select_related("created_by").order_by("-is_default", "-updated_at")
        page, size = parse_paging(request)
        total = qs.count()
        data = qs[(page - 1) * size: page * size]
        return make_response(data={
            "list": ContextStrategySerializer(data, many=True).data,
            "total": total, "page": page, "pageSize": size,
        })
    # POST
    ser = ContextStrategySerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    strategy = ser.save(created_by=request.user)
    if strategy.is_default:
        set_default_atomically(strategy)
    return make_response(data=ContextStrategySerializer(strategy).data)


@api_view(["GET", "PUT", "DELETE"])
def strategy_detail(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        strategy = ContextStrategy.objects.get(pk=pk)
    except ContextStrategy.DoesNotExist:
        return make_response(code=404, message="策略不存在", http_status=404)
    if request.method == "GET":
        return make_response(data=ContextStrategySerializer(strategy).data)
    elif request.method == "PUT":
        ser = ContextStrategySerializer(strategy, data=request.data, partial=True)
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        strategy = ser.save()
        if strategy.is_default:
            set_default_atomically(strategy)
        return make_response(data=ContextStrategySerializer(strategy).data)
    else:
        strategy.delete()
        return make_response(message="删除成功")


@api_view(["PUT"])
def strategy_set_default(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    try:
        strategy = ContextStrategy.objects.get(pk=pk)
    except ContextStrategy.DoesNotExist:
        return make_response(code=404, message="策略不存在", http_status=404)
    # 全局互斥：行锁 + 事务避免并发产生 0 条或 2 条默认
    set_default_atomically(strategy)
    return make_response(data=ContextStrategySerializer(strategy).data)
