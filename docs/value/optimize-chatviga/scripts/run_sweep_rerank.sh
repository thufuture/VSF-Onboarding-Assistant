#!/usr/bin/env bash
cd "$(dirname "$0")/../../../.."
PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/sweep_rerank.py > docs/value/optimize-chatviga/ket-qua/quet-tham-so/rerank.log 2>&1
echo "XONG quét rerank" >> docs/value/optimize-chatviga/ket-qua/quet-tham-so/rerank.log
