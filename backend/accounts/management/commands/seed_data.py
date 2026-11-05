"""
Seed the database with realistic mock data for development and demo.
Run: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from accounts.models import User
from courses.models import Course, ScheduleSlot
from enrollments.models import Enrollment
from chat.models import ChatSession, ChatMessage
from vector_db.models import VectorCollection
from files_app.models import UploadedFile
from dashboard.models import LearningRecord
from settings_app.models import SystemSetting, AgentAPIConfig
from prompt_engine.models import PromptTemplate
from context_engine.models import ContextStrategy
from harness.models import RAGPipeline


class Command(BaseCommand):
    help = 'Seed database with demo mock data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('[seed] Seeding database...'))

        # ── 1. Users ────────────────────────────────────
        users = self._seed_users()
        # ── 2. Courses ──────────────────────────────────
        courses = self._seed_courses(users)
        # ── 3. Enrollments ──────────────────────────────
        self._seed_enrollments(users, courses)
        # ── 4. Chat sessions + messages ─────────────────
        self._seed_chats(users, courses)
        # ── 5. Files ────────────────────────────────────
        self._seed_files(users, courses)
        # ── 6. Vector collections ───────────────────────
        self._seed_vectors(courses)
        # ── 7. Learning records ─────────────────────────
        self._seed_learning_records(users, courses)
        # ── 8. System settings ──────────────────────────
        self._seed_settings()
        # ── 9. Agent API config (if not exists) ─────────
        self._seed_agent_config()
        # -- 10. Prompt templates --
        self._seed_prompt_templates()
        # -- 11. Context strategies --
        self._seed_context_strategies()
        # -- 12. RAG pipeline --
        self._seed_pipeline()

        self.stdout.write(self.style.SUCCESS('\n--- Database seeded successfully! ---'))
        self._print_summary()

    # ── Users ───────────────────────────────────────────

    def _seed_users(self):
        teachers = [
            {'username': 'zhangwei', 'email': 'zhangwei@teek.edu.cn', 'role': User.Role.TEACHER,
             'signature': '十年树木，百年树人', 'dept': '计算机科学与技术学院', 'sex': '男', 'age': 42},
            {'username': 'lifang', 'email': 'lifang@teek.edu.cn', 'role': User.Role.TEACHER,
             'signature': '探索AI的无限可能', 'dept': '人工智能学院', 'sex': '女', 'age': 36},
            {'username': 'wangqiang', 'email': 'wangqiang@teek.edu.cn', 'role': User.Role.TEACHER,
             'signature': '学无止境', 'dept': '数据科学学院', 'sex': '男', 'age': 48},
            {'username': 'chenming', 'email': 'chenming@teek.edu.cn', 'role': User.Role.TEACHER,
             'signature': '认真对待每一个问题', 'dept': '软件工程学院', 'sex': '男', 'age': 31},
            {'username': 'huangxia', 'email': 'huangxia@teek.edu.cn', 'role': User.Role.TEACHER,
             'signature': '知行合一', 'dept': '计算机科学与技术学院', 'sex': '女', 'age': 38},
        ]
        students = [
            {'username': 'zhangsan', 'role': User.Role.STUDENT, 'dept': '人工智能学院', 'major': '人工智能', 'grade': '2023级', 'sex': '男', 'age': 21, 'student_id': '2023001'},
            {'username': 'lisi', 'role': User.Role.STUDENT, 'dept': '计算机科学与技术学院', 'major': '计算机科学与技术', 'grade': '2024级', 'sex': '女', 'age': 20, 'student_id': '2024001'},
            {'username': 'wangwu', 'role': User.Role.STUDENT, 'dept': '数据科学学院', 'major': '数据科学', 'grade': '2023级', 'sex': '男', 'age': 22, 'student_id': '2023002'},
            {'username': 'zhaoliu', 'role': User.Role.STUDENT, 'dept': '软件工程学院', 'major': '软件工程', 'grade': '2024级', 'sex': '男', 'age': 21, 'student_id': '2024002'},
            {'username': 'sunqi', 'role': User.Role.STUDENT, 'dept': '人工智能学院', 'major': '人工智能', 'grade': '2022级', 'sex': '女', 'age': 23, 'student_id': '2022001'},
            {'username': 'zhouba', 'role': User.Role.STUDENT, 'dept': '计算机科学与技术学院', 'major': '计算机科学与技术', 'grade': '2024级', 'sex': '男', 'age': 20, 'student_id': '2024003'},
            {'username': 'wujiu', 'role': User.Role.STUDENT, 'dept': '数据科学学院', 'sex': '女', 'age': 22},
            {'username': 'zhengshi', 'role': User.Role.STUDENT, 'dept': '电子与信息工程学院', 'sex': '男', 'age': 21},
            {'username': 'liuqian', 'role': User.Role.STUDENT, 'dept': '人工智能学院', 'sex': '女', 'age': 20},
            {'username': 'chenbai', 'role': User.Role.STUDENT, 'dept': '软件工程学院', 'sex': '男', 'age': 24},
            {'username': 'yangming', 'role': User.Role.STUDENT, 'dept': '计算机科学与技术学院', 'sex': '男', 'age': 21},
            {'username': 'linnan', 'role': User.Role.STUDENT, 'dept': '数据科学学院', 'sex': '女', 'age': 22},
        ]

        created = []
        # Ensure core users exist
        core = {
            'admin': {'email': 'admin@teek.com', 'password': 'admin123', 'role': User.Role.ADMIN, 'dept': '信息中心', 'sex': '男', 'age': 30, 'is_approved': True},
            'teacher': {'email': 'teacher@teek.com', 'password': 'teacher123', 'role': User.Role.TEACHER, 'dept': '教务处', 'sex': '男', 'age': 40, 'is_approved': True},
            'student': {'email': 'student@teek.com', 'password': 'student123', 'role': User.Role.STUDENT, 'student_id': '2023001', 'dept': '人工智能学院', 'sex': '女', 'age': 20, 'is_approved': True},
        }
        for uname, udata in core.items():
            u, created_flag = User.objects.get_or_create(username=uname, defaults=udata)
            if created_flag:
                u.set_password(udata['password'])
                u.save()
            created.append(u)

        # Teachers
        for td in teachers:
            u, created_flag = User.objects.get_or_create(username=td['username'], defaults={
                'email': td['email'], 'role': td['role'], 'signature': td['signature'],
                'dept': td['dept'], 'sex': td['sex'], 'age': td['age'],
            })
            if created_flag:
                u.set_password('123456')
                u.save()
            created.append(u)

        # Students
        for sd in students:
            u, created_flag = User.objects.get_or_create(username=sd['username'], defaults={
                'role': sd['role'], 'dept': sd['dept'], 'major': sd.get('major', ''),
                'grade': sd.get('grade', ''), 'sex': sd['sex'], 'age': sd['age'],
                'student_id': sd.get('student_id', ''), 'is_approved': True,
            })
            if created_flag:
                u.set_password('123456')
                u.save()
            created.append(u)

        self.stdout.write(f'  [OK] Users: {User.objects.count()} (admin: admin/admin123, teacher: teacher/teacher123, student: student/student123)')
        return created

    # ── Courses ─────────────────────────────────────────

    def _seed_courses(self, users):
        teachers = [u for u in users if u.role == User.Role.TEACHER]
        if not teachers:
            teachers = [u for u in users if u.role == User.Role.ADMIN]
        courses_data = [
            {'name': '人工智能导论', 'description': '系统介绍人工智能的基本概念、发展历程、知识表示、搜索推理、机器学习基础及伦理问题，帮助学生建立AI整体框架。', 'chapters': 12, 'cover_color': '#409EFF', 'cover_gradient': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', 'icon': 'MagicStick'},
            {'name': '机器学习实战', 'description': '从零开始掌握监督学习、无监督学习、集成学习等核心算法，通过Kaggle真实数据集进行项目实战。', 'chapters': 15, 'cover_color': '#67C23A', 'cover_gradient': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', 'icon': 'Cpu'},
            {'name': '深度学习与神经网络', 'description': '深入理解CNN、RNN、LSTM、Transformer、GAN等深度模型架构，使用PyTorch框架动手实现。', 'chapters': 14, 'cover_color': '#E6A23C', 'cover_gradient': 'linear-gradient(135deg, #f7971e 0%, #ffd200 100%)', 'icon': 'Connection'},
            {'name': '自然语言处理', 'description': '涵盖文本预处理、词向量、序列标注、机器翻译、预训练语言模型及大语言模型应用开发。', 'chapters': 10, 'cover_color': '#F56C6C', 'cover_gradient': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', 'icon': 'ChatDotRound'},
            {'name': '计算机视觉', 'description': '图像分类、目标检测(YOLO系列)、语义分割、图像生成、视频理解等CV核心任务。', 'chapters': 12, 'cover_color': '#909399', 'cover_gradient': 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)', 'icon': 'Picture'},
            {'name': '大模型应用开发', 'description': '深入理解Transformer架构，掌握RAG、Agent、Function Calling、LangChain等技术，构建智能应用。', 'chapters': 8, 'cover_color': '#409EFF', 'cover_gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'icon': 'Platform'},
            {'name': '数据挖掘导论', 'description': '关联规则、聚类分析、异常检测、推荐系统等数据挖掘经典算法与工业应用。', 'chapters': 10, 'cover_color': '#67C23A', 'cover_gradient': 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)', 'icon': 'DataAnalysis'},
            {'name': '强化学习入门', 'description': '马尔可夫决策过程、Q-Learning、DQN、策略梯度等强化学习基础理论与实践。', 'chapters': 9, 'cover_color': '#E6A23C', 'cover_gradient': 'linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%)', 'icon': 'Compass'},
        ]
        created = []
        for i, cd in enumerate(courses_data):
            teacher = random.choice(teachers)
            cd['max_students'] = cd.get('max_students', random.choice([30, 40, 50, 60, 80]))
            cd['college'] = cd.get('college', random.choice(['计算机科学与技术学院', '人工智能学院', '数据科学学院', '软件工程学院', '电子与信息工程学院']))
            cd['major'] = cd.get('major', random.choice(['计算机科学与技术', '人工智能', '数据科学', '软件工程', '电子信息']))
            cd['grade'] = cd.get('grade', random.choice(['2023级', '2024级', '2025级']))
            cd['year'] = cd.get('year', 2025)
            cd['semester'] = cd.get('semester', random.choice(['fall', 'spring']))
            course, _ = Course.objects.get_or_create(
                name=cd['name'],
                defaults={**cd, 'teacher': teacher, 'created_at': timezone.now() - timedelta(days=random.randint(30, 200))}
            )
            created.append(course)
        
        # Update all courses with new fields if missing
        colleges = ['计算机科学与技术学院', '人工智能学院', '数据科学学院', '软件工程学院', '电子与信息工程学院']
        majors = ['计算机科学与技术', '人工智能', '数据科学', '软件工程', '电子信息']
        grades = ['2023级', '2024级', '2025级']
        semesters = ['spring', 'fall']
        for course in created:
            updated = False
            if not course.max_students or course.max_students == 0:
                course.max_students = random.choice([30, 40, 50, 60, 80])
                updated = True
            if not course.college:
                course.college = random.choice(colleges)
                updated = True
            if not course.major:
                course.major = random.choice(majors)
                updated = True
            if not course.grade:
                course.grade = random.choice(grades)
                updated = True
            if not course.semester:
                course.semester = random.choice(semesters)
                updated = True
            if updated:
                course.save(update_fields=['max_students', 'college', 'major', 'grade', 'semester'])
        
                # Seed schedule slots for each course
        import datetime
        slot_count = 0
        time_slots = [
            (1, (8, 0), (10, 30)),   # 周一 8:00-10:30
            (2, (10, 0), (12, 0)),   # 周二 10:00-12:00
            (3, (14, 0), (16, 30)),  # 周三 14:00-16:30
            (4, (8, 0), (9, 40)),    # 周四 8:00-9:40
            (5, (14, 0), (15, 35)),  # 周五 14:00-15:35
        ]
        for course in created:
            if not ScheduleSlot.objects.filter(course=course).exists():
                n_slots = random.randint(1, 2)
                for si in range(n_slots):
                    wd, (sh, sm), (eh, em) = random.choice(time_slots)
                    ws = 1 if si == 0 else random.choice([1, 9])
                    we = random.choice([8, 12, 16, 18])
                    if we <= ws:
                        we = ws + random.randint(4, 12)
                    ScheduleSlot.objects.create(
                        course=course, weekday=wd,
                        start_time=datetime.time(sh, sm),
                        end_time=datetime.time(eh, em),
                        week_start=ws, week_end=min(we, 20),
                        location=random.choice(["教学楼A201", "教学楼B103", "实验楼C401", "逸夫楼301", "线上"]),
                    )
                    slot_count += 1
        self.stdout.write(f'  [OK] ScheduleSlots: {slot_count}')
        self.stdout.write(f'  [OK] Courses: {Course.objects.count()}')
        return created

    # ── Enrollments ─────────────────────────────────────

    def _seed_enrollments(self, users, courses):
        students = [u for u in users if u.role == User.Role.STUDENT]
        if Enrollment.objects.exists():
            self.stdout.write(f'  [SKIP]  Enrollments: {Enrollment.objects.count()} (skipped)')
            return

        count = 0
        for student in students:
            enrolled = random.sample(courses, k=random.randint(2, 5))
            for course in enrolled:
                status = random.choices(
                    ['approved', 'approved', 'approved', 'pending', 'rejected'],
                    weights=[60, 60, 60, 25, 10]
                )[0]
                days_ago = random.randint(1, 90)
                enrollment = Enrollment.objects.create(
                    student=student, course=course, status=status,
                    enrolled_at=timezone.now() - timedelta(days=days_ago),
                )
                if status != 'pending':
                    enrollment.reviewed_at = enrollment.enrolled_at + timedelta(hours=random.randint(1, 48))
                    if status == 'rejected':
                        enrollment.review_comment = random.choice(['名额已满', '请先完成先修课程', '不符合课程要求'])
                    enrollment.save()
                count += 1
        self.stdout.write(f'  [OK] Enrollments: {count}')

    # ── Chat sessions + messages ───────────────────────

    def _seed_chats(self, users, courses):
        if ChatSession.objects.exists():
            self.stdout.write(f'  [SKIP]  Chat: {ChatSession.objects.count()} sessions (skipped)')
            return

        students = [u for u in users if u.role == User.Role.STUDENT]
        skills = ['qa', 'formula', 'code_debug', 'lab_guide', 'paper_reader']
        session_count = 0
        msg_count = 0

        chat_templates = [
            {
                'skill': 'qa',
                'title': '反向传播算法原理',
                'user_msgs': ['什么是反向传播算法？它在神经网络中是如何工作的？'],
                'ai_msgs': ['反向传播（Backpropagation）是训练神经网络的核心算法。\n\n**基本思想：**\n1. **前向传播** — 输入数据通过网络层层传递，得到预测输出\n2. **计算损失** — 用损失函数（MSE或交叉熵）比较预测值与真实值\n3. **反向传播** — 利用链式法则从输出层逐层计算梯度\n4. **参数更新** — 用优化器（SGD/Adam）更新权重：\n$$w_{new} = w_{old} - \\eta \\cdot \\frac{\\partial L}{\\partial w}$$\n\n这个过程反复迭代直到收敛。'],
            },
            {
                'skill': 'qa',
                'title': '梯度下降变体讨论',
                'user_msgs': ['SGD和Adam优化器有什么区别？什么时候用哪个？'],
                'ai_msgs': ['**SGD（随机梯度下降）**\n- 每次用随机样本更新\n- 收敛慢但泛化能力好\n- 需要手动调学习率\n\n**Adam（自适应矩估计）**\n- 结合Momentum + RMSProp\n- 自适应学习率，收敛快\n- 大多数场景的默认选择\n\n**选择建议：**\n- 需要精细调优 → SGD + 学习率衰减\n- 快速原型/一般任务 → Adam\n- 训练GAN → Adam 或 RMSProp'],
            },
            {
                'skill': 'code_debug',
                'title': 'CNN卷积核维度错误',
                'user_msgs': ['我用PyTorch写了一个CNN，但报错说维度不匹配。\n```python\nclass MyCNN(nn.Module):\n    def __init__(self):\n        self.conv1 = nn.Conv2d(3, 16, 3)\n        self.fc = nn.Linear(16*26*26, 10)\n```\n输入是 (1, 3, 28, 28) 报错 size mismatch'],
                'ai_msgs': ['问题在于 `nn.Linear` 的输入维度计算错了。\n\n对于输入 28×28，经过 3×3 卷积（默认padding=0）后：\n$$H_{out} = \\frac{28 - 3 + 2\\times0}{1} + 1 = 26$$\n\n所以特征图是 16×26×26 = 10816。\n\n**修正方案：**\n\n```python\nclass MyCNN(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.conv1 = nn.Conv2d(3, 16, 3)\n        # 先随便用一个数，然后动态计算\n        self.fc = nn.Linear(16*26*26, 10)\n\n    def forward(self, x):\n        # 或者用自适应池化统一尺寸\n        x = F.adaptive_avg_pool2d(self.conv1(x), (4,4))\n        x = x.view(x.size(0), -1)\n        return self.fc(x)\n```\n\n推荐使用 `torch.flatten` 或全局平均池化来避免手动计算。'],
            },
            {
                'skill': 'formula',
                'title': '交叉熵损失推导',
                'user_msgs': ['能不能帮我推导一下交叉熵损失函数的梯度公式？'],
                'ai_msgs': ['好的，我们来推导交叉熵损失对 logits 的梯度。\n\n**1. Softmax + 交叉熵**\n\n假设有 K 个类别，logits 为 $z = [z_1, z_2, ..., z_K]$：\n\n$$\\hat{y}_i = \\frac{e^{z_i}}{\\sum_{j=1}^K e^{z_j}}$$\n\n$$L = -\\sum_{i=1}^K y_i \\log(\\hat{y}_i)$$\n\n其中 $y$ 是 one-hot 标签。\n\n**2. 链式法则推导**\n\n$$\\frac{\\partial L}{\\partial z_i} = \\hat{y}_i - y_i$$\n\n这个结果非常优雅！梯度的每一维就是预测概率减去真实标签。\n\n因此在实际代码中，直接用 `nn.CrossEntropyLoss` 就够了，它内部集成了 Softmax。'],
            },
            {
                'skill': 'lab_guide',
                'title': 'MNIST手写数字识别实验',
                'user_msgs': ['MNIST分类实验怎么做？求实验步骤'],
                'ai_msgs': ['## MNIST手写数字识别实验指南\n\n### 1. 环境准备\n```python\nimport torch, torchvision\nfrom torch import nn, optim\n```\n\n### 2. 加载数据\n```python\ntransform = torchvision.transforms.ToTensor()\ntrain_set = torchvision.datasets.MNIST(root="./data", train=True, download=True, transform=transform)\ntest_set = torchvision.datasets.MNIST(root="./data", train=False, download=True, transform=transform)\n```\n\n### 3. 构建模型\n```python\nmodel = nn.Sequential(\n    nn.Flatten(),\n    nn.Linear(784, 128), nn.ReLU(),\n    nn.Linear(128, 10)\n)\n```\n\n### 4. 训练循环\n```python\ncriterion = nn.CrossEntropyLoss()\noptimizer = optim.Adam(model.parameters(), lr=0.001)\nfor epoch in range(5):\n    for x, y in train_loader:\n        optimizer.zero_grad()\n        loss = criterion(model(x), y)\n        loss.backward()\n        optimizer.step()\n```\n\n### 5. 评估\n期望准确率 > 97%。'],
            },
            {
                'skill': 'paper_reader',
                'title': 'Attention Is All You Need 解读',
                'user_msgs': ['"Attention Is All You Need" 这篇论文的核心创新点是什么？'],
                'ai_msgs': ['## Attention Is All You Need (Vaswani et al., 2017)\n\n这篇论文提出了 **Transformer** 架构，彻底改变了 NLP 领域。\n\n### 核心创新：\n\n**1. 完全抛弃 RNN/CNN**\n之前的 SOTA 模型（如 LSTM+Attention）仍需序列计算。Transformer 全部用 Attention 机制，实现了真正的并行化训练。\n\n**2. 多头自注意力 (Multi-Head Self-Attention)**\n$$Attention(Q,K,V) = softmax\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$$\n\n缩放因子 $\\sqrt{d_k}$ 防止内积过大导致梯度消失。\n\n**3. 位置编码 (Positional Encoding)**\n因为没有 RNN 的时序结构，用正弦/余弦函数为每个位置生成唯一编码。\n\n### 影响力：\n- BERT、GPT 系列的基础\n- 扩展到 CV（ViT）、语音等领域\n- 参数量的 scaling law 开启了大模型时代'],
            },
        ]

        for student in students[:8]:
            enrolled = Enrollment.objects.filter(student=student, status='approved').select_related('course')
            for enrollment in random.sample(list(enrolled), min(2, enrolled.count())):
                template = random.choice(chat_templates)
                skill = random.choice(skills)
                session = ChatSession.objects.create(
                    title=template['title'],
                    user=student, course=enrollment.course, skill=skill,
                    created_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                )
                session.updated_at = session.created_at + timedelta(minutes=random.randint(5, 120))
                session.save()
                session_count += 1

                for i, um in enumerate(template['user_msgs']):
                    ChatMessage.objects.create(
                        session=session, role='user', content=um,
                        created_at=session.created_at + timedelta(seconds=10 + i * 60),
                    )
                    msg_count += 1
                for i, am in enumerate(template['ai_msgs']):
                    ChatMessage.objects.create(
                        session=session, role='assistant', content=am,
                        sources=f'第{random.randint(1,8)}章 第{random.randint(1,5)}节',
                        created_at=session.created_at + timedelta(seconds=30 + i * 60),
                    )
                    msg_count += 1
        self.stdout.write(f'  [OK] Chat: {session_count} sessions, {msg_count} messages')

    # ── Files ───────────────────────────────────────────

    def _seed_files(self, users, courses):
        if UploadedFile.objects.exists():
            self.stdout.write(f'  [SKIP]  Files: {UploadedFile.objects.count()} (skipped)')
            return

        file_names = [
            ('第1章 绪论.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 2048000),
            ('第2章 基础知识.pdf', 'application/pdf', 3584000),
            ('实验报告模板.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 512000),
            ('课程大纲.pdf', 'application/pdf', 1024000),
            ('课后习题答案.md', 'text/markdown', 128000),
            ('期中考试试卷.pdf', 'application/pdf', 768000),
            ('参考文献列表.txt', 'text/plain', 32000),
            ('课堂笔记-第3章.md', 'text/markdown', 64000),
            ('习题解答-梯度下降.pdf', 'application/pdf', 256000),
            ('项目要求说明.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 196000),
            ('复习提纲.pdf', 'application/pdf', 448000),
            ('课外阅读材料.pdf', 'application/pdf', 640000),
        ]

        teachers = [u for u in users if u.role in (User.Role.TEACHER, User.Role.ADMIN)]
        count = 0
        from django.conf import settings
        import os, uuid

        media_dir = settings.MEDIA_ROOT
        files_dir = os.path.join(media_dir, 'files')
        os.makedirs(files_dir, exist_ok=True)

        for fname, mime, size in file_names:
            ext = os.path.splitext(fname)[1]
            stored_name = f'{uuid.uuid4().hex}{ext}'
            stored_path = os.path.join(files_dir, stored_name)
            # Create a dummy file with some content
            with open(stored_path, 'w', encoding='utf-8') as f:
                f.write(f'Mock file: {fname}\n' + '=' * 40 + '\n')
                f.write('This is a mock file for demo purposes.\n' * 20)

            course = random.choice(courses)
            uploader = random.choice(teachers)
            is_vec = True  # simulate that reindex was already run
            summary = f'"{fname}" — 课程辅助资料。包含{fname.split(".")[0]}相关内容。' if is_vec else ''
            UploadedFile.objects.create(
                original_name=fname,
                stored_path=stored_path,
                file_size=size,
                mime_type=mime,
                course=course,
                uploader=uploader,
                is_vectorized=is_vec,
                summary=summary,
                created_at=timezone.now() - timedelta(days=random.randint(1, 90)),
            )
            count += 1
        self.stdout.write(f'  [OK] Files: {count}')

    # ── Vector collections ──────────────────────────────

    def _seed_vectors(self, courses):
        if VectorCollection.objects.exists():
            self.stdout.write(f'  [SKIP] Vector collections: {VectorCollection.objects.count()} (skipped)')
            return

        embedding_models = ['bge-large-zh-v1.5', 'text-embedding-3-small', 'bge-large-zh-v1.5']
        dim_map = {'bge-large-zh-v1.5': 1024, 'text-embedding-3-small': 1536}

        count = 0
        for course in random.sample(list(courses), min(5, len(courses))):
            em = random.choice(embedding_models)
            fc = UploadedFile.objects.filter(course=course).count()
            vc = max(fc, random.randint(2, 5))
            VectorCollection.objects.create(
                name=f'{course.name}·知识库',
                course=course,
                embedding_model=em,
                document_count=vc,
                chunk_count=vc * random.randint(8, 25),
                vector_count=vc * random.randint(8, 25),
                dimension=dim_map.get(em, 1024),
                status=random.choices(['active', 'active', 'active', 'indexing'], weights=[7, 7, 7, 2])[0],
                description=f'{course.name}课程的向量知识库，包含课件、教材和参考资料的向量化索引',
                last_indexed_at=timezone.now() - timedelta(days=random.randint(0, 15)),
            )
            count += 1
        self.stdout.write(f'  [OK] Vector collections: {count}')

    # ── Learning records ────────────────────────────────

    def _seed_learning_records(self, users, courses):
        if LearningRecord.objects.exists():
            self.stdout.write(f'  [SKIP] Learning records: {LearningRecord.objects.count()} (skipped)')
            return

        students = [u for u in users if u.role == User.Role.STUDENT]
        count = 0

        for student in students:
            enrolled = Enrollment.objects.filter(student=student, status='approved').select_related('course')
            for enrollment in enrolled:
                for days_ago in range(30):
                    if random.random() < 0.6:  # 60% chance studied that day
                        LearningRecord.objects.create(
                            user=student,
                            course=enrollment.course,
                            date=timezone.now().date() - timedelta(days=days_ago),
                            duration_seconds=random.randint(15, 180) * 60,
                        )
                        count += 1
        self.stdout.write(f'  [OK] Learning records: {count}')

    # ── System settings ─────────────────────────────────

    def _seed_settings(self):
        if SystemSetting.objects.exists():
            self.stdout.write(f'  [SKIP] Settings: {SystemSetting.objects.count()} (skipped)')
            return

        settings_data = [
            ('site_name', 'Teek 教学助手', '站点名称'),
            ('site_description', '基于RAG的AI教学辅助平台', '站点描述'),
            ('max_upload_size_mb', '50', '最大上传文件大小(MB)'),
            ('default_language', 'zh-CN', '默认语言'),
            ('enable_registration', 'true', '是否开放注册'),
            ('maintenance_mode', 'false', '维护模式'),
        ]
        for key, value, desc in settings_data:
            SystemSetting.objects.create(key=key, value=value, description=desc)
        self.stdout.write(f'  [OK] Settings: {len(settings_data)}')

    # ── Agent API config ────────────────────────────────

    def _seed_agent_config(self):
        if AgentAPIConfig.objects.exists():
            self.stdout.write(f'  [SKIP] Agent API config: {AgentAPIConfig.objects.count()} (skipped)')
            return

        admin = User.objects.filter(role=User.Role.ADMIN).first()
        AgentAPIConfig.objects.create(
            name='DeepSeek 示例',
            base_url='https://api.deepseek.com/v1',
            api_key='',  # 请在管理后台填入真实的 API key
            model_list=['deepseek-chat', 'deepseek-reasoner'],
            default_model='deepseek-chat',
            is_active=True,
            is_default=True,
            created_by=admin,
        )
        self.stdout.write('  [OK] Agent API config: 1 (DeepSeek example -- please update api_key!)')

    # ── Summary ─────────────────────────────────────────

    def _print_summary(self):
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('=== Database Summary ===')
        self.stdout.write('=' * 50)
        for model, label in [
            (User, 'Users'), (Course, 'Courses'), (Enrollment, 'Enrollments'),
            (ChatSession, 'Chat Sessions'), (ChatMessage, 'Chat Messages'),
            (UploadedFile, 'Files'), (VectorCollection, 'Vector Collections'),
            (LearningRecord, 'Learning Records'), (SystemSetting, 'Settings'),
            (AgentAPIConfig, 'Agent API Configs'),
            (PromptTemplate, 'Prompt Templates'), (ContextStrategy, 'Context Strategies'),
            (RAGPipeline, 'RAG Pipelines'),
        ]:
            self.stdout.write(f'  {label}: {model.objects.count()}')
        self.stdout.write('\n>> Test accounts:')
        self.stdout.write('  admin    / admin123    (管理员)')
        self.stdout.write('  teacher  / teacher123  (教师)')
        self.stdout.write('  student  / student123  (学生)')
        self.stdout.write('  (all other users: password = 123456)')

    # ── Prompt Templates ────────────────────────────────

    def _seed_prompt_templates(self):
        from prompt_engine.models import PromptTemplate, PromptVersion
        from services.prompt_files import load_db_templates

        if PromptTemplate.objects.exists():
            self.stdout.write(f'  [SKIP] Prompt templates: {PromptTemplate.objects.count()} (skipped)')
            return

        admin = User.objects.filter(role=User.Role.ADMIN).first()
        # 模板正文维护在 docs/prompts/templates/*.md，这里是唯一出处；
        # 不要再往本文件里硬编码提示词文本。
        templates = [
            {
                "name": t["name"], "skill": t["skill"],
                "is_default": t["is_default"], "content": t["content"],
            }
            for t in load_db_templates()
        ]
        for td in templates:
            tmpl = PromptTemplate.objects.create(
                name=td["name"], skill=td["skill"], content=td["content"],
                variables={"course_name": "课程名称", "retrieval_docs": "检索到的参考资料",
                           "memory_prompt": "学生画像", "user_question": "学生问题"},
                is_default=td.get("is_default", False),
                created_by=admin,
            )
            PromptVersion.objects.create(
                template=tmpl, version=1, content=tmpl.content,
                variables=tmpl.variables, change_note="系统初始化",
                created_by=admin,
            )
        self.stdout.write(f'  [OK] Prompt templates: {PromptTemplate.objects.count()}')

    # ── Context Strategies ──────────────────────────────

    def _seed_context_strategies(self):
        from context_engine.models import ContextStrategy

        if ContextStrategy.objects.exists():
            self.stdout.write(f'  [SKIP] Context strategies: {ContextStrategy.objects.count()} (skipped)')
            return

        admin = User.objects.filter(role=User.Role.ADMIN).first()
        ContextStrategy.objects.create(
            name="默认策略",
            description="系统默认上下文策略 — 标准检索+记忆+历史",
            top_k=5, similarity_threshold=0.0,
            chunk_size=500, chunk_overlap=50,
            max_context_tokens=3000,
            include_memory=True, include_history=True, history_turns=10,
            rerank_enabled=False, enable_query_rewrite=False,
            is_active=True, is_default=True,
            created_by=admin,
        )
        self.stdout.write(f'  [OK] Context strategies: {ContextStrategy.objects.count()}')

    # ── RAG Pipeline ────────────────────────────────────

    def _seed_pipeline(self):
        from harness.models import RAGPipeline
        from prompt_engine.models import PromptTemplate
        from context_engine.models import ContextStrategy

        if RAGPipeline.objects.exists():
            self.stdout.write(f'  [SKIP] RAG Pipelines: {RAGPipeline.objects.count()} (skipped)')
            return

        admin = User.objects.filter(role=User.Role.ADMIN).first()
        template = PromptTemplate.objects.filter(is_default=True, skill="qa").first()
        strategy = ContextStrategy.objects.filter(is_default=True).first()
        agent = AgentAPIConfig.objects.filter(is_default=True).first()
        if template and strategy and agent:
            RAGPipeline.objects.create(
                name="默认管道", description="系统默认 RAG 管道",
                prompt_template=template, context_strategy=strategy,
                agent_config=agent, is_active=True, is_default=True,
                created_by=admin,
            )
            self.stdout.write('  [OK] RAG Pipeline: 1 (默认管道)')
        else:
            self.stdout.write('  [WARN] RAG Pipeline: skipped (missing template/strategy/agent config)')


