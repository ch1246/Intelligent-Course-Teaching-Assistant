"""
LangChain Embeddings 封装
将现有 BGE 模型封装为 LangChain Embeddings 接口
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # 仅类型标注用
    from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "BAAI/bge-large-zh-v1.5"
BGE_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

# langchain_core 是可选依赖：缺失时用最小占位基类，保证本模块仍可导入，
# 否则 chat/views.py 的模块级 import 会连带把整个 Django 应用拖垮。
try:
    from langchain_core.embeddings import Embeddings as _EmbeddingsBase
    HAS_LANGCHAIN_CORE = True
except Exception:  # pragma: no cover - 依赖缺失时的降级路径
    HAS_LANGCHAIN_CORE = False

    class _EmbeddingsBase:  # noqa: D401 - 占位基类
        """langchain_core 不可用时的最小基类，仅用于让类定义成立。"""

# 共享的底层模型实例：LangChain 路径与 services.rag_service 手写路径
# 共用同一个 SentenceTransformer，整个进程只加载一份 bge-large。
_shared_model = None
_shared_model_name = None


def get_sentence_transformer(model_name: str = DEFAULT_MODEL_NAME):
    """返回全局共享的 SentenceTransformer 实例（按模型名单例化）。"""
    global _shared_model, _shared_model_name
    if _shared_model is None or _shared_model_name != model_name:
        from sentence_transformers import SentenceTransformer

        _shared_model = SentenceTransformer(model_name)
        _shared_model_name = model_name
    return _shared_model


class BGEEmbeddings(_EmbeddingsBase):
    """
    封装 BGE 模型为 LangChain Embeddings 接口

    使用方式:
        embeddings = BGEEmbeddings()
        vector = embeddings.embed_query("什么是梯度下降？")
        vectors = embeddings.embed_documents(["文档1", "文档2"])
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        """
        初始化 BGE Embeddings

        Args:
            model_name: HuggingFace 模型名称，默认使用中文优化的 bge-large-zh-v1.5
        """
        # 复用共享实例，避免与 rag_service 各自加载一份模型
        self.model = get_sentence_transformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        批量嵌入文档

        Args:
            texts: 文档文本列表

        Returns:
            嵌入向量列表，每个向量是 1024 维的浮点数列表
        """
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """
        嵌入查询文本

        BGE 系列检索时**必须**给 query 加指令前缀（文档侧不加），
        否则 query 与 doc 落在不同的语义空间、召回质量明显下降。
        该前缀只影响 query 向量，已入库的文档向量无需重建。

        Args:
            text: 查询文本

        Returns:
            嵌入向量，1024 维的浮点数列表
        """
        query = text if text.startswith(BGE_QUERY_INSTRUCTION) else BGE_QUERY_INSTRUCTION + text
        embedding = self.model.encode([query], normalize_embeddings=True)
        return embedding[0].tolist()


# 全局单例
_embeddings_instance = None


def get_langchain_embeddings() -> BGEEmbeddings:
    """
    获取全局 BGEEmbeddings 单例

    Returns:
        BGEEmbeddings 实例
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = BGEEmbeddings()
    return _embeddings_instance