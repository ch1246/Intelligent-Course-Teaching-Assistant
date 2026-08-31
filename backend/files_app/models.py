from django.db import models
from django.conf import settings


class UploadedFile(models.Model):
    original_name = models.CharField(max_length=500, verbose_name="原始文件名")
    stored_path = models.CharField(max_length=500, verbose_name="存储路径")
    file_size = models.PositiveBigIntegerField(default=0, verbose_name="文件大小")
    mime_type = models.CharField(max_length=100, blank=True, default="", verbose_name="文件类型")
    course = models.ForeignKey(
        "courses.Course", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="files", verbose_name="所属课程"
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_files", verbose_name="上传者"
    )
    is_vectorized = models.BooleanField(default=False, verbose_name="是否已向量化")
    summary = models.TextField(blank=True, default="", verbose_name="AI 摘要")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        db_table = "uploaded_file"
        verbose_name = "上传文件"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name
