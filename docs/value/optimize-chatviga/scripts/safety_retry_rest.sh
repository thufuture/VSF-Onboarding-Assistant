#!/usr/bin/env bash
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
PY=backend/.venv/Scripts/python.exe
D=docs/value/optimize-chatviga
SAFETY=$D/bo-cau-hoi/safety_robustness_v0_draft.json
LOG=$D/ket-qua/safety_retry.log
{
$PY $D/scripts/retry_failed_questions.py --label R1_safety --rerank --golden $SAFETY 2>&1 | grep -E "câu lỗi|ghép"
for L in R0_safety R1_safety; do echo "== chấm $L"; $PY $D/scripts/score_benchmark.py --label $L --golden $SAFETY --judge 2>&1 | grep -v Warning | tail -3; done
echo "XONG an toàn lại"
} >> $LOG 2>&1
