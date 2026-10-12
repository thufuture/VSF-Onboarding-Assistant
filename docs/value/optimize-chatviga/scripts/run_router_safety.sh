#!/usr/bin/env bash
# Bộ an toàn 46 câu cho router v2 (một lượt), rồi chấm điểm.
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
D=docs/value/optimize-chatviga
S=$D/bo-cau-hoi/safety_robustness_v0_draft.json
LOG=$D/ket-qua/router_safety.log
VIGA_ROUTER_V2=1 $PY $D/scripts/run_viga_benchmark.py --label V_router_safety --golden $S 2>&1 | grep -v Warning | tail -2 >> $LOG
$PY $D/scripts/retry_failed_questions.py --label V_router_safety --golden $S 2>&1 | grep -E "câu lỗi|ghép" >> $LOG
$PY $D/scripts/score_benchmark.py --label V_router_safety --golden $S --judge 2>&1 | grep -v Warning | tail -2 >> $LOG
echo "XONG router an toàn" >> $LOG
