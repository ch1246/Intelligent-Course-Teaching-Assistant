import random
import string
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import models, IntegrityError
from .models import User
from .serializers import (
    UserSerializer, LoginSerializer, RegisterSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, UserUpdateSerializer,
)


def make_response(data=None, code=200, message="success", http_status=200):
    return Response({"code": code, "status": "ok" if code == 200 else "error", "message": message, "data": data}, status=http_status)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"accessToken": str(refresh.access_token), "refreshToken": str(refresh)}


def _generate_temp_password(length: int = 10) -> str:
    """Generate a random temporary password."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


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
        role=d.get("role", User.Role.STUDENT),
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
def refresh_token(request):
    refresh = request.data.get("refreshToken", "")
    if not refresh:
        return make_response(code=400, message="缺少 refreshToken", http_status=400)
    try:
        token = RefreshToken(refresh)
        return make_response(data={"accessToken": str(token.access_token), "refreshToken": str(token)})
    except Exception:
        return make_response(code=401, message="Token 无效或已过期", http_status=401)

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

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def forgot_password(request):
    ser = ForgotPasswordSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    email = ser.validated_data["email"]
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # 不暴露该邮箱是否已注册
        return make_response(message="如果该邮箱已注册，临时密码已发送，请查收")
    temp_password = _generate_temp_password()
    user.set_password(temp_password)
    user.save()
    # TODO: 接入邮件服务发送临时密码邮件
    # send_mail("密码重置", f"您的临时密码为：{temp_password}，请登录后尽快修改密码。", settings.DEFAULT_FROM_EMAIL, [email])
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[forgot_password] 用户 {user.username} 临时密码已生成 (未发送邮件，需配置 EMAIL_BACKEND)")
    return make_response(message="如果该邮箱已注册，临时密码已发送，请查收")

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
    page = max(1, int(request.GET.get("page", 1)))
    size = max(1, min(100, int(request.GET.get("pageSize", 20))))
    search = request.GET.get("search", "")
    if search:
        qs = qs.filter(models.Q(username__icontains=search) | models.Q(student_id__icontains=search) | models.Q(dept__icontains=search))
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
    """Admin: reject/delete a registration."""
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    try:
        user = User.objects.get(pk=pk, role=User.Role.STUDENT)
    except User.DoesNotExist:
        return make_response(code=404, message="用户不存在", http_status=404)
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
    """Admin: batch import students from CSV or xlsx."""
    if request.user.role != User.Role.ADMIN:
        return make_response(code=403, message="无权限", http_status=403)
    file = request.FILES.get("file")
    if not file:
        return make_response(code=400, message="请上传文件", http_status=400)

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
                role=User.Role.STUDENT, is_approved=True
            )
            created += 1
        except Exception as e:
            errors.append(f"第{i+2}行: {str(e)}")
            skipped += 1

    return make_response(data={
        "created": created, "skipped": skipped, "errors": errors[:10],
        "total_rows": len(rows),
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
        page = max(1, int(request.GET.get("page", 1)))
        size = max(1, min(100, int(request.GET.get("pageSize", 20))))
        search = request.GET.get("search", "")
        if search:
            qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search) | Q(student_id__icontains=search))
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
def message_list(request):
    return make_response(data={"unread": [], "read": [], "recycle": [], "total": 0, "unreadCount": 0})

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_menu_list(request):
    role = request.user.role
    all_menus = [
        {"menuCode": "home", "menuName": "首页", "menuUrl": "/home", "pagePath": "/home", "parentMenuCode": "", "seq": 1, "imageIcon": ""},
        {"menuCode": "workbenches", "menuName": "工作台", "menuUrl": "/workbenches", "pagePath": "/workbenches", "parentMenuCode": "", "seq": 2, "imageIcon": ""},
        {"menuCode": "course-management", "menuName": "课程管理", "menuUrl": "", "pagePath": "", "parentMenuCode": "", "seq": 3, "imageIcon": ""},
    ]
    if role == "student":
        all_menus += [
            {"menuCode": "my-courses", "menuName": "我的课程", "menuUrl": "/course/dashboard", "pagePath": "/course/dashboard", "parentMenuCode": "course-management", "seq": 1, "imageIcon": ""},
            {"menuCode": "course-enroll", "menuName": "选课中心", "menuUrl": "/course/enroll", "pagePath": "/course/enroll", "parentMenuCode": "course-management", "seq": 2, "imageIcon": ""},
        ]
    if role in ("admin", "teacher"):
        all_menus += [
            {"menuCode": "admin-center", "menuName": "管理中心", "menuUrl": "/admin/dashboard", "pagePath": "/admin/dashboard", "parentMenuCode": "", "seq": 99, "imageIcon": ""},
        ]
    return make_response(data=all_menus)


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
