from rest_framework import serializers
from .models import ContextStrategy


class ContextStrategySerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()

    class Meta:
        model = ContextStrategy
        fields = ["id", "name", "description", "top_k", "similarity_threshold",
                  "chunk_size", "chunk_overlap", "max_context_tokens",
                  "include_memory", "include_history", "history_turns",
                  "rerank_enabled", "enable_query_rewrite", "compression_method",
                  "is_active", "is_default", "created_by", "creator_name",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ""
