"""验证「安全硬伤包」三处修复。全部写操作都在回滚事务中，不污染真实数据。

跑法（在 backend 目录下）：
    .venv\\Scripts\\python.exe ..\\tools\\verify_security_fixes.py
"""
import os
import sys
from pathlib import Path

# 让脚本无论从哪里执行都能 import 到 backend 下的 config/各 app
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from cryptography.fernet import Fernet  # noqa: E402
from django.db import transaction  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

from accounts import views as accounts_views  # noqa: E402
from accounts.models import User  # noqa: E402
from settings_app import views as settings_views  # noqa: E402
from settings_app.encryption import (  # noqa: E402
    FERNET_KEY_ENV,
    can_decrypt,
    decrypt_value,
    encrypt_value,
    is_encrypted,
    reset_fernet_cache,
)
from settings_app.models import AgentAPIConfig, SystemSetting  # noqa: E402

factory = APIRequestFactory()
RESULTS = []


def check(name, ok, extra=""):
    RESULTS.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"   → {extra}" if extra else ""))


def main():
    admin = User.objects.filter(role=User.Role.ADMIN).first()
    student = User.objects.filter(role=User.Role.STUDENT).first()
    teacher = User.objects.filter(role=User.Role.TEACHER).first()
    assert admin and student and teacher, "缺少 admin/student/teacher 样本用户，无法验证"
    print(f"样本用户: admin={admin.username} student={student.username} teacher={teacher.username}\n")

    # ── 修复 1：注册不能自封管理员 ─────────────────────────
    print("① 注册越权提管理员")
    with transaction.atomic():
        resp = accounts_views.register(
            factory.post(
                "/api/auth/register",
                {
                    "username": "probe_admin_escalation",
                    "password": "probe123456",
                    "student_id": "PROBE-0001",
                    "sex": "男",
                    "dept": "测试学院",
                    "major": "测试专业",
                    "grade": "2025级",
                    "role": "admin",  # 攻击载荷
                },
                format="json",
            )
        )
        created = User.objects.filter(username="probe_admin_escalation").first()
        check(
            "提交 role=admin 被忽略，落库角色是 student",
            resp.status_code == 200 and created is not None and created.role == User.Role.STUDENT,
            f"http={resp.status_code} 落库 role={getattr(created, 'role', None)}",
        )
        check(
            "新注册账号仍未审核（is_approved=False）",
            created is not None and created.is_approved is False,
            f"is_approved={getattr(created, 'is_approved', None)}",
        )
        login_resp = accounts_views.login(
            factory.post(
                "/api/auth/login",
                {"username": "probe_admin_escalation", "password": "probe123456"},
                format="json",
            )
        )
        check(
            "该账号登录被「学生未审核」拦截（403）",
            login_resp.status_code == 403,
            f"http={login_resp.status_code}",
        )
        transaction.set_rollback(True)

    # ── 修复 2：系统设置的读写权限 ─────────────────────────
    print("\n② /api/settings/ 权限")
    with transaction.atomic():
        req = factory.get("/api/settings/")
        force_authenticate(req, user=student)
        resp = settings_views.system_settings(req)
        student_keys = {item["key"] for item in resp.data["data"]}
        check(
            "学生 GET 只拿到公开白名单",
            resp.status_code == 200 and student_keys <= settings_views.PUBLIC_SETTING_KEYS,
            f"keys={sorted(student_keys)}",
        )

        req = factory.get("/api/settings/")
        force_authenticate(req, user=admin)
        resp_admin = settings_views.system_settings(req)
        admin_keys = {item["key"] for item in resp_admin.data["data"]}
        check(
            "管理员 GET 拿到全量",
            resp_admin.status_code == 200 and admin_keys >= student_keys,
            f"共 {len(admin_keys)} 项",
        )

        before = SystemSetting.objects.get(key="site_name").value
        req = factory.put("/api/settings/", {"site_name": "HACKED_BY_STUDENT"}, format="json")
        force_authenticate(req, user=student)
        resp_put = settings_views.system_settings(req)
        after = SystemSetting.objects.get(key="site_name").value
        check(
            "学生 PUT 被拒（403）且数据未被修改",
            resp_put.status_code == 403 and after == before,
            f"http={resp_put.status_code} site_name 保持不变={after == before}",
        )

        req = factory.put("/api/settings/", {"site_name": "TEACHER_SET"}, format="json")
        force_authenticate(req, user=teacher)
        resp_teacher = settings_views.system_settings(req)
        check(
            "教师 PUT 也被拒（只有管理员能改）",
            resp_teacher.status_code == 403,
            f"http={resp_teacher.status_code}",
        )

        req = factory.put("/api/settings/", {"site_name": "ADMIN_SET_OK"}, format="json")
        force_authenticate(req, user=admin)
        resp_ok = settings_views.system_settings(req)
        value_now = SystemSetting.objects.get(key="site_name").value
        check(
            "管理员 PUT 正常生效",
            resp_ok.status_code == 200 and value_now == "ADMIN_SET_OK",
            f"http={resp_ok.status_code} site_name={value_now}",
        )
        transaction.set_rollback(True)

    # ── 修复 3：api_key 加解密鲁棒性 ──────────────────────
    print("\n③ api_key 加解密")
    cfg = AgentAPIConfig.objects.first()
    stored = cfg.api_key
    plain = cfg.get_api_key()
    check("库里现存密文结构识别正常", is_encrypted(stored), f"长度={len(stored)}")
    check("现存 api_key 仍可解密（向后兼容）", bool(plain) and len(plain) >= 16, f"明文长度={len(plain)}")
    check("can_decrypt 自检通过", can_decrypt(stored))

    token = encrypt_value("sk-probe-1234567890")
    check("加密结果可被识别为密文", is_encrypted(token) and token.startswith("gAAAAA"), f"长度={len(token)}")
    check("加解密往返一致", decrypt_value(token) == "sk-probe-1234567890")
    check(
        "明文与残缺串不会被误判为密文",
        not is_encrypted("sk-probe-1234567890")
        and not is_encrypted("gAAAAA")
        and not is_encrypted("gAAAAAshort")
        and not is_encrypted(""),
        "（收紧后的结构判断生效）",
    )

    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    try:
        got = decrypt_value(tampered)
        check("密文被篡改时不抛异常、返回空串", got == "", f"返回 {got!r}")
    except Exception as exc:  # noqa: BLE001
        check("密文被篡改时不抛异常、返回空串", False, f"抛出了 {type(exc).__name__}")

    old_token = token
    os.environ[FERNET_KEY_ENV] = Fernet.generate_key().decode()
    reset_fernet_cache()
    new_token = encrypt_value("another-secret")
    check(
        "配置独立密钥（环境变量）后，新密文可正常往返",
        decrypt_value(new_token) == "another-secret",
        f"{FERNET_KEY_ENV} 生效",
    )
    check("旧密钥加密的密文解不开时返回空串（不再 500）", decrypt_value(old_token) == "")
    check("但旧密文仍被认作密文（不会被二次加密毁数据）", is_encrypted(old_token))
    check("can_decrypt 能识别出旧密文已不可用", not can_decrypt(old_token))

    os.environ[FERNET_KEY_ENV] = "not-a-valid-fernet-key"
    reset_fernet_cache()
    try:
        encrypt_value("x")
        check("非法环境变量密钥会立刻报错", False, "未抛异常")
    except Exception as exc:  # noqa: BLE001
        check("非法环境变量密钥会立刻报错", type(exc).__name__ == "ImproperlyConfigured", type(exc).__name__)

    del os.environ[FERNET_KEY_ENV]
    reset_fernet_cache()
    check("恢复默认密钥后旧密文又能解开", decrypt_value(old_token) == "sk-probe-1234567890")

    # ── 汇总 ────────────────────────────────────────────
    failed = [name for name, ok in RESULTS if not ok]
    print(f"\n{'=' * 60}\n共 {len(RESULTS)} 项，通过 {len(RESULTS) - len(failed)} 项，失败 {len(failed)} 项")
    if failed:
        for name in failed:
            print("  FAIL:", name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
