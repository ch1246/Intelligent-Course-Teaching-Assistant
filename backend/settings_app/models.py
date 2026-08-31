from django.db import models
from django.conf import settings
from .encryption import encrypt_value, decrypt_value, is_encrypted


class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name="键")
    value = models.TextField(blank=True, default="", verbose_name="值")
    description = models.CharField(max_length=200, blank=True, default="", verbose_name="描述")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "system_setting"
        verbose_name = "系统设置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.key} = {self.value[:50]}"


class AgentAPIConfig(models.Model):
    name = models.CharField(max_length=100, verbose_name="配置名称")
    base_url = models.CharField(max_length=500, verbose_name="API 地址")
    api_key = models.CharField(max_length=500, verbose_name="API 密钥")
    model_list = models.JSONField(default=list, verbose_name="模型列表")
    default_model = models.CharField(max_length=100, blank=True, default="", verbose_name="默认模型")
    system_prompt = models.TextField(blank=True, default="", verbose_name="全局兜底 System Prompt")
    prompt_template = models.ForeignKey(
        "prompt_engine.PromptTemplate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="agent_configs", verbose_name="关联提示词模板"
    )
    context_strategy = models.ForeignKey(
        "context_engine.ContextStrategy", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="agent_configs", verbose_name="关联上下文策略"
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    is_default = models.BooleanField(default=False, verbose_name="是否默认配置")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_api_configs", verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "agent_api_config"
        verbose_name = "Agent API 配置"
        verbose_name_plural = verbose_name
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return self.name

    # ---- api_key encryption ----

    def set_api_key(self, plaintext: str) -> None:
        """Encrypt and store the api_key."""
        self.api_key = encrypt_value(plaintext) if plaintext else ""

    def get_api_key(self) -> str:
        """Decrypt and return the api_key. Handles legacy plaintext keys."""
        if not self.api_key:
            return ""
        if is_encrypted(self.api_key):
            return decrypt_value(self.api_key)
        # Legacy: plaintext key — return as-is and re-encrypt on next save
        return self.api_key

    def save(self, *args, **kwargs):
        """Auto-encrypt api_key if it is in plaintext (handles legacy data)."""
        if self.api_key and not is_encrypted(self.api_key):
            self.api_key = encrypt_value(self.api_key)
        super().save(*args, **kwargs)
