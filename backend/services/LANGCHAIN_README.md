# LangChain 集成说明

## 概述

本目录包含 LangChain 集成封装模块，将原有 RAG 系统的组件封装为 LangChain 接口。

## 文件说明

| 文件 | 说明 |
|------|------|
| `langchain_embeddings.py` | BGE 模型封装为 LangChain Embeddings 接口（含全进程共享的模型单例） |
| `langchain_vectorstore.py` | ChromaDB 封装为 LangChain VectorStore 接口 |
| `langchain_llm.py` | OpenAI 兼容接口封装为 LangChain ChatOpenAI |
| `rag_chain.py` | **生产在用**：系统提示词装配（render_system_prompt）+ LCEL RAG Chain 构建器 |

> 注：`langchain_example.py` 已删除；`search_similar_langchain`、`get_llm` 等
> 冗余封装已清理。生产链路见 `chat/views.py`：检索用 `search_with_scores`、
> 生成用 `get_llm_with_params(...).astream()`，两者失败时分别降级到
> `rag_service.search_similar` / `rag_service.chat_stream_structured`。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

新增的依赖：
- `langchain>=0.3`
- `langchain-core>=0.3`
- `langchain-community>=0.3`
- `langchain-openai>=0.2`
- `langchain-chroma>=0.1`

### 2. 使用 Embeddings

```python
from services.langchain_embeddings import get_langchain_embeddings

embeddings = get_langchain_embeddings()

# 嵌入查询
vector = embeddings.embed_query("什么是梯度下降？")
print(f"向量维度: {len(vector)}")  # 1024

# 批量嵌入文档
vectors = embeddings.embed_documents(["文档1", "文档2"])
```

### 3. 使用 Retriever

```python
from services.langchain_vectorstore import get_retriever

retriever = get_retriever("course_2", top_k=5)

# 执行检索
docs = retriever.invoke("什么是梯度下降？")
for doc in docs:
    print(doc.page_content)
```

### 4. 使用 LLM

```python
from services.langchain_llm import get_llm_with_params

llm = get_llm_with_params(
    base_url="https://api.deepseek.com",
    api_key="your-key",
    model="deepseek-chat"
)

# 流式输出
async for chunk in llm.astream([{"role": "user", "content": "什么是梯度下降？"}]):
    print(chunk.content, end="")
```

### 5. 使用 RAG Chain

```python
from services.langchain_llm import get_llm_with_params
from services.langchain_vectorstore import get_retriever
from services.rag_chain import build_rag_chain_stream

# 获取组件
llm = get_llm_with_params(base_url, api_key, model)
retriever = get_retriever("course_2", top_k=5)
memory_prompt = "\n\n【学生画像】\n- 薄弱：梯度下降"

# 构建 RAG Chain
chain = build_rag_chain_stream(llm, retriever, memory_prompt)

# 流式输出
async for chunk in chain.astream("什么是梯度下降？"):
    print(chunk, end="")
```

## 与现有系统集成

### 最小改动方案

在 `chat/views.py` 中替换原有调用：

```python
# 已在生产链路中使用（chat/views.py）:
from services.langchain_vectorstore import search_with_scores
context_docs = search_with_scores("course_2", "什么是梯度下降？", top_k=5)
```

```python
# 原有代码:
from services.rag_service import chat_stream_structured
async for event in chat_stream_structured(messages, base_url, api_key, model):
    yield event

# 替换为:
from services.langchain_llm import get_llm_with_params
llm = get_llm_with_params(base_url, api_key, model)
async for chunk in llm.astream(messages):
    yield {"type": "content", "content": chunk.content}
```

### 保留的原有逻辑

以下逻辑保持不变，继续使用原有实现：

- `UserMemory` 模型和更新逻辑
- `context_compressor.py` Token 压缩
- `TraceLog` 追踪逻辑
- 前端 SSE 协议

## 未来扩展

集成 LangChain 后，可以轻松添加：

### 1. Reranker（重排序）

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

reranker = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
compressor = CrossEncoderReranker(model=reranker)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=retriever
)
```

### 2. Multi-Query Retriever（查询改写）

```python
from langchain.retrievers import MultiQueryRetriever

retriever = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(),
    llm=llm
)
```

### 3. Ensemble Retriever（混合检索）

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

bm25_retriever = BM25Retriever.from_texts(documents)
vector_retriever = vectorstore.as_retriever()

ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.5, 0.5]
)
```

### 4. Agent（智能代理）

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent

agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
```

## 对比总结

| 功能 | 原有实现 | LangChain 实现 |
|------|---------|----------------|
| Embeddings | `SentenceTransformer` 直接调用 | `BGEEmbeddings` 封装 |
| 向量库 | `chromadb.PersistentClient` | `langchain_chroma.Chroma` |
| LLM | `openai.AsyncOpenAI` | `langchain_openai.ChatOpenAI` |
| 检索 | `collection.query()` | `retriever.invoke()` |
| 流式输出 | 手动 async generator | `llm.astream()` |
| RAG 流程 | 手动 5 阶段编排 | LCEL Chain |

## 注意事项

1. **性能**: LangChain 有少量开销，但对 RAG 系统影响可忽略
2. **兼容性**: 保留原有函数作为 fallback，可随时回退
3. **版本**: 锁定 LangChain 版本以避免兼容性问题
4. **测试**: 建议对比迁移前后的检索结果和回答质量