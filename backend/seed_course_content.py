"""
为「机器学习」课程生成完整的课程知识内容并索引到ChromaDB。
"""
import os, sys, time
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from services.rag_service import get_embedding_fn, embed_texts, chunk_text, get_collection, delete_collection

COURSE_ID = 2
COLLECTION_NAME = f"course_{COURSE_ID}"

print(f"=== 为课程「机器学习」(ID={COURSE_ID}) 生成知识库 ===\n")

# ── 课程内容（10章，每章约2000-3000字） ──────────────────────
chapters = {
    "第1章 绪论": """机器学习是人工智能的一个重要分支，它使计算机能够从数据中学习规律，而无需显式编程。机器学习的核心思想是通过算法从历史数据中提取模式，并利用这些模式对新数据进行预测或决策。

机器学习的发展历程可以追溯到20世纪50年代。1956年，Arthur Samuel在IBM开发了一个跳棋程序，首次提出了"机器学习"的概念。此后，感知机（Perceptron）、决策树、神经网络等算法相继被提出。进入21世纪，随着大数据和计算能力的提升，深度学习技术取得了突破性进展。

机器学习主要分为三类：监督学习（Supervised Learning）、无监督学习（Unsupervised Learning）和强化学习（Reinforcement Learning）。监督学习通过带标签的训练数据学习输入到输出的映射关系，典型任务包括分类和回归。无监督学习在没有标签的情况下发现数据中的结构和模式，典型任务包括聚类和降维。强化学习通过与环境的交互，基于奖励信号学习最优策略。

机器学习的基本流程包括：数据收集、数据预处理、特征工程、模型选择、模型训练、模型评估和模型部署。数据质量对模型性能有着决定性的影响，因此数据预处理和特征工程是机器学习实践中至关重要的环节。

评估机器学习模型性能的常用指标包括：准确率（Accuracy）、精确率（Precision）、召回率（Recall）、F1值、均方误差（MSE）、决定系数（R²）等。选择合适的评估指标需要根据具体的任务类型和业务需求来决定。""",

    "第2章 线性模型": """线性模型是最基础的机器学习算法之一，其核心思想是通过特征的线性组合来进行预测。

线性回归（Linear Regression）用于连续值预测。模型形式为 y = w^T x + b，其中w为权重向量，b为偏置项。训练目标是最小化均方误差（MSE）：L = (1/n) Σ(y_i - ŷ_i)²。求解方法包括正规方程法（解析解）和梯度下降法（迭代解）。正规方程为 w = (X^T X)^{-1} X^T y，当特征维度很高时计算代价较大。梯度下降法通过迭代更新参数：w = w - α ∂L/∂w，其中α为学习率。

逻辑回归（Logistic Regression）用于二分类问题。在线性回归基础上加入sigmoid函数：σ(z) = 1/(1+e^{-z})，将输出映射到(0,1)区间表示概率。使用交叉熵损失函数：L = -[y·log(ŷ) + (1-y)·log(1-ŷ)]。逻辑回归的决策边界是线性的，对于线性不可分的问题需要引入特征变换或使用核方法。

正则化是防止过拟合的重要手段。L1正则化（Lasso）添加λΣ|w_i|惩罚项，产生稀疏解，可用于特征选择。L2正则化（Ridge）添加λΣw_i²惩罚项，使权重趋向较小值。Elastic Net结合了L1和L2正则化。正则化强度λ需要通过交叉验证来选择。

岭回归（Ridge Regression）是线性回归的L2正则化版本，其解析解为 w = (X^T X + λI)^{-1} X^T y。岭回归在特征之间存在多重共线性时特别有用，因为正则化项使得矩阵X^T X + λI一定可逆。

线性模型的优点是模型简单、可解释性强、计算效率高。缺点是只能捕捉线性关系，对于复杂的非线性模式需要进行特征变换。""",

    "第3章 决策树与集成学习": """决策树是一种基于树结构的分类与回归算法，其核心思想是通过一系列的判断规则对数据进行划分。

决策树的构建过程是递归地选择最优特征进行分裂。特征选择的准则包括：信息增益（ID3算法使用）、信息增益比（C4.5算法使用）和基尼指数（CART算法使用）。信息增益定义为：IG(D,A) = H(D) - H(D|A)，其中H(D)为数据集的经验熵，H(D|A)为特征A给定条件下数据集的条件熵。基尼指数定义为：Gini(D) = 1 - Σp_k²，基尼指数越小说明数据集的纯度越高。

决策树容易过拟合，剪枝是控制过拟合的主要方法。预剪枝在树的构建过程中提前停止，后剪枝在树构建完成后再进行简化。常用的剪枝方法包括代价复杂度剪枝（CCP）。

集成学习通过组合多个基学习器来提升性能。Bagging（Bootstrap Aggregating）通过对训练集进行有放回采样，训练多个基学习器，然后通过投票（分类）或平均（回归）得到最终结果。随机森林（Random Forest）是Bagging的代表算法，在Bagging的基础上引入了特征随机选择，每棵树在每个节点分裂时只考虑随机选择的m个特征。

Boosting通过顺序地训练基学习器，每个新的基学习器重点关注前一个学习器预测错误的样本。AdaBoost通过调整样本权重来实现，权重更新规则为：w_i = w_i × exp(-α_t y_i h_t(x_i))。梯度提升（Gradient Boosting）通过拟合残差来逐步改进模型。XGBoost和LightGBM是梯度提升的高效实现。

随机森林的优点包括：不容易过拟合、对缺失值和异常值鲁棒、能评估特征重要性。缺点是模型可解释性较差、在高维稀疏数据上表现不如线性模型。""",

    "第4章 支持向量机": """支持向量机（Support Vector Machine, SVM）是一种经典的分类算法，其核心思想是找到一个超平面使得两类样本之间的间隔（margin）最大化。

对于线性可分的情况，SVM的目标是求解以下优化问题：min (1/2)||w||²，约束条件为 y_i(w^T x_i + b) ≥ 1。这个优化问题可以通过拉格朗日对偶方法求解。对偶问题为：max Σα_i - (1/2)ΣΣα_i α_j y_i y_j x_i^T x_j，约束条件为 α_i ≥ 0 且 Σα_i y_i = 0。

支持向量是距离超平面最近的样本点，它们决定了超平面的位置。间隔定义为 2/||w||，最大化间隔等价于最小化 ||w||²。

对于线性不可分的情况，引入松弛变量 ξ_i ≥ 0，允许部分样本违反间隔约束。优化问题变为：min (1/2)||w||² + CΣξ_i，其中C为惩罚参数，控制对误分类的容忍程度。C越大对误分类的惩罚越重，可能导致过拟合；C越小允许更多的误分类，可能导致欠拟合。

核技巧（Kernel Trick）是SVM处理非线性问题的关键。通过核函数 K(x_i, x_j) = φ(x_i)^T φ(x_j) 将数据隐式映射到高维空间，而无需显式计算高维映射。常用的核函数包括：线性核 K(x,y) = x^T y；多项式核 K(x,y) = (x^T y + c)^d；RBF核（高斯核） K(x,y) = exp(-γ||x-y||²)。RBF核是最常用的核函数，γ参数控制核的宽度。

SVM的求解通常使用序列最小优化算法（SMO），它将大优化问题分解为一系列小的子问题来求解。SVM在小样本高维数据上表现优异，但在大规模数据集上训练时间较长。""",

    "第5章 神经网络基础": """神经网络是一种受生物神经系统启发的计算模型，由大量的神经元（节点）相互连接组成。

单个神经元的计算过程为：z = Σw_i x_i + b，a = f(z)，其中w_i为权重，b为偏置，f为激活函数。常用的激活函数包括：sigmoid函数 σ(z) = 1/(1+e^{-z})，输出范围(0,1)；tanh函数 tanh(z) = (e^z - e^{-z})/(e^z + e^{-z})，输出范围(-1,1)；ReLU函数 ReLU(z) = max(0,z)，计算简单且能缓解梯度消失问题。

多层感知机（MLP）是最基本的前馈神经网络，由输入层、隐藏层和输出层组成。每层的神经元与下一层的神经元全连接。前向传播过程：输入数据逐层计算，得到最终输出。反向传播算法（Backpropagation）通过链式法则计算损失函数对每个参数的梯度。

反向传播的核心公式：设第l层的误差项为 δ^l，则 δ^l = (W^{l+1})^T δ^{l+1} ⊙ f'(z^l)，权重梯度为 ∂L/∂W^l = δ^l (a^{l-1})^T，偏置梯度为 ∂L/∂b^l = δ^l。其中⊙表示逐元素乘法。

梯度消失和梯度爆炸是深层网络训练中的主要问题。梯度消失是指在反向传播过程中，梯度逐层衰减到接近零，导致底层参数无法有效更新。梯度爆炸则是梯度逐层放大到极大值。解决方案包括：使用ReLU激活函数、批归一化（Batch Normalization）、残差连接（Residual Connection）、梯度裁剪（Gradient Clipping）。

权重初始化对网络训练有重要影响。Xavier初始化适用于sigmoid和tanh激活函数：W ~ N(0, 1/n_in)。He初始化适用于ReLU激活函数：W ~ N(0, 2/n_in)。合理的初始化可以保证各层的方差一致，避免梯度消失或爆炸。""",

    "第6章 卷积神经网络": """卷积神经网络（Convolutional Neural Network, CNN）是处理网格结构数据（如图像）的经典深度学习架构。

卷积层是CNN的核心组件。卷积操作通过可学习的卷积核（滤波器）在输入特征图上滑动，计算局部区域的加权和。输出特征图的尺寸计算公式：H_out = (H_in - K + 2P)/S + 1，其中K为卷积核大小，P为填充大小，S为步幅。卷积层的参数量为 K × K × C_in × C_out + C_out，远少于全连接层。

池化层（Pooling Layer）对特征图进行下采样，减少空间维度和参数量。最大池化（Max Pooling）取局部区域的最大值，平均池化（Average Pooling）取局部区域的平均值。全局平均池化（Global Average Pooling）将整个特征图平均为一个值，常用于替代最后的全连接层。

经典CNN架构：LeNet-5（1998）是最早的CNN架构，用于手写数字识别。AlexNet（2012）在ImageNet竞赛中取得突破性成绩，使用ReLU和Dropout。VGGNet（2014）使用3×3的小卷积核堆叠。GoogLeNet/Inception（2014）引入Inception模块。ResNet（2015）引入残差连接，解决了深层网络的退化问题，使得训练数百层的网络成为可能。

残差连接（Skip Connection）的形式为 y = F(x) + x，其中F(x)为残差函数。残差连接使得梯度可以直接从深层传到浅层，有效缓解了梯度消失问题。DenseNet进一步加强了层间的连接，每一层都与前面所有层连接。

CNN在计算机视觉领域有着广泛的应用，包括图像分类、目标检测（YOLO、Faster R-CNN）、语义分割（FCN、U-Net）、图像生成（GAN）等。""",

    "第7章 循环神经网络与序列模型": """循环神经网络（Recurrent Neural Network, RNN）是处理序列数据的神经网络架构，其核心特点是网络具有循环连接，能够捕捉序列中的时序依赖关系。

RNN的隐藏状态计算公式：h_t = f(W_hh h_{t-1} + W_xh x_t + b)，其中h_t为t时刻的隐藏状态，x_t为t时刻的输入，W_hh为隐藏层权重，W_xh为输入权重。输出为 y_t = W_hy h_t + b_y。

标准RNN存在长期依赖问题，即难以捕捉长距离的依赖关系。原因是梯度在反向传播过程中需要经过多次矩阵乘法，容易出现梯度消失或梯度爆炸。

长短期记忆网络（LSTM）通过引入门控机制解决了长期依赖问题。LSTM包含三个门：遗忘门 f_t = σ(W_f [h_{t-1}, x_t] + b_f)，决定丢弃哪些信息；输入门 i_t = σ(W_i [h_{t-1}, x_t] + b_i)，决定更新哪些信息；输出门 o_t = σ(W_o [h_{t-1}, x_t] + b_o)，决定输出哪些信息。细胞状态 c_t = f_t ⊙ c_{t-1} + i_t ⊙ tanh(W_c [h_{t-1}, x_t] + b_c)。

门控循环单元（GRU）是LSTM的简化版本，将遗忘门和输入门合并为更新门，将细胞状态和隐藏状态合并。GRU的参数量比LSTM少，训练速度更快，在某些任务上性能与LSTM相当。

双向RNN（BiRNN）同时从前往后和从后往前处理序列，能够捕捉双向的上下文信息。深层RNN（Stacked RNN）通过堆叠多个RNN层来增加模型的表达能力。

序列到序列（Seq2Seq）模型由编码器和解码器组成。编码器将输入序列编码为一个固定长度的向量，解码器从这个向量生成输出序列。注意力机制的引入使得解码器可以关注输入序列的不同部分，显著提升了Seq2Seq模型的性能。

RNN的典型应用包括：语言模型、机器翻译、文本生成、语音识别、时间序列预测等。""",

    "第8章 注意力机制与Transformer": """注意力机制（Attention Mechanism）是深度学习中的重要技术，最初被用于改进Seq2Seq模型，后来成为Transformer架构的核心。

注意力机制的基本思想是：在处理序列数据时，模型应该动态地关注输入中与当前任务最相关的部分。给定查询向量Q、键向量K和值向量V，注意力计算公式为：Attention(Q,K,V) = softmax(QK^T / √d_k) V，其中d_k为键向量的维度，√d_k为缩放因子，防止内积过大导致softmax梯度消失。

自注意力（Self-Attention）是指Q、K、V都来自同一个序列。自注意力能够捕捉序列内部的长距离依赖关系，计算复杂度为O(n²)，其中n为序列长度。

多头注意力（Multi-Head Attention）将Q、K、V通过不同的线性变换投影到多个子空间，在每个子空间中独立计算注意力，然后将结果拼接并线性变换。公式为：MultiHead(Q,K,V) = Concat(head_1, ..., head_h) W^O，其中head_i = Attention(QW_i^Q, KW_i^K, VW_i^V)。

Transformer架构完全基于注意力机制，摒弃了RNN的循环结构。编码器由N个相同的层组成，每层包含多头自注意力和前馈神经网络，加上残差连接和层归一化。解码器在编码器的基础上增加了交叉注意力层，关注编码器的输出。

位置编码（Positional Encoding）用于为输入序列注入位置信息，因为Transformer本身不具有时序感知能力。原始论文使用正弦和余弦函数：PE(pos,2i) = sin(pos/10000^{2i/d})，PE(pos,2i+1) = cos(pos/10000^{2i/d})。

Transformer的优点：并行化训练、捕捉长距离依赖、可扩展性强。基于Transformer的预训练语言模型包括BERT（双向编码器）、GPT系列（自回归解码器）、T5（编码器-解码器）等。""",

    "第9章 无监督学习与降维": """无监督学习在没有标签的情况下发现数据中的结构和模式，主要任务包括聚类、降维和密度估计。

K均值聚类（K-Means）是最常用的聚类算法。算法步骤：1)随机选择K个中心点；2)将每个样本分配到最近的中心点；3)重新计算每个簇的中心；4)重复直到收敛。K值的选择可以使用肘部法则（Elbow Method）或轮廓系数（Silhouette Score）。K-Means++改进了初始化策略，选择与已有中心点距离较远的点作为新的中心点。K-Means的局限性：需要预先指定K值、对初始中心敏感、假设簇为凸形。

层次聚类（Hierarchical Clustering）通过自底向上（凝聚）或自顶向下（分裂）的方式构建树状的聚类结构。凝聚层次聚类从每个样本作为一个簇开始，每次合并距离最近的两个簇。距离度量包括：单链接（最近点距离）、全链接（最远点距离）、平均链接（平均距离）、Ward方法（方差增量）。

DBSCAN（Density-Based Spatial Clustering of Applications with Noise）是基于密度的聚类算法。核心概念：核心点（邻域内至少有MinPts个样本）、边界点（在核心点的邻域内但本身不是核心点）、噪声点。DBSCAN的优点是不需要预先指定簇数、能发现任意形状的簇、对噪声鲁棒。

主成分分析（PCA）是最常用的降维方法。PCA的目标是找到数据方差最大的方向作为主成分。计算步骤：1)对数据进行中心化；2)计算协方差矩阵；3)对协方差矩阵进行特征值分解；4)选择前k个最大特征值对应的特征向量。保留的方差比例可以用来评估降维效果。

t-SNE（t-distributed Stochastic Neighbor Embedding）是一种非线性降维方法，特别适合高维数据的可视化。t-SNE通过保持高维空间和低维空间中样本之间的概率分布相似性来实现降维。UMAP（Uniform Manifold Approximation and Projection）是另一种非线性降维方法，速度比t-SNE快，且能更好地保持数据的全局结构。""",

    "第10章 模型评估与选择": """模型评估与选择是机器学习流程中的关键环节，直接影响模型的泛化性能。

训练集、验证集和测试集的划分是模型评估的基础。常用的划分方法包括：留出法（Hold-out）将数据按比例划分为训练集和测试集；K折交叉验证将数据分为K份，轮流用其中K-1份训练、1份验证；留一交叉验证（LOOCV）是K=N的特殊情况。分层采样（Stratified Sampling）确保各子集中类别比例与总体一致。

偏差-方差分解（Bias-Variance Decomposition）是理解模型泛化能力的重要框架。泛化误差 = 偏差² + 方差 + 噪声。偏差衡量模型的预测与真实值之间的系统性偏差，高偏差意味着欠拟合。方差衡量模型对训练数据变化的敏感程度，高方差意味着过拟合。模型复杂度与偏差-方差之间存在权衡关系。

超参数调优是选择模型最优超参数的过程。常用方法包括：网格搜索（Grid Search）遍历所有参数组合；随机搜索（Random Search）从参数分布中随机采样；贝叶斯优化（Bayesian Optimization）建立代理模型来指导搜索。

评估指标的选择需要根据任务类型和业务需求。二分类常用指标：准确率、精确率、召回率、F1值、AUC-ROC曲线、AUC-PR曲线。多分类常用指标：宏平均（Macro-average）、微平均（Micro-average）、加权平均。回归常用指标：MSE、RMSE、MAE、R²。

模型选择需要考虑多个因素：数据量大小、特征维度、计算资源、可解释性需求、实时性要求等。没有一个模型在所有情况下都是最好的，这就是没有免费午餐定理（No Free Lunch Theorem）的核心观点。

特征选择方法包括：过滤法（方差阈值、相关系数、互信息）、包装法（递归特征消除RFE）、嵌入法（L1正则化、树模型特征重要性）。特征选择可以减少过拟合、提高计算效率、增强模型可解释性。""",
}

# ── 分块并索引 ──────────────────────────────────────────────
print(f"共 {len(chapters)} 章课程内容\n")

# 清理旧集合
delete_collection(COLLECTION_NAME)
collection = get_collection(COLLECTION_NAME)

all_chunks = []
all_ids = []
all_metas = []

for chapter_title, content in chapters.items():
    chunks = chunk_text(content, chunk_size=500, overlap=50)
    print(f"  {chapter_title}: {len(chunks)} 个分块")
    for j, chunk in enumerate(chunks):
        all_chunks.append(chunk)
        all_ids.append(f"{chapter_title}_chunk_{j}")
        all_metas.append({
            "source": chapter_title,
            "chunk_index": j,
            "course_id": COURSE_ID,
            "course_name": "机器学习",
        })

print(f"\n总计 {len(all_chunks)} 个知识片段，正在向量化...")
start = time.perf_counter()
embeddings = embed_texts(all_chunks)
elapsed = time.perf_counter() - start
print(f"向量化完成，耗时 {elapsed:.1f}s")

collection.add(embeddings=embeddings, documents=all_chunks, metadatas=all_metas, ids=all_ids)
print(f"已索引到集合 '{COLLECTION_NAME}'，共 {collection.count()} 个chunks")

# 验证检索
print("\n=== 验证检索 ===")
test_queries = ["什么是梯度下降", "CNN的结构", "LSTM和RNN的区别"]
for q in test_queries:
    q_emb = embed_texts([q])
    results = collection.query(query_embeddings=q_emb, n_results=3)
    print(f"\n查询: {q}")
    for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0])):
        sim = 1 - dist
        print(f"  [{i+1}] 相似度={sim:.3f} | {doc[:60]}...")

print("\n完成！")
