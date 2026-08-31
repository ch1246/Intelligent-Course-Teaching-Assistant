from rest_framework import serializers
from .models import PromptTemplate, PromptVersion


class PromptVersionSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()

    class Meta:
        model = PromptVersion
        fields = ["id", "template", "version", "content", "variables",
                  "change_note", "created_by", "creator_name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ""


class PromptTemplateListSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()

    class Meta:
        model = PromptTemplate
        fields = ["id", "name", "description", "skill", "version",
                  "is_active", "is_default", "created_by", "creator_name",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "version", "created_at", "updated_at"]

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ""


class PromptTemplateDetailSerializer(serializers.ModelSerializer):
    versions = PromptVersionSerializer(many=True, read_only=True)
    creator_name = serializers.SerializerMethodField()

    class Meta:
        model = PromptTemplate
        fields = ["id", "name", "description", "skill", "content",
                  "variables", "version", "is_active", "is_default",
                  "created_by", "creator_name", "versions",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "version", "created_at", "updated_at"]

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ""


class PromptPreviewSerializer(serializers.Serializer):
    """预览渲染请求"""
    variables = serializers.DictField(required=False, default=dict)
