"""Hàm dựng khối nội dung dùng chung (import từ đây, không import content_documents để tránh vòng lặp).

Khối là tuple:
  H1(text) H2(text)          tiêu đề; KHÔNG tự đánh số (builder tự đánh số 1., 1.1)
  P(text)                    một đoạn văn thường (văn bản thuần, không markdown)
  B(item, ...)               danh sách gạch đầu dòng
  N(item, ...)               danh sách đánh số 1., 2., ...
  T(header, rows, widths=None, merges=None)   bảng; header là list tiêu đề cột, rows là list các hàng
  PB                         ngắt trang
"""
from __future__ import annotations

H1 = lambda t: ("h1", t)  # noqa: E731
H2 = lambda t: ("h2", t)  # noqa: E731
P = lambda t: ("p", t)  # noqa: E731
B = lambda *items: ("bullets", list(items))  # noqa: E731
N = lambda *items: ("numbered", list(items))  # noqa: E731
PB = ("pagebreak",)


def T(header, rows, widths=None, merges=None):
    return ("table", {"header": header, "rows": rows, "widths": widths, "merges": merges or []})


def blocks_text(blocks) -> str:
    """Toàn bộ chữ của một danh sách khối (để đếm từ và kiểm tra chuỗi)."""
    out = []
    for kind, *rest in blocks:
        if kind in ("h1", "h2", "p"):
            out.append(rest[0])
        elif kind in ("bullets", "numbered"):
            out.extend(rest[0])
        elif kind == "table":
            out.extend(rest[0]["header"])
            for r in rest[0]["rows"]:
                out.extend(r)
    return "\n".join(out)
