"""
LangChain LLM 封装
将现有 OpenAI 兼容接口封装为 LangChain ChatOpenAI

langchain_openai 在函数内惰性导入：依赖缺失时模块仍可导入，
调用处抛错后由 chat/views.py 降级到 rag_service.chat_stream_structured。
生成参数与手写路径共用 rag_service 的默认常量，两处不再各写一份。
"""
from typing import TYPE_CHECKING

from .rag_service import DEFAULT_LLM_MAX_TOKENS, DEFAULT_LLM_TEMPERATURE

if TYPE_CHECKING:  # 仅类型标注用
    from langchain_openai import ChatOpenAI


def get_llm_with_params(
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = DEFAULT_LLM_TEMPERATURE,
    max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
) -> "ChatOpenAI":
    """
    使用参数创建 LangChain ChatOpenAI

    Args:
        base_url: API 端点
        api_key: API 密钥
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大 token 数

    Returns:
        LangChain ChatOpenAI 实例
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=True,
    )