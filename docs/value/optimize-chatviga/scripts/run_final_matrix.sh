#!/usr/bin/env bash
# Ma trận cuối 2 × 3 trên tập kiểm 50 câu, mỗi ô 1 lượt, rồi chấm hai giám khảo và tổng hợp.
# Tham số rerank (TOP, LEN, TIMEOUT) lấy từ biến môi trường để đặt sau khi xem kết quả quét; RRF tối ưu: k=10, BM25:vector=0,1:1.
# Dùng: TOP=12 LEN=256 TIMEOUT=3 bash run_final_matrix.sh
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
D=docs/value/optimize-chatviga
IDS=$D/bo-cau-hoi/tap_kiem_50.json
LOG=$D/ket-qua/final_matrix.log
TOP="${TOP:-12}"; LEN="${LEN:-256}"; TIMEOUT="${TIMEOUT:-3}"
RRF="--rrf-k 10 --w-bm25 0.1 --w-vector 1"
RERANK="--rerank --rerank-top $TOP --rerank-keep 5 --rerank-query natural --rerank-max-len $LEN --rerank-timeout $TIMEOUT"
cell() { label="$1"; mode="$2"; shift 2
  echo "[$(date +%T)] chạy $label (suy luận: $mode)" >> $LOG
  ANSWER_THINKING_MODE=$mode $PY $D/scripts/run_viga_benchmark.py --label $label --ids-file $IDS "$@" 2>&1 | grep -v Warning | tail -1 >> $LOG
  echo "[$(date +%T)] chấm $label" >> $LOG
  $PY $D/scripts/score_benchmark.py --label $label --judge 2>&1 | grep -v Warning | tail -2 >> $LOG
}
cell F_A_on always $RRF
cell F_A_off off $RRF
cell F_A_adapt adaptive $RRF
cell F_B_on always $RRF $RERANK
cell F_B_off off $RRF $RERANK
cell F_B_adapt adaptive $RRF $RERANK
echo "XONG ma trận" >> $LOG
