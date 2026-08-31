from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
from rest_framework.decorators import api_view
from accounts.views import make_response
from accounts.models import User
from courses.models import Course
from chat.models import ChatSession, ChatMessage, UserMemory
from enrollments.models import Enrollment
from files_app.models import UploadedFile
from .models import LearningRecord


# ── Admin: global dashboard ───────────────────────────

@api_view(['GET'])
def admin_dashboard(request):
    if request.user.role not in (User.Role.ADMIN, User.Role.TEACHER):
        return make_response(code=403, message='无权限', http_status=403)
    today = timezone.now().date()
    return make_response(data={
        'user_count': User.objects.count(),
        'teacher_count': User.objects.filter(role=User.Role.TEACHER).count(),
        'student_count': User.objects.filter(role=User.Role.STUDENT).count(),
        'course_count': Course.objects.count(),
        'active_course_count': Course.objects.filter(is_active=True).count(),
        'file_count': UploadedFile.objects.count(),
        'today_chats': ChatMessage.objects.filter(created_at__date=today).count(),
        'total_messages': ChatMessage.objects.count(),
        'pending_enrollments': Enrollment.objects.filter(status='pending').count(),
        'system_days': (today - (Course.objects.order_by('created_at').first().created_at or today).date()).days if Course.objects.exists() and Course.objects.order_by('created_at').first() and Course.objects.order_by('created_at').first().created_at else 0,
    })


# ── Student: home stats ──────────────────────────────

@api_view(['GET'])
def student_home_stats(request):
    """Student-facing home stats: enrolled courses, learning minutes, messages, days."""
    course_count = request.user.enrollments.filter(status='approved').count()
    total_minutes = round(
        sum(r.duration_seconds for r in LearningRecord.objects.filter(user=request.user)) / 60, 1
    )
    total_messages = ChatMessage.objects.filter(session__user=request.user).count()
    days = (timezone.now().date() - request.user.date_joined.date()).days
    return make_response(data={
        'course_count': course_count,
        'total_minutes': total_minutes,
        'total_messages': total_messages,
        'system_days': max(0, days),
    })


# ── Course: dashboard ─────────────────────────────────

@api_view(['GET'])
def dashboard(request, course_id):
    """Course dashboard: stats for a course."""
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return make_response(code=404, message='课程不存在', http_status=404)

    student_count = Enrollment.objects.filter(course=course, status='approved').count()
    session_count = ChatSession.objects.filter(course=course).count()
    message_count = ChatMessage.objects.filter(session__course=course).count()
    today = timezone.now().date()
    today_record = LearningRecord.objects.filter(
        user=request.user, course=course, date=today
    ).first()

    # Total learning minutes for this user (stored as seconds)
    total_minutes = round(
        sum(r.duration_seconds for r in LearningRecord.objects.filter(user=request.user, course=course)) / 60, 1
    )

    # Progress: learning minutes / (chapters * 60 min per chapter), capped at 100
    if course.chapters > 0:
        progress = min(100, round(total_minutes / (course.chapters * 60) * 100))
    else:
        progress = 0

    # Last study time: most recent LearningRecord or chat session
    last_record = LearningRecord.objects.filter(
        user=request.user, course=course
    ).order_by("-date").first()
    last_session = ChatSession.objects.filter(
        user=request.user, course=course
    ).order_by("-updated_at").first()

    if last_record and last_session:
        last_dt = max(last_record.date, last_session.updated_at.date())
        last_study_time = str(last_dt)
    elif last_record:
        last_study_time = str(last_record.date)
    elif last_session:
        last_study_time = str(last_session.updated_at.date())
    else:
        last_study_time = ""

    return make_response(data={
        'course_name': course.name,
        'student_count': student_count,
        'session_count': session_count,
        'message_count': message_count,
        'file_count': UploadedFile.objects.filter(course=course).count(),
        'today_minutes': round(today_record.duration_seconds / 60, 1) if today_record else 0,
        'total_minutes': total_minutes,
        'progress': progress,
        'last_study_time': last_study_time,
    })


@api_view(['GET'])
def chat_stats(request, course_id):
    """Chat statistics for a course."""
    sessions = ChatSession.objects.filter(course_id=course_id)
    total_sessions = sessions.count()
    total_messages = ChatMessage.objects.filter(session__course_id=course_id).count()
    # Per-skill stats
    skill_stats = {}
    for skill in ChatSession.Skill.values:
        count = sessions.filter(skill=skill).count()
        skill_stats[skill] = {
            'label': dict(ChatSession.Skill.choices).get(skill, skill),
            'count': count,
        }
    # Last 7 days
    days = []
    for i in range(6, -1, -1):
        d = timezone.now().date() - timedelta(days=i)
        count = ChatMessage.objects.filter(
            session__course_id=course_id, created_at__date=d
        ).count()
        days.append({'date': str(d), 'count': count})

    total_questions = ChatMessage.objects.filter(
        session__course_id=course_id, role=ChatMessage.Role.USER
    ).count()

    return make_response(data={
        'total_sessions': total_sessions,
        'total_questions': total_questions,
        'total_messages': total_messages,
        'skill_stats': list(skill_stats.values()),
        'daily_stats': days,
    })


@api_view(['GET'])
def learning_time(request, course_id):
    """Get learning time for a course. Time is recorded automatically from real chat turns."""
    records = LearningRecord.objects.filter(
        user=request.user, course_id=course_id
    ).order_by('-date')[:30]
    total = round(sum(r.duration_seconds for r in records) / 60, 1)
    return make_response(data={
        'records': [
            {'date': str(r.date), 'duration_minutes': round(r.duration_seconds / 60, 1),
             'duration_seconds': r.duration_seconds}
            for r in records
        ],
        'total_minutes': total,
    })


@api_view(['POST'])
def course_summary(request, course_id):
    """Generate course learning summary (structured sections + recent sessions)."""
    try:
        course_obj = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return make_response(code=404, message='课程不存在', http_status=404)

    total_time = round(
        sum(r.duration_seconds for r in LearningRecord.objects.filter(user=request.user, course=course_obj)) / 60
    )
    chat_count = ChatSession.objects.filter(user=request.user, course=course_obj).count()
    msg_count = ChatMessage.objects.filter(
        session__user=request.user, session__course=course_obj
    ).count()

    summary_text = (
        f'你在《{course_obj.name}》课程中累计学习 {total_time} 分钟，'
        f'进行了 {chat_count} 次 AI 对话，发送了 {msg_count} 条消息。'
    )

    # ── Knowledge points & mastery from UserMemory ──
    memories = UserMemory.objects.filter(
        user=request.user, course=course_obj
    ).order_by('-mastery', '-question_count')
    resolved = [m.topic for m in memories if m.mastery >= 0.75]
    unresolved = [m.topic for m in memories if m.mastery < 0.5]
    knowledge_points = [m.topic for m in memories]

    # ── Recent sessions ─────────────────────────────
    recent_sessions = ChatSession.objects.filter(
        user=request.user, course=course_obj
    ).annotate(message_count=Count('messages')).order_by('-updated_at')[:5]
    recent_sessions_data = [
        {
            'id': s.id,
            'title': s.title,
            'date': s.updated_at.strftime('%Y-%m-%d'),
            'messages': s.message_count,
        }
        for s in recent_sessions
    ]

    return make_response(data={
        'course_name': course_obj.name,
        'total_learning_minutes': total_time,
        'total_chat_sessions': chat_count,
        'total_chat_messages': msg_count,
        'summary': summary_text,
        'sections': {
            'topic_summary': summary_text,
            'resolved_questions': resolved,
            'unresolved_questions': unresolved,
            'knowledge_points': knowledge_points,
        },
        'recent_sessions': recent_sessions_data,
    })


# ── Aggregated sidebar data ──────────────────────────

_SUGGESTION_TEMPLATES = [
    {
        "icon": "ep:edit-pen", "class": "sg-practice",
        "template": '针对"{}"知识点，建议完成 3 道相关习题巩固理解',
        "time": "建议 30 分钟",
    },
    {
        "icon": "ep:reading", "class": "sg-review",
        "template": '"{}"是核心考点，建议重新阅读教材对应章节',
        "time": "建议 20 分钟",
    },
    {
        "icon": "ep:video-camera", "class": "sg-preview",
        "template": '"{}"理解难度较高，可以搜索相关教学视频辅助学习',
        "time": "建议 15 分钟",
    },
    {
        "icon": "ep:trend-charts", "class": "sg-review",
        "template": '回顾"{}"相关知识点，尝试绘制思维导图串联知识体系',
        "time": "建议 25 分钟",
    },
    {
        "icon": "ep:question-filled", "class": "sg-practice",
        "template": '在 AI 对话中向助教提问"{}"相关问题，加深理解',
        "time": "建议 10 分钟",
    },
]




@api_view(["GET"])
def my_sidebar(request):
    """Return aggregated sidebar data: weak points, suggestions, papers across all enrolled courses."""
    enrollments = request.user.enrollments.filter(status="approved").select_related("course")
    courses = [e.course for e in enrollments]
    course_ids = [c.id for c in courses]

    if not courses:
        return make_response(data={"weak_points": [], "suggestions": [], "papers": []})

    # ── Weak points: aggregate UserMemory with mastery < 0.5 across all courses ──
    weak_memories = UserMemory.objects.filter(
        user=request.user, course_id__in=course_ids, mastery__lt=0.5
    ).order_by("mastery")[:15]
    weak_points = [m.topic for m in weak_memories]

    # ── Suggestions: rule-based from weak points ──
    suggestions = []
    if weak_points:
        for i, topic in enumerate(weak_points[:5]):
            tmpl = _SUGGESTION_TEMPLATES[i % len(_SUGGESTION_TEMPLATES)]
            suggestions.append({
                "icon": tmpl["icon"],
                "class": tmpl["class"],
                "title": tmpl["template"].format(topic),
                "time": tmpl["time"],
            })

    # ── Papers: uploaded files across enrolled courses ──
    uploaded = UploadedFile.objects.filter(
        course_id__in=course_ids
    ).select_related("course").order_by("-created_at")[:10]
    papers = []
    for f in uploaded:
        papers.append({
            "icon": "ep:document",
            "class": "pp-main",
            "title": f.original_name,
            "status": f.course.name if f.course else "",
            "time": f.created_at.strftime("%m-%d"),
        })

    return make_response(data={
        "weak_points": weak_points,
        "suggestions": suggestions,
        "papers": papers,
    })
