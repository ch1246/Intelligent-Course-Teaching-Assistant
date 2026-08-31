from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    class Skill(models.TextChoices):
        QA = "qa", "智能问答"
        FORMULA = "formula", "公式推导"
        CODE_DEBUG = "code_debug", "代码调试"
        LAB_GUIDE = "lab_guide", "实验指导"
        PAPER_READER = "paper_reader", "论文阅读"

    title = models.CharField(max_length=200, verbose_name="会话标题")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions", verbose_name="用户"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="chat_sessions", verbose_name="课程"
    )
    skill = models.CharField(max_length=30, choices=Skill.choices, default=Skill.QA, verbose_name="技能")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "chat_session"
        verbose_name = "对话会话"
        verbose_name_plural = verbose_name
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "用户"
        ASSISTANT = "assistant", "助手"

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages", verbose_name="会话"
    )
    role = models.CharField(max_length=10, choices=Role.choices, verbose_name="角色")
    content = models.TextField(verbose_name="内容")
    sources = models.TextField(blank=True, default="", verbose_name="引用来源")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "chat_message"
        verbose_name = "对话消息"
        verbose_name_plural = verbose_name
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"


class UserMemory(models.Model):
    """User knowledge mastery tracking — 用户知识点记忆"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memories", verbose_name="用户"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="user_memories", verbose_name="课程"
    )
    topic = models.CharField(max_length=200, verbose_name="知识点")
    mastery = models.FloatField(default=0.5, verbose_name="掌握程度 (0-1)")
    question_count = models.PositiveIntegerField(default=1, verbose_name="提问次数")
    last_asked_at = models.DateTimeField(auto_now=True, verbose_name="最近提问")
    notes = models.TextField(blank=True, default="", verbose_name="AI 备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "user_memory"
        verbose_name = "用户记忆"
        verbose_name_plural = verbose_name
        ordering = ["-last_asked_at"]
        unique_together = ["user", "course", "topic"]

    def __str__(self):
        return f"{self.user.username} / {self.course.name} / {self.topic} ({self.mastery:.0%})"
