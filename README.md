<p align="center">
  <img src="UI/public/logo2.png" alt="Teek" width="96" />
</p>

<h1 align="center">Teek 教学助手</h1>
<p align="center"><strong>Teek Teaching Assistant</strong> — 基于 RAG 的 AI 教学辅助平台</p>

<p align="center">
  <img src="https://img.shields.io/badge/backend-Django%206.0.7-092E20?logo=django" alt="Django" />
  <img src="https://img.shields.io/badge/framework-DRF-ff1709?logo=django" alt="DRF" />
  <img src="https://img.shields.io/badge/database-MySQL-4479A1?logo=mysql" alt="MySQL" />
  <img src="https://img.shields.io/badge/vector--db-ChromaDB-FF7F50" alt="ChromaDB" />
  <img src="https://img.shields.io/badge/auth-SimpleJWT-000?logo=jsonwebtokens" alt="JWT" />
  <img src="https://img.shields.io/badge/frontend-Vue%203-4FC08D?logo=vue.js" alt="Vue" />
  <img src="https://img.shields.io/badge/UI-Element%20Plus-409EFF?logo=element" alt="Element Plus" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

---

## 📖 项目简介

**Teek 教学助手**是一款面向高校课程的 AI 教学辅助平台。通过 **RAG（检索增强生成）** 技术，将教师上传的课件、教材、实验指导等课程资料向量化存储，学生在对话时自动检索相关内容，结合 LLM 生成精准、有据可查的回答。

平台集成了 **提示词工程**、**上下文工程** 和 **编排评估（Harness）** 三大核心能力，不仅提供智能问答，还可以通过可视化界面管理提示词模板、调优检索策略、编排管道并追踪链路。

### 核心功能

| 模块 | 功能 |
|------|------|
| 🤖 **AI 智能对话** | 5 种技能模式（问答/公式推导/代码调试/实验指导/论文速读），SSE 流式输出 |
| 📚 **向量知识库** | 支持 PDF/Word/PPT/Markdown 上传，自动分块、嵌入、索引 |
| ✏️ **提示词工程** | Jinja2 模板编辑、变量插值、版本历史、在线预览、一键回滚 |
| 🎛️ **上下文工程** | 检索 Top-K、相似度阈值、分块参数、Token 预算、重排开关可配置 |
| 📊 **编排评估** | 管道编排 + 链路追踪 |
| 🔐 **安全认证** | JWT 双 Token + 刷新轮换与黑名单、API Key Fernet 加密 |
| 🌓 **主题切换** | Element Plus 暗黑/明亮模式，CSS 变量统一管理 |
| 🌍 **国际化** | 中英文切换，i18n key 规范化 |

---

## 🏗️ 技术架构

```
                   ┌─────────────────────────┐
                   │   Vue 3 + Element Plus   │
                   │      前端 (UI/)          │
                   └───────────┬─────────────┘
                               │ HTTP / SSE
                               ▼
                   ┌─────────────────────────┐
                   │   Django 6 + DRF        │
                   │    REST API (backend/)   │
                   └─────┬──────┬──────┬─────┘
                         │      │      │
              ┌──────────▼┐  ┌──▼──┐ ┌─▼──────────┐
              │   MySQL    │  │ JWT  │ │  ChromaDB   │
              │ (业务数据)  │  │ 认证  │ │  (向量存储)  │
              └────────────┘  └─────┘ └─────────────┘
```

### RAG 管线流程

```
用户上传文档 → 递归分块 → BGE Embedding (1024维) → ChromaDB 存储
                                                       ↓
用户提问 → Embedding → Top-K 相似检索 → 相似度过滤 → 上下文策略组装
                                                       ↓
                  Jinja2 模板渲染 ← 学生画像注入 ← 对话历史裁剪
                                                       ↓
                          OpenAI 兼容 LLM → SSE 流式输出 → TraceLog 记录
```

### 项目结构

```
rag/
├── .env                        # 环境配置（唯一需要修改的文件）
├── .env.example                # 配置模板（Git 跟踪）
├── .gitignore
├── README.md
├── backend/                    # Django 后端
│   ├── main.py                 # 启动入口
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                 # settings / urls / wsgi
│   ├── accounts/               # 用户与认证（JWT + Token 黑名单）
│   ├── courses/                # 课程管理
│   ├── enrollments/            # 选课审批
│   ├── chat/                   # AI 对话（SSE 流式 + 记忆追踪）
│   ├── vector_db/              # 向量知识库
│   ├── files_app/              # 文件管理
│   ├── dashboard/              # 仪表盘与统计
│   ├── settings_app/           # 系统设置 + Agent API
│   ├── prompt_engine/          # ★ 提示词工程
│   ├── context_engine/         # ★ 上下文工程
│   ├── harness/                # ★ 编排评估 + 链路追踪
│   └── services/               # RAG 核心服务
├── UI/                         # Vue 3 前端
│   ├── src/
│   │   ├── views/admin/        # 管理中心（13 个页面）
│   │   ├── views/course/       # 课程中心（6 个页面）
│   │   ├── common/http/        # Axios 封装（自动刷新 Token）
│   │   ├── common/languages/   # 中英文翻译
│   │   └── pinia/              # 状态管理
│   ├── vite.config.mts         # Vite 配置
│   └── .env.development
└── docs/                       # 项目文档
```

---

## 🚀 快速开始

### 前提条件

- Python 3.12+
- Node.js 20+ / pnpm
- MySQL 8.0+

### 1. 克隆项目

```bash
git clone <repo-url>
cd rag
```

### 2. 配置环境变量

```bash
# 复制模板（只需一次）
copy .env.example .env
```

编辑 `.env`，修改数据库密码等配置：

```env
DB_PASSWORD=your_real_password    # 必改
DJANGO_SECRET_KEY=xxx             # 生产必改
VITE_PROXY_TARGET=http://localhost:9000
```

### 3. 创建数据库

```sql
CREATE DATABASE teek_teaching_assistant DEFAULT CHARACTER SET utf8mb4;
```

### 4. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# 数据库迁移 + 种子数据
python manage.py migrate
python manage.py seed_data

# 启动
python main.py runserver 127.0.0.1:9000
```

### 5. 启动前端

```bash
cd UI
pnpm install
pnpm dev
```

访问 **http://localhost:8099**

### 6. 登录测试

| 账号 | 密码 | 角色 |
|------|------|------|
| `admin` | `admin123` | 管理员 |
| `teacher` | `teacher123` | 教师 |
| `student` | `student123` | 学生 |

---

## ⚙️ 配置 LLM API

运行 `seed_data` 后已自动创建示例配置（api_key = `your-api-key-here`）。

登录后在 **管理中心 → Agent API 配置** 填入真实 API Key 即可。

> 💡 **安全说明**：API Key 以 Fernet 加密存储于数据库，API 响应脱敏为 `sk-****xxxx`，前端无法读取真实值。

支持的 LLM 服务：
- [OpenAI](https://platform.openai.com/) — `https://api.openai.com/v1`
- [DeepSeek](https://platform.deepseek.com/) — `https://api.deepseek.com/v1`
- [阿里百炼](https://bailian.console.aliyun.com/) — `https://dashscope.aliyuncs.com/compatible-mode/v1`
- [硅基流动](https://siliconflow.cn/) — `https://api.siliconflow.cn/v1`
- [Ollama](https://ollama.com/) — `http://localhost:11434/v1`（本地部署）

---

## 📡 API 接口概览

> 认证方式：JWT Bearer Token（登录获取 `accessToken` / `refreshToken`）  
> 响应格式：`{ code, status, message, data }`

### 认证

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录（获取 Token） |
| POST | `/api/auth/register` | 注册（需审核） |
| GET | `/api/auth/getUserInfo` | 获取当前用户信息 |
| POST | `/api/auth/refresh` | 刷新 Token |
| POST | `/api/auth/change-password` | 修改密码 |
| POST | `/api/auth/forgot-password` | 忘记密码 |

### AI 对话

| 方法 | 接口 | 说明 |
|------|------|------|
| GET/POST | `/api/course/{id}/chat/sessions` | 会话列表 / 创建 |
| DELETE | `/api/course/{id}/chat/sessions/{sid}` | 删除会话 |
| POST | `/api/course/{id}/chat/completions` | **SSE 流式对话** |
| GET | `/api/course/{id}/chat/memory` | 用户学习记忆 |

### 管理中心

| 模块 | 接口前缀 | 功能 |
|------|----------|------|
| 仪表盘 | `/api/admin/dashboard` | 数据概览 |
| 用户管理 | `/api/admin/users` | CRUD + 搜索 |
| 课程管理 | `/api/admin/courses` | CRUD |
| 选课审核 | `/api/admin/enroll-review` | 审核通过/拒绝/批量 |
| 向量知识库 | `/api/admin/vector-db/collections` | 集合管理 + 文档上传 + 重建索引 |
| Agent API | `/api/admin/agent-api-configs` | LLM 配置管理 |
| **提示词模板** | `/api/admin/prompts` | CRUD + 预览 + 版本历史 + 回滚 |
| **上下文策略** | `/api/admin/context-strategies` | CRUD + 设为默认 |
| **管道编排** | `/api/admin/pipelines` | CRUD + 绑定模板/策略/模型 |
| **链路追踪** | `/api/admin/traces` | 检索/组装/生成/记忆四阶段耗时 |

### 课程中心

| 接口 | 说明 |
|------|------|
| `/api/course/my-courses` | 我的课程列表 |
| `/api/course/enroll` | 选课申请 |
| `/api/course/{id}/dashboard` | 课程看板 |
| `/api/course/{id}/chat-stats` | 对话统计 |
| `/api/course/{id}/learning-time` | 学习时长统计 |
| `/api/course/{id}/summary` | 一键总结 |

---

## 🔒 安全特性

| 特性 | 实现方式 |
|------|----------|
| **密码哈希** | Django `AbstractUser` — PBKDF2 + SHA256 |
| **API Key 加密** | `cryptography.fernet` 对称加密，密钥由 `API_KEY_ENCRYPTION_KEY` 提供（未配置时由 SECRET_KEY 派生） |
| **JWT 双 Token** | access 2h / refresh 7d；每次刷新都轮换 refresh 并把旧 token 拉黑（`token_blacklist`），access 过期后仍可用 refresh 续期 |
| **CORS 白名单** | `django-cors-headers` + `CORS_ALLOWED_ORIGINS` |
| **忘记密码** | 邮箱查用户 + 随机临时密码；**确认邮件送达后才覆盖原密码**，避免账号被反复锁死 |
| **Excel 导入** | 随机 10 位初始密码（非学号后 6 位） |
| **配置安全** | 全部通过 `.env` 注入，无敏感信息硬编码 |

---

## 🔧 环境变量参考

> 所有变量集中在 `rag/.env`，后端 `python-dotenv` + 前端 Vite 自动加载

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DJANGO_SECRET_KEY` | (fallback) | Django 密钥 |
| `API_KEY_ENCRYPTION_KEY` | (由 SECRET_KEY 派生) | API Key 的 Fernet 密钥（32 字节 urlsafe-base64），未配置则回退派生 |
| `DJANGO_DEBUG` | `True` | 调试开关 |
| `DJANGO_ALLOWED_HOSTS` | `*` | 允许主机 |
| `DB_NAME` | `teek_teaching_assistant` | 数据库名 |
| `DB_USER` | `root` | 数据库用户 |
| `DB_PASSWORD` | — | 数据库密码 |
| `DB_HOST` | `127.0.0.1` | 数据库地址 |
| `DB_PORT` | `3306` | 数据库端口 |
| `CORS_ALLOWED_ORIGINS` | `localhost:8099` | CORS 白名单 |
| `CHROMADB_PERSIST_DIR` | `backend/chroma_data` | 向量数据目录 |
| `VITE_PROXY_TARGET` | `http://localhost:9000` | 前端代理地址 |

---

## 📋 提示词模板变量

Jinja2 模板中可用的变量：

| 变量 | 说明 |
|------|------|
| `{{ course_name }}` | 当前课程名称 |
| `{{ retrieval_docs }}` | 检索到的课程资料文本 |
| `{{ memory_prompt }}` | 学生画像（薄弱/已掌握知识点） |
| `{{ user_question }}` | 学生当前问题 |

---

## 📄 License

MIT License

---

## 🙏 致谢

- [Django](https://www.djangoproject.com/)
- [Vue.js](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [ChromaDB](https://www.trychroma.com/)
- [BAAI/bge-large-zh-v1.5](https://huggingface.co/BAAI/bge-large-zh-v1.5)
- [Teek Design Vue3](https://github.com/Kele-Bingtang/teek-design-vue3) — 前端模板
