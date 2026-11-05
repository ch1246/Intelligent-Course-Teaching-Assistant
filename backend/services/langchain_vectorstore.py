"""
LangChain VectorStore 封装
将现有 ChromaDB 封装为 LangChain VectorStore 接口

注意：langchain_chroma / chromadb 在函数内惰性导入 —— 模块导入永不抛错，
依赖缺失时只在调用处失败，由调用方降级到 services.rag_service.search_similar，
避免「模块级 import 失败 → 整个 Django 应用起不来」。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # 仅类型标注用
    from langchain_chroma import Chroma

from .langchain_embeddings import get_langchain_embeddings

# 缓存 VectorStore 实例：key = (集合名, 持久化目录)
# 旧实现只按集合名缓存，不同 persist_dir 会互相串用同一个实例。
_vectorstores: dict[tuple[str, str], "Chroma"] = {}


def _resolve_persist_dir(persist_dir: str | None = None) -> str:
    """统一持久化目录来源。

    未显式传入时读 settings.CHROMADB_PERSIST_DIR（绝对路径）。
    旧实现默认值是字面量 "chroma_data"（相对当前工作目录），与 rag_service 用的
    绝对路径不一致 —— 换个启动目录就会读到另一个库、甚至新建空库。
    """
    if persist_dir:
        return str(persist_dir)
    from django.conf import settings

    return str(getattr(settings, "CHROMADB_PERSIST_DIR", "chroma_data"))


def get_vectorstore(collection_name: str, persist_dir: str | None = None) -> Chroma:
    """获取或创建 LangChain Chroma VectorStore。

    Args:
        collection_name: ChromaDB 集合名称（格式: course_{id}）
        persist_dir: ChromaDB 持久化目录；默认取 settings.CHROMADB_PERSIST_DIR
    """
    resolved = _resolve_persist_dir(persist_dir)
    key = (collection_name, resolved)
    if key not in _vectorstores:
        from chromadb import PersistentClient
        from chromadb.config import Settings as CS
        from langchain_chroma import Chroma

        client = PersistentClient(
            path=resolved,
            settings=CS(anonymized_telemetry=False),
        )
        _vectorstores[key] = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=get_langchain_embeddings(),
        )
    return _vectorstores[key]


def get_retriever(collection_name: str, top_k: int = 5, persist_dir: str | None = None):
    """获取 Retriever（注意：retriever 不返回距离，需要距离请用 search_with_scores）。"""
    vectorstore = get_vectorstore(collection_name, persist_dir)
    return vectorstore.as_retriever(search_kwargs={"k": top_k})


def search_with_scores(
    collection_name: str,
    query: str,
    top_k: int = 5,
    persist_dir: str | None = None,
) -> list[dict]:
    """带真实距离的检索（替代原来硬编码 distance=0.0 的写法）。

    用 `similarity_search_with_score`，它返回 (Document, distance)，
    distance 是 Chroma 的距离（本项目 space=l2，即**平方** L2 距离，越小越相似）。
    用 rag_service.distance_to_similarity() 可以换算成余弦相似度。
    """
    vectorstore = get_vectorstore(collection_name, persist_dir)
    pairs = vectorstore.similarity_search_with_score(query, k=top_k)
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "distance": float(score),
        }
        for doc, score in pairs
    ]
