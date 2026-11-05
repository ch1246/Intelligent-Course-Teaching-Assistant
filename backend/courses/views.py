from rest_framework.decorators import api_view
from .models import Course, annotate_course_counts
from services.pagination import parse_paging
from services.search import search_filter
from .serializers import CourseSerializer
from accounts.views import make_response
from accounts.models import User


def _is_course_owner(user, course) -> bool:
    """权限判断：admin 可操作全部课程；teacher 只能操作自己授课的课程。

    此前只校验了 role ∈ {admin, teacher}，任何教师都能改/删别人的课程。
    """
    if user.role == User.Role.ADMIN:
        return True
    return course.teacher_id == user.id


def _replace_schedule_slots(course, slots_data) -> None:
    """整体替换课程的上课时段：先校验，再在单个事务里「删旧 + 建新」。

    旧实现是无事务的两步（先 delete 再逐条 create），中途任何一条 insert
    抛错，这门课的全部上课时段就直接丢光。同时补上此前完全缺失的参数校验：
    星期、周次、时间先后关系。
    """
    from django.db import transaction
    from django.utils.dateparse import parse_time
    from .models import ScheduleSlot

    cleaned = []
    for i, slot in enumerate(slots_data, start=1):
        try:
            weekday = int(slot.get("weekday", 1))
            week_start = int(slot.get("week_start", 1))
            week_end = int(slot.get("week_end", 18))
        except (TypeError, ValueError):
            raise ValueError(f"第 {i} 个时段：weekday / week_start / week_end 必须是整数")

        start = parse_time(str(slot.get("start_time", "08:00")))
        end = parse_time(str(slot.get("end_time", "10:00")))
        if start is None or end is None:
            raise ValueError(f"第 {i} 个时段：时间格式非法，应为 HH:MM")
        if weekday not in range(1, 8):
            raise ValueError(f"第 {i} 个时段：weekday 必须在 1-7 之间")
        if not (1 <= week_start <= week_end <= 30):
            raise ValueError(f"第 {i} 个时段：周次范围非法（需满足 1 <= 起始周 <= 结束周 <= 30）")
        if start >= end:
            raise ValueError(f"第 {i} 个时段：开始时间必须早于结束时间")

        cleaned.append(ScheduleSlot(
            course=course, weekday=weekday,
            start_time=start, end_time=end,
            week_start=week_start, week_end=week_end,
            location=slot.get("location", "") or "",
        ))

    with transaction.atomic():
        course.schedule_slots.all().delete()
        ScheduleSlot.objects.bulk_create(cleaned)


# ── Student: enrolled courses ─────────────────────────

@api_view(['GET'])
def my_courses(request):
    # 用 pk__in 子查询而不是 join 过滤：若在 WHERE 里关联 enrollments，会把
    # annotate 的聚合值也一起污染（只统计到匹配的那条选课记录）。
    # 全程 2 条 SQL，替代旧实现的「取选课 + 逐门 3 次 COUNT」。
    course_ids = request.user.enrollments.filter(status='approved').values_list('course_id', flat=True)
    courses = annotate_course_counts(Course.objects.filter(pk__in=course_ids))
    return make_response(data=CourseSerializer(courses, many=True).data)


# ── Public: active course catalog (for enrollment) ───

@api_view(['GET'])
def course_catalog(request):
    """All active courses, visible to any authenticated user for enrollment."""
    qs = annotate_course_counts(Course.objects.filter(is_active=True).order_by('-created_at'))
    return make_response(data=CourseSerializer(qs, many=True).data)


# ── Public: course detail ─────────────────────────────

@api_view(['GET'])
def course_detail(request, pk):
    try:
        course = Course.objects.get(pk=pk)
    except Course.DoesNotExist:
        return make_response(code=404, message='课程不存在', http_status=404)
    return make_response(data=CourseSerializer(course).data)



# ── Teacher list for dropdown ─────────────────────────

@api_view(["GET"])
def teacher_list(request):
    """Return list of teachers for course creation dropdown."""
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message="无权限", http_status=403)
    teachers = User.objects.filter(role__in=(User.Role.TEACHER, User.Role.ADMIN)).values("id", "username")
    return make_response(data=list(teachers))


# ── Admin: course CRUD ────────────────────────────────

@api_view(['GET', 'POST'])
def admin_course_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message='无权限', http_status=403)
    if request.method == 'GET':
        qs = annotate_course_counts(Course.objects.all().order_by('-created_at'))
        # 教师只看自己授课的课程；管理员看全部
        if request.user.role == User.Role.TEACHER:
            qs = qs.filter(teacher=request.user)
        page, size = parse_paging(request)
        search = request.GET.get('search', '')
        if search:
            qs = search_filter(qs, search, "course")
        status = request.GET.get('status', '')
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'archived':
            qs = qs.filter(is_active=False)
        total = qs.count()
        courses = qs[(page - 1) * size: page * size]
        return make_response(data={
            'list': CourseSerializer(courses, many=True).data,
            'total': total, 'page': page, 'pageSize': size,
        })
    ser = CourseSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    course = ser.save()
    # 保存上课时段
    slots_data = request.data.get("schedule_slots")
    if slots_data is not None:
        try:
            _replace_schedule_slots(course, slots_data)
        except ValueError as e:
            course.delete()
            return make_response(code=400, message=str(e), http_status=400)
    course.refresh_from_db()
    return make_response(data=CourseSerializer(course).data)


@api_view(['GET', 'PUT', 'DELETE'])
def admin_course_detail(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message='无权限', http_status=403)
    try:
        course = Course.objects.get(pk=pk)
    except Course.DoesNotExist:
        return make_response(code=404, message='课程不存在', http_status=404)
    # 归属校验：教师只能查看/修改/删除自己授课的课程
    if not _is_course_owner(request.user, course):
        return make_response(code=403, message='无权操作其他教师的课程', http_status=403)
    if request.method == 'GET':
        return make_response(data=CourseSerializer(course).data)
    elif request.method == 'PUT':
        ser = CourseSerializer(course, data=request.data, partial=True)
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        ser.save()
        slots_data = request.data.get("schedule_slots")
        if slots_data is not None:
            try:
                _replace_schedule_slots(course, slots_data)
            except ValueError as e:
                return make_response(code=400, message=str(e), http_status=400)
        course.refresh_from_db()
        return make_response(data=CourseSerializer(course).data)
    else:
        course.delete()
        return make_response(message='删除成功')
