#!/usr/bin/env bash
# Chạy toàn bộ benchmark theo thứ tự XEN KẼ để nhiễu theo thời gian (mạng, tải DeepSeek) không thiên về một cấu hình:
#   golden 120 câu: R0, R1, R0, R1, R0, R1 (3 lượt mỗi cấu hình)   rồi   bộ an toàn 50 câu: R0, R1, R0, R1 (2 lượt)
# R0 = Viga hiện tại (không rerank). R1 = lấy 20 ứng viên, rerank bằng bge-reranker-v2-m3, giữ 5 mục.
# Dùng: run_all_benchmarks.sh   (cần: DB vsf_bench, embedder local, dịch vụ rerank run_reranker.sh start 6)
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
RUN=docs/value/optimize-chatviga/scripts/run_viga_benchmark.py
SAFETY=docs/value/optimize-chatviga/bo-cau-hoi/safety_robustness_v0_draft.json
curl -fs http://127.0.0.1:8090/health > /dev/null || { echo "dịch vụ rerank chưa chạy"; exit 1; }
stamp() { date '+%H:%M:%S'; }

for k in 1 2 3; do
  echo "[$(stamp)] golden R0 lượt $k"; $PY $RUN --label R0_full --start-run "$k" --runs 1 2>&1 | grep -v Warning | tail -3
  echo "[$(stamp)] golden R1 lượt $k"; $PY $RUN --label R1_full --rerank --start-run "$k" --runs 1 2>&1 | grep -v Warning | tail -3
done
for k in 1 2; do
  echo "[$(stamp)] an toàn R0 lượt $k"; $PY $RUN --label R0_safety --golden "$SAFETY" --start-run "$k" --runs 1 2>&1 | grep -v Warning | tail -3
  echo "[$(stamp)] an toàn R1 lượt $k"; $PY $RUN --label R1_safety --golden "$SAFETY" --rerank --start-run "$k" --runs 1 2>&1 | grep -v Warning | tail -3
done
echo "[$(stamp)] XONG chạy; tiếp theo: chấm điểm (score_benchmark.py --judge) cho từng nhãn"
