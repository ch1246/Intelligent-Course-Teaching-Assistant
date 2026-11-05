"""验证第二批修复：权限归属、reindex 全量重灌、distance/阈值、策略参数生效。

全部写操作跑在回滚事务里，不污染真实数据（Chroma 写操作被 mock 掉）。

跑法：& backend\\.venv\\Scripts\\python.exe tools\\verify_fix_batch2.py
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

from accounts.models import User  # noqa: E402
from context_engine.models import ContextStrategy  # noqa: E402
from courses.models import Course  # noqa: E402
from courses import views as course_views  # noqa: E402
from enrollments.models import Enrollment  # noqa: E402
from enrollments import views as enroll_views  # noqa: E402
from files_app.models import UploadedFile  # noqa: E402
from files_app import views as file_views  # noqa: E402
from files_app.serializers import UploadedFileSerializer  # noqa: E402
from services.context_compressor import compress_messages, count_messages_tokens  # noqa: E402
from services.rag_service import distance_to_similarity, expand_queries, lexical_rerank  # noqa: E402
from vector_db.models import VectorCollection  # noqa: E402
from vector_db import views as vdb_views  # noqa: E402

factory = APIRequestFactory()
RESULTS = []


def check(name, ok, extra=""):
    RESULTS.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"   → {extra}" if extra else ""))


def req(method, path, user, data=None):
    r = getattr(factory, method)(path, data or {}, format="json")
    force_authenticate(r, user=user)
    return r


def main():
    admin = User.objects.filter(role=User.Role.ADMIN).first()
    teacher_own = User.objects.filter(role=User.Role.TEACHER).first()
    student = User.objects.filter(role=User.Role.STUDENT).first()
    own_course = Course.objects.filter(teacher=teacher_own).first()
    other_course = Course.objects.exclude(teacher=teacher_own).exclude(teacher=None).first()
    other_teacher = other_course.teacher
    print(f"样本: 自己的课={own_course.id} 别人的课={other_course.id}(teacher={other_teacher.username})")
    print(f"      teacher_own={teacher_own.username}(id={teacher_own.id}) admin={admin.username} student={student.username}\n")

    # ── ① 课程 / 选课 / 文件的归属校验 ────────────────────
    print("① 归属校验（教师越权）")
    with transaction.atomic():
        r = course_views.admin_course_detail(req("get", "/", teacher_own), own_course.pk)
        check("教师可读自己的课", r.status_code == 200, f"http={r.status_code}")

        r = course_views.admin_course_detail(req("get", "/", teacher_own), other_course.pk)
        check("教师读别人的课被拒 403", r.status_code == 403, f"http={r.status_code}")

        r = course_views.admin_course_detail(
            req("put", "/", teacher_own, {"name": "HACKED"}), other_course.pk)
        check("教师改别人的课被拒 403", r.status_code == 403, f"http={r.status_code}")
        other_course.refresh_from_db()
        check("别人的课名未被改动", other_course.name != "HACKED", f"name={other_course.name}")

        r = course_views.admin_course_detail(req("delete", "/", teacher_own), other_course.pk)
        check("教师删别人的课被拒 403", r.status_code == 403, f"http={r.status_code}")
        check("课程仍然存在", Course.objects.filter(pk=other_course.pk).exists())

        r = course_views.admin_course_detail(req("get", "/", admin), other_course.pk)
        check("管理员可读任意课程", r.status_code == 200, f"http={r.status_code}")

        r = course_views.admin_course_list(req("get", "/", teacher_own))
        listed = r.data["data"]["list"]
        check("课程列表：教师只看到自己的课",
              r.status_code == 200 and all(c["teacher"] == teacher_own.id for c in listed),
              f"共 {len(listed)} 门")

        # 选课审核
        enr_other = Enrollment.objects.filter(course=other_course).first()
        if enr_other is None:
            enr_other = Enrollment.objects.create(student=student, course=other_course)
        r = enroll_views.admin_enroll_review(
            req("put", "/", teacher_own, {"status": "approved"}), enr_other.pk)
        check("教师审核别人课程的选课被拒 403", r.status_code == 403, f"http={r.status_code}")
        enr_other.refresh_from_db()
        check("该选课状态未被改动", enr_other.status != "approved", f"status={enr_other.status}")

        enr_own = Enrollment.objects.filter(course=own_course).first()
        if enr_own is None:
            enr_own = Enrollment.objects.create(student=student, course=own_course)
        r = enroll_views.admin_enroll_review(
            req("put", "/", teacher_own, {"status": "approved"}), enr_own.pk)
        check("教师可审核自己课程的选课", r.status_code == 200, f"http={r.status_code}")

        r = enroll_views.admin_enroll_list(req("get", "/", teacher_own))
        rows = r.data["data"]["list"]
        own_course_ids = set(
            Course.objects.filter(teacher=teacher_own).values_list("id", flat=True)
        )
        check("选课列表：教师只看到自己课程的申请",
              r.status_code == 200 and rows and all(x["course"] in own_course_ids for x in rows),
              f"共 {len(rows)} 条，覆盖 {len({x['course'] for x in rows})}/{len(own_course_ids)} 门自己的课")

        # 文件访问
        tmp = Path(tempfile.gettempdir()) / "probe_uploadedfile.txt"
        tmp.write_text("probe", encoding="utf-8")
        uf = UploadedFile.objects.create(
            original_name="probe.txt", stored_path=str(tmp), file_size=5,
            mime_type="text/plain", course=other_course, uploader=student,
        )
        r = file_views.file_detail(req("get", "/", teacher_own), uf.pk)
        check("他人文件：非授课教师 GET 被拒 403", r.status_code == 403, f"http={r.status_code}")
        r = file_views.file_detail(req("get", "/", other_teacher), uf.pk)
        check("他人文件：授课教师 GET 放行", r.status_code == 200, f"http={r.status_code}")
        r = file_views.file_detail(req("get", "/", student), uf.pk)
        check("他人文件：上传者本人 GET 放行", r.status_code == 200, f"http={r.status_code}")
        r = file_views.file_detail(req("get", "/", admin), uf.pk)
        check("他人文件：管理员 GET 放行", r.status_code == 200, f"http={r.status_code}")
        check("文件响应不再包含 stored_path",
              "stored_path" not in UploadedFileSerializer(uf).data,
              f"字段={sorted(UploadedFileSerializer(uf).data.keys())[:4]}…")
        transaction.set_rollback(True)

    # ── ② reindex 全量重灌 ────────────────────────────────
    print("\n② reindex 全量重灌（不再丢向量数据）")
    with transaction.atomic():
        course = Course.objects.create(name="探针课程", semester="fall", year=2025, is_active=True)
        vc = VectorCollection.objects.create(name="探针集合", course=course)
        f1_path = Path(tempfile.gettempdir()) / "probe_vec_1.txt"
        f2_path = Path(tempfile.gettempdir()) / "probe_vec_2.txt"
        f1_path.write_text("short content one", encoding="utf-8")
        f2_path.write_text("short content two", encoding="utf-8")
        UploadedFile.objects.create(original_name="v1.txt", stored_path=str(f1_path), file_size=17,
                                    course=course, uploader=student, is_vectorized=True, summary="旧摘要")
        UploadedFile.objects.create(original_name="v2.txt", stored_path=str(f2_path), file_size=17,
                                    course=course, uploader=student, is_vectorized=False)

        # 策略分块参数：改成 200/20 验证是否真的被 reindex 读取
        ContextStrategy.objects.update(is_default=False)
        ContextStrategy.objects.create(name="探针策略", chunk_size=200, chunk_overlap=20,
                                       is_active=True, is_default=True, created_by=admin)

        with mock.patch("vector_db.views.index_documents", return_value=7) as mocked, \
                mock.patch("vector_db.views.delete_collection") as del_mock:
            r = vdb_views.reindex(req("post", "/", admin), vc.pk)
            called_args, called_kwargs = mocked.call_args
            docs = called_args[1]
            summaries = called_args[4]
            check("reindex 返回 200", r.status_code == 200, f"http={r.status_code}")
            check("已向量化的文件也会被重新索引（旧实现会漏掉）", len(docs) == 2, f"传入 {len(docs)} 个文档")
            check("旧集合确实被删除后再重建", del_mock.called)
            check("chunk_size 来自 ContextStrategy", called_kwargs.get("chunk_size") == 200,
                  f"chunk_size={called_kwargs.get('chunk_size')}")
            check("chunk_overlap 来自 ContextStrategy", called_kwargs.get("chunk_overlap") == 20,
                  f"chunk_overlap={called_kwargs.get('chunk_overlap')}")
            check("已有的摘要被复用（不重复调 LLM）", "旧摘要" in summaries, f"summaries={summaries}")
            vc.refresh_from_db()
            check("统计字段已更新", vc.vector_count == 7 and vc.status == "active",
                  f"vector_count={vc.vector_count} status={vc.status}")
        transaction.set_rollback(True)

    # ── ③ distance → 相似度换算 ───────────────────────────
    print("\n③ 距离换算与阈值语义")
    cases = [(0.0, 1.0), (0.8, 0.6), (1.0, 0.5), (2.0, 0.0), (None, 0.0)]
    for d, expect in cases:
        got = distance_to_similarity(d)
        check(f"distance_to_similarity({d}) == {expect}", abs(got - expect) < 1e-6, f"得到 {got}")
    check("实测平均距离 1.04 → 相似度约 0.48",
          abs(distance_to_similarity(1.04) - 0.48) < 1e-6)

    # 阈值过滤：用真实距离语义验证（旧公式会把 0.6 的相似度算成 0.2）
    docs = [{"distance": d} for d in (0.8, 1.2)]
    for d in docs:
        d["similarity"] = distance_to_similarity(d["distance"])
    kept = [d for d in docs if d["similarity"] >= 0.5]
    check("阈值 0.5 现在能正确保留/过滤（旧公式会全杀）", len(kept) == 1,
          f"保留 {len(kept)}/2，相似度={[d['similarity'] for d in docs]}")

    # ── ④ 查询改写 / 重排 / 压缩 ──────────────────────────
    print("\n④ 策略参数真正生效")
    q1 = expand_queries("什么是梯度下降算法？")
    check("查询改写：生成多条检索式", len(q1) >= 2 and q1[0] == "什么是梯度下降算法？", f"{q1}")
    q2 = expand_queries("CNN 和 ResNet 的区别")
    check("查询改写：抽出英文术语", any("CNN" in x and "ResNet" in x for x in q2), f"{q2}")

    ranked = lexical_rerank("梯度下降 学习率", [
        {"content": "梯度下降的学习率过大会震荡", "similarity": 0.40},
        {"content": "随机森林的袋外估计", "similarity": 0.45},
    ])
    check("重排：字面相关的片段被提到前面", "学习率" in ranked[0]["content"],
          f"首位相似度={ranked[0]['vector_similarity']} 字面={ranked[0]['lexical_overlap']}")
    check("重排：补充了诊断字段", all("rerank_score" in d for d in ranked))

    history = [{"role": "system", "content": "你是教学助手。"}]
    for i in range(12):
        history.append({"role": "user", "content": f"第{i}个问题：请详细解释梯度下降的收敛性。 " * 8})
        history.append({"role": "assistant", "content": f"第{i}个回答：梯度下降的收敛依赖学习率。 " * 8})
    history.append({"role": "user", "content": "总结一下"})

    out_truncate = compress_messages(list(history), 1500, "truncate")
    out_summarize = compress_messages(list(history), 1500, "summarize")
    check("压缩：两种模式都压进预算",
          count_messages_tokens(out_truncate) <= 1500 and count_messages_tokens(out_summarize) <= 1500,
          f"truncate={count_messages_tokens(out_truncate)} summarize={count_messages_tokens(out_summarize)} tokens")
    check("summarize 模式额外保留了一段历史摘要",
          any("历史对话摘要" in (m.get("content") or "") for m in out_summarize),
          f"消息数 truncate={len(out_truncate)} summarize={len(out_summarize)}")
    check("truncate 模式不产生摘要（行为保持原样）",
          not any("历史对话摘要" in (m.get("content") or "") for m in out_truncate))

    # 极小预算下 summarize 应优雅降级（摘要放不下就退回纯丢弃，不能超预算）
    tiny = compress_messages(list(history), 300, "summarize")
    check("极小预算下 summarize 优雅降级且不超预算",
          count_messages_tokens(tiny) <= 300, f"{count_messages_tokens(tiny)} tokens")

    # ── 汇总 ─────────────────────────────────────────────
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{'=' * 62}\n共 {len(RESULTS)} 项，通过 {len(RESULTS) - len(failed)} 项，失败 {len(failed)} 项")
    for n in failed:
        print("  FAIL:", n)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
