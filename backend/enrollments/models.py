from django.db import models
from django.conf import settings


class Enrollment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', '待审核'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已拒绝'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments', verbose_name='学生'
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='enrollments', verbose_name='课程'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name='状态')
    review_comment = models.TextField(blank=True, default='', verbose_name='审核意见')
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')

    class Meta:
        db_table = 'enrollment'
        verbose_name = '选课记录'
        verbose_name_plural = verbose_name
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']

    def __str__(self):
        return f'{self.student.username} → {self.course.name}'
