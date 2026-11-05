"""
RAG 链路核心模块（生产在用）—— 提示词装配 + LCEL Chain 构建。

生产链路（chat/views.py）直接调用：
  - render_system_prompt()        系统提示词装配（DB 模板 Jinja2 渲染 / legacy 技能提示词兜底）
  - build_system_prompt_legacy() / build_system_prompt_from_template()  同上的两个内部实现
  - format_docs()                 LangChain Document 列表格式化

LCEL 构建器（build_rag_chain*）供脚本与实验使用：
  chain = build_rag_chain(llm, retriever, memory_prompt)
  支持 .invoke() / .stream() / .astream()（流式由 llm 的 streaming=True 决定）。

设计约束：
  - langchain_core 在 LCEL 构建函数内惰性导入，提示词装配本身不依赖 LangChain，
    保证缺依赖时生产链路仍可降级运行；
  - 提示词正文集中在本文件，改提示词只改这里。
"""
import logging
from functools import lru_cache
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # 仅类型标注用
    from langchain_core.documents import Document


# ── 文档格式化 ─────────────────────────────────────────

def format_docs(docs: list["Document"]) -> str:
    """把 LangChain Document 列表格式化为「来源 + 正文」的文本块。"""
    return "\n\n---\n\n".join([
        f"[来源: {d.metadata.get('source', '未知')}]\n{d.page_content}"
        for d in docs
    ])


def _docs_to_context(context_docs: list[dict]) -> str:
    """把检索结果（dict: content/metadata）格式化为参考资料文本块。"""
    return "\n\n---\n\n".join([
        f"[来源: {d.get('metadata', {}).get('source', '未知')}]\n{d['content']}"
        for d in context_docs
    ])


# ── 系统提示词装配（生产链路）───────────────────────────
#
# 提示词文本全部维护在 docs/prompts/ 下的 Markdown 文档里，那是唯一出处：
#   docs/prompts/templates/*.md  → 存库的 Jinja2 模板（seed_data 读它入库）
#   docs/prompts/legacy/*.md     → 兜底提示词（本文件读它组装）
# 要改提示词请改文档，不要改本文件；本文件只负责读取与组装。


@lru_cache(maxsize=1)
def _get_legacy_prompts() -> tuple[dict, str]:
    """读取兜底提示词（角色/要求）与通用要求。

    文档目录缺失时退回最小可用提示词并告警 —— 宁可回答朴素，也不能因为
    少了几个 md 文件就把整个问答链路打挂。
    """
    from services import prompt_files

    try:
        return prompt_files.load_legacy_prompts(), prompt_files.load_common_rules()
    except Exception:
        logger.warning("docs/prompts/legacy 不可用，已退回内置最小兜底提示词", exc_info=True)
        minimal = "优先依据【参考资料】回答；资料中没有的信息不要编造，并注明是补充说明。"
        return {}, minimal


def build_system_prompt_legacy(
    skill: str, course_name: str, context_docs: list[dict], memory_prompt: str = "",
) -> str:
    """Legacy 兜底提示词：按技能组装（DB 模板缺失时使用）。

    角色/要求/通用规则三段都来自 docs/prompts/legacy/ 文档。
    """
    prompts, common_rules = _get_legacy_prompts()
    role, rules = prompts.get(skill) or prompts.get("qa") or ("", "")

    if not role:
        role = f'你是"{course_name}"课程的 AI 教学助手，请根据提供的课程资料解答学生问题。'
    # 用 replace 而不是 str.format：提示词正文里可能有任意花括号（LaTeX 等），
    # format 会把它们当占位符解析而炸掉。
    role = role.replace("{course_name}", course_name)

    sections = [role]
    if rules:
        sections.append(rules.replace("{course_name}", course_name))
    if common_rules:
        sections.append(common_rules)
    prompt = "\n\n".join(sections)

    if context_docs:
        prompt += f"\n\n【参考资料】\n{_docs_to_context(context_docs)}"
    if memory_prompt:
        prompt += memory_prompt
    return prompt


def build_system_prompt_from_template(
    template_content: str, course_name: str, context_docs: list[dict],
    memory_prompt: str = "", user_question: str = "",
) -> str:
    """用 Jinja2 渲染 DB 提示词模板；渲染失败退回字符串替换兜底。

    模板可用变量：{{ course_name }} / {{ retrieval_docs }} /
    {{ memory_prompt }} / {{ user_question }}
    """
    docs_text = _docs_to_context(context_docs) if context_docs else ""
    try:
        from jinja2 import Template
        return Template(template_content).render(
            course_name=course_name,
            retrieval_docs=docs_text,
            memory_prompt=memory_prompt,
            user_question=user_question,
        )
    except Exception:
        # Jinja2 渲染失败 → 退回 legacy 字符串替换
        return template_content.replace("{{ course_name }}", course_name) \
                               .replace("{{ retrieval_docs }}", docs_text) \
                               .replace("{{ memory_prompt }}", memory_prompt) \
                               .replace("{{ user_question }}", user_question)


def render_system_prompt(
    template_content: str | None, skill: str, course_name: str,
    context_docs: list[dict], memory_prompt: str = "", user_question: str = "",
    global_preamble: str = "",
) -> str:
    """统一入口：有 DB 模板走 Jinja2 渲染，否则走 legacy 技能提示词。

    ``global_preamble`` 来自 AgentAPIConfig.system_prompt（后台的「全局 System
    Prompt」），作为**全局前置**拼在最终 system prompt 最前面 —— 无论用哪套技能
    模板都生效，适合放校方统一规范、安全红线等。此前这个字段在后台能填、
    序列化器也返回，但运行时零读取，属于「配置骗人」。
    """
    if template_content:
        prompt = build_system_prompt_from_template(
            template_content, course_name, context_docs, memory_prompt, user_question,
        )
    else:
        prompt = build_system_prompt_legacy(skill, course_name, context_docs, memory_prompt)

    preamble = (global_preamble or "").strip()
    if preamble:
        prompt = f"{preamble}\n\n{prompt}"
    return prompt


# ── LCEL Chain 构建器（脚本/实验用）────────────────────

_CHAIN_TEMPLATE = """你是教学助手，请根据【参考资料】回答用户问题。

回答要求：优先使用参考资料并标注来源；资料未覆盖的内容不要编造，可补充通用知识但须说明；结构清晰，公式用 LaTeX $$...$$ 呈现。

【参考资料】
{context}
{memory_prompt}
用户问题：{question}"""

_CHAIN_TEMPLATE_WITH_HISTORY = """你是教学助手，请根据【参考资料】和对话历史回答用户问题。

回答要求：优先使用参考资料并标注来源；资料未覆盖的内容不要编造，可补充通用知识但须说明；结构清晰，公式用 LaTeX $$...$$ 呈现；与历史回答保持一致，不要重复已讲过的内容。

【参考资料】
{context}
{memory_prompt}
{history}
用户问题：{question}"""


def _build_chain(llm, retriever, template: str, memory_prompt: str, with_history: bool = False):
    """LCEL 组装的唯一实现（build_rag_chain* 全部委托到这里）。"""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough

    prompt = ChatPromptTemplate.from_template(template)
    mapping = {
        "context": retriever | format_docs,
        "question": RunnablePassthrough(),
        "memory_prompt": lambda _: memory_prompt,
    }
    if with_history:
        mapping["history"] = RunnablePassthrough()
    return mapping | prompt | llm | StrOutputParser()


def build_rag_chain(llm, retriever, memory_prompt: str = ""):
    """构建 LCEL RAG Chain（同步/流式均可用：.invoke() / .stream() / .astream()）。"""
    return _build_chain(llm, retriever, _CHAIN_TEMPLATE, memory_prompt)


def build_rag_chain_stream(llm, retriever, memory_prompt: str = ""):
    """兼容别名：流式由 llm 的 streaming=True 决定，链本身与 build_rag_chain 相同。"""
    return build_rag_chain(llm, retriever, memory_prompt)


def build_rag_chain_with_history(llm, retriever, memory_prompt: str = ""):
    """构建含对话历史的 LCEL RAG Chain，输入需为 {"question": ..., "history": ...}。"""
    return _build_chain(llm, retriever, _CHAIN_TEMPLATE_WITH_HISTORY, memory_prompt, with_history=True)
