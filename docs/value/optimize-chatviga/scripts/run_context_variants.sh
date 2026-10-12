#!/usr/bin/env bash
# Chạy các biến thể tối ưu (cờ cấu hình) trên golden 120 câu, mỗi biến thể 1 lượt, rồi chấm điểm bằng hai giám khảo.
# Mỗi biến thể = một tập biến môi trường (xem config.py). R0 (không cờ) đã chạy ở lần benchmark trước.
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
D=docs/value/optimize-chatviga
LOG=$D/ket-qua/variants.log
run() { label="$1"; shift
  echo "[$(date +%T)] chạy $label" >> $LOG
  env "$@" $PY $D/scripts/run_viga_benchmark.py --label $label 2>&1 | grep -v Warning | tail -2 >> $LOG
  $PY $D/scripts/retry_failed_questions.py --label $label 2>&1 | grep -E "câu lỗi|ghép" >> $LOG
  echo "[$(date +%T)] chấm $label" >> $LOG
  $PY $D/scripts/score_benchmark.py --label $label --judge 2>&1 | grep -v Warning | tail -2 >> $LOG
}
run V_router VIGA_ROUTER_V2=1
run V_k5 RETRIEVAL_MAX_SECTIONS=5
run V_k3 RETRIEVAL_MAX_SECTIONS=3
run V_k5_dedupe_cap RETRIEVAL_MAX_SECTIONS=5 RETRIEVAL_DEDUPE_SECTIONS=1 RETRIEVAL_TOTAL_TOKEN_CAP=2500
echo "XONG biến thể" >> $LOG
