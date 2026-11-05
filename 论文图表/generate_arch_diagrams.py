"""Generate architecture and flow diagrams for thesis using matplotlib."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib
import numpy as np
import os

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

output_dir = os.path.dirname(os.path.abspath(__file__))


def draw_box(ax, x, y, w, h, text, color='#4C72B0', text_color='white', fontsize=10, alpha=0.9):
    """Draw a rounded rectangle with centered text."""
    box = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                   facecolor=color, edgecolor='#333', linewidth=1.2, alpha=alpha)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color=text_color, wrap=True)


def draw_arrow(ax, x1, y1, x2, y2, color='#555', style='->', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw))


# ============================================================
# 图1-1: 系统总体流程图
# ============================================================
fig, ax = plt.subplots(figsize=(14, 6))
ax.set_xlim(0, 14)
ax.set_ylim(0, 6)
ax.axis('off')
ax.set_title('图1-1  基于RAG的大模型智能教学助手系统流程图', fontsize=14, fontweight='bold', pad=20)

# Row 1: main flow
draw_box(ax, 0.2, 4.5, 1.8, 0.8, u'学生提问\n(Query)', '#2ecc71', 'white', 10)
draw_box(ax, 2.5, 4.5, 1.8, 0.8, u'BGE向量化\n(1024维)', '#3498db', 'white', 9)
draw_box(ax, 4.8, 4.5, 2.0, 0.8, u'ChromaDB\nTop-K检索', '#3498db', 'white', 9)
draw_box(ax, 7.3, 4.5, 2.0, 0.8, u'相似度阈值\n过滤', '#e67e22', 'white', 9)
draw_box(ax, 9.8, 4.5, 1.8, 0.8, u'LLM流式\n生成(SSE)', '#e74c3c', 'white', 10)
draw_box(ax, 12.1, 4.5, 1.6, 0.8, u'返回回答', '#2ecc71', 'white', 10)

# Arrows row 1
for x1, x2 in [(2.0, 2.5), (4.3, 4.8), (6.8, 7.3), (9.3, 9.8), (11.6, 12.1)]:
    draw_arrow(ax, x1, 4.9, x2, 4.9)

# Row 2: context assembly
draw_box(ax, 3.0, 2.8, 2.5, 0.8, u'提示词模板\n(Jinja2)', '#9b59b6', 'white', 9)
draw_box(ax, 6.0, 2.8, 2.0, 0.8, u'学生画像\n(Memory)', '#9b59b6', 'white', 9)
draw_box(ax, 8.5, 2.8, 2.0, 0.8, u'Token预算\n+压缩', '#e67e22', 'white', 9)

# Arrow from filter to context assembly
draw_arrow(ax, 8.3, 4.5, 8.5, 3.6, '#555', '->')
draw_arrow(ax, 4.25, 3.6, 4.25, 4.5, '#9b59b6', '->')

# Row 3: memory update
draw_box(ax, 9.8, 1.2, 2.2, 0.8, u'知识点提取\n+掌握度衰减', '#1abc9c', 'white', 9)
draw_box(ax, 12.3, 1.2, 1.4, 0.8, u'更新\n学生画像', '#1abc9c', 'white', 9)
draw_arrow(ax, 10.9, 4.5, 10.9, 2.0, '#1abc9c', '->')
draw_arrow(ax, 12.0, 1.6, 12.3, 1.6)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'system_flow_diagram.png'), dpi=200, bbox_inches='tight')
plt.close()
print("system_flow_diagram.png done")


# ============================================================
# 图2-1: 定长滑动窗口分块算法示意图
# ============================================================
fig, ax = plt.subplots(figsize=(12, 4))
ax.set_xlim(0, 12)
ax.set_ylim(0, 4)
ax.axis('off')
ax.set_title(u'图2-1  定长滑动窗口分块算法示意图 (chunk_size=500, overlap=50)', fontsize=13, fontweight='bold', pad=15)

# Original text bar
ax.barh(3.2, 10, height=0.5, left=0.5, color='#ecf0f1', edgecolor='#bdc3c7', linewidth=1.5)
ax.text(5.5, 3.45, u'原始文本 T (长度 N)', ha='center', va='center', fontsize=11, color='#555')

# Chunk 0
ax.barh(2.2, 4.5, height=0.5, left=0.5, color='#3498db', edgecolor='#2980b9', alpha=0.8)
ax.text(2.75, 2.45, 'chunk_0 (500字符)', ha='center', va='center', fontsize=9, color='white', fontweight='bold')

# Chunk 1
ax.barh(1.4, 4.5, height=0.5, left=4.0, color='#e74c3c', edgecolor='#c0392b', alpha=0.8)
ax.text(6.25, 1.65, 'chunk_1 (500字符)', ha='center', va='center', fontsize=9, color='white', fontweight='bold')

# Chunk 2
ax.barh(0.6, 4.5, height=0.5, left=7.5, color='#2ecc71', edgecolor='#27ae60', alpha=0.8)
ax.text(9.75, 0.85, 'chunk_2 (500字符)', ha='center', va='center', fontsize=9, color='white', fontweight='bold')

# Overlap arrows
draw_arrow(ax, 4.5, 2.15, 4.5, 1.95, '#e67e22', '->', 2)
ax.text(4.8, 2.05, u'overlap=50', fontsize=8, color='#e67e22', fontweight='bold')

draw_arrow(ax, 8.0, 1.35, 8.0, 1.15, '#e67e22', '->', 2)
ax.text(8.3, 1.25, u'overlap=50', fontsize=8, color='#e67e22', fontweight='bold')

# Step annotation
ax.text(1.5, 0.15, u'start_0 = 0', fontsize=9, color='#3498db', fontweight='bold')
ax.text(5.0, 0.15, u'start_1 = 450', fontsize=9, color='#e74c3c', fontweight='bold')
ax.text(8.5, 0.15, u'start_2 = 900', fontsize=9, color='#2ecc71', fontweight='bold')
ax.text(1.5, -0.3, u'步长 = chunk_size - overlap = 450', fontsize=10, color='#555')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'chunking_algorithm.png'), dpi=200, bbox_inches='tight')
plt.close()
print("chunking_algorithm.png done")


# ============================================================
# 图2-2: 文本向量化流程图
# ============================================================
fig, ax = plt.subplots(figsize=(6, 10))
ax.set_xlim(0, 6)
ax.set_ylim(0, 10)
ax.axis('off')
ax.set_title(u'图2-2  文本向量化与L2归一化流程', fontsize=13, fontweight='bold', pad=15)

boxes = [
    (1.5, 8.8, 3.0, 0.7, u'输入文本 t', '#2ecc71'),
    (1.5, 7.5, 3.0, 0.7, u'分词 (Tokenization)\n-> {x1, x2, ..., xm}', '#3498db'),
    (1.5, 6.2, 3.0, 0.7, u'Embedding层\n+ 位置编码', '#3498db'),
    (1.5, 4.9, 3.0, 0.7, u'L层 Transformer\n编码器', '#9b59b6'),
    (1.5, 3.6, 3.0, 0.7, u'池化 (CLS/均值)', '#9b59b6'),
    (1.5, 2.3, 3.0, 0.7, u'L2归一化\nv = v / ||v||', '#e74c3c'),
    (1.5, 1.0, 3.0, 0.7, u'输出: 1024维归一化向量\n||v|| = 1', '#2ecc71'),
]

for x, y, w, h, text, color in boxes:
    draw_box(ax, x, y, w, h, text, color, 'white', 10)

for i in range(len(boxes) - 1):
    draw_arrow(ax, 3.0, boxes[i][1], 3.0, boxes[i+1][1] + boxes[i+1][3], '#555', '->', 2)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'vectorization_flow.png'), dpi=200, bbox_inches='tight')
plt.close()
print("vectorization_flow.png done")


# ============================================================
# 图2-3: 文档级摘要索引策略对比图
# ============================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.set_xlim(0, 6)
ax1.set_ylim(0, 6)
ax1.axis('off')
ax1.set_title(u'传统分块索引', fontsize=12, fontweight='bold')

draw_box(ax1, 0.5, 4.5, 5.0, 0.8, u'文档 D', '#95a5a6', 'white', 11)
draw_arrow(ax1, 3.0, 4.5, 3.0, 4.1, '#555', '->', 1.5)
draw_box(ax1, 0.5, 3.2, 1.4, 0.7, u'c1', '#3498db', 'white', 11)
draw_box(ax1, 2.3, 3.2, 1.4, 0.7, u'c2', '#3498db', 'white', 11)
draw_box(ax1, 4.1, 3.2, 1.4, 0.7, u'c3', '#3498db', 'white', 11)
draw_arrow(ax1, 3.0, 3.2, 3.0, 2.6, '#555', '->', 1.5)
draw_box(ax1, 1.0, 1.8, 4.0, 0.6, u'→ 存入 ChromaDB', '#2c3e50', 'white', 10)

ax2.set_xlim(0, 6)
ax2.set_ylim(0, 6)
ax2.axis('off')
ax2.set_title(u'文档级摘要索引 (本系统)', fontsize=12, fontweight='bold')

draw_box(ax2, 0.5, 4.5, 5.0, 0.8, u'文档 D', '#95a5a6', 'white', 11)
draw_arrow(ax2, 1.8, 4.5, 1.8, 4.1, '#555', '->', 1.5)
draw_arrow(ax2, 4.2, 4.5, 4.2, 4.1, '#555', '->', 1.5)
draw_box(ax2, 0.5, 3.2, 2.5, 0.7, u'LLM生成摘要', '#e74c3c', 'white', 10)
draw_box(ax2, 3.5, 3.2, 2.0, 0.7, u'分块 c1 c2 c3', '#3498db', 'white', 10)
draw_box(ax2, 0.5, 2.0, 1.8, 0.7, u'摘要块\n(is_summary)', '#e74c3c', 'white', 9)
draw_box(ax2, 2.8, 2.0, 1.2, 0.7, u'c1', '#3498db', 'white', 10)
draw_box(ax2, 4.2, 2.0, 1.2, 0.7, u'c2 c3', '#3498db', 'white', 10)
draw_arrow(ax2, 3.0, 2.0, 3.0, 1.4, '#555', '->', 1.5)
draw_box(ax2, 1.0, 0.6, 4.0, 0.6, u'→ 全部存入 ChromaDB', '#2c3e50', 'white', 10)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'summary_index_comparison.png'), dpi=200, bbox_inches='tight')
plt.close()
print("summary_index_comparison.png done")


# ============================================================
# 图3-1: RAG管线四阶段架构图
# ============================================================
fig, ax = plt.subplots(figsize=(14, 5))
ax.set_xlim(0, 14)
ax.set_ylim(0, 5)
ax.axis('off')
ax.set_title(u'图3-1  RAG管线四阶段架构设计', fontsize=14, fontweight='bold', pad=15)

stages = [
    (0.3, 1.5, 2.8, 2.5, u'检索 Retrieve', '#3498db',
     [u'输入: 用户查询 q', u'', u'1. BGE向量化', u'2. Top-K向量检索', u'3. 相似度阈值过滤', u'', u'输出: D\' = {d1,...,dk}']),
    (3.5, 1.5, 2.8, 2.5, u'组装 Build Prompt', '#9b59b6',
     [u'输入: D\', M, H, T', u'', u'1. 上下文策略应用', u'2. Token预算控制', u'3. Jinja2模板渲染', u'', u'输出: 系统提示词 p']),
    (6.7, 1.5, 2.8, 2.5, u'生成 Generate', '#e74c3c',
     [u'输入: p, q', u'', u'1. LLM调用', u'2. SSE流式输出', u'', u'', u'输出: 回答 y']),
    (9.9, 1.5, 2.8, 2.5, u'记忆 Memory', '#1abc9c',
     [u'输入: q, y', u'', u'1. 知识点提取', u'2. 掌握度衰减', u'3. 画像更新', u'', u'输出: M\' (更新画像)']),
]

for x, y, w, h, title, color, lines in stages:
    box = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                                   facecolor=color, edgecolor='#333', linewidth=1.5, alpha=0.15)
    ax.add_patch(box)
    draw_box(ax, x, y + h - 0.6, w, 0.6, title, color, 'white', 12)
    for i, line in enumerate(lines):
        ax.text(x + 0.15, y + h - 1.1 - i * 0.25, line, fontsize=8, color='#333', va='top')

for i in range(3):
    x1 = stages[i][0] + stages[i][2]
    x2 = stages[i+1][0]
    draw_arrow(ax, x1, 2.75, x2, 2.75, '#555', '->', 2.5)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'rag_pipeline_stages.png'), dpi=200, bbox_inches='tight')
plt.close()
print("rag_pipeline_stages.png done")


# ============================================================
# 图3-2: 上下文压缩流程图
# ============================================================
fig, ax = plt.subplots(figsize=(8, 12))
ax.set_xlim(0, 8)
ax.set_ylim(0, 12)
ax.axis('off')
ax.set_title(u'图3-2  上下文压缩算法流程图', fontsize=14, fontweight='bold', pad=15)

# Start
draw_box(ax, 2.5, 11.0, 3.0, 0.6, u'开始: 计算总Token数 T_total', '#2ecc71', 'white', 10)

# Decision 1
draw_box(ax, 2.5, 9.8, 3.0, 0.6, u'T_total ≤ B (预算)?', '#f39c12', 'white', 10)
draw_box(ax, 6.0, 9.8, 1.5, 0.6, u'返回原消息', '#27ae60', 'white', 9)

# Step 1
draw_box(ax, 2.5, 8.5, 3.0, 0.7, u'Step1: 丢弃最旧历史\n(保留最后2条)', '#e74c3c', 'white', 9)
draw_arrow(ax, 4.0, 11.0, 4.0, 10.4, '#555', '->')
draw_arrow(ax, 4.0, 9.8, 4.0, 9.2, '#555', '->')
draw_arrow(ax, 5.5, 10.1, 6.0, 10.1, '#27ae60', '->')
ax.text(5.7, 10.25, u'是', fontsize=9, color='#27ae60')
ax.text(4.15, 9.5, u'否', fontsize=9, color='#e74c3c')

# Decision 2
draw_box(ax, 2.5, 7.2, 3.0, 0.6, u'T\' ≤ B?', '#f39c12', 'white', 10)
draw_box(ax, 6.0, 7.2, 1.5, 0.6, u'返回结果', '#27ae60', 'white', 9)
draw_arrow(ax, 4.0, 8.5, 4.0, 7.8, '#555', '->')
draw_arrow(ax, 4.0, 7.2, 4.0, 6.6, '#555', '->')
draw_arrow(ax, 5.5, 7.5, 6.0, 7.5, '#27ae60', '->')
ax.text(5.7, 7.65, u'是', fontsize=9, color='#27ae60')
ax.text(4.15, 6.9, u'否', fontsize=9, color='#e74c3c')

# Step 2
draw_box(ax, 2.5, 5.9, 3.0, 0.7, u'Step2: 截断系统提示词\n(尾部=最不相关文档)', '#e74c3c', 'white', 9)

# Decision 3
draw_box(ax, 2.5, 4.6, 3.0, 0.6, u'T\' ≤ B?', '#f39c12', 'white', 10)
draw_box(ax, 6.0, 4.6, 1.5, 0.6, u'返回结果', '#27ae60', 'white', 9)
draw_arrow(ax, 4.0, 5.9, 4.0, 5.2, '#555', '->')
draw_arrow(ax, 4.0, 4.6, 4.0, 4.0, '#555', '->')
draw_arrow(ax, 5.5, 4.9, 6.0, 4.9, '#27ae60', '->')
ax.text(5.7, 5.05, u'是', fontsize=9, color='#27ae60')
ax.text(4.15, 4.3, u'否', fontsize=9, color='#e74c3c')

# Step 3
draw_box(ax, 2.5, 3.3, 3.0, 0.6, u'Step3: 截断用户消息', '#e74c3c', 'white', 10)

# Decision 4
draw_box(ax, 2.5, 2.1, 3.0, 0.6, u'T\' ≤ B?', '#f39c12', 'white', 10)
draw_box(ax, 6.0, 2.1, 1.5, 0.6, u'返回结果', '#27ae60', 'white', 9)
draw_arrow(ax, 4.0, 3.3, 4.0, 2.7, '#555', '->')
draw_arrow(ax, 4.0, 2.1, 4.0, 1.5, '#555', '->')
draw_arrow(ax, 5.5, 2.4, 6.0, 2.4, '#27ae60', '->')
ax.text(5.7, 2.55, u'是', fontsize=9, color='#27ae60')
ax.text(4.15, 1.8, u'否', fontsize=9, color='#e74c3c')

# Step 4: skeleton
draw_box(ax, 2.5, 0.8, 3.0, 0.6, u'Step4: 骨架兜底', '#c0392b', 'white', 10)
draw_arrow(ax, 4.0, 0.8, 4.0, 0.3, '#555', '->')

# End
draw_box(ax, 2.5, -0.3, 3.0, 0.5, u'返回最小上下文', '#2c3e50', 'white', 10)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'compression_flowchart.png'), dpi=200, bbox_inches='tight')
plt.close()
print("compression_flowchart.png done")


# ============================================================
# 图5-1: 系统总体架构图 (四层)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 8))
ax.set_xlim(0, 12)
ax.set_ylim(0, 8)
ax.axis('off')
ax.set_title(u'图5-1  系统总体架构图', fontsize=14, fontweight='bold', pad=15)

# Layer 1: Presentation
layer1 = mpatches.FancyBboxPatch((0.3, 6.2), 11.4, 1.5, boxstyle="round,pad=0.05",
                                  facecolor='#3498db', edgecolor='#2980b9', linewidth=2, alpha=0.15)
ax.add_patch(layer1)
ax.text(0.5, 7.5, u'表现层 (Vue 3 + Element Plus)', fontsize=11, fontweight='bold', color='#2980b9')
modules1 = [u'智能对话', u'课程中心', u'知识库管理', u'提示词管理', u'上下文策略', u'编排评估']
for i, m in enumerate(modules1):
    draw_box(ax, 0.6 + i * 1.85, 6.35, 1.65, 0.55, m, '#3498db', 'white', 8)

# Arrow down
for x in [2.5, 6.0, 9.5]:
    draw_arrow(ax, x, 6.2, x, 5.85, '#555', '->', 1.5)
ax.text(5.5, 5.95, u'REST API / SSE', fontsize=9, color='#555', ha='center')

# Layer 2: Application
layer2 = mpatches.FancyBboxPatch((0.3, 4.0), 11.4, 1.7, boxstyle="round,pad=0.05",
                                  facecolor='#9b59b6', edgecolor='#8e44ad', linewidth=2, alpha=0.15)
ax.add_patch(layer2)
ax.text(0.5, 5.5, u'应用层 (Django 5 + DRF)', fontsize=11, fontweight='bold', color='#8e44ad')
modules2 = [u'用户认证', u'课程管理', u'RAG管线', u'提示词引擎', u'上下文引擎', u'链路追踪']
for i, m in enumerate(modules2):
    draw_box(ax, 0.6 + i * 1.85, 4.15, 1.65, 0.55, m, '#9b59b6', 'white', 8)

# Arrow down
for x in [3.5, 8.5]:
    draw_arrow(ax, x, 4.0, x, 3.65, '#555', '->', 1.5)

# Layer 3: Data
layer3 = mpatches.FancyBboxPatch((0.3, 2.0), 11.4, 1.5, boxstyle="round,pad=0.05",
                                  facecolor='#2ecc71', edgecolor='#27ae60', linewidth=2, alpha=0.15)
ax.add_patch(layer3)
ax.text(0.5, 3.3, u'数据层', fontsize=11, fontweight='bold', color='#27ae60')
draw_box(ax, 1.0, 2.15, 4.0, 0.6, u'MySQL 8.0 (业务数据)', '#2ecc71', 'white', 10)
draw_box(ax, 6.5, 2.15, 4.5, 0.6, u'ChromaDB (向量数据 1024维)', '#2ecc71', 'white', 10)

# Arrow down
for x in [3.5, 8.5]:
    draw_arrow(ax, x, 2.0, x, 1.65, '#555', '->', 1.5)

# Layer 4: Service
layer4 = mpatches.FancyBboxPatch((0.3, 0.2), 11.4, 1.3, boxstyle="round,pad=0.05",
                                  facecolor='#e74c3c', edgecolor='#c0392b', linewidth=2, alpha=0.15)
ax.add_patch(layer4)
ax.text(0.5, 1.3, u'服务层', fontsize=11, fontweight='bold', color='#c0392b')
draw_box(ax, 1.0, 0.35, 4.0, 0.6, u'LLM服务 (DeepSeek/阿里百炼)', '#e74c3c', 'white', 9)
draw_box(ax, 6.5, 0.35, 4.5, 0.6, u'Embedding服务 (BGE-large-zh-v1.5)', '#e74c3c', 'white', 9)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'system_architecture.png'), dpi=200, bbox_inches='tight')
plt.close()
print("system_architecture.png done")


# ============================================================
# 图5-2: RAG管线数据流图 (两条主线)
# ============================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

# Left: Document indexing flow
ax1.set_xlim(0, 7)
ax1.set_ylim(0, 9)
ax1.axis('off')
ax1.set_title(u'文档索引流程', fontsize=13, fontweight='bold', color='#3498db')

steps_left = [
    (1.0, 7.8, u'教师上传文档\n(PDF/Word/PPT/MD)', '#2ecc71'),
    (1.0, 6.5, u'文本提取\n(PyPDF2/python-docx/pptx)', '#3498db'),
    (1.0, 5.2, u'LLM生成文档摘要\n(150-300字)', '#e74c3c'),
    (1.0, 3.9, u'定长滑动窗口分块\n(chunk_size=500, overlap=50)', '#3498db'),
    (1.0, 2.6, u'BGE模型向量化\n(1024维, L2归一化)', '#9b59b6'),
    (1.0, 1.3, u'存入 ChromaDB\n(course_{course_id})', '#2c3e50'),
]
for x, y, text, color in steps_left:
    draw_box(ax1, x, y, 5.0, 0.8, text, color, 'white', 9)
for i in range(len(steps_left) - 1):
    draw_arrow(ax1, 3.5, steps_left[i][1], 3.5, steps_left[i+1][1] + 0.8, '#555', '->', 1.5)

# Right: QA retrieval flow
ax2.set_xlim(0, 7)
ax2.set_ylim(0, 9)
ax2.axis('off')
ax2.set_title(u'问答检索流程', fontsize=13, fontweight='bold', color='#e74c3c')

steps_right = [
    (1.0, 8.2, u'学生输入问题', '#2ecc71'),
    (1.0, 7.2, u'BGE向量化查询', '#3498db'),
    (1.0, 6.2, u'ChromaDB Top-K检索', '#3498db'),
    (1.0, 5.2, u'相似度阈值过滤', '#e67e22'),
    (1.0, 4.2, u'加载学生画像 + 对话历史', '#9b59b6'),
    (1.0, 3.2, u'Jinja2模板渲染', '#9b59b6'),
    (1.0, 2.2, u'Token预算压缩', '#e67e22'),
    (1.0, 1.2, u'LLM流式生成 (SSE)', '#e74c3c'),
    (1.0, 0.2, u'知识点提取 → 掌握度更新', '#1abc9c'),
]
for x, y, text, color in steps_right:
    draw_box(ax2, x, y, 5.0, 0.7, text, color, 'white', 9)
for i in range(len(steps_right) - 1):
    draw_arrow(ax2, 3.5, steps_right[i][1], 3.5, steps_right[i+1][1] + 0.7, '#555', '->', 1.5)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'data_flow_diagram.png'), dpi=200, bbox_inches='tight')
plt.close()
print("data_flow_diagram.png done")


print("\nAll architecture diagrams generated in:", output_dir)
