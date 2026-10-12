#!/usr/bin/env bash
# Ô đề xuất cuối: RRF tối ưu (k=10, BM25:vector=0,1:1) + cắt còn 5 mục mỗi câu hỏi con + tắt suy luận ở bước trả lời, không rerank.
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
D=docs/value/optimize-chatviga
LOG=$D/ket-qua/best_cell.log
echo "[$(date +%T)] chạy F_C_cut5_off" >> $LOG
ANSWER_THINKING_MODE=off RETRIEVAL_MAX_SECTIONS=5 $PY $D/scripts/run_viga_benchmark.py --label F_C_cut5_off --ids-file $D/bo-cau-hoi/tap_kiem_50.json --rrf-k 10 --w-bm25 0.1 --w-vector 1 2>&1 | grep -v Warning | tail -1 >> $LOG
$PY $D/scripts/score_benchmark.py --label F_C_cut5_off --judge 2>&1 | grep -v Warning | tail -2 >> $LOG
echo "XONG ô tốt nhất" >> $LOG
