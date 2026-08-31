from rest_framework.decorators import api_view
from .models import Course
from .serializers import CourseSerializer
from accounts.views import make_response
from accounts.models import User


# ── Student: enrolled courses ─────────────────────────

@api_view(['GET'])
def my_courses(request):
    enrollments = request.user.enrollments.filter(status='approved').select_related('course')
    courses = [e.course for e in enrollments]
    ser = CourseSerializer(courses, many=True)
    return make_response(data=ser.data)


# ── Public: active course catalog (for enrollment) ───

@api_view(['GET'])
def course_catalog(request):
    """All active courses, visible to any authenticated user for enrollment."""
    qs = Course.objects.filter(is_active=True).order_by('-created_at')
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
        qs = Course.objects.all().order_by('-created_at')
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('pageSize', 20))
        search = request.GET.get('search', '')
        if search:
            qs = qs.filter(name__icontains=search)
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
        course.schedule_slots.all().delete()
        from .models import ScheduleSlot
        for slot in slots_data:
            ScheduleSlot.objects.create(
                course=course,
                weekday=slot.get("weekday", 1),
                start_time=slot.get("start_time", "08:00"),
                end_time=slot.get("end_time", "10:00"),
                week_start=slot.get("week_start", 1),
                week_end=slot.get("week_end", 18),
                location=slot.get("location", ""),
            )
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
    if request.method == 'GET':
        return make_response(data=CourseSerializer(course).data)
    elif request.method == 'PUT':
        ser = CourseSerializer(course, data=request.data, partial=True)
        if not ser.is_valid():
            return make_response(code=400, message=str(ser.errors), http_status=400)
        ser.save()
        slots_data = request.data.get("schedule_slots")
        if slots_data is not None:
            course.schedule_slots.all().delete()
            from .models import ScheduleSlot
            for slot in slots_data:
                ScheduleSlot.objects.create(
                    course=course,
                    weekday=slot.get("weekday", 1),
                    start_time=slot.get("start_time", "08:00"),
                    end_time=slot.get("end_time", "10:00"),
                    week_start=slot.get("week_start", 1),
                    week_end=slot.get("week_end", 18),
                    location=slot.get("location", ""),
                )
        course.refresh_from_db()
        return make_response(data=CourseSerializer(course).data)
    else:
        course.delete()
        return make_response(message='删除成功')
