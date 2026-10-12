#!/usr/bin/env bash
# Theo yêu cầu: chỉ cần 2 lượt cho R0 và R1. Kịch bản run_all_benchmarks.sh đang chạy theo vòng lặp 3 lượt và không sửa giữa chừng được,
# nên script này chờ đến khi nó BẮT ĐẦU lượt 3 (nghĩa là đã xong R0 và R1 lượt 2), dừng nó, rồi chạy bộ an toàn 2 lượt mỗi cấu hình.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"
LOG=docs/value/optimize-chatviga/ket-qua/run_all.log
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
RUN=docs/value/optimize-chatviga/scripts/run_viga_benchmark.py
SAFETY=docs/value/optimize-chatviga/bo-cau-hoi/safety_robustness_v0_draft.json
stamp() { date '+%H:%M:%S'; }

until grep -q "golden R0 lượt 3" "$LOG"; do sleep 5; done
echo "[$(stamp)] đã xong 2 lượt R0 và R1; dừng kịch bản 3 lượt" >> "$LOG"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'run_all_benchmarks|run_viga_benchmark' -and \$_.CommandLine -notmatch 'Get-CimInstance' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" || true
sleep 3
rm -f docs/value/optimize-chatviga/ket-qua/R0_full/lượt_3.jsonl docs/value/optimize-chatviga/ket-qua/R1_full/lượt_3.jsonl

for k in 1 2; do
  echo "[$(stamp)] an toàn R0 lượt $k" >> "$LOG"; $PY $RUN --label R0_safety --golden "$SAFETY" --start-run "$k" --runs 1 2>&1 | grep -v Warning | tail -3 >> "$LOG"
  echo "[$(stamp)] an toàn R1 lượt $k" >> "$LOG"; $PY $RUN --label R1_safety --golden "$SAFETY" --rerank --start-run "$k" --runs 1 2>&1 | grep -v Warning | tail -3 >> "$LOG"
done
echo "[$(stamp)] XONG chạy (2 lượt mỗi cấu hình); tiếp theo: chấm điểm" >> "$LOG"
