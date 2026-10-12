#!/usr/bin/env bash
# Xác nhận hồ sơ RETRIEVAL_PROFILE=optimized của SẢN PHẨM (không dùng cờ riêng của harness) cho kết quả khớp ô C_cut5 đã đo.
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
D=docs/value/optimize-chatviga
LOG=$D/ket-qua/product_check.log
echo "[$(date +%T)] chạy F_P_optimized (hồ sơ sản phẩm, VIGA_ROUTER_V2=1, suy luận bật)" >> $LOG
RETRIEVAL_PROFILE=optimized VIGA_ROUTER_V2=1 ANSWER_THINKING_MODE=always $PY $D/scripts/run_viga_benchmark.py --label F_P_optimized --ids-file $D/bo-cau-hoi/tap_kiem_50.json 2>&1 | grep -v Warning | tail -1 >> $LOG
$PY $D/scripts/score_benchmark.py --label F_P_optimized --judge 2>&1 | grep -v Warning | tail -2 >> $LOG
echo "XONG kiểm sản phẩm" >> $LOG
