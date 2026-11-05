# 提示词模板

本目录是 **Teek 教学助手所有提示词的唯一出处**。提示词以 Markdown 文档维护，
代码从这里读取，不再在源码或种子脚本里硬编码提示词正文。

```
docs/prompts/
├── README.md              ← 本文
├── templates/             ← 存库的 Jinja2 模板（管理后台「提示词模板」页面用的就是它们）
│   ├── qa.md              ← 问答
│   ├── formula.md         ← 公式推导
│   ├── code_debug.md      ← 代码调试
│   ├── lab_guide.md       ← 实验指导
│   └── paper_reader.md    ← 论文速读
└── legacy/                ← 兜底提示词（数据库没有可用模板时才用）
    ├── _common-rules.md   ← 通用要求，拼在每个兜底提示词末尾
    ├── qa.md
    ├── formula.md
    ├── code_debug.md
    ├── lab_guide.md
    └── paper_reader.md
```

---

## 一、两套提示词的区别

| | `templates/` | `legacy/` |
|---|---|---|
| 用途 | **主用**：写入数据库，运行时渲染 | **兜底**：数据库里查不到模板时才用 |
| 格式 | Jinja2 模板 | 三段拼接（角色 + 要求 + 通用要求） |
| 谁读它 | `manage.py seed_data`（首次入库） | `services/rag_chain.py`（每次组装 system prompt） |
| 能否在线改 | 能，在管理后台「提示词模板」页面 | 不能，只能改这里的文档 |

**优先级**（见 `services/rag_chain.py` 的 `render_system_prompt`）：

```
命中数据库模板？ ──是──▶ Jinja2 渲染模板
        │
        否
        ▼
   用 legacy/ 兜底组装
        │
        ▼
   Jinja2 渲染抛异常？ ──是──▶ 退回字符串替换（只替换 4 个 {{ 变量 }}）
```

---

## 二、可用变量

模板里只能用这 4 个变量（多写无效，会被原样输出）：

| 变量 | 含义 | 示例 |
|---|---|---|
| `{{ course_name }}` | 当前课程名称 | `机器学习` |
| `{{ retrieval_docs }}` | 检索到的课程资料文本，每段前带 `[来源: 文件名]` | — |
| `{{ memory_prompt }}` | 学生画像（薄弱 / 学习中 / 已掌握的知识点） | — |
| `{{ user_question }}` | 学生当前的问题 | — |

> `legacy/` 里的 `{course_name}` 是**单花括号**，因为它走字符串替换而不是 Jinja2。
> 两套格式不要混用。

---

## 三、文档格式

### `templates/*.md` — front matter + 模板正文

```markdown
---
name: 默认问答助手
skill: qa
is_default: true
---

你是"{{ course_name }}"课程的AI教学助手。……
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | ✅ | 模板显示名，入库后可在后台改 |
| `skill` | ✅ | 技能标识，只能是 `qa` / `formula` / `code_debug` / `lab_guide` / `paper_reader` |
| `is_default` | | `true` 表示作为该技能的默认模板。同一技能下只能有一个默认 |

front matter 之后的**全部内容**就是模板正文，会原样入库。

### `legacy/*.md` — front matter + `[角色]` / `[要求]` 两段

```markdown
---
skill: qa
---

[角色]
你是"{course_name}"课程的 AI 教学助手……

[要求]
讲解要求：概念先给定义、再给直觉解释、最后举例或应用场景。
```

`[要求]` 之后的内容是输出规范；`_common-rules.md` 的「通用要求：」之后的段落
会追加到每个技能的末尾。

---

## 四、怎么改提示词

### 改「出厂模板」（影响新建的数据库模板）

1. 直接编辑 `templates/` 下对应的 `.md` 文件；
2. 如果数据库里**还没有**模板，重新执行一次即可入库：
   ```powershell
   cd backend
   .venv\Scripts\python.exe manage.py seed_data
   ```
   （`seed_data` 在 `PromptTemplate` 已有数据时会跳过，不会覆盖你在后台做的修改。）

### 改「正在使用的模板」

数据库里已经有模板时，**改这里的文档不会影响线上行为** —— 运行时读的是数据库。
请登录管理后台 →「提示词模板」页面编辑，那里的每次保存都会生成新版本、可一键回滚。

> 建议：在后台改完后，把最终满意的版本同步回 `templates/` 下的文档，
> 这样文档始终是可信的底稿。

### 改「兜底提示词」

直接编辑 `legacy/` 下的文档，**立即生效**，无需重启或入库
（进程内有内存缓存，开发环境建议重启一下后端进程）。

---

## 五、常见问题

**Q：改了文档没生效？**
A：`templates/` 的文档只在 `seed_data` 入库那一刻起作用；`legacy/` 的文档实时生效
但有内存缓存。两者都改完后请重启后端进程。

**Q：可以新增一种技能吗？**
A：可以，但要同时改四处：`chat/models.py` 的 `ChatSession.Skill`、
`prompt_engine/models.py` 的 `PromptTemplate.skill`、前端技能下拉框、以及本目录下
新增一个 `templates/xxx.md` 和 `legacy/xxx.md`。

**Q：为什么提示词要放 docs/ 而不是 resources/？**
A：提示词本质是**给老师和运营读、改的文档**，不是二进制资源。
放 `docs/` 便于直接阅读、评审和 diff。
