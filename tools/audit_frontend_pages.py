"""一次性审计脚本：找出前端的死页面 / 孤立视图 / 仅 URL 可达的路由。用完即删。"""
import pathlib

ROOT = pathlib.Path(r"D:\work\code\rag\UI\src")
VIEWS = ROOT / "views"
ROUTER = ROOT / "router"


def all_balanced_blocks(txt: str):
    """返回每个 `{` 对应的配平子串（含嵌套，所有层级）。"""
    out = []
    for i, ch in enumerate(txt):
        if ch != "{":
            continue
        depth = 0
        for j in range(i, len(txt)):
            if txt[j] == "{":
                depth += 1
            elif txt[j] == "}":
                depth -= 1
                if depth == 0:
                    out.append(txt[i:j + 1])
                    break
    return out


import re

all_views = sorted(
    str(p.relative_to(VIEWS)).replace("\\", "/") for p in VIEWS.rglob("*.vue")
)

comps = set()
routes = []
for p in ROUTER.rglob("*.ts"):
    txt = p.read_text(encoding="utf-8")
    rel = str(p.relative_to(ROOT)).replace("\\", "/")
    for block in all_balanced_blocks(txt):
        # 两种写法都要抓：字符串式 "/admin/prompts/index"，以及惰性式 () => import("@/views/x.vue")
        cm = re.search(r"component:\s*[\"']([^\"']+)[\"']", block)
        if cm:
            comp = cm.group(1).lstrip("/")
        else:
            lm = re.search(r"import\(\s*[\"']@/views/([^\"']+?)(?:\.vue)?[\"']\s*\)", block)
            if not lm:
                continue
            comp = lm.group(1)
        comps.add(comp)
        pm = re.search(r"path:\s*[\"']([^\"']+)[\"']", block)
        nm = re.search(r"name:\s*[\"']([^\"']+)[\"']", block)
        routes.append({
            "path": pm.group(1) if pm else "?",
            "name": nm.group(1) if nm else "?",
            "component": comp,
            "hideInMenu": "hideInMenu: true" in block or "hideInMenu:true" in block,
            "file": rel,
        })

print("视图文件总数:", len(all_views))
print("路由条目数:", len(routes), " | 引用到的组件数:", len(comps))
print()
print("=== A. 没有任何路由指向的视图文件（彻底死页面）===")
orphan = []
for v in all_views:
    stem = v[:-len(".vue")]
    if stem not in comps:
        orphan.append(v)
        print("   ", v)
if not orphan:
    print("    （无）")

print()
print("=== B. 路由总表 ===")
for r in sorted(routes, key=lambda x: (x["file"], x["path"])):
    flag = "隐藏" if r["hideInMenu"] else "菜单"
    print(f"    [{flag}] {r['path']:<30} {r['name']:<26} {r['component']}")

print()
print("=== C. 隐藏路由的跳转入口检查 ===")
contents = {}
for p in ROOT.rglob("*"):
    if p.suffix in (".ts", ".vue") and "router" not in str(p) and not p.name.endswith(".d.ts"):
        contents[p] = p.read_text(encoding="utf-8", errors="ignore")

for r in sorted(routes, key=lambda x: x["path"]):
    if not r["hideInMenu"]:
        continue
    path = r["path"]
    # 参数化路由（chat/:courseId、prompts/:id/edit）不能拿完整字面量去搜，
    # 改用去掉参数段后的前缀（如 "/chat/"、"/prompts/"/"/edit"）
    if ":" in path:
        prefix = "/" + path.split(":")[0].strip("/")
        needles = [prefix] if prefix != "/" else []
        suffix = path.rsplit("/", 1)[-1]
        if suffix and ":" not in suffix:
            needles.append("/" + suffix)
    else:
        needles = [path]
    hits = []
    for pp, t in contents.items():
        if any(n in t for n in needles if n):
            hits.append(str(pp.relative_to(ROOT)).replace("\\", "/"))
    status = "OK " if hits else "!! 只能手输 URL"
    print(f"    [{status}] {path}   (搜索: {needles})")
    for h in hits[:5]:
        print(f"            <- {h}")
