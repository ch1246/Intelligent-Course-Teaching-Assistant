from rest_framework import serializers
from .models import UploadedFile


class UploadedFileSerializer(serializers.ModelSerializer):
    uploader_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        # 注意：不再输出 stored_path —— 它是服务器绝对路径，属于信息泄露。
        # 需要下载能力时另加受鉴权的下载接口，而不是把磁盘路径交给前端。
        fields = ['id', 'original_name', 'file_size', 'mime_type',
                  'course', 'course_name', 'uploader', 'uploader_name', 'is_vectorized', 'created_at']
        read_only_fields = ['id', 'created_at', 'uploader_name']

    def get_uploader_name(self, obj):
        return obj.uploader.username if obj.uploader else ''

    def get_course_name(self, obj):
        return obj.course.name if obj.course else ''
