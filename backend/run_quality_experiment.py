"""
实验三：RAG回答质量评估（自动化部分）
- RAG vs 纯LLM基线对比
- Top-K值对比
- 相似度阈值对比
"""
import os, sys, time, json, asyncio, re
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import chromadb
from chromadb.config import Settings as CS
from services.rag_service import get_embedding_fn, embed_texts, chunk_text, chat_stream_structured
from settings_app.models import AgentAPIConfig

# ============================================================
# 配置
# ============================================================
config = AgentAPIConfig.objects.filter(is_active=True).first()
base_url = config.base_url
api_key = config.get_api_key()
model_name = config.default_model

model = get_embedding_fn()
client = chromadb.PersistentClient(path='chroma_data', settings=CS(anonymized_telemetry=False))
col = client.get_collection(name='course_2')
total_chunks = col.count()
print(f"知识库: course_2, {total_chunks} chunks")
print(f"LLM: {model_name} @ {base_url}")

# 测试问题（从50题中选取代表性问题）
test_questions = [
    # 概念解释
    "什么是梯度下降算法？",
    "什么是反向传播算法？",
    "什么是卷积神经网络？",
    "什么是注意力机制？",
    "什么是过拟合？",
    "什么是正则化？",
    "什么是交叉验证？",
    "什么是特征工程？",
    "什么是损失函数？",
    "什么是批归一化？",
    # 原理推导
    "推导线性回归的正规方程",
    "推导交叉熵损失函数的梯度",
    "推导反向传播中权重梯度的计算公式",
    "推导sigmoid函数的导数",
    "推导注意力机制的计算过程",
    # 对比分析
    "比较线性回归和逻辑回归的区别",
    "比较L1和L2正则化的区别",
    "比较SGD和Adam优化器的区别",
    "比较BatchNorm和LayerNorm的区别",
    "比较监督学习和无监督学习",
    # 应用场景
    "在什么情况下使用随机森林而不是决策树？",
    "什么情况下需要使用数据增强？",
    "什么情况下使用迁移学习效果更好？",
    "如何选择合适的损失函数？",
    "如何处理类别不平衡问题？",
]

# ============================================================
# 工具函数
# ============================================================
def retrieve(query, top_k=5, threshold=0.0):
    """检索知识片段"""
    q_emb = model.encode([query], normalize_embeddings=True).tolist()
    results = col.query(query_embeddings=q_emb, n_results=top_k)
    docs = []
    if results['documents'] and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            dist = results['distances'][0][i] if results['distances'] else 0
            sim = 1 - dist
            if sim >= threshold:
                docs.append({"text": doc, "similarity": round(sim, 4)})
    return docs

async def call_llm_stream(system_msg, user_msg, retries=5):
    """调用LLM（流式）"""
    messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]
    for attempt in range(retries):
        try:
            full = ""
            async for event in chat_stream_structured(messages, base_url, api_key, model_name):
                if event['type'] == 'content':
                    full += event['content']
            if full:
                return full
            if attempt < retries - 1:
                await asyncio.sleep(5)
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(5)
            else:
                print(f"    LLM失败: {e}")
                return ""
    return ""

def count_claims(text):
    """简单统计断言数（按句号分割）"""
    sentences = re.split(r'[。！？\.!\?]', text)
    return max(1, len([s for s in sentences if len(s.strip()) > 5]))

def check_groundedness(response, context_docs):
    """检查回答是否有依据（基于检索到的知识片段）"""
    if not context_docs:
        return 0.0
    context_text = " ".join([d["text"] for d in context_docs])
    # 提取回答中的关键短语（4字以上的中文词组）
    key_phrases = re.findall(r'[一-鿿]{4,}', response)
    if not key_phrases:
        return 0.5
    # 检查有多少关键短语在上下文中出现
    grounded = sum(1 for p in key_phrases if p in context_text)
    return round(grounded / len(key_phrases), 4)

# ============================================================
# 实验3.1: RAG vs 纯LLM基线对比
# ============================================================
print("\n" + "=" * 60)
print("实验3.1: RAG vs 纯LLM基线对比")
print("=" * 60)

async def run_rag_vs_plain():
    results = []
    for i, q in enumerate(test_questions):
        print(f"  [{i+1}/{len(test_questions)}] {q}")

        # RAG回答
        docs = retrieve(q, top_k=5, threshold=0.0)
        context = "\n\n".join([d["text"] for d in docs])
        rag_sys = f"你是一个教学助手。根据以下参考资料回答问题。\n\n参考资料：\n{context}"
        rag_resp = await call_llm_stream(rag_sys, q)
        await asyncio.sleep(2)

        # 纯LLM回答
        plain_resp = await call_llm_stream("你是一个教学助手。请回答用户的问题。", q)
        await asyncio.sleep(2)

        # 计算有依据率
        rag_grounded = check_groundedness(rag_resp, docs)
        plain_grounded = check_groundedness(plain_resp, [])  # 无上下文

        results.append({
            "query": q,
            "rag_response": rag_resp,
            "rag_len": len(rag_resp),
            "rag_grounded": rag_grounded,
            "rag_avg_sim": round(sum(d["similarity"] for d in docs) / max(len(docs), 1), 4) if docs else 0,
            "plain_response": plain_resp,
            "plain_len": len(plain_resp),
            "plain_grounded": plain_grounded,
        })
        print(f"    RAG: {len(rag_resp)}字, 有依据率={rag_grounded:.0%} | 纯LLM: {len(plain_resp)}字")
    return results

print("对比测试中（25题）...")
rag_vs_plain = asyncio.run(run_rag_vs_plain())

if rag_vs_plain:
    rag_avg_len = sum(r["rag_len"] for r in rag_vs_plain) / len(rag_vs_plain)
    plain_avg_len = sum(r["plain_len"] for r in rag_vs_plain) / len(rag_vs_plain)
    rag_avg_grounded = sum(r["rag_grounded"] for r in rag_vs_plain) / len(rag_vs_plain)
    plain_avg_grounded = sum(r["plain_grounded"] for r in rag_vs_plain) / len(rag_vs_plain)
    rag_longer = sum(1 for r in rag_vs_plain if r["rag_len"] > r["plain_len"])

    print(f"\n=== RAG vs 纯LLM 总结 ===")
    print(f"RAG平均长度: {rag_avg_len:.0f}字, 纯LLM平均长度: {plain_avg_len:.0f}字")
    print(f"RAG有依据率: {rag_avg_grounded:.0%}, 纯LLM有依据率: {plain_avg_grounded:.0%}")
    print(f"RAG更长比例: {rag_longer}/{len(rag_vs_plain)}")

# ============================================================
# 实验3.2: Top-K值对比
# ============================================================
print("\n" + "=" * 60)
print("实验3.2: Top-K值对比")
print("=" * 60)

async def run_topk_comparison():
    topk_results = []
    # 用前10题做测试
    subset = test_questions[:10]

    for k in [3, 5, 8, 10]:
        print(f"\n  Top-K={k}")
        total_len = 0
        total_grounded = 0
        total_sim = 0
        total_docs = 0
        count = 0

        for i, q in enumerate(subset):
            docs = retrieve(q, top_k=k, threshold=0.0)
            context = "\n\n".join([d["text"] for d in docs])
            rag_sys = f"你是一个教学助手。根据以下参考资料回答问题。\n\n参考资料：\n{context}"
            resp = await call_llm_stream(rag_sys, q)
            await asyncio.sleep(2)

            grounded = check_groundedness(resp, docs)
            avg_sim = sum(d["similarity"] for d in docs) / max(len(docs), 1) if docs else 0

            total_len += len(resp)
            total_grounded += grounded
            total_sim += avg_sim
            total_docs += len(docs)
            count += 1
            print(f"    [{i+1}/10] {q[:15]}... → {len(resp)}字, {len(docs)}片段, 有依据率={grounded:.0%}")

        topk_results.append({
            "top_k": k,
            "avg_len": round(total_len / count, 1),
            "avg_grounded": round(total_grounded / count, 4),
            "avg_sim": round(total_sim / count, 4),
            "avg_docs": round(total_docs / count, 1),
        })
    return topk_results

print("Top-K对比测试中...")
topk_results = asyncio.run(run_topk_comparison())

if topk_results:
    print(f"\n=== Top-K 对比总结 ===")
    print(f"{'Top-K':<8} {'平均长度':<10} {'有依据率':<10} {'平均相似度':<12} {'平均片段数':<10}")
    print("-" * 50)
    for r in topk_results:
        print(f"{r['top_k']:<8} {r['avg_len']:<10.0f} {r['avg_grounded']:<10.0%} {r['avg_sim']:<12.4f} {r['avg_docs']:<10.1f}")

# ============================================================
# 实验3.3: 相似度阈值对比
# ============================================================
print("\n" + "=" * 60)
print("实验3.3: 相似度阈值对比")
print("=" * 60)

async def run_threshold_comparison():
    threshold_results = []
    subset = test_questions[:10]

    for threshold in [0.0, 0.3, 0.5, 0.7]:
        print(f"\n  阈值={threshold}")
        total_len = 0
        total_grounded = 0
        total_docs_before = 0
        total_docs_after = 0
        count = 0

        for i, q in enumerate(subset):
            # 先检索所有（top_k=10），再按阈值过滤
            all_docs = retrieve(q, top_k=10, threshold=0.0)
            filtered_docs = [d for d in all_docs if d["similarity"] >= threshold]

            if filtered_docs:
                context = "\n\n".join([d["text"] for d in filtered_docs])
                rag_sys = f"你是一个教学助手。根据以下参考资料回答问题。\n\n参考资料：\n{context}"
                resp = await call_llm_stream(rag_sys, q)
            else:
                resp = await call_llm_stream("你是一个教学助手。请回答用户的问题。", q)
            await asyncio.sleep(2)

            grounded = check_groundedness(resp, filtered_docs)
            total_len += len(resp)
            total_grounded += grounded
            total_docs_before += len(all_docs)
            total_docs_after += len(filtered_docs)
            count += 1
            print(f"    [{i+1}/10] {q[:15]}... → 过滤前{len(all_docs)}片段, 过滤后{len(filtered_docs)}片段, {len(resp)}字")

        threshold_results.append({
            "threshold": threshold,
            "avg_len": round(total_len / count, 1),
            "avg_grounded": round(total_grounded / count, 4),
            "avg_docs_before": round(total_docs_before / count, 1),
            "avg_docs_after": round(total_docs_after / count, 1),
            "filter_rate": round(1 - (total_docs_after / max(total_docs_before, 1)), 4),
        })
    return threshold_results

print("阈值对比测试中...")
threshold_results = asyncio.run(run_threshold_comparison())

if threshold_results:
    print(f"\n=== 相似度阈值 对比总结 ===")
    print(f"{'阈值':<8} {'过滤前片段':<12} {'过滤后片段':<12} {'过滤率':<10} {'平均长度':<10} {'有依据率':<10}")
    print("-" * 62)
    for r in threshold_results:
        print(f"{r['threshold']:<8} {r['avg_docs_before']:<12.1f} {r['avg_docs_after']:<12.1f} {r['filter_rate']:<10.0%} {r['avg_len']:<10.0f} {r['avg_grounded']:<10.0%}")

# ============================================================
# 保存结果
# ============================================================
print("\n" + "=" * 60)
print("保存实验结果")
print("=" * 60)

all_results = {
    "rag_vs_plain": [{
        "query": r["query"],
        "rag_len": r["rag_len"],
        "rag_grounded": r["rag_grounded"],
        "rag_avg_sim": r["rag_avg_sim"],
        "plain_len": r["plain_len"],
    } for r in rag_vs_plain],
    "topk_comparison": topk_results,
    "threshold_comparison": threshold_results,
}

with open("experiment_quality.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("结果已保存到 experiment_quality.json")
print("测试完成！")
