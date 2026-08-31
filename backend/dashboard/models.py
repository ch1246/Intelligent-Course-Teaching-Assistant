from django.db import models
from django.conf import settings


class LearningRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_records', verbose_name='用户'
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='learning_records', verbose_name='课程'
    )
    date = models.DateField(verbose_name='日期')
    duration_seconds = models.PositiveIntegerField(default=0, verbose_name='学习时长(秒)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'learning_record'
        verbose_name = '学习记录'
        verbose_name_plural = verbose_name
        ordering = ['-date']

    def __str__(self):
        return f'{self.user.username} - {self.course.name} - {self.date}'
