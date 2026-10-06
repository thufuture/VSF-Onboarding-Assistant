# -*- coding: utf-8 -*-
"""Sinh golden_set.json (25 câu) từ bộ câu hỏi Viga có sẵn (docs/.../eval/viga_eval.py): một nguồn duy nhất, không gõ lại.

Mỗi câu có: id, tài liệu, câu hỏi, kỳ vọng (ANSWER | NO_BASIS | ANY), các ý bắt buộc phải có trong câu trả lời, và nhóm câu hỏi.
Bỏ câu 22 vì trùng nghĩa với câu 17 (chỉ khác dấu phẩy), còn lại giữ nguyên để kết quả so được với các lần đo trước.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVAL_PY = ROOT / "docs" / "chatbot-vsf" / "plan" / "plan-portal" / "eval" / "viga_eval.py"
OUT = Path(__file__).resolve().parents[1] / "golden_set.json"

source = EVAL_PY.read_text(encoding="utf-8")
start = source.index("CASES = [")
end = source.index("\n]\n", start) + 3
scope: dict = {}
exec(source[start:end], scope)  # noqa: S102

GROUPS = {
    **{i: "tra cứu một ý" for i in range(1, 16)},
    16: "tình huống ngoại lệ", 17: "tình huống ngoại lệ", 18: "tình huống ngoại lệ", 19: "tình huống ngoại lệ",
    20: "ngoài phạm vi tài liệu", 21: "câu viết tắt, sai dấu", 23: "câu viết tắt, sai dấu", 24: "câu mơ hồ", 25: "câu mơ hồ",
    26: "tình huống ngoại lệ",
}
cases = [
    {
        "id": case_id,
        "document": doc,
        "question": question,
        "expect": expect,
        "must_contain": must,
        "group": GROUPS.get(case_id, "tra cứu một ý"),
    }
    for case_id, doc, question, expect, must in scope["CASES"]
    if case_id != 22
]
payload = {
    "name": "Golden set Viga: hỏi đáp tài liệu onboarding",
    "documents": {"D1": "Hướng dẫn ngày 1 onboarding", "D2": "Ngoại lệ: laptop, tài khoản, hồ sơ ngày 1"},
    "grading": "ANSWER: phải trả lời có trích dẫn và có đủ các ý must_contain; NO_BASIS: phải từ chối; ANY: chấp nhận cả hai, chỉ kiểm must_contain nếu có",
    "count": len(cases),
    "cases": cases,
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(cases)} câu -> {OUT}")
