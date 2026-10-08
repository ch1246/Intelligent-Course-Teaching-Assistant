"""
LangChain Embeddings 封装
将现有 BGE 模型封装为 LangChain Embeddings 接口
"""
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


class BGEEmbeddings(Embeddings):
    """
    封装 BGE 模型为 LangChain Embeddings 接口

    使用方式:
        embeddings = BGEEmbeddings()
        vector = embeddings.embed_query("什么是梯度下降？")
        vectors = embeddings.embed_documents(["文档1", "文档2"])
    """

    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5"):
        """
        初始化 BGE Embeddings

        Args:
            model_name: HuggingFace 模型名称，默认使用中文优化的 bge-large-zh-v1.5
        """
        self.model = SentenceTransformer(model_name)

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

        Args:
            text: 查询文本

        Returns:
            嵌入向量，1024 维的浮点数列表
        """
        embedding = self.model.encode([text], normalize_embeddings=True)
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