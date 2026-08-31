from rest_framework import serializers
from .models import RAGPipeline, TraceLog


class RAGPipelineListSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()
    strategy_name = serializers.SerializerMethodField()
    agent_config_name = serializers.SerializerMethodField()

    class Meta:
        model = RAGPipeline
        fields = ["id", "name", "description", "prompt_template", "template_name",
                  "context_strategy", "strategy_name", "agent_config", "agent_config_name",
                  "is_active", "is_default", "created_by", "creator_name",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ""

    def get_template_name(self, obj):
        return obj.prompt_template.name if obj.prompt_template else ""

    def get_strategy_name(self, obj):
        return obj.context_strategy.name if obj.context_strategy else ""

    def get_agent_config_name(self, obj):
        return obj.agent_config.name if obj.agent_config else ""


class RAGPipelineDetailSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()
    strategy_name = serializers.SerializerMethodField()
    agent_config_name = serializers.SerializerMethodField()
    template_content = serializers.SerializerMethodField()
    strategy_detail = serializers.SerializerMethodField()

    class Meta:
        model = RAGPipeline
        fields = ["id", "name", "description", "prompt_template", "template_name",
                  "template_content", "context_strategy", "strategy_name",
                  "strategy_detail", "agent_config", "agent_config_name",
                  "is_active", "is_default", "created_by", "creator_name",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ""

    def get_template_name(self, obj):
        return obj.prompt_template.name if obj.prompt_template else ""

    def get_strategy_name(self, obj):
        return obj.context_strategy.name if obj.context_strategy else ""

    def get_agent_config_name(self, obj):
        return obj.agent_config.name if obj.agent_config else ""

    def get_template_content(self, obj):
        return obj.prompt_template.content if obj.prompt_template else ""

    def get_strategy_detail(self, obj):
        if not obj.context_strategy:
            return None
        from context_engine.serializers import ContextStrategySerializer
        return ContextStrategySerializer(obj.context_strategy).data


class TraceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TraceLog
        fields = ["id", "session", "pipeline", "phase", "duration_ms",
                  "detail", "created_at"]
        read_only_fields = ["id", "created_at"]
