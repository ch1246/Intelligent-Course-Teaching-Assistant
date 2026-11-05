"""
提示词文档加载器 —— 让 ``docs/prompts/`` 成为提示词的唯一出处。

两套提示词都以 Markdown 文档形式维护：

``docs/prompts/templates/*.md``
    存库的 Jinja2 模板（5 种技能）。``seed_data`` 从这里读取写入
    ``PromptTemplate`` 表，之后由管理后台的「提示词模板」页面在线编辑。
    **注意**：在线编辑改的是数据库，不会回写这些文档；文档是"出厂模板"。

``docs/prompts/legacy/*.md``
    兜底提示词。数据库里没有可用模板时才用它组装 system prompt。

文档格式
--------
模板文档用 front matter 存元信息，正文即提示词全文::

    ---
    name: 默认问答助手
    skill: qa
    is_default: true
    ---
    正文（Jinja2 模板）……

兜底文档把「角色」和「要求」分成两段，便于分别复用::

    ---
    skill: qa
    ---
    [角色]
    你是"{course_name}"课程的 AI 教学助手……

    [要求]
    讲解要求：……

解析只依赖标准库，不引入 YAML 依赖。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# 「角色」/「要求」分段标记（见模块 docstring）
_LEGACY_ROLE_MARK = "[角色]"
_LEGACY_RULE_MARK = "[要求]"


def get_prompts_dir() -> Path:
    """提示词文档根目录。默认 ``<repo>/docs/prompts``，可用环境变量覆盖。

    放在 docs/ 下是刻意的：提示词就是给"人"读和改的文档，
    不该埋在代码常量或数据库里。
    """
    env = os.environ.get("PROMPTS_DIR", "").strip()
    if env:
        return Path(env)
    # 本文件位于 backend/services/，项目根目录是它的上两级
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "docs" / "prompts"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """把文档拆成 (元信息, 正文)。

    front matter 是两个 ``---`` 行之间的 ``key: value`` 行。这里只按行解析，
    不引入 PyYAML；值里再出现 ``: `` 也不会误切（只在第一个分隔符处切一次）。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    meta: dict[str, str] = {}
    end = None
    for i in range(1, len(lines)):
        stripped = lines[i].strip()
        if stripped == "---":
            end = i
            break
        if not stripped or ":" not in lines[i]:
            continue
        key, _, value = lines[i].partition(":")
        meta[key.strip()] = value.strip()

    if end is None:  # 没有闭合的 ---，按无 front matter 处理
        return {}, text

    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return meta, body


# ── 存库模板（docs/prompts/templates/）─────────────────

@lru_cache(maxsize=1)
def load_db_templates() -> tuple[dict, ...]:
    """读取全部存库模板文档，按文件名排序返回。

    每项形如 ``{"name", "skill", "is_default", "content", "file"}``。
    """
    directory = get_prompts_dir() / "templates"
    if not directory.is_dir():
        raise FileNotFoundError(f"提示词模板目录不存在：{directory}")

    templates = []
    for path in sorted(directory.glob("*.md")):
        meta, body = _parse_front_matter(_read_text(path))
        skill = meta.get("skill", "").strip()
        name = meta.get("name", "").strip()
        if not skill or not name:
            raise ValueError(f"{path} 缺少 front matter 字段 name / skill")
        templates.append({
            "name": name,
            "skill": skill,
            "is_default": meta.get("is_default", "false").strip().lower() == "true",
            "content": body,
            "file": str(path),
        })

    if not templates:
        raise FileNotFoundError(f"提示词模板目录里没有 .md 文件：{directory}")
    return tuple(templates)


# ── 兜底提示词（docs/prompts/legacy/）──────────────────

@lru_cache(maxsize=1)
def load_common_rules() -> str:
    """通用要求：拼在每个兜底提示词末尾。"""
    path = get_prompts_dir() / "legacy" / "_common-rules.md"
    if not path.is_file():
        raise FileNotFoundError(f"通用要求文档不存在：{path}")
    # 文档开头有说明段落，真正的规则从「通用要求：」开始
    text = _read_text(path)
    marker = "通用要求："
    idx = text.find(marker)
    return text[idx:].strip() if idx >= 0 else text.strip()


@lru_cache(maxsize=1)
def load_legacy_prompts() -> dict[str, tuple[str, str]]:
    """读取兜底提示词，返回 ``{skill: (角色, 要求)}``。"""
    directory = get_prompts_dir() / "legacy"
    if not directory.is_dir():
        raise FileNotFoundError(f"兜底提示词目录不存在：{directory}")

    result: dict[str, tuple[str, str]] = {}
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("_"):
            continue  # _common-rules.md 由 load_common_rules() 单独处理
        meta, body = _parse_front_matter(_read_text(path))
        skill = meta.get("skill", "").strip() or path.stem

        if _LEGACY_RULE_MARK in body:
            role, _, rules = body.partition(_LEGACY_RULE_MARK)
        else:
            role, rules = body, ""
        role = role.replace(_LEGACY_ROLE_MARK, "", 1).strip()
        rules = rules.strip()
        result[skill] = (role, rules)

    if not result:
        raise FileNotFoundError(f"兜底提示词目录里没有 .md 文件：{directory}")
    return result
