"""
API Key encryption using Fernet (symmetric encryption).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import re

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# 独立密钥的环境变量名：设置后不再依赖 SECRET_KEY，SECRET_KEY 轮换也不会导致历史密文失效。
FERNET_KEY_ENV = "API_KEY_ENCRYPTION_KEY"

# Fernet token = base64url(version(0x80) | timestamp | IV | ciphertext | HMAC-SHA256)
# 因首字节固定为 0x80，base64url 编码后必以 "gAAAAA" 开头；最短长度也在 100 字符左右。
_FERNET_TOKEN_RE = re.compile(r"^gAAAAA[A-Za-z0-9_\-]{50,}={0,2}$")


def _derive_fernet_key() -> bytes:
    """解析 Fernet 密钥。

    优先读环境变量 API_KEY_ENCRYPTION_KEY（独立密钥，可单独轮换）；
    未配置时回退到「由 SECRET_KEY 派生」，保证对已有密文的兼容。
    """
    env_key = os.environ.get(FERNET_KEY_ENV, "").strip()
    if env_key:
        try:
            raw = env_key.encode("utf-8")
            if len(base64.urlsafe_b64decode(raw)) != 32:
                raise ValueError("解码后不是 32 字节")
            return raw
        except Exception as exc:  # noqa: BLE001 - 配错要立刻暴露
            from django.core.exceptions import ImproperlyConfigured

            raise ImproperlyConfigured(
                f"{FERNET_KEY_ENV} 不是合法的 Fernet 密钥"
                f"（应为 32 字节 urlsafe-base64，可用 Fernet.generate_key() 生成）：{exc}"
            ) from exc

    from django.conf import settings

    secret = settings.SECRET_KEY.encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(digest)


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_fernet_key())
    return _fernet


def reset_fernet_cache() -> None:
    """清空密钥缓存（测试或运行期切换密钥后使用）。"""
    global _fernet
    _fernet = None


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string. Returns plaintext.

    安全兜底：密钥不匹配或密文被篡改时**不抛异常**，返回空串并记录错误日志，
    避免一个坏掉的 api_key 让整个问答请求 500；调用方看到空串会走「未配置密钥」的提示。
    """
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.error(
            "API Key 解密失败：密文无效或加密密钥已变更（检查 %s 与 DJANGO_SECRET_KEY 是否被轮换），"
            "请在管理后台重新录入 api_key。",
            FERNET_KEY_ENV,
        )
        return ""
    except Exception:  # noqa: BLE001 - 兜底，避免因为配置问题导致 500
        logger.exception("API Key 解密出现未预期错误")
        return ""


def is_encrypted(value: str) -> bool:
    """判断是否为 Fernet 密文（结构判断，不尝试解密）。

    这里刻意**不做解密验证**：若加密密钥被轮换，老密文虽然解不开，但结构上仍是密文。
    一旦把它判成「非密文」，保存流程会把它当明文再加密一次（双重加密，数据报废）。
    需要「能不能真的解开」时用 can_decrypt()。
    """
    if not value or not isinstance(value, str):
        return False
    return bool(_FERNET_TOKEN_RE.match(value))


def can_decrypt(value: str) -> bool:
    """解密验证（诊断/自检用）：能解出明文才算真的可用。"""
    if not value or not is_encrypted(value):
        return False
    try:
        _get_fernet().decrypt(value.encode("utf-8"))
        return True
    except Exception:  # noqa: BLE001
        return False
