"""Tự kiểm một module tài liệu dài trước khi báo xong.

Chạy (từ thư mục data):  python tools/check_long.py long_policies_a
Kiểm: import được; mọi id có số từ ≥ MIN_WORDS; không chứa chuỗi FORBIDDEN; mọi chuỗi bắt buộc của câu hỏi vàng
(content_golden) gắn với các id đó có mặt; không email/URL/số điện thoại lạ; mỗi QA hợp lệ (chuỗi có thật trong văn bản).
"""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import content_facts as cf  # noqa: E402
import content_golden as cg  # noqa: E402
from blocks import blocks_text  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).lower()


def main(name: str) -> int:
    m = importlib.import_module(name)
    blocks = getattr(m, "BLOCKS", {})
    qa = getattr(m, "QA", [])
    errs: list[str] = []
    texts = {i: blocks_text(b) for i, b in blocks.items()}
    print(f"{name}: {len(blocks)} tài liệu, {len(qa)} câu QA")
    for i, tx in sorted(texts.items()):
        words = len(tx.split())
        need = cf.MIN_WORDS.get(i, 0)
        flag = "OK " if words >= need else "NGẮN"
        print(f"  {flag} {i:5s} {words:6d} từ (tối thiểu {need})")
        if words < need:
            errs.append(f"{i}: {words} từ < {need}")
        for bad in cf.FORBIDDEN.get(i, []):
            if norm(bad) in norm(tx):
                errs.append(f"{i}: chứa chuỗi cấm '{bad}'")
        for em in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", tx):
            if not em.rstrip(".").lower().endswith(cf.EMAIL_ALLOW_DOMAINS):
                errs.append(f"{i}: email lạ {em}")
        for url in re.findall(r"https?://([^\s/)\]\"',;]+)", tx):
            ok = url.lower().endswith(cf.ALLOWED_URL_HOST_SUFFIXES) or any(url.lower().endswith(h) for h in cf.URL_EXCEPTIONS.get(i, ()))
            if not ok:
                errs.append(f"{i}: URL lạ {url}")
        if re.search(cf.PHONE_PATTERN, tx):
            errs.append(f"{i}: chứa chuỗi giống số điện thoại")
    # chuỗi bắt buộc của câu hỏi vàng
    for it in cg._items:
        for ti, turn in enumerate(it["turns"], 1):
            e = turn["expect"]
            if e.get("response_type") in ("ANSWER", "GUIDE_PROCESS") and e.get("docs"):
                docs = [d for d in e["docs"] if d in texts]
                if not docs or len(docs) != len([d for d in e["docs"]]):
                    continue  # câu hỏi dùng tài liệu ngoài module này: bỏ qua
                corpus = norm("\n".join(texts[d] for d in docs))
                for tok in e.get("must_include", []):
                    if norm(tok) not in corpus:
                        errs.append(f"golden {it['id']}#{ti}: thiếu chuỗi bắt buộc '{tok}' trong {docs}")
    for q in qa:
        for key in ("id", "q", "must_include", "docs"):
            if key not in q:
                errs.append(f"QA thiếu trường {key}: {q}")
        docs = [d for d in q.get("docs", []) if d in texts]
        if not docs:
            errs.append(f"QA {q.get('id')}: docs phải thuộc module này")
            continue
        corpus = norm("\n".join(texts[d] for d in docs))
        for tok in q.get("must_include", []):
            if norm(tok) not in corpus:
                errs.append(f"QA {q.get('id')}: chuỗi '{tok}' không có trong {docs}")
    if errs:
        print(f"\n{len(errs)} LỖI:")
        for e in errs:
            print("  -", e)
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
