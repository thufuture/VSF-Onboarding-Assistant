#!/usr/bin/env bash
# Rút ngắn thời gian theo yêu cầu: R1 với 20 ứng viên rất chậm trên CPU. Giữ lại R1 (20 ứng viên) lượt 1 đã chạy làm một điểm so sánh,
# rồi các lượt R1 sau dùng 10 ứng viên -> giữ 5 (nhãn R1_top10). Script chờ đến khi kịch bản 3 lượt cũ BẮT ĐẦU "golden R1 lượt 2"
# (nghĩa là đã xong R0 lượt 2), dừng nó, rồi chạy: R1_top10 2 lượt trên golden, bộ an toàn R0 2 lượt và R1_top10 1 lượt.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"
LOG=docs/value/optimize-chatviga/ket-qua/run_all.log
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
RUN=docs/value/optimize-chatviga/scripts/run_viga_benchmark.py
SAFETY=docs/value/optimize-chatviga/bo-cau-hoi/safety_robustness_v0_draft.json
stamp() { date '+%H:%M:%S'; }

until grep -q "golden R1 lượt 2" "$LOG"; do sleep 5; done
echo "[$(stamp)] đã xong R0 lượt 2; dừng kịch bản cũ, chuyển sang R1 với 10 ứng viên" >> "$LOG"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'run_all_benchmarks|run_viga_benchmark|finish_after_two_runs' -and \$_.CommandLine -notmatch 'Get-CimInstance' -and \$_.CommandLine -notmatch 'finish_with_top10' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" || true
sleep 3
rm -f docs/value/optimize-chatviga/ket-qua/R1_full/lượt_2.jsonl

for k in 1 2; do
  echo "[$(stamp)] golden R1_top10 lượt $k" >> "$LOG"; $PY $RUN --label R1_top10 --rerank --rerank-top 10 --rerank-keep 5 --start-run "$k" --runs 1 2>&1 | grep -v Warning | tail -3 >> "$LOG"
done
for k in 1 2; do
  echo "[$(stamp)] an toàn R0 lượt $k" >> "$LOG"; $PY $RUN --label R0_safety --golden "$SAFETY" --start-run "$k" --runs 1 2>&1 | grep -v Warning | tail -3 >> "$LOG"
done
echo "[$(stamp)] an toàn R1_top10 lượt 1" >> "$LOG"; $PY $RUN --label R1_safety --golden "$SAFETY" --rerank --rerank-top 10 --rerank-keep 5 --start-run 1 --runs 1 2>&1 | grep -v Warning | tail -3 >> "$LOG"
echo "[$(stamp)] XONG chạy; tiếp theo: chấm điểm" >> "$LOG"
