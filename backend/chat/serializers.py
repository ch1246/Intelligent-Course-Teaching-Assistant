from rest_framework import serializers
from .models import ChatSession, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'role', 'content', 'sources', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'user', 'course', 'skill', 'messages',
                  'message_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatCreateSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    skill = serializers.ChoiceField(choices=ChatSession.Skill.choices, default=ChatSession.Skill.QA)
    title = serializers.CharField(default='新对话')


class ChatCompletionSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    message = serializers.CharField()
    # 可选：省略时以会话自身的 skill 为准（chat_completions 兜底），
    # 显式传入时才覆盖 —— 避免默认值 "qa" 与 session.skill 漂移
    skill = serializers.ChoiceField(
        choices=ChatSession.Skill.choices, required=False, allow_null=True, default=None,
    )
