"""
RAG系统实验测试（修复版）
"""
import os, sys, time, json, statistics
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import chromadb
from chromadb.config import Settings as ChromaSettings
from services.rag_service import get_embedding_fn, embed_texts, chunk_text, get_collection

print("=" * 60)
print("RAG系统实验测试")
print("=" * 60)

# ChromaDB
client = chromadb.PersistentClient(path='chroma_data', settings=ChromaSettings(anonymized_telemetry=False))

# 创建测试数据（用更多内容）
test_col_name = "test_experiment"
try:
    client.delete_collection(name=test_col_name)
except:
    pass
test_col = client.get_or_create_collection(name=test_col_name)

course_materials = [
    "梯度下降算法是机器学习中最基础的优化算法之一。其核心思想是通过迭代的方式，沿着损失函数梯度的反方向更新模型参数，逐步逼近函数的最小值。设损失函数为J(θ)，参数更新公式为θ = θ - α∇J(θ)，其中α为学习率。学习率过大可能导致震荡无法收敛，过小则收敛速度过慢。常见的梯度下降变体包括批量梯度下降（BGD）、随机梯度下降（SGD）和小批量梯度下降（Mini-batch SGD）。SGD每次随机选择一个样本计算梯度，虽然噪声大但能跳出局部最优。Mini-batch SGD兼顾了两者的优点，batch size通常设为32、64、128等。",
    "反向传播算法是训练神经网络的核心算法。它通过链式法则计算损失函数对每个参数的梯度。前向传播时，输入数据从输入层逐层传递到输出层，计算预测值和损失。反向传播时，梯度从输出层向输入层逐层传递，计算每个参数的偏导数。对于第l层的权重W(l)，其梯度∂L/∂W(l) = δ(l) · a(l-1)T，其中δ(l)为第l层的误差项，a(l-1)为上一层的激活值。反向传播的时间复杂度与前向传播相当，约为O(n)，其中n为网络中的参数数量。",
    "线性回归和逻辑回归是两种基本的回归和分类算法。线性回归用于连续值预测，模型为y = wTx + b，通过最小化均方误差MSE = (1/n)Σ(yi - ŷi)²来训练。逻辑回归用于二分类问题，在线性回归基础上加入sigmoid函数σ(z) = 1/(1+e^(-z))将输出映射到(0,1)区间，表示概率。逻辑回归使用交叉熵损失函数L = -[ylog(ŷ) + (1-y)log(1-ŷ)]进行优化。两者都可以使用梯度下降来求解参数。",
    "过拟合是指模型在训练集上表现很好但在测试集上表现差的现象。原因通常是模型过于复杂或训练数据不足。解决过拟合的方法包括：正则化（L1正则化添加λ|w|惩罚项产生稀疏解，L2正则化添加λ||w||²惩罚项使权重趋向较小值）；Dropout训练时随机丢弃部分神经元；早停（Early Stopping）监控验证集损失当不再下降时停止训练；数据增强扩充训练数据。交叉验证也是检测过拟合的重要手段。",
    "卷积神经网络（CNN）是处理图像数据的经典深度学习架构。其核心组件包括：卷积层使用可学习的滤波器在输入上滑动提取局部特征，输出特征图（Feature Map）；池化层对特征图进行下采样减少参数量，常用最大池化和平均池化；全连接层将特征图展平后进行分类或回归。典型的CNN架构如LeNet-5、AlexNet、VGG、ResNet等。ResNet引入了残差连接解决了深层网络的梯度消失问题。",
    "注意力机制（Attention Mechanism）是Transformer架构的核心。自注意力（Self-Attention）的计算过程：首先将输入通过三个线性变换得到Query(Q)、Key(K)、Value(V)，然后计算注意力分数Attention(Q,K,V) = softmax(QKT/√dk)V。多头注意力（Multi-Head Attention）将Q、K、V分成多个头并行计算。Transformer由编码器和解码器组成，每层包含多头注意力和前馈网络，加上残差连接和层归一化。",
    "L1正则化和L2正则化是两种常用的正则化方法。L1正则化（Lasso）在损失函数中添加权重的绝对值之和λΣ|wi|，会产生稀疏解即部分权重变为0，起到特征选择的作用。L2正则化（Ridge）添加权重的平方和λΣwi²，使权重趋向较小的值但不会变为0。从几何角度看，L1正则化的约束区域是菱形更容易在坐标轴上产生交点（稀疏解），L2正则化的约束区域是圆形。Elastic Net结合了L1和L2的优点。",
    "随机森林是一种基于Bagging思想的集成学习算法。其核心思想是构建多棵决策树，每棵树使用随机子集的训练数据和随机子集的特征进行训练，最终通过投票（分类）或平均（回归）得到预测结果。两个关键随机性：样本随机使用Bootstrap采样获得训练子集；特征随机在每个节点分裂时从随机选择的m个特征中选择最优特征。随机森林不容易过拟合，对缺失值和异常值有较好的鲁棒性。",
    "特征工程是机器学习中至关重要的环节，指从原始数据中提取、构造和选择对模型预测有用的特征。主要包括：特征提取从原始数据中提取有意义的特征如TF-IDF；特征变换对特征进行标准化（Z-score）归一化（Min-Max）；特征构造组合已有特征创建新特征如BMI；特征选择从所有特征中选择最相关的子集。好的特征工程往往比选择更复杂的模型更能提升性能。",
    "交叉验证是评估模型泛化能力的重要方法。最常用的是K折交叉验证：将数据集随机分为K个子集，每次用K-1个子集作为训练集，剩余1个作为验证集，重复K次取平均值。K通常取5或10。优点：充分利用数据、评估结果更稳定可靠、能有效检测过拟合。其他变体包括留一交叉验证（LOOCV）和分层交叉验证（Stratified K-Fold）。分层交叉验证确保每个折中各类别的比例与总体一致。",
    "损失函数是衡量模型预测值与真实值之间差异的函数。常见的损失函数包括：均方误差MSE用于回归任务；交叉熵损失用于分类任务；Huber损失结合了MSE和MAE的优点对异常值更鲁棒。对于多分类问题使用softmax交叉熵。损失函数的选择直接影响模型的优化方向和最终性能。在目标检测中还常用IoU Loss和Focal Loss等专门设计的损失函数。",
    "优化算法用于最小化损失函数。除了基础的梯度下降外还有：动量法引入历史梯度的指数移动平均加速收敛；AdaGrad自适应调整学习率对稀疏特征友好；RMSprop改进AdaGrad使用指数衰减避免学习率过快衰减；Adam结合了Momentum和RMSprop的优点是目前最常用的优化器。Adam的默认参数通常为β1=0.9, β2=0.999, ε=1e-8。学习率调度策略如余弦退火、Warmup等也广泛使用。",
    "批归一化（Batch Normalization）是深度网络训练中的重要技术。它在每一层的激活值上进行归一化使其均值为0方差为1，然后通过可学习的缩放和偏移参数恢复表达能力。BN的优点：加速训练收敛、允许使用更大的学习率、起到正则化效果。层归一化（Layer Normalization）是BN的替代方案在Transformer中更常用。实例归一化（Instance Normalization）常用于风格迁移任务。",
    "生成对抗网络（GAN）由生成器G和判别器D组成。生成器接收随机噪声z生成假样本G(z)，判别器判断输入是真实样本还是生成样本。两者通过对抗训练不断改进。训练目标为min_G max_D V(D,G) = E[logD(x)] + E[log(1-D(G(z)))]。GAN的变体包括DCGAN（使用卷积）、WGAN（Wasserstein距离改进训练稳定性）、StyleGAN（实现风格控制）。GAN训练不稳定是主要挑战之一。",
    "强化学习是机器学习的一个分支，智能体通过与环境交互来学习最优策略。核心概念包括状态、动作、奖励、策略。马尔可夫决策过程（MDP）是强化学习的数学框架。Q-learning通过更新Q值表Q(s,a) ← Q(s,a) + α[r + γmax_a'Q(s',a') - Q(s,a)]来学习最优动作价值函数。DQN使用神经网络近似Q函数解决了连续状态空间问题。策略梯度方法直接优化策略函数。",
    "迁移学习是将在一个任务上学到的知识应用到另一个相关任务上的方法。在深度学习中通常使用预训练模型（如在ImageNet上训练的CNN）作为特征提取器或微调的起点。微调（Fine-tuning）是在预训练模型的基础上用目标任务的数据继续训练。迁移学习特别适合目标任务数据较少的场景。常见的策略包括冻结底层参数只训练顶层、逐步解冻、使用不同的学习率等。",
    "支持向量机（SVM）是一种经典的分类算法。其核心思想是找到一个超平面使得两类样本之间的间隔（margin）最大化。对于线性不可分的情况使用核技巧（Kernel Trick）将数据映射到高维空间。常用的核函数包括线性核、多项式核、RBF核（高斯核）。SVM的对偶问题可以高效求解。软间隔SVM引入松弛变量允许部分样本违反间隔约束。SVM在小样本高维数据上表现优异。",
    "主成分分析（PCA）是最常用的降维方法。其目标是找到数据方差最大的方向作为主成分。PCA的计算步骤：1)对数据进行中心化；2)计算协方差矩阵；3)对协方差矩阵进行特征值分解；4)选择前k个最大特征值对应的特征向量。PCA是无监督的线性降维方法。保留的方差比例可以用来评估降维效果。Kernel PCA可以处理非线性降维问题。",
    "K均值聚类（K-Means）是最常用的无监督学习算法之一。算法步骤：1)随机选择K个中心点；2)将每个样本分配到最近的中心点；3)重新计算每个簇的中心；4)重复2-3直到收敛。K值的选择可以使用肘部法则（Elbow Method）或轮廓系数（Silhouette Score）。K-Means的局限性：需要预先指定K值、对初始中心敏感、假设簇为凸形。K-Means++改进了初始化策略。",
    "自然语言处理中的词向量（Word Embedding）将词语映射为稠密向量。Word2Vec是经典的词向量训练方法包括CBOW和Skip-gram两种架构。GloVe利用全局共现矩阵训练词向量。BERT等预训练语言模型生成上下文相关的词向量（同一个词在不同上下文中有不同的向量表示）。词向量的评估包括词类比任务和下游任务性能。余弦相似度常用于衡量词向量之间的语义相似性。",
]

# 分块并索引
all_chunks = []
all_ids = []
all_metas = []
for i, doc in enumerate(course_materials):
    chunks = chunk_text(doc, chunk_size=500, overlap=50)
    for j, chunk in enumerate(chunks):
        all_chunks.append(chunk)
        all_ids.append(f"doc_{i}_chunk_{j}")
        all_metas.append({"doc_index": i, "chunk_index": j, "source": f"doc_{i}"})

print(f"生成 {len(all_chunks)} 个知识片段")
embeddings = embed_texts(all_chunks)
test_col.add(embeddings=embeddings, documents=all_chunks, metadatas=all_metas, ids=all_ids)
print(f"已索引到集合 '{test_col_name}' ({test_col.count()} chunks)")

# BGE模型
print("\n加载BGE模型...")
model = get_embedding_fn()
# 预热：跑几次消除CUDA初始化开销
print("预热中...")
warmup_texts = ["预热文本"] * 10
for _ in range(3):
    model.encode(warmup_texts, normalize_embeddings=True)
print("预热完成")

# ============================================================
# 实验1: Embedding推理耗时
# ============================================================
print("\n" + "=" * 60)
print("实验1: Embedding推理耗时")
print("=" * 60)

test_texts = all_chunks * 5  # 足够多的文本
print(f"测试文本数量: {len(test_texts)}")
print(f"\n{'批量大小':<12} {'推理耗时(ms)':<15} {'单条平均(ms)':<15}")
print("-" * 42)

embedding_results = []
for bs in [1, 5, 10, 20, 50, 100]:
    batch = test_texts[:bs]
    times = []
    for _ in range(5):  # 5次取中位数
        start = time.perf_counter()
        model.encode(batch, normalize_embeddings=True)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    median_time = sorted(times)[len(times)//2]
    per_item = median_time / bs
    embedding_results.append({"batch_size": bs, "total_ms": round(median_time, 1), "per_item_ms": round(per_item, 2)})
    print(f"{bs:<12} {median_time:<15.1f} {per_item:<15.2f}")

# ============================================================
# 实验2: 向量检索响应时间
# ============================================================
print("\n" + "=" * 60)
print("实验2: 向量检索响应时间")
print("=" * 60)

total_chunks = test_col.count()
print(f"集合 '{test_col_name}' 共 {total_chunks} 个chunks")

test_queries = [
    "什么是梯度下降算法",
    "反向传播的原理是什么",
    "线性回归和逻辑回归的区别",
    "如何解决过拟合问题",
    "卷积神经网络的结构",
    "注意力机制的计算过程",
    "L1和L2正则化有什么不同",
    "随机森林的工作原理",
    "什么是特征工程",
    "交叉验证的作用是什么",
]

print(f"\n{'Top-K':<8} {'平均(ms)':<12} {'最小(ms)':<12} {'最大(ms)':<12} {'平均相似度':<12}")
print("-" * 56)

retrieval_results = []
for k in [3, 5, 8, 10]:
    all_times = []
    all_sims = []
    for q in test_queries:
        q_emb = model.encode([q], normalize_embeddings=True).tolist()
        times_k = []
        for _ in range(5):
            start = time.perf_counter()
            results = test_col.query(query_embeddings=q_emb, n_results=k)
            elapsed = (time.perf_counter() - start) * 1000
            times_k.append(elapsed)
        all_times.append(sorted(times_k)[2])  # 中位数
        if results['distances'] and results['distances'][0]:
            sims = [1 - d for d in results['distances'][0]]
            all_sims.extend(sims)

    avg_t = statistics.mean(all_times)
    min_t = min(all_times)
    max_t = max(all_times)
    avg_sim = statistics.mean(all_sims) if all_sims else 0
    retrieval_results.append({"top_k": k, "avg_ms": round(avg_t, 2), "min_ms": round(min_t, 2), "max_ms": round(max_t, 2), "avg_similarity": round(avg_sim, 4)})
    print(f"{k:<8} {avg_t:<12.2f} {min_t:<12.2f} {max_t:<12.2f} {avg_sim:<12.4f}")

# ============================================================
# 实验3: 端到端管线耗时
# ============================================================
print("\n" + "=" * 60)
print("实验3: RAG管线端到端耗时分析")
print("=" * 60)

from settings_app.models import AgentAPIConfig
import asyncio
from services.rag_service import chat_stream_structured

llm_config = AgentAPIConfig.objects.filter(is_active=True).first()
base_url = llm_config.base_url
api_key = llm_config.get_api_key()
model_name = llm_config.default_model
print(f"LLM: {model_name} @ {base_url}")

async def test_e2e(query, top_k=5, threshold=0.0, retries=3):
    """测试单次RAG管线，带重试"""
    for attempt in range(retries):
        try:
            timings = {}
            # 向量化
            t0 = time.perf_counter()
            q_emb = model.encode([query], normalize_embeddings=True).tolist()
            timings['embed'] = (time.perf_counter() - t0) * 1000

            # 检索
            t0 = time.perf_counter()
            results = test_col.query(query_embeddings=q_emb, n_results=top_k)
            timings['retrieve'] = (time.perf_counter() - t0) * 1000

            docs = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    dist = results['distances'][0][i] if results['distances'] else 0
                    if (1 - dist) >= threshold:
                        docs.append(doc)

            # 组装
            t0 = time.perf_counter()
            context = "\n\n".join(docs)
            system = f"你是一个教学助手。根据以下参考资料回答问题。\n\n参考资料：\n{context}"
            messages = [{"role": "system", "content": system}, {"role": "user", "content": query}]
            timings['assemble'] = (time.perf_counter() - t0) * 1000

            # LLM
            t0 = time.perf_counter()
            first_token = None
            full_resp = ""
            async for event in chat_stream_structured(messages, base_url, api_key, model_name):
                if event['type'] == 'content':
                    if first_token is None:
                        first_token = (time.perf_counter() - t0) * 1000
                    full_resp += event['content']
            timings['ttft'] = first_token or 0
            timings['llm_total'] = (time.perf_counter() - t0) * 1000
            timings['e2e'] = timings['embed'] + timings['retrieve'] + timings['assemble'] + timings['llm_total']
            timings['response_len'] = len(full_resp)
            return timings
        except Exception as e:
            if attempt < retries - 1:
                print(f"    重试 ({attempt+1}/{retries}): {e}")
                await asyncio.sleep(2)
            else:
                print(f"    失败: {e}")
                return None

print("\n测试端到端管线（每条查询2次取中位数）...")
e2e_results = []
for i, q in enumerate(test_queries[:8]):
    print(f"  [{i+1}/8] {q}")
    runs = []
    for trial in range(2):
        t = asyncio.run(test_e2e(q))
        if t:
            runs.append(t)
            print(f"    trial{trial+1}: TTFT={t['ttft']:.0f}ms, E2E={t['e2e']:.0f}ms, len={t['response_len']}")
    if runs:
        # 取中位数（如果是2次就取第一次，因为第二次可能有缓存）
        best = runs[0]
        e2e_results.append(best)

if e2e_results:
    print(f"\n{'阶段':<35} {'平均(ms)':<12} {'占比':<8}")
    print("-" * 55)
    avg_embed = statistics.mean([r['embed'] for r in e2e_results])
    avg_retrieve = statistics.mean([r['retrieve'] for r in e2e_results])
    avg_assemble = statistics.mean([r['assemble'] for r in e2e_results])
    avg_ttft = statistics.mean([r['ttft'] for r in e2e_results])
    avg_gen = statistics.mean([r['llm_total'] - r['ttft'] for r in e2e_results])
    avg_e2e = statistics.mean([r['e2e'] for r in e2e_results])

    stages = [
        ("Query向量化（BGE Embedding）", avg_embed),
        ("向量检索（ChromaDB Top-K）", avg_retrieve),
        ("上下文组装（模板渲染+Token计数）", avg_assemble),
        ("LLM首Token等待", avg_ttft),
        ("LLM流式生成（全部Token）", avg_gen),
    ]
    for name, ms in stages:
        pct = ms / avg_e2e * 100 if avg_e2e > 0 else 0
        print(f"{name:<35} {ms:<12.1f} {pct:.1f}%")
    print(f"{'端到端总计':<35} {avg_e2e:<12.1f} 100%")

    # 每条查询详情
    print(f"\n各查询详情:")
    print(f"{'查询':<20} {'embed':>7} {'retr':>7} {'TTFT':>8} {'生成':>8} {'E2E':>8} {'长度':>6}")
    print("-" * 66)
    for r in e2e_results:
        gen = r['llm_total'] - r['ttft']
        print(f"{r.get('query','')[:19]:<20} {r['embed']:>7.0f} {r['retrieve']:>7.1f} {r['ttft']:>8.0f} {gen:>8.0f} {r['e2e']:>8.0f} {r['response_len']:>6}")

# ============================================================
# 实验4: RAG vs 纯LLM
# ============================================================
print("\n" + "=" * 60)
print("实验4: RAG vs 纯LLM回答质量对比")
print("=" * 60)

async def call_llm(system_msg, user_msg, retries=5):
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
                print(f"    LLM调用失败: {e}")
                return ""

async def run_comparison():
    results = []
    for i, q in enumerate(test_queries[:6]):
        print(f"  [{i+6}/12] {q}")

        # RAG回答
        q_emb = model.encode([q], normalize_embeddings=True).tolist()
        search = test_col.query(query_embeddings=q_emb, n_results=5)
        docs = search['documents'][0] if search['documents'] else []
        context = "\n\n".join(docs)
        rag_sys = f"你是一个教学助手。根据以下参考资料回答问题。\n\n参考资料：\n{context}"
        rag_resp = await call_llm(rag_sys, q)
        await asyncio.sleep(3)

        # 纯LLM回答
        plain_resp = await call_llm("你是一个教学助手。请回答用户的问题。", q)
        await asyncio.sleep(3)

        results.append({
            "query": q,
            "rag_response": rag_resp,
            "rag_len": len(rag_resp),
            "plain_response": plain_resp,
            "plain_len": len(plain_resp),
        })
        print(f"    RAG: {len(rag_resp)}字, 纯LLM: {len(plain_resp)}字")
    return results

print("对比测试中...")
comparison = asyncio.run(run_comparison())

if comparison:
    print(f"\n{'查询':<25} {'RAG(字)':<10} {'纯LLM(字)':<12} {'RAG更长':<8}")
    print("-" * 55)
    rag_total = 0
    plain_total = 0
    rag_longer = 0
    for c in comparison:
        longer = "是" if c['rag_len'] > c['plain_len'] else "否"
        if c['rag_len'] > c['plain_len']:
            rag_longer += 1
        rag_total += c['rag_len']
        plain_total += c['plain_len']
        print(f"{c['query'][:24]:<25} {c['rag_len']:<10} {c['plain_len']:<12} {longer:<8}")

    n = len(comparison)
    print(f"\n平均: RAG={rag_total//n}字, 纯LLM={plain_total//n}字, RAG更长比例={rag_longer}/{n}")

    with open("experiment_comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

# ============================================================
# 保存结果
# ============================================================
print("\n" + "=" * 60)
print("保存实验结果")
print("=" * 60)

all_results = {
    "embedding_performance": embedding_results,
    "retrieval_performance": retrieval_results,
    "e2e_pipeline": [{k: v for k, v in r.items() if k != 'query'} for r in e2e_results] if e2e_results else [],
    "e2e_queries": [r.get('query', '') for r in e2e_results] if e2e_results else [],
}
with open("experiment_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print("结果已保存到 experiment_results.json 和 experiment_comparison.json")
print("测试完成！")
