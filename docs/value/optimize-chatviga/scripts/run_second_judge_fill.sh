#!/usr/bin/env bash
# Lượt bù: chấm Haiku cho các câu còn thiếu điểm (do lệnh bị từ chối trước đó), 2 lệnh song song.
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend JUDGE_PARALLEL=4
LOG=docs/value/optimize-chatviga/ket-qua/second_judge_fill.log
for L in "$@"; do
  backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/add_second_judge.py --label $L --provider openrouter 2>&1 | grep -v Warning | tail -1 >> $LOG
done
echo "XONG lượt bù" >> $LOG
