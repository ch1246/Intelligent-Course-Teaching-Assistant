"""
RAG Service: ChromaDB + BGE Embedding + LLM summarization + structured SSE streaming.
"""
import asyncio
import re
from typing import AsyncGenerator
from django.conf import settings
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import AsyncOpenAI

# ── 全局默认参数（全项目唯一出处；LangChain 与手写实现共用）──
DEFAULT_LLM_TEMPERATURE = 0.7
DEFAULT_LLM_MAX_TOKENS = 2048
DEFAULT_RERANK_ALPHA = 0.5   # lexical_rerank 融合权重：0=纯语义，1=纯字面
DEFAULT_MAX_QUERIES = 3      # expand_queries 生成检索式上限
SUMMARY_RANK_PENALTY = 0.85  # 文档级摘要块的排序降权系数

_chroma_client = None
_embedding_fn = None


def collection_name_for_course(course_id) -> str:
    """Chroma 集合命名约定（全项目唯一出处）：course_{course_id}。

    此前 chat/views.py、vector_db/views.py 三处各写一遍 f-string，改名要改三处。
    """
    return f"course_{course_id}"


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMADB_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_embedding_fn():
    """返回全局唯一的 SentenceTransformer 实例。

    优先复用 langchain_embeddings 的共享单例 —— LangChain 检索路径与手写
    索引/检索路径共用同一个模型对象，bge-large 整个进程只加载一份
    （此前两处各 new 一个，重复占用 GB 级内存）。
    langchain_core 不可用时退回本地直载，保证纯手写降级路径仍能工作。
    """
    global _embedding_fn
    if _embedding_fn is None:
        try:
            from services.langchain_embeddings import get_sentence_transformer
            _embedding_fn = get_sentence_transformer()
        except Exception:
            from sentence_transformers import SentenceTransformer
            _embedding_fn = SentenceTransformer("BAAI/bge-large-zh-v1.5")
    return _embedding_fn


def get_collection(collection_name: str):
    client = get_chroma_client()
    return client.get_or_create_collection(name=collection_name)


def embed_texts(texts: list[str], as_query: bool = False) -> list[list[float]]:
    """批量向量化。

    as_query=True 时给文本加 BGE 官方要求的检索指令前缀。BGE 系列规定
    「query 加指令、doc 不加」，否则两者落在不同语义空间、召回明显变差。
    该前缀只影响 query 向量，已入库的文档向量无需重建。
    """
    model = get_embedding_fn()
    if as_query:
        from services.langchain_embeddings import BGE_QUERY_INSTRUCTION

        texts = [
            t if (t or "").startswith(BGE_QUERY_INSTRUCTION)
            else BGE_QUERY_INSTRUCTION + (t or "")
            for t in texts
        ]
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    # 参数兜底：chunk_size<=0 会导致死循环；overlap>=chunk_size 会让步长非正
    if chunk_size <= 0:
        chunk_size = 500
    if overlap < 0:
        overlap = 0
    if overlap >= chunk_size:
        overlap = chunk_size // 5
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ── Similarity / Query rewrite / Rerank ────────────────

def distance_to_similarity(distance: float | None) -> float:
    """把 Chroma 的距离换算成余弦相似度。

    实测确认（用临时集合做对照实验）：`space=l2` 返回的是**平方** L2 距离；
    而本项目所有向量入库前都做了 L2 归一化，因此
        d = ‖a-b‖² = 2 - 2·cos   →   cos = 1 - d/2
    旧代码用 `1 - d`（例如 d=0.8 会算成 0.2，实际 cos=0.6），导致 similarity_threshold
    的语义整体偏低、很容易把好片段全过滤掉。
    """
    if distance is None:
        return 0.0
    try:
        sim = 1.0 - float(distance) / 2.0
    except (TypeError, ValueError):
        return 0.0
    return max(-1.0, min(1.0, sim))


_QUESTION_PREFIXES = (
    "请问一下", "请问", "帮我", "麻烦", "我想知道", "想知道", "解释一下", "介绍一下",
    "什么是", "什么叫", "如何", "怎么", "怎样", "为什么", "为何", "哪些", "哪个",
    "是否", "能不能", "可不可以", "可以", "讲讲", "说说",
)
_QUESTION_TAILS = "呢吗吧啊？?。！!，,、 \t"


def expand_queries(question: str, max_queries: int = DEFAULT_MAX_QUERIES) -> list[str]:
    """规则式查询改写（不调用 LLM，零延迟、可离线）。

    生成 1~3 条互补的检索式：
      1) 原问题——保留完整语义；
      2) 去掉疑问前缀/语气词后的"核心词版"——提升关键词命中率；
      3) 问题里的英文术语/缩写（CNN、Adam、L2 等）——课程资料里这类词往往是强信号。
    """
    q = (question or "").strip()
    if not q:
        return []

    candidates = [q]

    core = q
    for prefix in _QUESTION_PREFIXES:
        if core.startswith(prefix):
            core = core[len(prefix):]
            break
    core = core.rstrip(_QUESTION_TAILS).strip("：:，,、 ")
    candidates.append(core)

    terms = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,20}", q)
    if terms:
        candidates.append(" ".join(dict.fromkeys(terms)))

    result: list[str] = []
    for item in candidates:
        if item and len(item) >= 2 and item not in result:
            result.append(item)
    return result[:max_queries]


def _char_bigrams(text: str) -> set[str]:
    """字符二元组集合，用于计算字面重合度（对中文友好，无需分词）。"""
    compact = re.sub(r"\s+", "", (text or "").lower())
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def _is_summary_chunk(doc: dict) -> bool:
    """判断是否为文档级摘要块（chunk_index=-1 / is_summary=True）。"""
    meta = doc.get("metadata") or {}
    return bool(meta.get("is_summary")) or meta.get("chunk_index") == -1


def rank_key(doc: dict) -> float:
    """排序用分数：摘要块降权。

    摘要块是整篇文档的概括，与正文分块同权竞争 top_k 时会把正文挤出上下文
    （正文往往才是能回答问题的那几段）。降权后摘要只在确实更相关时才靠前，
    且不影响 similarity 的对外展示值。
    """
    sim = float(doc.get("similarity", 0.0) or 0.0)
    return sim * SUMMARY_RANK_PENALTY if _is_summary_chunk(doc) else sim


def lexical_rerank(question: str, docs: list[dict], alpha: float = DEFAULT_RERANK_ALPHA) -> list[dict]:
    """轻量重排：把「向量相似度」与「字面重合度」加权融合后重新排序。

    alpha 越小越偏语义，越大越偏关键词。向量检索擅长语义、但容易把"同主题不同问题"
    的片段排前面，字面重合度能补上精确匹配。零额外依赖，后续可替换为 BGE-reranker
    （Cross-Encoder）做真正的语义重排。
    """
    q_grams = _char_bigrams(question)
    for doc in docs:
        similarity = doc.get("similarity")
        if similarity is None:
            similarity = distance_to_similarity(doc.get("distance"))
        similarity = float(similarity)

        grams = _char_bigrams(doc.get("content", ""))
        overlap = (len(q_grams & grams) / len(q_grams)) if q_grams else 0.0

        doc["vector_similarity"] = round(similarity, 4)
        doc["lexical_overlap"] = round(overlap, 4)
        doc["rerank_score"] = round((1 - alpha) * similarity + alpha * overlap, 6)
        # 摘要块同样降权：重排是排序的最后一步，这里不降权就等于白降
        if _is_summary_chunk(doc):
            doc["rerank_score"] = round(doc["rerank_score"] * SUMMARY_RANK_PENALTY, 6)

    return sorted(docs, key=lambda d: d["rerank_score"], reverse=True)


def search_similar(
    collection_name: str,
    query: str,
    n_results: int = 5,
) -> list[dict]:
    """Search ChromaDB for similar documents."""
    collection = get_collection(collection_name)
    query_embedding = embed_texts([query], as_query=True)
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
    chunk_size: int = 500,
    chunk_overlap: int = 50,
):
    """Index documents + their AI summaries into ChromaDB.

    chunk_size / chunk_overlap 由调用方（reindex）从 ContextStrategy 读取，
    这样后台配置的分块参数才真正生效（此前是写死的 500/50）。
    """
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
        chunks = chunk_text(doc, chunk_size=chunk_size, overlap=chunk_overlap)
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
    import logging
    logger = logging.getLogger(__name__)
    client = get_chroma_client()
    try:
        client.delete_collection(name=collection_name)
    except Exception as e:
        logger.warning(f"Failed to delete collection '{collection_name}': {e}")


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
    temperature: float = DEFAULT_LLM_TEMPERATURE,
    max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
) -> AsyncGenerator[dict, None]:
    """Stream chat completion with structured events."""
    clean_url = base_url.rstrip("/")
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


