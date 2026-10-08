"""
LangChain 集成示例
展示如何使用 LangChain 封装模块替换原有 RAG 流程
"""
import asyncio
from .langchain_embeddings import get_langchain_embeddings
from .langchain_vectorstore import get_retriever, search_similar_langchain
from .langchain_llm import get_llm
from .rag_chain import build_rag_chain, build_rag_chain_stream


# ============================================================
# 示例 1: 使用 LangChain Embeddings
# ============================================================
def example_embeddings():
    """示例：使用 LangChain Embeddings"""
    embeddings = get_langchain_embeddings()

    # 嵌入单个查询
    query_vector = embeddings.embed_query("什么是梯度下降？")
    print(f"查询向量维度: {len(query_vector)}")

    # 批量嵌入文档
    docs = ["机器学习是人工智能的一个分支", "深度学习是机器学习的子集"]
    doc_vectors = embeddings.embed_documents(docs)
    print(f"文档向量数量: {len(doc_vectors)}")


# ============================================================
# 示例 2: 使用 LangChain Retriever
# ============================================================
def example_retriever():
    """示例：使用 LangChain Retriever"""
    collection_name = "course_2"  # 替换为实际的集合名

    # 获取 Retriever
    retriever = get_retriever(collection_name, top_k=5)

    # 执行检索
    docs = retriever.invoke("什么是梯度下降？")
    print(f"检索到 {len(docs)} 个文档")
    for doc in docs:
        print(f"  - {doc.page_content[:50]}...")


# ============================================================
# 示例 3: 使用 LangChain LLM
# ============================================================
async def example_llm():
    """示例：使用 LangChain LLM"""
    # 假设 config 是 AgentAPIConfig 实例
    # config = AgentAPIConfig.objects.filter(is_active=True).first()
    # llm = get_llm(config)

    # 流式输出
    # async for chunk in llm.astream([{"role": "user", "content": "什么是梯度下降？"}]):
    #     print(chunk.content, end="")
    pass


# ============================================================
# 示例 4: 使用 RAG Chain
# ============================================================
async def example_rag_chain():
    """示例：使用 RAG Chain"""
    # 假设 config 是 AgentAPIConfig 实例
    # config = AgentAPIConfig.objects.filter(is_active=True).first()

    # # 获取组件
    # llm = get_llm(config)
    # retriever = get_retriever("course_2", top_k=5)
    # memory_prompt = "\n\n【学生画像】\n- 薄弱：梯度下降、反向传播"

    # # 构建 RAG Chain
    # chain = build_rag_chain_stream(llm, retriever, memory_prompt)

    # # 流式输出
    # async for chunk in chain.astream("什么是梯度下降？"):
    #     print(chunk, end="")
    pass


# ============================================================
# 示例 5: 与现有系统集成（最小改动）
# ============================================================
def example_integration():
    """
    示例：与现有系统集成

    在 chat/views.py 中替换原有调用：
    """
    # 原有代码:
    # from services.rag_service import search_similar
    # context_docs = search_similar("course_2", "什么是梯度下降？", n_results=5)

    # 替换为:
    # from services.langchain_vectorstore import search_similar_langchain
    # context_docs = search_similar_langchain("course_2", "什么是梯度下降？", top_k=5)

    # 原有代码:
    # from services.rag_service import chat_stream_structured
    # async for event in chat_stream_structured(messages, base_url, api_key, model):
    #     yield event

    # 替换为:
    # from services.langchain_llm import get_llm_with_params
    # llm = get_llm_with_params(base_url, api_key, model)
    # async for chunk in llm.astream(messages):
    #     yield {"type": "content", "content": chunk.content}

    pass


# ============================================================
# 对比: 原有实现 vs LangChain 实现
# ============================================================
"""
原有实现 (rag_service.py):
─────────────────────────
def search_similar(collection_name, query, n_results=5):
    model = get_embedding_fn()
    collection = get_collection(collection_name)
    q_emb = model.encode([query], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=q_emb, n_results=n_results)
    ...

async def chat_stream_structured(messages, base_url, api_key, model):
    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    stream = await client.chat.completions.create(model=model, messages=messages, stream=True)
    async for chunk in stream:
        yield {"type": "content", "content": chunk.choices[0].delta.content}


LangChain 实现:
──────────────
from services.langchain_vectorstore import get_retriever
from services.langchain_llm import get_llm_with_params

# 检索
retriever = get_retriever("course_2", top_k=5)
docs = retriever.invoke("什么是梯度下降？")

# LLM
llm = get_llm_with_params(base_url, api_key, model)
async for chunk in llm.astream(messages):
    yield {"type": "content", "content": chunk.content}

# 或使用 RAG Chain
from services.rag_chain import build_rag_chain_stream
chain = build_rag_chain_stream(llm, retriever, memory_prompt)
async for chunk in chain.astream("什么是梯度下降？"):
    yield {"type": "content", "content": chunk}
"""


if __name__ == "__main__":
    # 测试 Embeddings
    example_embeddings()

    # 测试 Retriever
    example_retriever()