from django.db import models
from django.conf import settings


class RAGPipeline(models.Model):
    """RAG 管道 — 模板 + 策略 + 模型 = 命名管道"""

    name = models.CharField(max_length=200, verbose_name="管道名称")
    description = models.TextField(blank=True, default="", verbose_name="管道说明")
    prompt_template = models.ForeignKey(
        "prompt_engine.PromptTemplate", on_delete=models.PROTECT,
        related_name="pipelines", verbose_name="提示词模板"
    )
    context_strategy = models.ForeignKey(
        "context_engine.ContextStrategy", on_delete=models.PROTECT,
        related_name="pipelines", verbose_name="上下文策略"
    )
    agent_config = models.ForeignKey(
        "settings_app.AgentAPIConfig", on_delete=models.PROTECT,
        related_name="pipelines", verbose_name="Agent API 配置"
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    is_default = models.BooleanField(default=False, verbose_name="是否默认管道")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="rag_pipelines", verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "rag_pipeline"
        verbose_name = "RAG 管道"
        verbose_name_plural = verbose_name
        ordering = ["-is_default", "-updated_at"]

    def __str__(self):
        return self.name


class TraceLog(models.Model):
    """RAG 链路追踪日志"""

    class Phase(models.TextChoices):
        RETRIEVE = "retrieve", "检索"
        BUILD_PROMPT = "build_prompt", "组装提示词"
        GENERATE = "generate", "生成"
        MEMORY = "memory", "记忆更新"

    session = models.ForeignKey(
        "chat.ChatSession", on_delete=models.CASCADE,
        related_name="trace_logs", verbose_name="会话"
    )
    pipeline = models.ForeignKey(
        RAGPipeline, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="trace_logs", verbose_name="管道"
    )
    phase = models.CharField(
        max_length=20, choices=Phase.choices, verbose_name="阶段"
    )
    duration_ms = models.FloatField(default=0, verbose_name="耗时(ms)")
    detail = models.JSONField(default=dict, verbose_name="详情")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "trace_log"
        verbose_name = "链路追踪"
        verbose_name_plural = verbose_name
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.session_id} / {self.phase} ({self.duration_ms:.0f}ms)"
