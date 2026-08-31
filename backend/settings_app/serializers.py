from rest_framework import serializers
from .models import SystemSetting, AgentAPIConfig


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ["id", "key", "value", "description", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class AgentAPIConfigSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()
    strategy_name = serializers.SerializerMethodField()

    class Meta:
        model = AgentAPIConfig
        fields = ["id", "name", "base_url", "api_key", "model_list",
                  "default_model", "system_prompt", "prompt_template",
                  "template_name", "context_strategy", "strategy_name",
                  "is_active", "is_default",
                  "created_by", "creator_name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]
        extra_kwargs = {
            "api_key": {"write_only": True},
        }

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ""

    def get_template_name(self, obj):
        return obj.prompt_template.name if obj.prompt_template else ""

    def get_strategy_name(self, obj):
        return obj.context_strategy.name if obj.context_strategy else ""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Replace api_key with masked version in responses
        raw = instance.get_api_key()
        if raw:
            data["api_key"] = "sk-****" + raw[-4:] if len(raw) > 4 else "****"
        else:
            data["api_key"] = ""
        return data

    def create(self, validated_data):
        plaintext_key = validated_data.pop("api_key", "")
        instance = super().create(validated_data)
        if plaintext_key:
            instance.set_api_key(plaintext_key)
            instance.save(update_fields=["api_key"])
        return instance

    def update(self, instance, validated_data):
        plaintext_key = validated_data.pop("api_key", None)
        instance = super().update(instance, validated_data)
        if plaintext_key is not None and plaintext_key != "":
            # Only update if a new plaintext key was provided
            instance.set_api_key(plaintext_key)
            instance.save(update_fields=["api_key"])
        return instance
