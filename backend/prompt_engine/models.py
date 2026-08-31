from django.db import models
from django.conf import settings


class PromptTemplate(models.Model):
    """提示词模板 — Prompt Engineering core."""

    class Skill(models.TextChoices):
        QA = "qa", "智能问答"
        FORMULA = "formula", "公式推导"
        CODE_DEBUG = "code_debug", "代码调试"
        LAB_GUIDE = "lab_guide", "实验指导"
        PAPER_READER = "paper_reader", "论文阅读"

    name = models.CharField(max_length=200, verbose_name="模板名称")
    description = models.TextField(blank=True, default="", verbose_name="用途说明")
    skill = models.CharField(
        max_length=30, choices=Skill.choices, default=Skill.QA, verbose_name="绑定技能"
    )
    content = models.TextField(verbose_name="模板内容（Jinja2）")
    variables = models.JSONField(default=dict, verbose_name="变量定义")
    version = models.PositiveIntegerField(default=1, verbose_name="版本号")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    is_default = models.BooleanField(default=False, verbose_name="是否默认模板")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="prompt_templates", verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "prompt_template"
        verbose_name = "提示词模板"
        verbose_name_plural = verbose_name
        ordering = ["-is_default", "-updated_at"]

    def __str__(self):
        return f"{self.name} (v{self.version})"


class PromptVersion(models.Model):
    """提示词版本历史"""

    template = models.ForeignKey(
        PromptTemplate, on_delete=models.CASCADE, related_name="versions", verbose_name="所属模板"
    )
    version = models.PositiveIntegerField(verbose_name="版本号")
    content = models.TextField(verbose_name="模板内容")
    variables = models.JSONField(default=dict, verbose_name="变量定义")
    change_note = models.CharField(max_length=500, blank=True, default="", verbose_name="变更说明")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="prompt_versions", verbose_name="修改者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "prompt_version"
        verbose_name = "提示词版本"
        verbose_name_plural = verbose_name
        ordering = ["-version"]
        unique_together = ["template", "version"]

    def __str__(self):
        return f"{self.template.name} v{self.version}"
