#!/usr/bin/env bash
# Chấm bổ sung bằng giám khảo thứ hai (OpenRouter / Claude Haiku 5.5) cho các ô của ma trận cuối. Khóa đọc từ tệp ngoài repo (JUDGE_KEY_FILE).
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
LOG=docs/value/optimize-chatviga/ket-qua/second_judge.log
for L in "$@"; do
  backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/add_second_judge.py --label $L --provider openrouter 2>&1 | grep -v Warning | tail -1 >> $LOG
done
echo "XONG giám khảo hai" >> $LOG
