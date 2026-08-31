from rest_framework import serializers
from .models import UploadedFile


class UploadedFileSerializer(serializers.ModelSerializer):
    uploader_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = ['id', 'original_name', 'stored_path', 'file_size', 'mime_type',
                  'course', 'course_name', 'uploader', 'uploader_name', 'is_vectorized', 'created_at']
        read_only_fields = ['id', 'created_at', 'uploader_name']

    def get_uploader_name(self, obj):
        return obj.uploader.username if obj.uploader else ''

    def get_course_name(self, obj):
        return obj.course.name if obj.course else ''
