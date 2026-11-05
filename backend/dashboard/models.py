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
        # 覆盖索引：学习时长相关的查询固定按 (用户, 课程) 过滤，再按 date 排序/取区间。
        # 把 date 与 duration_seconds 放进索引尾部，SUM 与列表查询都能走 "Using index"，
        # 既避免 index_merge 回表，也消除 ORDER BY date DESC 的 filesort。
        indexes = [
            models.Index(
                fields=['user', 'course', 'date', 'duration_seconds'],
                name='idx_lr_user_course_date_dur',
            ),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.course.name} - {self.date}'
