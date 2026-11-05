"""真实向量库端到端验证：检索距离是否真实 + 全量重灌幂等 + 分块参数是否生效。

只读现有集合；写入只发生在临时集合 `probe_full_reindex` 上，跑完即删。

跑法：& backend\\.venv\\Scripts\\python.exe tools\\verify_retrieval_e2e.py
"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402

from services.rag_service import (  # noqa: E402
    delete_collection,
    distance_to_similarity,
    get_chroma_client,
    get_collection,
    index_documents,
    search_similar,
)

PROBE = "probe_full_reindex"
OK = []


def check(name, ok, extra=""):
    OK.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"   → {extra}" if extra else ""))


def collection_names():
    return sorted(getattr(c, "name", c) for c in get_chroma_client().list_collections())


def main():
    print("现有集合:", collection_names())

    # ── 1) 真实检索：距离是真实值，阈值语义正确 ───────────
    print("\n① 真实检索（只读 course_2）")
    query = "什么是梯度下降算法"
    docs = search_similar("course_2", query, n_results=5)
    check("检索返回结果", len(docs) > 0, f"{len(docs)} 条")
    if docs:
        sims_new, sims_old = [], []
        for d in docs:
            cos = distance_to_similarity(d["distance"])
            sims_new.append(cos)
            sims_old.append(1 - d["distance"])
            print(f"     distance={d['distance']:.4f}  cos≈{cos:.4f}  "
                  f"source={d['metadata'].get('source', '?')}  {d['content'][:30]}…")
        check("距离不是全 0（旧代码里 LangChain 路径恒为 0）",
              any(d["distance"] for d in docs), f"distances={[round(d['distance'], 3) for d in docs]}")
        keep_new = sum(1 for s in sims_new if s >= 0.5)
        keep_old = sum(1 for s in sims_old if s >= 0.5)
        print(f"     平均 cos={sum(sims_new) / len(sims_new):.4f}；"
              f"阈值 0.5 保留：新公式 {keep_new}/{len(sims_new)}，旧公式 {keep_old}/{len(sims_old)}")
        check("新公式下相似度落在合理区间（0~1）", all(0.0 <= s <= 1.0 for s in sims_new))

    # ── 2) 全量重灌幂等 + 分块参数生效（临时集合） ─────────
    print("\n② 全量重灌与分块参数（临时集合，跑完删除）")
    docs_text = [
        "梯度下降通过负梯度方向迭代更新参数，学习率过大会震荡。" * 10,
        "反向传播用链式法则逐层计算梯度。" * 10,
    ]
    metas = [{"source": "probe_a.txt"}, {"source": "probe_b.txt"}]
    ids = ["probe_a", "probe_b"]

    delete_collection(PROBE)
    n1 = index_documents(PROBE, docs_text, metas, ids, None, chunk_size=120, chunk_overlap=20)
    cnt1 = get_collection(PROBE).count()

    # 模拟修复后的 reindex：先删集合，再把**全部**文件重灌一遍
    delete_collection(PROBE)
    n2 = index_documents(PROBE, docs_text, metas, ids, None, chunk_size=120, chunk_overlap=20)
    cnt2 = get_collection(PROBE).count()

    check("第二次全量重灌后向量数完全恢复（旧实现会丢）",
          n1 == n2 and cnt1 == cnt2 and cnt1 > 0, f"chunk {n1}→{n2}，集合 {cnt1}→{cnt2}")

    delete_collection(PROBE)
    n_big = index_documents(PROBE, docs_text, metas, ids, None, chunk_size=500, chunk_overlap=50)
    check("分块参数真的影响结果（120/20 与 500/50 块数不同）",
          n_big != n1, f"120/20 → {n1} 块，500/50 → {n_big} 块")

    # 检索仍然可用（用刚才写入的临时集合自测）
    hits = search_similar(PROBE, "学习率太大为什么会震荡", n_results=2)
    check("临时集合可正常检索", len(hits) > 0, f"top1 cos≈{distance_to_similarity(hits[0]['distance']):.4f}")

    # ── 3) 清理 ───────────────────────────────────────────
    delete_collection(PROBE)
    check("临时集合已删除", PROBE not in collection_names(), f"剩余: {collection_names()}")

    failed = [n for n, ok in OK if not ok]
    print(f"\n{'=' * 60}\n共 {len(OK)} 项，通过 {len(OK) - len(failed)} 项，失败 {len(failed)} 项")
    for n in failed:
        print("  FAIL:", n)
    return 1 if failed else 0


if __name__ == "__main__":
    conn = connection
    sys.exit(main())
