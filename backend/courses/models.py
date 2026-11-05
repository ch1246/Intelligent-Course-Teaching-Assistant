from django.db import models
from django.conf import settings


class Course(models.Model):
    class SemesterType(models.TextChoices):
        FALL = "fall", "秋季学期 (9月-1月)"
        SPRING = "spring", "春季学期 (2月-7月)"

    name = models.CharField(max_length=200, verbose_name="课程名称")
    description = models.TextField(blank=True, default="", verbose_name="课程描述")
    cover_color = models.CharField(max_length=20, blank=True, default="#409EFF", verbose_name="封面颜色")
    cover_gradient = models.CharField(
        max_length=500, blank=True, default="",
        verbose_name="封面渐变",
        help_text="CSS 渐变，如 linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    )
    icon = models.CharField(
        max_length=100, blank=True, default="Notebook",
        verbose_name="卡片图标",
        help_text="Element Plus 图标名，如 School, Notebook, Reading 等"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="teaching_courses", verbose_name="授课教师"
    )
    chapters = models.PositiveIntegerField(default=0, verbose_name="章节数")
    max_students = models.PositiveIntegerField(default=60, verbose_name="最大学生数")
    college = models.CharField(max_length=100, blank=True, default="", verbose_name="学院")
    major = models.CharField(max_length=100, blank=True, default="", verbose_name="专业")
    grade = models.CharField(max_length=50, blank=True, default="", verbose_name="年级")

    # 学期范围
    semester = models.CharField(max_length=20, choices=SemesterType.choices, verbose_name="学期")
    year = models.PositiveIntegerField(verbose_name="学年", help_text="例如 2025 表示 2025-2026 学年")

    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "course"
        verbose_name = "课程"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    @property
    def enrolled_count(self):
        from enrollments.models import Enrollment
        return Enrollment.objects.filter(course=self, status="approved").count()

    def __str__(self):
        return self.name


def annotate_course_counts(queryset):
    """把列表页要用的三个计数一次性打进查询。

    列表页的 ``enrolled_count`` / ``files_count`` / ``total_messages`` 此前是
    序列化时逐行查库（每行 3 次 COUNT）——20 门课就是 60 次查询。这里用
    ``annotate`` + ``Count(distinct=True)`` 合成一条带 GROUP BY 的 SQL。

    ``distinct=True`` 是必须的：三个计数各自沿不同的多值关联展开，join 会
    让行数相乘，不去重就会算出虚高数字。

    序列化器优先读这些注解值；单条记录的详情视图不调用本函数时，序列化器会
    回落到逐条查询，行为不变。
    """
    from django.db.models import Count, Q

    return queryset.select_related("teacher").annotate(
        annotated_enrolled_count=Count(
            "enrollments",
            filter=Q(enrollments__status="approved"),
            distinct=True,
        ),
        annotated_files_count=Count("files", distinct=True),
        annotated_total_messages=Count("chat_sessions__messages", distinct=True),
    )


WEEKDAYS = [
    (1, "周一"), (2, "周二"), (3, "周三"), (4, "周四"),
    (5, "周五"), (6, "周六"), (7, "周日"),
]


class ScheduleSlot(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="schedule_slots", verbose_name="课程"
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS, verbose_name="星期")
    start_time = models.TimeField(verbose_name="开始时间")
    end_time = models.TimeField(verbose_name="结束时间")
    week_start = models.PositiveSmallIntegerField(default=1, verbose_name="起始周")
    week_end = models.PositiveSmallIntegerField(default=18, verbose_name="结束周")
    location = models.CharField(max_length=100, blank=True, default="", verbose_name="上课地点")

    class Meta:
        db_table = "schedule_slot"
        verbose_name = "上课时段"
        verbose_name_plural = verbose_name
        ordering = ["week_start", "weekday", "start_time"]

    def __str__(self):
        return f"{self.course.name} | {self.get_weekday_display()} {self.start_time}-{self.end_time} | 第{self.week_start}-{self.week_end}周"