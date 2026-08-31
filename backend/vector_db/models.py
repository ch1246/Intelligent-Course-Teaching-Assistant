from django.db import models


class VectorCollection(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', '活跃'
        INDEXING = 'indexing', '索引中'
        ERROR = 'error', '错误'

    name = models.CharField(max_length=200, verbose_name='集合名称')
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='vector_collections', verbose_name='所属课程'
    )
    embedding_model = models.CharField(
        max_length=100, default='bge-large-zh-v1.5', verbose_name='嵌入模型'
    )
    document_count = models.PositiveIntegerField(default=0, verbose_name='文档数')
    chunk_count = models.PositiveIntegerField(default=0, verbose_name='分块数')
    vector_count = models.PositiveIntegerField(default=0, verbose_name='向量数')
    dimension = models.PositiveIntegerField(default=1024, verbose_name='向量维度')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name='状态')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    last_indexed_at = models.DateTimeField(null=True, blank=True, verbose_name='上次索引时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'vector_collection'
        verbose_name = '向量集合'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.course.name})'
