"""
RAG Service: ChromaDB + BGE Embedding + LLM summarization + structured SSE streaming.
"""
import asyncio
from typing import AsyncGenerator
from django.conf import settings
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import AsyncOpenAI

_chroma_client = None
_embedding_fn = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMADB_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        from sentence_transformers import SentenceTransformer
        _embedding_fn = SentenceTransformer("BAAI/bge-large-zh-v1.5")
    return _embedding_fn


def get_collection(collection_name: str):
    client = get_chroma_client()
    return client.get_or_create_collection(name=collection_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_fn()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def search_similar(
    collection_name: str,
    query: str,
    n_results: int = 5,
) -> list[dict]:
    """Search ChromaDB for similar documents."""
    collection = get_collection(collection_name)
    query_embedding = embed_texts([query])
    results = collection.query(query_embeddings=query_embedding, n_results=n_results)
    docs = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            docs.append({
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
    return docs


def index_documents(
    collection_name: str,
    documents: list[str],
    metadatas: list[dict] | None = None,
    ids: list[str] | None = None,
    summaries: list[str] | None = None,
):
    """Index documents + their AI summaries into ChromaDB."""
    collection = get_collection(collection_name)
    all_chunks = []
    all_metas = []
    all_ids = []

    for i, doc in enumerate(documents):
        # 先索引文档级摘要（如果存在）
        if summaries and i < len(summaries) and summaries[i]:
            all_chunks.append(summaries[i])
            meta = (metadatas[i] if metadatas else {}).copy()
            meta["chunk_index"] = -1
            meta["doc_index"] = i
            meta["is_summary"] = True
            all_metas.append(meta)
            all_ids.append(f"{ids[i]}_summary" if ids else f"doc_{i}_summary")

        # 再索引正文分块
        chunks = chunk_text(doc)
        for j, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            meta = (metadatas[i] if metadatas else {}).copy()
            meta["chunk_index"] = j
            meta["doc_index"] = i
            all_metas.append(meta)
            all_ids.append(f"{ids[i]}_chunk_{j}" if ids else f"doc_{i}_chunk_{j}")

    if all_chunks:
        embeddings = embed_texts(all_chunks)
        collection.add(embeddings=embeddings, documents=all_chunks, metadatas=all_metas, ids=all_ids)

    return len(all_chunks)


def delete_collection(collection_name: str):
    client = get_chroma_client()
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass


# ── Document Summarization ─────────────────────────────

async def summarize_document(
    content: str,
    filename: str,
    base_url: str,
    api_key: str,
    model: str,
    max_input_chars: int = 6000,
) -> str:
    """Generate a concise AI summary of a document."""
    truncated = content[:max_input_chars]
    prompt = f"""请用 150-300 字总结以下文档的核心内容，提取关键知识点和主要结论。

文档名：{filename}

文档内容：
{truncated}

总结要求：
1. 概括文档的核心主题和目的
2. 列出 3-5 个关键知识点
3. 如有重要结论或公式，简要提及

请直接给出总结，不要加前缀说明。"""

    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/v1"):
        clean_url = clean_url[:-3].rstrip("/")
    client = AsyncOpenAI(base_url=clean_url, api_key=api_key)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=500,
    )
    return response.choices[0].message.content or ""


# ── Structured SSE Chat Stream ─────────────────────────

async def chat_stream_structured(
    messages: list[dict],
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> AsyncGenerator[dict, None]:
    """Stream chat completion with structured events."""
    # OpenAI SDK 会自动拼接 /v1，如果用户已配置含 /v1 的 URL，需要去掉尾部
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/v1"):
        clean_url = clean_url[:-3].rstrip("/")
    client = AsyncOpenAI(base_url=clean_url, api_key=api_key)
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield {"type": "content", "content": chunk.choices[0].delta.content}


