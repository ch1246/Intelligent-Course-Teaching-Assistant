from rest_framework.decorators import api_view
from django.utils import timezone
from .models import Enrollment
from .serializers import EnrollmentSerializer
from accounts.views import make_response
from accounts.models import User
from courses.models import Course


# ── Student: enroll ───────────────────────────────────

@api_view(['GET', 'POST'])
def enroll(request):
    """Student views their enrollments or enrolls in a course."""
    if request.method == 'GET':
        qs = request.user.enrollments.select_related('course').order_by('-enrolled_at')
        return make_response(data=EnrollmentSerializer(qs, many=True).data)
    # POST: enroll
    course_id = request.data.get('course_id')
    if not course_id:
        return make_response(code=400, message='缺少 course_id', http_status=400)
    try:
        course = Course.objects.get(pk=course_id, is_active=True)
    except Course.DoesNotExist:
        return make_response(code=404, message='课程不存在', http_status=404)
    if Enrollment.objects.filter(student=request.user, course=course).exists():
        return make_response(code=400, message='已申请过该课程', http_status=400)
    enrollment = Enrollment.objects.create(student=request.user, course=course)
    return make_response(data=EnrollmentSerializer(enrollment).data)


# ── Admin: enrollment review ──────────────────────────

@api_view(['GET'])
def admin_enroll_list(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message='无权限', http_status=403)
    qs = Enrollment.objects.select_related('student', 'course').order_by('-enrolled_at')
    status_filter = request.GET.get('status', '')
    if status_filter and status_filter not in ('', 'undefined', 'null'):
        qs = qs.filter(status=status_filter)
    try:
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('pageSize', 20))
    except (ValueError, TypeError):
        page, size = 1, 20
    total = qs.count()
    data = qs[(page - 1) * size: page * size]
    return make_response(data={
        'list': EnrollmentSerializer(data, many=True).data,
        'total': total, 'page': page, 'pageSize': size,
    })


@api_view(['PUT'])
def admin_enroll_review(request, pk):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message='无权限', http_status=403)
    try:
        enrollment = Enrollment.objects.get(pk=pk)
    except Enrollment.DoesNotExist:
        return make_response(code=404, message='记录不存在', http_status=404)
    status = request.data.get('status', '')
    if status not in ('approved', 'rejected'):
        return make_response(code=400, message='状态值无效', http_status=400)
    enrollment.status = status
    enrollment.review_comment = request.data.get('review_comment', '')
    enrollment.reviewed_at = timezone.now()
    enrollment.save()
    return make_response(data=EnrollmentSerializer(enrollment).data)
