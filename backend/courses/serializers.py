from datetime import datetime

from rest_framework import serializers
from .models import Course, ScheduleSlot


class ScheduleSlotSerializer(serializers.ModelSerializer):
    weekday_label = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleSlot
        fields = ["id", "weekday", "weekday_label", "start_time", "end_time",
                  "week_start", "week_end", "location"]

    def get_weekday_label(self, obj):
        return obj.get_weekday_display()


class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()
    schedule_slots = ScheduleSlotSerializer(many=True, read_only=True)
    files_count = serializers.SerializerMethodField()
    total_messages = serializers.SerializerMethodField()
    # 提供默认值，避免通过 API 创建课程时因缺 semester/year 而失败
    semester = serializers.ChoiceField(choices=Course.SemesterType.choices, default=Course.SemesterType.FALL)
    year = serializers.IntegerField(default=lambda: datetime.now().year)

    class Meta:
        model = Course
        fields = [
            "id", "name", "description", "cover_color", "cover_gradient", "icon",
            "teacher", "teacher_name", "chapters", "max_students", "enrolled_count",
            "college", "major", "grade", "semester", "year",
            "files_count", "total_messages",
            "schedule_slots",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "enrolled_count"]

    def get_teacher_name(self, obj):
        return obj.teacher.username if obj.teacher else ""

    def get_enrolled_count(self, obj):
        try:
            return obj.enrolled_count
        except Exception:
            return 0

    def get_files_count(self, obj):
        try:
            from files_app.models import UploadedFile
            return UploadedFile.objects.filter(course=obj).count()
        except Exception:
            return 0

    def get_total_messages(self, obj):
        try:
            from chat.models import ChatMessage
            return ChatMessage.objects.filter(session__course=obj).count()
        except Exception:
            return 0
