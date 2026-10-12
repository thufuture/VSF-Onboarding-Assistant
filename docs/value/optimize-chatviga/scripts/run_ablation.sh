#!/usr/bin/env bash
# Hai ô đối chứng cho ma trận cuối (cùng 50 câu, RRF tối ưu, suy luận bật luôn):
#   F_C_cut5     : chỉ cắt còn 5 mục mỗi câu hỏi con, KHÔNG rerank (tách hiệu ứng "cắt ngữ cảnh")
#   F_B_full_on  : rerank 8 ứng viên, 256 token, KHÔNG giới hạn thời gian (đo chất lượng rerank thật và thời gian thật)
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
D=docs/value/optimize-chatviga
IDS=$D/bo-cau-hoi/tap_kiem_50.json
LOG=$D/ket-qua/ablation.log
RRF="--rrf-k 10 --w-bm25 0.1 --w-vector 1"
echo "[$(date +%T)] chạy F_C_cut5" >> $LOG
ANSWER_THINKING_MODE=always RETRIEVAL_MAX_SECTIONS=5 $PY $D/scripts/run_viga_benchmark.py --label F_C_cut5 --ids-file $IDS $RRF 2>&1 | grep -v Warning | tail -1 >> $LOG
$PY $D/scripts/score_benchmark.py --label F_C_cut5 --judge 2>&1 | grep -v Warning | tail -2 >> $LOG
echo "[$(date +%T)] chạy F_B_full_on" >> $LOG
ANSWER_THINKING_MODE=always $PY $D/scripts/run_viga_benchmark.py --label F_B_full_on --ids-file $IDS $RRF --rerank --rerank-top 8 --rerank-keep 5 --rerank-query natural --rerank-max-len 256 2>&1 | grep -v Warning | tail -1 >> $LOG
$PY $D/scripts/score_benchmark.py --label F_B_full_on --judge 2>&1 | grep -v Warning | tail -2 >> $LOG
echo "XONG đối chứng" >> $LOG
