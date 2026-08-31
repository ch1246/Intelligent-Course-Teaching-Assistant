from rest_framework import serializers
from .models import VectorCollection


class VectorCollectionSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = VectorCollection
        fields = ['id', 'name', 'course', 'course_name', 'embedding_model',
                  'document_count', 'chunk_count', 'vector_count', 'dimension',
                  'status', 'description', 'last_indexed_at', 'created_at']
        read_only_fields = ['id', 'document_count', 'chunk_count', 'vector_count',
                           'last_indexed_at', 'created_at']

    def get_course_name(self, obj):
        return obj.course.name
