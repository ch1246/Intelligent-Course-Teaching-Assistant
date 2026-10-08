"""
LangChain VectorStore 封装
将现有 ChromaDB 封装为 LangChain VectorStore 接口
"""
from langchain_chroma import Chroma
from chromadb import PersistentClient
from chromadb.config import Settings as CS
from .langchain_embeddings import get_langchain_embeddings

# 缓存 VectorStore 实例
_vectorstores: dict[str, Chroma] = {}


def get_vectorstore(collection_name: str, persist_dir: str = "chroma_data") -> Chroma:
    """
    获取或创建 LangChain Chroma VectorStore

    Args:
        collection_name: ChromaDB 集合名称（格式: course_{id}）
        persist_dir: ChromaDB 持久化目录

    Returns:
        LangChain Chroma VectorStore 实例
    """
    if collection_name not in _vectorstores:
        client = PersistentClient(
            path=persist_dir,
            settings=CS(anonymized_telemetry=False)
        )
        _vectorstores[collection_name] = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=get_langchain_embeddings(),
        )
    return _vectorstores[collection_name]


def get_retriever(collection_name: str, top_k: int = 5, persist_dir: str = "chroma_data"):
    """
    获取 Retriever

    Args:
        collection_name: ChromaDB 集合名称
        top_k: 返回的文档数量
        persist_dir: ChromaDB 持久化目录

    Returns:
        LangChain Retriever 实例
    """
    vectorstore = get_vectorstore(collection_name, persist_dir)
    return vectorstore.as_retriever(search_kwargs={"k": top_k})


def search_similar_langchain(
    collection_name: str,
    query: str,
    top_k: int = 5,
    persist_dir: str = "chroma_data",
) -> list[dict]:
    """
    使用 LangChain 检索相似文档（兼容原有 search_similar 接口）

    Args:
        collection_name: ChromaDB 集合名称
        query: 查询文本
        top_k: 返回的文档数量
        persist_dir: ChromaDB 持久化目录

    Returns:
        文档列表，每个文档包含 content, metadata, distance
    """
    vectorstore = get_vectorstore(collection_name, persist_dir)
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})

    # 执行检索
    docs = retriever.invoke(query)

    # 转换为原有格式
    results = []
    for doc in docs:
        results.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
            "distance": 0.0,  # LangChain 不直接返回距离，需要额外计算
        })

    return results