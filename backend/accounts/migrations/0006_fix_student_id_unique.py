# 修复 student_id 的「假唯一约束」。
#
# 现象
# ----
# `accounts/models.py` 里声明了 `student_id = CharField(..., unique=True)`，
# 相关迁移也记录为 applied，但实测 `SHOW INDEX FROM accounts_user` **没有任何
# student_id 索引**（连普通索引都没有）。原因是建库时 20 行数据的 student_id
# 全是空字符串 ''（COUNT(DISTINCT)=1），唯一索引建不上去，当时用
# `migrate --fake` 跳过了。
#
# 后果
# ----
# 1. 按学号查询/查重全表扫描（`accounts/views.py` 里按学号查用户的两处）；
# 2. **没有任何唯一性保障**，两条记录可以有相同的学号。
#
# 修复
# ----
# 1. 把空字符串规范成 NULL —— 字段本就是 `null=True, default=None`，
#    空串只是历史脏数据；MySQL 的唯一索引允许多个 NULL，所以「未填学号」
#    不会互相冲突。
# 2. 补上真正的唯一索引。若现存非空学号存在重复，则不建索引、只打印告警，
#    交由人工处理，避免迁移在生产上直接炸掉。

from django.db import migrations, models


def normalize_and_add_unique(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    connection = schema_editor.connection

    # 1) 空串 → NULL
    User.objects.filter(student_id="").update(student_id=None)

    # 2) 检查非空学号是否重复
    dupes = (
        User.objects.exclude(student_id__isnull=True)
        .values("student_id")
        .annotate(n=models.Count("id"))
        .filter(n__gt=1)
        .values_list("student_id", "n")
    )
    dupes = list(dupes)
    if dupes:
        print(
            "\n  [accounts] 未添加 student_id 唯一索引：存在重复学号 "
            + "、".join(f"{sid}×{n}" for sid, n in dupes)
            + "。请先人工合并这些记录，再重跑本迁移。"
        )
        return

    if connection.vendor != "mysql":
        # 其它数据库交给 Django 的标准约束；本项目实际跑在 MySQL 上。
        schema_editor.execute(
            "CREATE UNIQUE INDEX accounts_user_student_id_uniq ON accounts_user (student_id)"
        )
        return

    schema_editor.execute(
        "ALTER TABLE accounts_user ADD UNIQUE INDEX accounts_user_student_id_uniq (student_id)"
    )
    print("\n  [accounts] 已补上 student_id 唯一索引（空串已规范为 NULL）")


def drop_unique(apps, schema_editor):
    schema_editor.execute("ALTER TABLE accounts_user DROP INDEX accounts_user_student_id_uniq")


class Migration(migrations.Migration):

    # MySQL 的 DDL 不可回滚，不能跑在事务里，必须关掉 atomic
    atomic = False

    dependencies = [
        ("accounts", "0005_alter_user_student_id"),
    ]

    operations = [
        migrations.RunPython(normalize_and_add_unique, drop_unique),
    ]
