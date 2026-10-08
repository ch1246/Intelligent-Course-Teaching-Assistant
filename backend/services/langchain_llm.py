"""
LangChain LLM 封装
将现有 OpenAI 兼容接口封装为 LangChain ChatOpenAI
"""
from langchain_openai import ChatOpenAI


def get_llm(config) -> ChatOpenAI:
    """
    从 AgentAPIConfig 创建 LangChain ChatOpenAI

    Args:
        config: AgentAPIConfig 实例，包含 base_url, api_key, default_model

    Returns:
        LangChain ChatOpenAI 实例
    """
    return ChatOpenAI(
        base_url=config.base_url,
        api_key=config.get_api_key(),
        model=config.default_model,
        temperature=0.7,
        max_tokens=2048,
        streaming=True,
    )


def get_llm_with_params(
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> ChatOpenAI:
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
    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=True,
    )