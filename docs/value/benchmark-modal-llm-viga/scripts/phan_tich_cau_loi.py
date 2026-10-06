# -*- coding: utf-8 -*-
"""Liệt kê từng câu không đạt (✓) và từng câu đổi kết quả giữa các phương án; đo độ dao động tự nhiên giữa hai lượt chạy
của CÙNG một phương án (để biết chênh lệch nào là nhiễu của LLM, chênh lệch nào là do tắt thinking)."""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "ket-qua"
LABELS = ["A_hien_trang", "B_tat_route_rewrite", "C_tat_ca"]
data = {label: json.loads((BASE / f"{label}.json").read_text(encoding="utf-8"))["results"] for label in LABELS}
out: list[str] = []

out.append("### Các câu không đạt ✓ (mỗi dòng: phương án, lượt, câu, kết quả, ý còn thiếu)")
for label in LABELS:
    for r in data[label]:
        if r["verdict"] != "✓":
            out.append(f"- {label} · lượt {r['run']} · #{r['id']} · {r['verdict']} {r['got']} · thiếu {r['missing'] or '–'} · “{r['question'][:70]}”")

out.append("")
out.append("### Dao động tự nhiên: cùng phương án, lượt 1 so với lượt 2 (số câu đổi kết quả / 40)")
for label in LABELS:
    first = {r["id"]: r for r in data[label] if r["run"] == 1}
    second = {r["id"]: r for r in data[label] if r["run"] == 2}
    diff = [i for i in first if first[i]["verdict"] != second[i]["verdict"]]
    out.append(f"- {label}: {len(diff)}/40 câu đổi kết quả giữa hai lượt ({diff})")

out.append("")
out.append("### Câu đổi kết quả so với A (cùng câu, cùng lượt)")
base = {(r["run"], r["id"]): r for r in data["A_hien_trang"]}
for label in LABELS[1:]:
    for r in data[label]:
        a = base[(r["run"], r["id"])]
        if a["verdict"] != r["verdict"]:
            out.append(f"- {label} · lượt {r['run']} · #{r['id']}: A={a['verdict']} ({a['got']}) → {r['verdict']} ({r['got']}) · thiếu {r['missing'] or '–'} · “{r['question'][:60]}”")

text = "\n".join(out) + "\n"
(BASE.parent / "phan-tich-cau-loi.md").write_text(text, encoding="utf-8")
sys.stdout.buffer.write(text.encode("utf-8"))
