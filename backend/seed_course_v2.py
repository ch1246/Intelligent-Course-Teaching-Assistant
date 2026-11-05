import os, sys, time
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from services.rag_service import get_embedding_fn, embed_texts, chunk_text, get_collection, delete_collection

COLLECTION_NAME = 'course_2'
delete_collection(COLLECTION_NAME)
collection = get_collection(COLLECTION_NAME)

# 10章课程 + 每章补充详细内容
chapters = {
    '第1章 绪论': '机器学习是人工智能的一个重要分支,它使计算机能够从数据中学习规律而无需显式编程。机器学习的核心思想是通过算法从历史数据中提取模式,并利用这些模式对新数据进行预测或决策。机器学习的发展历程可以追溯到20世纪50年代。1956年Arthur Samuel在IBM开发了一个跳棋程序首次提出了机器学习的概念。此后感知机、决策树、神经网络等算法相继被提出。进入21世纪随着大数据和计算能力的提升深度学习技术取得了突破性进展。机器学习主要分为三类:监督学习、无监督学习和强化学习。监督学习通过带标签的训练数据学习输入到输出的映射关系典型任务包括分类和回归。无监督学习在没有标签的情况下发现数据中的结构和模式典型任务包括聚类和降维。强化学习通过与环境的交互基于奖励信号学习最优策略。机器学习的基本流程包括:数据收集、数据预处理、特征工程、模型选择、模型训练、模型评估和模型部署。评估指标包括准确率Accuracy、精确率Precision、召回率Recall、F1值、均方误差MSE、决定系数R2等。',
    '第2章 线性模型': '线性模型是最基础的机器学习算法之一。线性回归用于连续值预测模型形式为y=wTx+b通过最小化均方误差MSE训练。正规方程解析解为w=(XTX)-1XTy。梯度下降法通过迭代更新参数w=w-alpha*梯度。逻辑回归用于二分类问题加入sigmoid函数sigma(z)=1/(1+e(-z))将输出映射到0-1区间表示概率使用交叉熵损失函数。正则化是防止过拟合的重要手段。L1正则化Lasso添加lambda*|w|惩罚项产生稀疏解可用于特征选择。L2正则化Ridge添加lambda*w2惩罚项使权重趋向较小值。Elastic Net结合L1和L2。岭回归是L2正则化的线性回归版本解析解为w=(XTX+lambdaI)-1XTy。线性模型的优点是简单可解释性强计算效率高缺点是只能捕捉线性关系。',
    '第3章 决策树与集成学习': '决策树是基于树结构的分类与回归算法。特征选择准则包括信息增益ID3使用、信息增益比C4.5使用和基尼指数CART使用。信息增益IG(D,A)=H(D)-H(D|A)其中H(D)为经验熵H(D|A)为条件熵。基尼指数Gini(D)=1-Sum(pk2)越小纯度越高。决策树容易过拟合剪枝是控制过拟合的主要方法。集成学习通过组合多个基学习器提升性能。Bagging通过对训练集Bootstrap采样训练多个基学习器通过投票或平均得到结果。随机森林是Bagging的代表在Bagging基础上引入特征随机选择。Boosting顺序训练基学习器每个重点关注前一个预测错误的样本。AdaBoost通过调整样本权重实现。梯度提升通过拟合残差逐步改进模型。XGBoost和LightGBM是高效实现。随机森林优点:不容易过拟合、对缺失值鲁棒、能评估特征重要性。',
    '第4章 支持向量机': 'SVM找到最大间隔超平面分类数据。对于线性可分情况目标是min(1/2)||w||2约束yi(wTxi+b)>=1。通过拉格朗日对偶方法求解对偶问题max Sum(alpha_i)-(1/2)Sum(alpha_i*alpha_j*yi*yj*xiTxj)。支持向量是距离超平面最近的样本点。间隔定义为2/||w||。对于线性不可分引入松弛变量和惩罚参数C。核技巧是SVM处理非线性问题的关键通过核函数K(xi,xj)将数据隐式映射到高维空间。常用核函数:线性核K(x,y)=xTy;多项式核K(x,y)=(xTy+c)d;RBF核K(x,y)=exp(-gamma||x-y||2)。RBF核最常用gamma控制核宽度。SMO算法用于高效求解。SVM在小样本高维数据上表现优异。',
    '第5章 神经网络基础': '神经网络由大量神经元相互连接组成。单个神经元计算z=Sum(wi*xi)+b然后通过激活函数a=f(z)。常用激活函数:sigmoid输出0-1;tanh输出-1到1;ReLU计算简单且缓解梯度消失。多层感知机MLP由输入层、隐藏层和输出层组成。前向传播逐层计算得到输出。反向传播通过链式法则计算梯度。核心公式:误差项delta_l=((Wl+1)T*delta_l+1)*f(zl);权重梯度dL/dWl=delta_l*(al-1)T;偏置梯度dL/dbl=delta_l。梯度消失和爆炸是深层网络主要问题。解决方案:ReLU激活、批归一化BN、残差连接、梯度裁剪。权重初始化:Xavier适用于sigmoid/tanh;He初始化适用于ReLU。合理的初始化保证各层方差一致。',
    '第6章 卷积神经网络': 'CNN是处理图像数据的经典架构。卷积层通过卷积核在输入上滑动提取局部特征。输出尺寸Hout=(Hin-K+2P)/S+1其中K为核大小P为填充S为步幅。池化层下采样减少参数:最大池化取局部最大值、平均池化取局部平均值、全局平均池化将整个特征图平均为一个值。经典架构:LeNet-5最早用于手写数字识别;AlexNet使用ReLU和Dropout;VGG使用3x3小卷积核堆叠;GoogLeNet引入Inception模块;ResNet引入残差连接解决深层退化问题。残差连接y=F(x)+x使得梯度可以直接从深层传到浅层。DenseNet密集连接每一层与前面所有层连接。CNN应用:图像分类、目标检测YOLO/Faster R-CNN、语义分割FCN/U-Net、图像生成GAN。',
    '第7章 循环神经网络与序列模型': 'RNN通过循环连接处理序列数据。隐藏状态ht=f(Whh*ht-1+Wxh*xt+b)。标准RNN存在长期依赖问题梯度容易消失或爆炸。LSTM通过门控机制解决:遗忘门ft决定丢弃哪些信息;输入门it决定更新哪些信息;输出门ot决定输出哪些信息。细胞状态Ct=ft*Ct-1+it*Ct_tilde。GRU是LSTM简化版本将遗忘门和输入门合并为更新门参数量更少。双向RNN同时从前后两个方向处理捕捉双向上下文。Seq2Seq模型由编码器和解码器组成。注意力机制使得解码器关注输入不同部分。RNN应用:语言模型、机器翻译、文本生成、语音识别、时间序列预测。',
    '第8章 注意力机制与Transformer': '注意力机制动态关注输入中最相关的部分。计算公式Attention(Q,K,V)=softmax(QKT/sqrt(dk))V其中sqrt(dk)为缩放因子防止梯度消失。自注意力QKV都来自同一序列能捕捉长距离依赖。多头注意力将QKV投影到多个子空间独立计算后拼接。Transformer完全基于注意力摒弃RNN循环结构。编码器由N层组成每层含多头自注意力和前馈网络加残差连接和层归一化。位置编码用正弦余弦函数注入位置信息PE(pos,2i)=sin(pos/10000(2i/d))。优点:并行训练、捕捉长距离依赖、可扩展性强。BERT双向编码器;GPT自回归解码器;T5编码器-解码器。',
    '第9章 无监督学习与降维': 'K-Means聚类:随机选K个中心点,将样本分配到最近中心,重新计算中心,重复直到收敛。K值用肘部法则或轮廓系数选择。K-Means++改进初始化选择与已有中心距离较远的点。层次聚类自底向上凝聚或自顶向下分裂构建树状结构。DBSCAN基于密度的聚类:核心点邻域至少MinPts个样本、边界点、噪声点。优点不需要指定簇数能发现任意形状的簇。PCA主成分分析找到最大方差方向:中心化数据、计算协方差矩阵、特征值分解、选前k个特征向量。保留方差比例评估降维效果。t-SNE非线性降维适合高维可视化。UMAP速度更快且保持全局结构。',
    '第10章 模型评估与选择': '训练集、验证集、测试集划分:留出法按比例划分;K折交叉验证轮流用K-1份训练1份验证;分层采样确保类别比例一致。偏差-方差分解:泛化误差=偏差2+方差+噪声。高偏差意味着欠拟合高方差意味着过拟合。超参数调优:网格搜索遍历所有组合;随机搜索从分布中采样;贝叶斯优化建立代理模型指导搜索。评估指标:二分类用准确率、精确率、召回率、F1、AUC-ROC;多分类用宏平均微平均加权平均;回归用MSE、RMSE、MAE、R2。特征选择:过滤法方差阈值相关系数互信息;包装法递归特征消除RFE;嵌入法L1正则化树模型特征重要性。没有免费午餐定理:没有一个模型在所有情况下都是最好的。',
    '第2章 正规方程推导': '线性回归正规方程的详细推导。设训练数据为(xi,yi)设计矩阵X每一行为一个样本目标向量为y。均方误差损失L(w)=(1/2)||Xw-y||2。对w求导并令为零:dL/dw=XT(Xw-y)=0展开得XTXw=XTy。当XTX可逆时正规方程解析解w=(XTX)-1XTy。时间复杂度O(n3)其中n为特征维度。当特征维度很高n>10000时建议使用梯度下降。当XTX不可逆时(完全共线性或样本数少于特征数)可使用岭回归w=(XTX+lambdaI)-1XTy。',
    '第3章 信息增益计算': '信息增益的详细计算。数据集D的经验熵H(D)=-Sum(|Ck|/|D|)*log2(|Ck|/|D|)其中Ck为第k类样本集合。特征A对D的信息增益IG(D,A)=H(D)-H(D|A)。条件熵H(D|A)=Sum(|Di|/|D|)*H(Di)其中Di为特征A取第i个值的样本子集。信息增益越大说明分裂后纯度提升越大。ID3用信息增益但偏向取值多的特征。C4.5用信息增益比IGR(D,A)=IG(D,A)/HA(D)修正偏差。',
    '第5章 反向传播推导': '反向传播详细推导。网络有L层第l层输出al=f(zl)其中zl=Wl*al-1+bl。输出层误差deltaL=dL/dzL=dL/dAL*f(zL)。隐藏层误差递推:deltal=((Wl+1)T*deltal+1)*f(zl)。权重梯度dL/dWl=deltal*(al-1)T。偏置梯度dL/dbl=deltal。sigmoid导数f(z)=f(z)(1-f(z));ReLU导数f(z)=1 if z>0 else 0。反向传播时间复杂度与前向传播相同为O(n)其中n为参数总数。',
    '第6章 ResNet残差学习': 'ResNet核心是残差连接。对于期望映射H(x)网络学习残差F(x)=H(x)-x输出y=F(x)+x。优势:1)梯度通过跳跃连接直接从深层传到浅层缓解梯度消失;2)当最优映射接近恒等映射时学习F(x)=0比H(x)=x更容易。ResNet-50用bottleneck:1x1降维然后3x3卷积然后1x1升维加残差连接。变体:ResNeXt分组卷积、DenseNet密集连接、SENet通道注意力。',
    '第8章 位置编码': 'Transformer位置编码公式:PE(pos,2i)=sin(pos/10000(2i/d))PE(pos,2i+1)=cos(pos/10000(2i/d))。优点:1)每个位置编码唯一;2)对于固定偏移k PE(pos+k)可表示为PE(pos)的线性函数使模型学习相对位置;3)编码值有界不发散。位置编码与词嵌入相加作为输入。后续改进:可学习位置编码、旋转位置编码RoPE。',
    '第9章 PCA数学推导': 'PCA推导。数据矩阵X属于R(nd)中心化后为X_tilde。协方差矩阵C=(1/n)*X_tildeT*X_tilde。特征值分解C=V*Lambda*VT。选前k个最大特征值对应特征向量构成投影矩阵W属于R(dk)。降维后数据Z=X_tilde*W属于R(nk)。保留方差比例=Sum(lambdai,i=1..k)/Sum(lambdai,i=1..d)。也可通过SVD:X_tilde=U*Sigma*VT其中V前k列即为主成分方向。',
}

all_chunks = []
all_ids = []
all_metas = []
for title, content in chapters.items():
    chunks = chunk_text(content, chunk_size=500, overlap=50)
    for j, chunk in enumerate(chunks):
        all_chunks.append(chunk)
        all_ids.append(f'{title}_chunk_{j}')
        all_metas.append({'source': title, 'chunk_index': j, 'course_id': 2, 'course_name': '机器学习'})

print(f'总计 {len(all_chunks)} 个知识片段, 正在向量化...')
start = time.perf_counter()
embeddings = embed_texts(all_chunks)
elapsed = time.perf_counter() - start
print(f'向量化完成, 耗时 {elapsed:.1f}s')

collection.add(embeddings=embeddings, documents=all_chunks, metadatas=all_metas, ids=all_ids)
print(f'已索引到集合 course_2, 共 {collection.count()} 个chunks')

print('\n=== 验证检索 ===')
test_qs = ['什么是梯度下降', 'CNN卷积层的工作原理', 'LSTM的门控机制', '随机森林和决策树的区别', '什么是过拟合']
for q in test_qs:
    q_emb = embed_texts([q])
    res = collection.query(query_embeddings=q_emb, n_results=3)
    sims = [1-d for d in res['distances'][0]]
    print(f'\nQ: {q}')
    for i in range(3):
        print(f'  [{i+1}] sim={sims[i]:.3f} | {res["documents"][0][i][:60]}')
print('\n完成!')
