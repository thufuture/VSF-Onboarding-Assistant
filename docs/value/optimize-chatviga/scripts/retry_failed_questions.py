"""Chạy lại các câu bị lỗi chập chờn (embedding quá giờ khi máy tải nặng) rồi ghép kết quả vào lượt gốc.

Lỗi hạ tầng của môi trường đo (đã xác nhận: gọi riêng embedder 150/150 thành công, nhật ký embedder không có lỗi) không phải hành vi của Viga, nên
sau khi máy rảnh ta chạy lại đúng các câu đó với CÙNG cấu hình. Bản gốc được giữ trong lượt_<k>_lần_đầu.jsonl; câu được thay có cờ `đã_thử_lại`.
Số câu lỗi lần đầu được báo riêng như một chỉ số độ tin cậy của môi trường đo, không giấu.

Chạy từ gốc repo:
  PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/retry_failed_questions.py --label R1_full --rerank [--golden <tệp>]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DIR = Path(__file__).resolve().parents[1]
RUN = DIR / "scripts" / "run_viga_benchmark.py"


def failed_ids(path: Path) -> list[str]:
    ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        result = row.get("kết_quả") or {}
        if row.get("lỗi") or result.get("loại") == "ERROR":
            ids.append(row["id"])
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--rerank-top", type=int, default=20)
    parser.add_argument("--rerank-keep", type=int, default=5)
    parser.add_argument("--golden", default=None)
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--only-current-failures", action="store_true", help="chỉ chạy lại các câu hiện vẫn lỗi trong lượt đã ghép (bản gốc lần đầu giữ nguyên)")
    args = parser.parse_args()
    base = DIR / "ket-qua" / args.label
    target = base / f"lượt_{args.run}.jsonl"
    first = base / f"lượt_{args.run}_lần_đầu.jsonl"
    if not first.exists():
        first.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")  # giữ bản gốc, không bao giờ ghi đè
    ids = failed_ids(target if args.only_current_failures else first)
    print(f"[{args.label}] {len(ids)} câu lỗi lần đầu: {ids}")
    if not ids:
        return
    retry_label = f"{args.label}_thử_lại"
    command = [sys.executable, str(RUN), "--label", retry_label, "--ids", ",".join(ids), "--start-run", str(args.run), "--runs", "1"]
    if args.rerank:
        command += ["--rerank", "--rerank-top", str(args.rerank_top), "--rerank-keep", str(args.rerank_keep)]
    if args.golden:
        command += ["--golden", args.golden]
    subprocess.run(command, check=True, cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "backend"), "PYTHONIOENCODING": "utf-8"})
    retried = {json.loads(line)["id"]: json.loads(line) for line in (DIR / "ket-qua" / retry_label / f"lượt_{args.run}.jsonl").read_text(encoding="utf-8").splitlines()}
    merged, still_failed = [], []
    for line in (target if args.only_current_failures else first).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["id"] in retried:
            new = retried[row["id"]]
            new["đã_thử_lại"] = True
            new["nhãn"] = args.label
            if new.get("lỗi") or (new.get("kết_quả") or {}).get("loại") == "ERROR":
                still_failed.append(row["id"])
            row = new
        merged.append(json.dumps(row, ensure_ascii=False, default=str))
    target.write_text("\n".join(merged) + "\n", encoding="utf-8")
    print(f"đã ghép lại: {len(ids) - len(still_failed)} câu thành công, {len(still_failed)} câu vẫn lỗi: {still_failed}")


if __name__ == "__main__":
    main()
