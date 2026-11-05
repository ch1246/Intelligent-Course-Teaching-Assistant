# 为关键词搜索补上 MySQL 全文索引（ngram），消除 `LIKE '%kw%'` 全表扫描。
#
# 背景
# ----
# 列表接口的搜索框此前都是 `name__icontains=search` 之类的写法。LIKE 的通配符
# 在左边，B+ 树索引用不上，必然全表扫描。MySQL 8 内置 ngram 解析器正好适合
# 中文这类无空格文本，这里为被搜索的列建 FULLTEXT 索引。
#
# 为什么是「多列」索引而不是逐列
# -----------------------------
# 多字段搜索必须写成 `MATCH(a,b,c) AGAINST (...)` **一条**条件，MySQL 才能走
# 索引。若写成 `MATCH(a) OR MATCH(b) OR MATCH(c)`，优化器无法用单个索引覆盖
# OR 分支，实测仍退化成 type=ALL 全表扫描。
#
# 同理，MATCH 的列清单必须与某个 FULLTEXT 索引的列集合一致。所以这里把
# 「会被一起搜索的列」各自合成一个多列索引，并在 services/search.py 里用
# 同一份分组常量 SEARCH_GROUPS 保证两边不漂移。
#
# 注意
# ----
# 1. 本迁移只在 MySQL 上执行（其它数据库由 services/search.py 自动退回 icontains）；
# 2. MySQL 的 DDL 不可回滚，必须 `atomic = False`；
# 3. 索引不存在时 ftsearch 会报错，所以请务必先跑完本迁移再上线检索代码。

from django.db import migrations

# (表名, 列元组) —— 必须与 services/search.py 的 SEARCH_GROUPS 保持一致
FULLTEXT_GROUPS = [
    ("accounts_user", ("username", "student_id", "dept", "email")),
    ("course", ("name",)),
    ("prompt_template", ("name", "description")),
    ("vector_collection", ("name",)),
]


def _index_name(table: str) -> str:
    return f"ft_{table}_ngram"


def add_fulltext(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        print("\n  [search] 非 MySQL 后端，跳过 FULLTEXT 索引（检索代码会自动退回 icontains）")
        return

    for table, columns in FULLTEXT_GROUPS:
        cols = ", ".join(columns)
        schema_editor.execute(
            f"ALTER TABLE {table} ADD FULLTEXT INDEX {_index_name(table)} ({cols}) WITH PARSER ngram"
        )
    print(f"\n  [search] 已为 {len(FULLTEXT_GROUPS)} 组列补上 FULLTEXT(ngram) 索引")


def drop_fulltext(apps, schema_editor):
    """删索引。必须幂等：索引不存在时安静跳过，否则在手工清理过索引的环境里
    回滚会直接炸掉，导致迁移状态卡住无法前进。"""
    if schema_editor.connection.vendor != "mysql":
        return
    for table, _ in FULLTEXT_GROUPS:
        try:
            schema_editor.execute(f"ALTER TABLE {table} DROP INDEX {_index_name(table)}")
        except Exception:  # noqa: BLE001 - 索引本就不存在，跳过
            pass


class Migration(migrations.Migration):

    # MySQL 的 DDL 不可回滚，不能包在事务里
    atomic = False

    dependencies = [
        ("accounts", "0006_fix_student_id_unique"),
        ("courses", "0006_add_cover_icon"),
        ("prompt_engine", "0001_initial"),
        ("vector_db", "0002_uniq_collection_per_course"),
    ]

    operations = [
        migrations.RunPython(add_fulltext, drop_fulltext),
    ]
