#!/usr/bin/env bash
# Theo yêu cầu mới: mỗi cấu hình chỉ chạy 1 lần. R0 lượt 1 đã xong; R1 (20 ứng viên, giữ 5) lượt 1 đang chạy. Script này chờ đến khi kịch bản 3 lượt cũ
# BẮT ĐẦU "golden R0 lượt 2" (nghĩa là R1 lượt 1 đã xong), dừng nó, rồi chạy bộ an toàn 50 câu một lần cho R0 và một lần cho R1 (cùng cấu hình 20 -> 5).
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"
LOG=docs/value/optimize-chatviga/ket-qua/run_all.log
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
RUN=docs/value/optimize-chatviga/scripts/run_viga_benchmark.py
SAFETY=docs/value/optimize-chatviga/bo-cau-hoi/safety_robustness_v0_draft.json
stamp() { date '+%H:%M:%S'; }

until grep -q "golden R0 lượt 2" "$LOG"; do sleep 5; done
echo "[$(stamp)] đã xong R1 lượt 1; dừng kịch bản cũ (mỗi cấu hình chỉ 1 lần)" >> "$LOG"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'run_all_benchmarks|run_viga_benchmark|finish_with_top10|finish_after_two_runs' -and \$_.CommandLine -notmatch 'Get-CimInstance' -and \$_.CommandLine -notmatch 'finish_single_run' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" || true
sleep 3
rm -f docs/value/optimize-chatviga/ket-qua/R0_full/lượt_2.jsonl

echo "[$(stamp)] an toàn R0 lượt 1" >> "$LOG"; $PY $RUN --label R0_safety --golden "$SAFETY" --start-run 1 --runs 1 2>&1 | grep -v Warning | tail -3 >> "$LOG"
echo "[$(stamp)] an toàn R1 lượt 1" >> "$LOG"; $PY $RUN --label R1_safety --golden "$SAFETY" --rerank --start-run 1 --runs 1 2>&1 | grep -v Warning | tail -3 >> "$LOG"
echo "[$(stamp)] XONG chạy (mỗi cấu hình 1 lần); tiếp theo: chấm điểm" >> "$LOG"
