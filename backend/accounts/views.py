import logging
import secrets
import string

from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import models, IntegrityError
from .models import User
from services.pagination import parse_paging
from services.search import search_filter
from .serializers import (
    UserSerializer, LoginSerializer, RegisterSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, UserUpdateSerializer,
)

logger = logging.getLogger(__name__)


def make_response(data=None, code=200, message="success", http_status=200):
    return Response({"code": code, "status": "ok" if code == 200 else "error", "message": message, "data": data}, status=http_status)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"accessToken": str(refresh.access_token), "refreshToken": str(refresh)}


def _generate_temp_password(length: int = 10) -> str:
    """生成随机临时密码。

    必须用 secrets 而不是 random：random 是可预测的 Mersenne Twister，
    拿它生成凭等于给攻击者留后门。这里的密码直接决定账号能否被接管。
    """
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# ── Auth ─────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login(request):
    ser = LoginSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    user = authenticate(username=ser.validated_data["username"], password=ser.validated_data["password"])
    if not user:
        return make_response(code=401, message="用户名或密码错误", http_status=401)
    if not user.is_active:
        return make_response(code=403, message="账号已被禁用", http_status=403)
    if user.role == User.Role.STUDENT and not user.is_approved:
        return make_response(code=403, message="账号尚未通过审核，请联系管理员", http_status=403)
    tokens = get_tokens_for_user(user)
    tokens["user"] = UserSerializer(user).data
    return make_response(data=tokens)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    ser = RegisterSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    d = ser.validated_data
    if User.objects.filter(username=d["username"]).exists():
        return make_response(code=400, message="用户名已存在", http_status=400)
    if d.get("student_id") and User.objects.filter(student_id=d["student_id"]).exists():
        return make_response(code=400, message="该学号已被注册", http_status=400)
    user = User.objects.create_user(
        username=d["username"], password=d["password"],
        email=d.get("email", ""),
        # 安全：自助注册一律为学生，角色由服务端决定，绝不采用客户端提交的值。
        # 否则任何人都能以 role=admin 注册，而登录只拦截「学生未审核」，等于自助提权。
        role=User.Role.STUDENT,
        student_id=d.get("student_id", ""),
        sex=d.get("sex", ""),
        dept=d.get("dept", ""),
        major=d.get("major", ""),
        grade=d.get("grade", ""),
        is_approved=False,
    )
    if d.get("phone"):
        user.phone = d["phone"]
    user.save()
    return make_response(message="注册成功，请等待管理员审核")


# ── Profile ───────────────────────────────────────────

@api_view(["GET"])
def get_user_info(request):
    return make_response(data=UserSerializer(request.user).data)

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def refresh_token(request):
    """刷新 access token。

    必须 AllowAny：access 过期后前端手里只剩 refresh，此时请求没有有效凭证，
    会被全局 IsAuthenticated 直接挡在视图之外 —— 旧实现没加，导致「过期就
    再也刷不了」只能重新登录。

    同时落实「双 Token 轮换 + 旧 refresh 即时失效」：每次刷新都签发新的
    refresh，并把旧的拉黑。此前 refresh 原样返回、旧 token 永久有效，
    配置里的 BLACKLIST_AFTER_ROTATION 对这个手写视图完全不生效。
    """
    refresh = request.data.get("refreshToken", "")
    if not refresh:
        return make_response(code=400, message="缺少 refreshToken", http_status=400)
    try:
        token = RefreshToken(refresh)
        user = User.objects.get(pk=token["user_id"], is_active=True)
    except Exception:
        return make_response(code=401, message="Token 无效或已过期", http_status=401)

    new_refresh = RefreshToken.for_user(user)
    # 旧 refresh 立即作废；失败不影响本次刷新，但要留痕便于排查
    try:
        token.blacklist()
    except Exception:
        logger.warning("refresh token 拉黑失败（token_blacklist 未就绪）", exc_info=True)

    return make_response(data={
        "accessToken": str(new_refresh.access_token),
        "refreshToken": str(new_refresh),
    })

@api_view(["POST"])
def change_password(request):
    ser = ChangePasswordSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    user = request.user
    if not user.check_password(ser.validated_data["old_password"]):
        return make_response(code=400, message="原密码错误", http_status=400)
    user.set_password(ser.validated_data["new_password"])
    user.save()
    return make_response(message="密码修改成功")

def _send_reset_email(to_email: str, username: str, temp_password: str) -> bool:
    """尝试把临时密码发给用户。返回是否真的送达。

    邮件服务未配置 / 发送失败都返回 False —— 调用方据此决定**是否真的改密**。
    """
    from django.conf import settings
    from django.core.mail import send_mail, BadHeaderError

    if not getattr(settings, "EMAIL_HOST", None) and not getattr(settings, "EMAIL_BACKEND", None):
        return False
    try:
        send_mail(
            subject="【Teek 教学助手】密码重置",
            message=f"您好 {username}：\n\n您的临时密码为：{temp_password}\n\n请尽快登录并修改密码。",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except (BadHeaderError, OSError, Exception):  # noqa: BLE001 - 任何发送失败都不能改密
        logger.warning("忘记密码邮件发送失败，未重置密码", exc_info=True)
        return False


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def forgot_password(request):
    """忘记密码：**只有确认临时密码能送达时才覆盖原密码**。

    旧实现无条件 set_password 后才发现邮件是 TODO —— 攻击者可以对任意邮箱
    反复调用，每次都把密码改成一个没人知道的随机串，账号被永久锁死。
    这里改成「先送达、后生效」，同时对不存在的邮箱保持同样的返回，
    不暴露邮箱是否已注册。
    """
    ser = ForgotPasswordSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    email = ser.validated_data["email"]
    generic_message = "如果该邮箱已注册，临时密码已发送，请查收"
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # 不暴露该邮箱是否已注册
        return make_response(message=generic_message)

    temp_password = _generate_temp_password()
    if not _send_reset_email(email, user.username, temp_password):
        # 关键：不改密码。宁可让用户去找管理员，也不能把人锁在门外。
        logger.warning(
            "[forgot_password] 邮件未送达，已跳过密码重置（user=%s）", user.username
        )
        return make_response(message=generic_message)

    user.set_password(temp_password)
    user.save(update_fields=["password"])
    logger.info("[forgot_password] 用户 %s 临时密码已发送并生效", user.username)
    return make_response(message=generic_message)

@api_view(["GET", "PUT"])
def profile(request):
    if request.method == "GET":
        return make_response(data=UserSerializer(request.user).data)
    ser = UserUpdateSerializer(request.user, data=request.data, partial=True)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    ser.save()
    return make_response(data=UserSerializer(request.user).data)

@api_view(["POST"])
def avatar_upload(request):
    import uuid, os
    from django.conf import settings
    file = request.FILES.get("file")
    if not file:
        return make_response(code=400, message="请选择文件", http_status=400)
    ext = os.path.splitext(file.name)[1] or ".png"
    name = f"avatar_{request.user.id}_{uuid.uuid4().hex[:8]}{ext}"
    avatars_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
    save_path = os.path.join(avatars_dir, name)
    with open(save_path, "wb+") as dest:
        for chunk in file.chunks():
            dest.write(chunk)
    url = f"{settings.MEDIA_URL}avatars/{name}"
    request.user.avatar = url
    request.user.save(update_fields=["avatar"])
    return make_response(data={"avatar": url})


# ── Admin: Registration Management ───────────────────

@api_view(["GET"])
def registration_list(request):
    """Admin: list pending/approved/rejected registrations."""
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    status_filter = request.GET.get("status", "pending")
    qs = User.objects.filter(role=User.Role.STUDENT)
    if status_filter == "pending":
        qs = qs.filter(is_approved=False)
    elif status_filter == "approved":
        qs = qs.filter(is_approved=True)
    page, size = parse_paging(request)
    search = request.GET.get("search", "")
    if search:
        qs = search_filter(qs, search, "user")
    total = qs.count()
    users = qs.order_by("-date_joined")[(page - 1) * size : page * size]
    return make_response(data={
        "list": UserSerializer(users, many=True).data,
        "total": total, "page": page, "pageSize": size,
    })


@api_view(["POST"])
def approve_registration(request, pk):
    """Admin: approve a student registration."""
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    try:
        user = User.objects.get(pk=pk, role=User.Role.STUDENT)
    except User.DoesNotExist:
        return make_response(code=404, message="用户不存在", http_status=404)
    user.is_approved = True
    user.approved_at = timezone.now()
    user.approved_by = request.user
    user.save()
    return make_response(data=UserSerializer(user).data)


@api_view(["POST"])
def reject_registration(request, pk):
    """Admin: 拒绝一条**待审核**的注册申请。

    只允许处理 is_approved=False 的记录：已通过审核的用户是真实账号，
    走这里被物理删除会连带丢掉他的课程、对话、学习记录。
    旧实现只校验 role=student，等于给管理员留了一个误删在用账号的入口。
    """
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    try:
        user = User.objects.get(pk=pk, role=User.Role.STUDENT, is_approved=False)
    except User.DoesNotExist:
        return make_response(code=404, message="待审核用户不存在", http_status=404)
    user.delete()
    return make_response(message="已拒绝并删除")


@api_view(["POST"])
def batch_approve(request):
    """Admin: batch approve registrations."""
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    ids = request.data.get("ids", [])
    if not ids:
        return make_response(code=400, message="请选择要审核的用户", http_status=400)
    cnt = User.objects.filter(pk__in=ids, role=User.Role.STUDENT, is_approved=False).update(
        is_approved=True, approved_at=timezone.now(), approved_by=request.user
    )
    return make_response(data={"approved": cnt})


@api_view(["POST"])
def import_excel(request):
    """Admin: 从 CSV / xlsx 批量导入学生。

    与自助注册保持同一套审核语义：默认**进入待审核**（is_approved=False），
    走既有的批量审核接口通过。需要直接开通时显式传 approved=true，
    不再静默绕过审核。

    同时把新账号的初始密码返回给管理员 —— 旧实现随机生成密码却谁也不告诉，
    导入进来的学生实际上无法登录。
    """
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    file = request.FILES.get("file")
    if not file:
        return make_response(code=400, message="请上传文件", http_status=400)

    raw_approved = request.data.get("approved", False)
    approved = str(raw_approved).lower() in ("1", "true", "yes", "on") if not isinstance(raw_approved, bool) else raw_approved

    try:
        import openpyxl
    except ImportError:
        return make_response(code=500, message="请安装 openpyxl: pip install openpyxl", http_status=500)

    filename = file.name.lower()
    rows = []
    if filename.endswith(".csv"):
        import csv, io
        data = file.read().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(data))
        next(reader, None)
        for row in reader:
            if len(row) >= 5:
                rows.append(tuple(row[:5]))
    elif filename.endswith(".xlsx"):
        wb = openpyxl.load_workbook(file, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
    else:
        return make_response(code=400, message="仅支持 .csv 或 .xlsx 文件", http_status=400)

    if not rows:
        return make_response(code=400, message="文件中无数据", http_status=400)

    created = 0
    skipped = 0
    errors = []
    credentials = []
    for i, row in enumerate(rows):
        try:
            student_id_raw = str(row[0] if row[0] is not None else "").strip()
            name = str(row[1] if row[1] is not None else "").strip()
            dept = str(row[2] if row[2] is not None else "").strip()
            grade = str(row[3] if row[3] is not None else "").strip()
            sex_str = str(row[4] if row[4] is not None else "").strip()

            if not all([student_id_raw, name, dept, grade, sex_str]):
                errors.append(f"第{i+2}行: 存在空字段")
                skipped += 1
                continue

            sex = "男" if sex_str in ("男", "M", "m") else "女"
            username = student_id_raw
            password = _generate_temp_password()  # 随机临时密码

            if User.objects.filter(username=username).exists() or User.objects.filter(student_id=student_id_raw).exists():
                skipped += 1
                continue

            User.objects.create_user(
                username=username, password=password,
                student_id=student_id_raw, sex=sex, dept=dept,
                major="", grade=grade,
                role=User.Role.STUDENT, is_approved=approved,
            )
            created += 1
            credentials.append({"username": username, "password": password})
        except Exception as e:
            errors.append(f"第{i+2}行: {str(e)}")
            skipped += 1

    return make_response(data={
        "created": created, "skipped": skipped, "errors": errors[:10],
        "total_rows": len(rows),
        "approved": approved,
        "pending_review": 0 if approved else created,
        # 初始密码只在本次响应里出现，管理员需自行分发并要求学生尽快改密
        "credentials": credentials,
    })


# ── User management (admin) ───────────────────────────

@api_view(["GET", "POST"])
def user_list(request):
    from django.db.models import Q
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    if request.method == "GET":
        from django.db.models import Count
        qs = User.objects.annotate(
            course_count=Count("enrollments", filter=Q(enrollments__status="approved"))
        ).order_by("-date_joined")
        page, size = parse_paging(request)
        search = request.GET.get("search", "")
        if search:
            qs = search_filter(qs, search, "user")
        role = request.GET.get("role", "")
        if role:
            qs = qs.filter(role=role)
        status = request.GET.get("status", "")
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "disabled":
            qs = qs.filter(is_active=False)
        total = qs.count()
        users = qs[(page - 1) * size : page * size]
        return make_response(data={"list": UserSerializer(users, many=True).data, "total": total, "page": page, "pageSize": size})
    ser = UserSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    password = request.data.get("password", "")
    if not password:
        return make_response(code=400, message="请输入密码", http_status=400)
    if len(password) < 6:
        return make_response(code=400, message="密码至少6位", http_status=400)
    student_id = ser.validated_data.get("student_id", "") or None
    try:
        user = User.objects.create_user(
            username=ser.validated_data["username"], password=password,
            email=ser.validated_data.get("email", ""),
            role=ser.validated_data.get("role", User.Role.STUDENT),
            phone=ser.validated_data.get("phone", ""),
            student_id=student_id,
            sex=ser.validated_data.get("sex", ""),
            dept=ser.validated_data.get("dept", ""),
            major=ser.validated_data.get("major", ""),
            grade=ser.validated_data.get("grade", ""),
            is_approved=True,
        )
        return make_response(data=UserSerializer(user).data)
    except IntegrityError:
        return make_response(code=400, message="学号已存在", http_status=400)

@api_view(["GET", "PUT", "DELETE"])
def user_detail(request, pk):
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return make_response(code=404, message="用户不存在", http_status=404)
    if request.method == "GET":
        return make_response(data=UserSerializer(user).data)
    elif request.method == "PUT":
        ser = UserSerializer(user, data=request.data, partial=True)
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        ser.save()
        return make_response(data=UserSerializer(user).data)
    else:
        if user == request.user:
            return make_response(code=400, message="不能删除自己", http_status=400)
        user.delete()
        return make_response(message="删除成功")

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def message_list(request):
    """Return real system messages for the current user."""
    user = request.user
    unread = []
    read = []

    # Pending enrollment approvals (for admin/teacher)
    if hasattr(user, "role") and user.role in ("admin", "teacher"):
        from enrollments.models import Enrollment
        pending = Enrollment.objects.filter(status="pending").select_related("student", "course").order_by("-enrolled_at")[:10]
        for e in pending:
            msg = {
                "id": f"enroll_{e.id}",
                "title": f"选课审批：{e.student.username} 申请加入「{e.course.name}」",
                "content": f"学生 {e.student.username} 申请选修课程「{e.course.name}」，请审批。",
                "description": f"申请时间：{e.enrolled_at.strftime('%Y-%m-%d %H:%M')}",
                "createTime": e.enrolled_at.strftime("%Y-%m-%d %H:%M"),
            }
            unread.append(msg)

    # Enrollment status (for student)
    if hasattr(user, "role") and user.role == "student":
        from enrollments.models import Enrollment
        my_enrolls = Enrollment.objects.filter(student=user).select_related("course").order_by("-enrolled_at")[:10]
        for e in my_enrolls:
            status_map = {"pending": "审核中", "approved": "已通过", "rejected": "已拒绝"}
            ts = e.reviewed_at or e.enrolled_at
            msg = {
                "id": f"my_enroll_{e.id}",
                "title": f"选课状态更新：「{e.course.name}」",
                "content": f"您的选课申请「{e.course.name}」当前状态：{status_map.get(e.status, e.status)}",
                "description": f"更新时间：{ts.strftime('%Y-%m-%d %H:%M') if ts else ''}",
                "createTime": ts.strftime("%Y-%m-%d %H:%M") if ts else "",
            }
            if e.status == "pending":
                unread.append(msg)
            else:
                read.append(msg)

    # Recent chat sessions (for all users)
    from chat.models import ChatSession
    recent_sessions = ChatSession.objects.filter(user=user).order_by("-updated_at")[:5]
    for s in recent_sessions:
        msg = {
            "id": f"session_{s.id}",
            "title": f"对话会话：{s.title}",
            "content": f"课程对话「{s.title}」有新的活动",
            "description": f"最后更新：{s.updated_at.strftime('%Y-%m-%d %H:%M') if s.updated_at else ''}",
            "createTime": s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else "",
        }
        read.append(msg)

    return make_response(data={"unread": unread, "read": read, "recycle": []})
