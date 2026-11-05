from django.db import models

from services.rag_service import collection_name_for_course


class VectorCollection(models.Model):
    """课程知识库记录。

    **一门课一个知识库**：Chroma 的物理集合名由 ``collection_name`` 唯一决定
    （``course_{course_id}``），与本表的 ``name`` 字段无关 —— ``name`` 只是给
    人看的展示名。

    早期版本没有这层约束，同一门课可以建多条记录，而它们全都映射到**同一个**
    物理集合：删掉其中任意一条记录就会把整门课的向量库清空，reindex 也会互相
    覆盖。这里用数据库唯一约束把该故障模式从结构上排除掉。
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', '活跃'
        INDEXING = 'indexing', '索引中'
        ERROR = 'error', '错误'

    name = models.CharField(max_length=200, verbose_name='集合名称（展示名）')
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
        constraints = [
            models.UniqueConstraint(fields=['course'], name='uniq_vector_collection_per_course'),
        ]

    @property
    def collection_name(self) -> str:
        """Chroma 物理集合名。全项目唯一出处在 services.rag_service。"""
        return collection_name_for_course(self.course_id)

    def __str__(self):
        return f'{self.name} ({self.course.name})'
