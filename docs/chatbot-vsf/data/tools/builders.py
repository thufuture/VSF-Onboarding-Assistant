"""Dựng DOCX / PDF / PDF scan / file hỏng tiếng Việt từ đặc tả tài liệu (spec).

Khối nội dung (blocks) là tuple:
  ("h1", text) ("h2", text) ("p", text) ("bullets", [..]) ("numbered", [..])
  ("table", {"header": [...], "rows": [[...]], "widths": [..] | None, "merges": [((r1,c1),(r2,c2)), ...]})
  ("pagebreak",)
Toạ độ merge tính trên bảng đầy đủ, hàng 0 là hàng tiêu đề.
"""
from __future__ import annotations

import io
import os
import random
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document as Docx
from docx.oxml.ns import qn
from docx.shared import Pt
from PIL import Image, ImageEnhance, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    import pymupdf
except ImportError:  # pragma: no cover
    import fitz as pymupdf

SYNTH_NOTICE = "TÀI LIỆU GIẢ LẬP (SYNTHETIC) - chỉ dùng để kiểm thử, không phải chính sách hay quy trình VSF đã xác nhận"

_FONT_DIRS = [
    os.environ.get("VSF_FONT_DIR", ""),
    "C:/Windows/Fonts",
    "/usr/share/fonts/truetype/msttcorefonts",
    "/usr/share/fonts/truetype/dejavu",
    "/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
]
_FONT_SETS = [
    ("arial.ttf", "arialbd.ttf", "ariali.ttf"),
    ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf"),
    ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf"),
]
_fonts_ready = False
DOCX_FONT = "Arial"


def _register_fonts() -> None:
    global _fonts_ready, DOCX_FONT
    if _fonts_ready:
        return
    for names in _FONT_SETS:
        for d in _FONT_DIRS:
            if d and all((Path(d) / n).exists() for n in names):
                pdfmetrics.registerFont(TTFont("VSF", str(Path(d) / names[0])))
                pdfmetrics.registerFont(TTFont("VSF-B", str(Path(d) / names[1])))
                pdfmetrics.registerFont(TTFont("VSF-I", str(Path(d) / names[2])))
                pdfmetrics.registerFontFamily("VSF", normal="VSF", bold="VSF-B", italic="VSF-I", boldItalic="VSF-B")
                DOCX_FONT = "Arial" if names[0].lower().startswith("arial") else "DejaVu Sans"
                _fonts_ready = True
                return
    raise RuntimeError("Không tìm thấy font hỗ trợ tiếng Việt (Arial hoặc DejaVu). Đặt VSF_FONT_DIR.")


def number_blocks(blocks: list) -> list:
    """Tự đánh số tiêu đề: h1 -> '1. Tiêu đề', h2 -> '1.1 Tiêu đề'."""
    out, a, b = [], 0, 0
    for blk in blocks:
        if blk[0] == "h1":
            a, b = a + 1, 0
            out.append(("h1", f"{a}. {blk[1]}"))
        elif blk[0] == "h2":
            b += 1
            out.append(("h2", f"{a}.{b} {blk[1]}"))
        else:
            out.append(blk)
    return out


def prepared_blocks(spec: dict) -> list:
    blocks = spec["blocks"]
    return number_blocks(blocks) if spec.get("style", {}).get("numbered") and spec.get("style", {}).get("headings", True) else blocks


def meta_line(spec: dict) -> str:
    parts = [f"Phiên bản: {spec['version']}"]
    if spec.get("effective_from"):
        y, m, d = spec["effective_from"].split("-")
        parts.append(f"Ngày hiệu lực: {d}/{m}/{y}")
    if spec.get("effective_to"):
        y, m, d = spec["effective_to"].split("-")
        parts.append(f"Hết hiệu lực: {d}/{m}/{y}")
    parts.append(f"Đơn vị ban hành: {spec['unit']}")
    return " | ".join(parts)


# ----------------------------------------------------------------------------- DOCX
def build_docx(spec: dict, path: Path) -> None:
    style = spec.get("style", {})
    headings = style.get("headings", True)
    doc = Docx()
    normal = doc.styles["Normal"]
    normal.font.name = DOCX_FONT if _fonts_ready else "Arial"
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")

    sec = doc.sections[0]
    sec.header.paragraphs[0].text = f"{spec['code']} | {spec['title']}"
    sec.footer.paragraphs[0].text = spec.get("notice") or (SYNTH_NOTICE if spec.get("synthetic", True) else spec["title"])

    if headings:
        doc.add_paragraph(spec["title"], style="Title")
    else:
        p = doc.add_paragraph()
        r = p.add_run(spec["title"])
        r.bold = True
        r.font.size = Pt(16)
    if spec.get("version"):
        p = doc.add_paragraph()
        r = p.add_run(meta_line(spec))
        r.italic = True
        r.font.size = Pt(9.5)

    blocks = prepared_blocks(spec)
    if style.get("toc"):
        doc.add_paragraph("Mục lục").runs[0].bold = True
        n = 0
        for kind, *rest in blocks:
            if kind == "h1":
                n += 1
                doc.add_paragraph(rest[0] if style.get("numbered") else f"{n}. {rest[0]}")
        doc.add_page_break()

    for kind, *rest in blocks:
        if kind in ("h1", "h2"):
            if headings:
                doc.add_heading(rest[0], level=1 if kind == "h1" else 2)
            else:
                p = doc.add_paragraph()
                p.add_run(rest[0]).bold = True
        elif kind == "p":
            doc.add_paragraph(rest[0])
        elif kind == "bullets":
            for item in rest[0]:
                doc.add_paragraph(item, style="List Bullet")
        elif kind == "numbered":
            for i, item in enumerate(rest[0], 1):
                p = doc.add_paragraph(f"{i}. {item}")
                p.paragraph_format.left_indent = Pt(18)
        elif kind == "table":
            _docx_table(doc, rest[0])
            doc.add_paragraph()
        elif kind == "pagebreak":
            doc.add_page_break()
        else:
            raise ValueError(f"block không hỗ trợ: {kind}")
    doc.save(str(path))


def _docx_table(doc, t: dict) -> None:
    header, rows = t["header"], t["rows"]
    table = doc.add_table(rows=len(rows) + 1, cols=len(header))
    table.style = "Table Grid"
    for c, text in enumerate(header):
        cell = table.cell(0, c)
        cell.text = text
        for r in cell.paragraphs[0].runs:
            r.bold = True
    for ri, row in enumerate(rows, 1):
        for c, text in enumerate(row):
            table.cell(ri, c).text = text
    for (r1, c1), (r2, c2) in t.get("merges", []):
        a, b = table.cell(r1, c1), table.cell(r2, c2)
        merged = a.merge(b)
        for p in merged.paragraphs[1:]:
            if not p.text.strip():
                p._element.getparent().remove(p._element)


# ----------------------------------------------------------------------------- PDF
def _styles(headings: bool) -> dict:
    _register_fonts()
    body = ParagraphStyle("body", fontName="VSF", fontSize=10.5, leading=15, spaceAfter=6)
    return {
        "title": ParagraphStyle("title", parent=body, fontName="VSF-B", fontSize=18, leading=22, spaceAfter=6),
        "meta": ParagraphStyle("meta", parent=body, fontName="VSF-I", fontSize=9, leading=12, spaceAfter=10),
        "h1": ParagraphStyle("h1", parent=body, fontName="VSF-B", fontSize=14 if headings else 10.5, leading=18 if headings else 15, spaceBefore=8, spaceAfter=4, keepWithNext=1),
        "h2": ParagraphStyle("h2", parent=body, fontName="VSF-B", fontSize=12 if headings else 10.5, leading=16 if headings else 15, spaceBefore=6, spaceAfter=3, keepWithNext=1),
        "body": body,
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=16, bulletIndent=4, spaceAfter=3),
        "cell": ParagraphStyle("cell", parent=body, fontSize=9, leading=12, spaceAfter=0),
        "cellb": ParagraphStyle("cellb", parent=body, fontName="VSF-B", fontSize=9, leading=12, spaceAfter=0),
    }


def build_pdf(spec: dict, path: Path) -> None:
    style = spec.get("style", {})
    headings = style.get("headings", True)
    st = _styles(headings)
    synthetic = spec.get("synthetic", True)
    footer_text = spec.get("notice") or (SYNTH_NOTICE if synthetic else spec["title"])

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("VSF", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(2 * cm, A4[1] - 1.2 * cm, f"{spec['code']} | {spec['title']}")
        canvas.drawString(2 * cm, 1.0 * cm, footer_text[:120])
        canvas.drawRightString(A4[0] - 2 * cm, 1.0 * cm, f"Trang {doc.page}")
        canvas.restoreState()

    story = [Paragraph(escape(spec["title"]), st["title"] if headings else st["h1"])]
    if spec.get("version"):
        story.append(Paragraph(escape(meta_line(spec)), st["meta"]))

    blocks = prepared_blocks(spec)
    if style.get("toc"):
        story.append(Paragraph("<b>Mục lục</b>", st["h1"]))
        n = 0
        for kind, *rest in blocks:
            if kind == "h1":
                n += 1
                story.append(Paragraph(escape(rest[0] if style.get("numbered") else f"{n}. {rest[0]}"), st["body"]))
        story.append(PageBreak())

    for kind, *rest in blocks:
        if kind in ("h1", "h2"):
            txt = escape(rest[0])
            story.append(Paragraph(txt if headings else f"<b>{txt}</b>", st[kind]))
        elif kind == "p":
            story.append(Paragraph(escape(rest[0]), st["body"]))
        elif kind == "bullets":
            for item in rest[0]:
                story.append(Paragraph(escape(item), st["bullet"], bulletText="•"))
        elif kind == "numbered":
            for i, item in enumerate(rest[0], 1):
                story.append(Paragraph(escape(item), st["bullet"], bulletText=f"{i}."))
        elif kind == "table":
            story.append(_pdf_table(rest[0], st))
            story.append(Spacer(1, 8))
        elif kind == "pagebreak":
            story.append(PageBreak())
        else:
            raise ValueError(f"block không hỗ trợ: {kind}")

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=1.8 * cm,
                            title=spec["title"], author="VSF seed data generator")
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)


def _pdf_table(t: dict, st: dict) -> Table:
    header, rows = t["header"], t["rows"]
    total = 17 * cm
    n = len(header)
    widths = t.get("widths") or [1 / n] * n
    col_w = [total * w / sum(widths) for w in widths]
    data = [[Paragraph(escape(h), st["cellb"]) for h in header]]
    for row in rows:
        data.append([Paragraph(escape(c), st["cell"]) for c in row])
    table = Table(data, colWidths=col_w, repeatRows=1)
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.92, 0.93, 0.97)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for (r1, c1), (r2, c2) in t.get("merges", []):
        cmds.append(("SPAN", (c1, r1), (c2, r2)))
    table.setStyle(TableStyle(cmds))
    return table


# ----------------------------------------------------------------------------- scan / hỏng / giả
def render_scan(src_pdf: Path, out_pdf: Path, dpi: int = 130, seed: int = 7) -> None:
    """Rasterize từng trang rồi ghép lại thành PDF chỉ có ảnh (không lớp chữ), thêm nhiễu nhẹ."""
    rnd = random.Random(seed)
    src = pymupdf.open(str(src_pdf))
    out = pymupdf.open()
    for page in src:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
        img = img.rotate(rnd.uniform(-0.8, 0.8), resample=Image.BICUBIC, fillcolor=255)
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        img = Image.blend(img, Image.effect_noise(img.size, 18), 0.05)
        img = ImageEnhance.Contrast(img).enhance(0.92)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=55)
        p = out.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, stream=buf.getvalue())
    out.save(str(out_pdf))
    out.close()
    src.close()


def truncate_file(src: Path, dst: Path, ratio: float = 0.55) -> None:
    data = src.read_bytes()
    dst.write_bytes(data[: int(len(data) * ratio)])


def write_fake_pdf(dst: Path, text: str) -> None:
    dst.write_text(text, encoding="utf-8")


def build_document(spec: dict, path: Path, tmp_dir: Path) -> None:
    """Dựng đúng một file theo spec['format'] và spec.get('defect')."""
    _register_fonts()
    fmt, defect = spec["format"], spec.get("defect")
    if defect == "scan":
        tmp = tmp_dir / f"_{spec['id']}_text.pdf"
        build_pdf(spec, tmp)
        render_scan(tmp, path)
        tmp.unlink()
    elif defect == "corrupt":
        tmp = tmp_dir / f"_{spec['id']}_full.pdf"
        build_pdf(spec, tmp)
        truncate_file(tmp, path)
        tmp.unlink()
    elif defect == "fake_pdf":
        write_fake_pdf(path, "\n".join(str(b[1]) for b in spec["blocks"] if b[0] == "p"))
    elif fmt == "docx":
        build_docx(spec, path)
    elif fmt == "pdf":
        build_pdf(spec, path)
    else:
        raise ValueError(f"định dạng không hỗ trợ: {fmt}")
