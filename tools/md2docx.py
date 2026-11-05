"""把项目里的 Markdown 手册转成排版好的 Word 文档（python-docx）。

用法：python tools/md2docx.py <input.md> <output.docx>
支持：H1-H4 标题、管道表格、无序/有序列表、引用块、围栏代码块、**粗体**、`行内代码`、[链接](地址)、--- 分隔线。
"""
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

CN_FONT = "微软雅黑"
EN_FONT = "Calibri"
MONO_FONT = "Consolas"

BODY_SIZE = 10.5
TABLE_SIZE = 8.5
CODE_SIZE = 9


# ── 基础工具 ────────────────────────────────────────────────

def style_run(run, size=BODY_SIZE, bold=False, italic=False, mono=False, color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = MONO_FONT if mono else EN_FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), MONO_FONT if mono else EN_FONT)
    rfonts.set(qn("w:hAnsi"), MONO_FONT if mono else EN_FONT)
    rfonts.set(qn("w:eastAsia"), CN_FONT)
    if color is not None:
        run.font.color.rgb = color


def shade(element, fill="F2F2F2"):
    """给段落或单元格加底色。"""
    pr = element.get_or_add_pPr() if element.tag.endswith("}p") else element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def add_inline(paragraph, text, size=BODY_SIZE, base_bold=False, mono_all=False):
    """写入一段带行内格式的文本。"""
    for token in INLINE_RE.split(text):
        if not token:
            continue
        if token.startswith("**") and token.endswith("**") and len(token) > 4:
            style_run(paragraph.add_run(token[2:-2]), size=size, bold=True)
        elif token.startswith("`") and token.endswith("`") and len(token) > 2:
            style_run(paragraph.add_run(token[1:-1]), size=size - 0.5, mono=True)
        elif token.startswith("[") and "](" in token:
            label, target = token[1:-1].split("](", 1)
            style_run(paragraph.add_run(label), size=size, bold=base_bold, color=RGBColor(0x1F, 0x4E, 0x79))
            if target and target != label:
                style_run(paragraph.add_run(f"（{target}）"), size=size - 1,
                          color=RGBColor(0x80, 0x80, 0x80))
        else:
            style_run(paragraph.add_run(token), size=size, bold=base_bold, mono=mono_all)


def add_page_number_footer(section):
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    style_run(run, size=8, color=RGBColor(0x80, 0x80, 0x80))
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)


# ── 文档骨架 ────────────────────────────────────────────────

def build_document():
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = EN_FONT
    normal.font.size = Pt(BODY_SIZE)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.15

    for name, size in (("Heading 1", 17), ("Heading 2", 14), ("Heading 3", 12), ("Heading 4", 11)):
        st = doc.styles[name]
        st.font.name = EN_FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0x1A, 0x33, 0x55)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
        st.paragraph_format.space_before = Pt(10 if name != "Heading 1" else 16)
        st.paragraph_format.space_after = Pt(4)

    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(1.9)
    sec.bottom_margin = Cm(1.9)
    sec.left_margin = Cm(1.9)
    sec.right_margin = Cm(1.9)
    add_page_number_footer(sec)
    return doc


# ── Markdown 解析 ───────────────────────────────────────────

def is_table_sep(line):
    return bool(re.fullmatch(r"[\s|:\-]+", line.strip())) and "-" in line


def split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def set_row_flags(row, header=False):
    """行不跨页断开；表头行在续页重复。"""
    trpr = row._tr.get_or_add_trPr()
    trpr.append(OxmlElement("w:cantSplit"))
    if header:
        trpr.append(OxmlElement("w:tblHeader"))


def add_table(doc, rows):
    header, body = rows[0], rows[1:]
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=1, cols=cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    set_row_flags(table.rows[0], header=True)

    for idx in range(cols):
        cell = table.rows[0].cells[idx]
        cell.text = ""
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(1)
        add_inline(para, header[idx] if idx < len(header) else "", size=TABLE_SIZE, base_bold=True)
        shade(cell._tc, "DCE6F1")
    for row in body:
        new_row = table.add_row()
        set_row_flags(new_row)
        cells = new_row.cells
        for idx in range(cols):
            cells[idx].text = ""
            para = cells[idx].paragraphs[0]
            para.paragraph_format.space_after = Pt(1)
            add_inline(para, row[idx] if idx < len(row) else "", size=TABLE_SIZE)
    doc.add_paragraph()


def add_code_block(doc, lines):
    for line in lines:
        para = doc.add_paragraph()
        para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.left_indent = Cm(0.4)
        style_run(para.add_run(line if line else " "), size=CODE_SIZE, mono=True)
        shade(para._p, "F5F5F5")
    doc.add_paragraph()


def convert(md_path, docx_path):
    with open(md_path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    doc = build_document()
    i = 0
    first_heading = True
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 围栏代码块
        if stripped.startswith("```"):
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i].rstrip())
                i += 1
            i += 1
            add_code_block(doc, block)
            continue

        # 表格
        if stripped.startswith("|") and i + 1 < len(lines) and is_table_sep(lines[i + 1]):
            rows = [split_row(stripped)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i].strip()))
                i += 1
            add_table(doc, rows)
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1 and first_heading:
                doc.add_heading(text, level=0)
                first_heading = False
            else:
                doc.add_heading(text, level=min(level, 4))
            i += 1
            continue

        # 分隔线
        if re.fullmatch(r"(-{3,}|\*{3,})", stripped):
            i += 1
            continue

        # 引用块
        if stripped.startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip())
                i += 1
            for chunk in [b for b in block if b]:
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Cm(0.6)
                para.paragraph_format.space_after = Pt(3)
                add_inline(para, chunk, size=BODY_SIZE)
                shade(para._p, "F7F9FC")
            continue

        # 无序列表
        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m:
            para = doc.add_paragraph(style="List Bullet")
            para.paragraph_format.space_after = Pt(2)
            add_inline(para, m.group(2))
            i += 1
            continue

        # 有序列表：保留原始编号，避免 Word 自动编号跨列表连号
        m = re.match(r"^(\s*)(\d+)[.)]\s+(.*)$", line)
        if m:
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0.75)
            para.paragraph_format.first_line_indent = Cm(-0.4)
            para.paragraph_format.space_after = Pt(2)
            style_run(para.add_run(f"{m.group(2)}. "), bold=True)
            add_inline(para, m.group(3))
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        para = doc.add_paragraph()
        add_inline(para, stripped)
        i += 1

    doc.save(docx_path)
    return docx_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("用法: python tools/md2docx.py <input.md> <output.docx>")
    print("生成:", convert(sys.argv[1], sys.argv[2]))
