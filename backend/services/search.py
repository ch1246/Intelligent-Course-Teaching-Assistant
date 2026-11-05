"""
关键词搜索的统一入口。

问题
----
各视图原本直接写 ``name__icontains=search``。``LIKE '%kw%'`` 的通配符在左边，
B+ 树索引完全用不上，必然全表扫描；数据量一上来列表接口就会跟着变慢。

方案
----
MySQL 上改走 FULLTEXT（``WITH PARSER ngram``）索引，由 ``MATCH ... AGAINST``
检索，不再扫表。ngram 解析器是 MySQL 8 内置的，专门解决中文这类无空格文本的
分词问题。

两条降级规则，保证语义不回退：

1. **单字查询退回 icontains** —— ngram 的 ``ngram_token_size`` 默认是 2，
   一个汉字在 FULLTEXT 里根本匹配不到；用户随手输一个字时必须还能搜。
2. **非 MySQL 后端退回 icontains** —— 其它数据库没有 ngram，直接用 LIKE
   保证行为一致（这些表在非 MySQL 环境下也都很小）。

关于多字段
----------
多列搜索必须写成 ``MATCH(a,b,c) AGAINST (...)`` **一条**条件才能走索引；
写成 ``MATCH(a) OR MATCH(b)`` 会被优化器退化成全表扫描。因此这里按「搜索分组」
组织，每组对应一个多列 FULLTEXT 索引，索引定义见
``accounts/migrations/0007_fulltext_ngram_search.py``。两边用同一份
``SEARCH_GROUPS`` 常量，避免索引列与查询列漂移。
"""
from __future__ import annotations

import functools

from django.db import connection
from django.db.models import Q
from django.db.models.expressions import RawSQL

MAX_TERM_LEN = 50
# ngram_token_size 默认 2，短于这个长度 FULLTEXT 匹配不到任何行
MIN_FULLTEXT_TERM_LEN = 2

# 搜索分组 → 参与匹配的列。必须与 0007_fulltext_ngram_search.py 的索引列一致。
SEARCH_GROUPS: dict[str, tuple[str, ...]] = {
    "user": ("username", "student_id", "dept", "email"),
    "course": ("name",),
    "prompt": ("name", "description"),
    "collection": ("name",),
}


@functools.lru_cache(maxsize=1)
def _supports_fulltext() -> bool:
    """是否走 FULLTEXT 检索（仅 MySQL）。"""
    return connection.vendor == "mysql"


def normalize_term(term: str | None) -> str:
    """清洗关键词：去首尾空白、压缩连续空白、截断到安全长度。"""
    if not term:
        return ""
    cleaned = " ".join(str(term).split())
    return cleaned[:MAX_TERM_LEN]


def search_filter(queryset, term: str | None, group: str):
    """按关键词过滤 queryset。``group`` 取 ``SEARCH_GROUPS`` 的键。

    空关键词直接原样返回，不做任何过滤；未知分组抛 ``KeyError``，避免拼错
    分组名时悄悄退化成全表扫描。
    """
    cleaned = normalize_term(term)
    if not cleaned:
        return queryset

    columns = SEARCH_GROUPS[group]

    use_fulltext = _supports_fulltext() and len(cleaned) >= MIN_FULLTEXT_TERM_LEN
    if not use_fulltext:
        q = Q()
        for column in columns:
            q |= Q(**{f"{column}__icontains": cleaned})
        return queryset.filter(q)

    # 一条 MATCH 覆盖整组列，让优化器能命中对应的多列 FULLTEXT 索引
    column_list = ", ".join(columns)
    return (
        queryset.annotate(
            _ft_rank=RawSQL(f"MATCH ({column_list}) AGAINST (%s)", (cleaned,))
        )
        .filter(_ft_rank__gt=0)
    )
