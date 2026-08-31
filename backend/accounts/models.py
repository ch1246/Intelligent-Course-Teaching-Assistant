from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "管理员"
        TEACHER = "teacher", "教师"
        STUDENT = "student", "学生"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, verbose_name="角色")
    student_id = models.CharField(max_length=30, blank=True, null=True, default=None, unique=True, verbose_name="学号")
    phone = models.CharField(max_length=20, blank=True, default="", verbose_name="手机号")
    avatar = models.CharField(max_length=500, blank=True, default="", verbose_name="头像")
    signature = models.CharField(max_length=200, blank=True, default="", verbose_name="个性签名")
    sex = models.CharField(max_length=10, blank=True, default="", verbose_name="性别")
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name="年龄")
    dept = models.CharField(max_length=100, blank=True, default="", verbose_name="学院")
    major = models.CharField(max_length=100, blank=True, default="", verbose_name="专业")
    grade = models.CharField(max_length=50, blank=True, default="", verbose_name="年级")
    is_approved = models.BooleanField(default=False, verbose_name="审核通过")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")
    approved_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_users", verbose_name="审核人"
    )

    class Meta:
        db_table = "accounts_user"
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.username}({self.get_role_display()})"