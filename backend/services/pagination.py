"""
分页参数的统一安全解析。

此前各视图都写 ``int(request.GET.get("pageSize", 20))``，有两个后果：

1. 传 ``?pageSize=abc`` 直接抛 ValueError → 500；
2. 传 ``?pageSize=999999`` 会一次性把整表拉进内存，既拖慢数据库也吃爆应用。

这里统一成「非数字回退默认、越界夹到上限」，并给出各处一致的上限。
"""
from __future__ import annotations

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


def parse_paging(request, default_size: int = DEFAULT_PAGE_SIZE, max_size: int = MAX_PAGE_SIZE):
    """解析 ``page`` / ``pageSize`` 查询参数，返回 ``(page, size)``。

    - 非数字 → 回退默认值（不再 500）
    - page 最小 1
    - size 夹在 ``[1, max_size]`` 之间
    """

    def _int(name, default, minimum, maximum):
        try:
            value = int(request.GET.get(name, default))
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, value))

    page = _int("page", 1, 1, 10 ** 9)
    size = _int("pageSize", default_size, 1, max_size)
    return page, size
