from django.db import models
from django.conf import settings


class ContextStrategy(models.Model):
    """上下文组装策略 — Context Engineering core."""

    name = models.CharField(max_length=200, verbose_name="策略名称")
    description = models.TextField(blank=True, default="", verbose_name="策略说明")

    # ── 检索参数 ──
    top_k = models.PositiveSmallIntegerField(default=5, verbose_name="检索返回数")
    similarity_threshold = models.FloatField(
        default=0.0, verbose_name="相似度阈值 (0-1)"
    )

    # ── 分块参数 ──
    chunk_size = models.PositiveIntegerField(default=500, verbose_name="分块大小")
    chunk_overlap = models.PositiveIntegerField(default=50, verbose_name="分块重叠")

    # ── 上下文预算 ──
    max_context_tokens = models.PositiveIntegerField(
        default=3000, verbose_name="上下文Token上限"
    )

    # ── 内容开关 ──
    include_memory = models.BooleanField(default=True, verbose_name="注入学生画像")
    include_history = models.BooleanField(default=True, verbose_name="包含对话历史")
    history_turns = models.PositiveSmallIntegerField(
        default=10, verbose_name="历史轮数"
    )

    # ── 高级选项 ──
    rerank_enabled = models.BooleanField(default=False, verbose_name="启用重排")
    enable_query_rewrite = models.BooleanField(
        default=False, verbose_name="启用查询改写"
    )

    # ── 压缩设置 ──
    compression_method = models.CharField(
        max_length=20,
        choices=[("truncate", "截断"), ("summarize", "LLM 摘要")],
        default="truncate",
        verbose_name="压缩方式",
    )

    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    is_default = models.BooleanField(default=False, verbose_name="是否默认策略")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="context_strategies", verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "context_strategy"
        verbose_name = "上下文策略"
        verbose_name_plural = verbose_name
        ordering = ["-is_default", "-updated_at"]

    def __str__(self):
        return self.name
