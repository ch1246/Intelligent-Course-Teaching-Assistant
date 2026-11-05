"""
「设为默认」的原子化工具。

项目里有 4 个模型带 `is_default` 标记，语义都是「同一范围内至多一条默认」：
- PromptTemplate：按 skill 互斥
- ContextStrategy / RAGPipeline / AgentAPIConfig：全局互斥

旧实现都是两步、且不在事务里::

    Model.objects.filter(...).update(is_default=False)   # 步骤 1
    obj.is_default = True
    obj.save(update_fields=["is_default"])               # 步骤 2

并发两个请求交错执行时会出现 0 条默认（双方都把对方的标记清掉）或
2 条默认（互看不见对方）。MySQL 不支持部分唯一索引，
`UniqueConstraint(condition=Q(is_default=True))` 在这里用不了，
所以用 `select_for_update()` 行锁把并发的「设为默认」串行化。
"""
from __future__ import annotations

from django.db import transaction


def set_default_atomically(obj, *, scope: dict | None = None, field: str = "is_default"):
    """把 obj 设为默认，并在同一事务里取消同范围内其他记录的默认标记。

    Args:
        obj: 待设为默认的模型实例（必须已持久化，有 pk）。
        scope: 互斥范围的过滤条件，例如 ``{"skill": obj.skill}`` 表示按技能互斥；
            传 ``None`` 或 ``{}`` 表示全局互斥。
        field: 标记字段名，默认 ``is_default``。

    Returns:
        锁定并更新后的实例。同时会就地更新传入的 obj，让调用方手里的对象
        反映最新状态，避免序列化出旧值。
    """
    model = type(obj)
    scope = dict(scope or {})

    with transaction.atomic():
        locked = model.objects.select_for_update().get(pk=obj.pk)
        model.objects.filter(**scope).exclude(pk=locked.pk).update(**{field: False})
        setattr(locked, field, True)
        locked.save(update_fields=[field])

    setattr(obj, field, True)
    return locked
