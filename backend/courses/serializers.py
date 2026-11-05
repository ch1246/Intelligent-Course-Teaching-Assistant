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
        # 列表视图会走 annotate_course_counts() 注入该值（一条 GROUP BY 查全表）；
        # 详情视图没注解时回落到模型属性，逐条查。吞掉异常返回 0 会把「查不出」
        # 伪装成「没有」，所以这里不兜异常。
        annotated = getattr(obj, "annotated_enrolled_count", None)
        return obj.enrolled_count if annotated is None else annotated

    def get_files_count(self, obj):
        annotated = getattr(obj, "annotated_files_count", None)
        if annotated is not None:
            return annotated
        from files_app.models import UploadedFile
        return UploadedFile.objects.filter(course=obj).count()

    def get_total_messages(self, obj):
        annotated = getattr(obj, "annotated_total_messages", None)
        if annotated is not None:
            return annotated
        from chat.models import ChatMessage
        return ChatMessage.objects.filter(session__course=obj).count()
