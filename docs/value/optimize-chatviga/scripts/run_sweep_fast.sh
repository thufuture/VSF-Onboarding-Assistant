#!/usr/bin/env bash
# Hai thử nhanh để rerank vừa ngân sách thời gian: (1) bge-reranker-v2-m3 lượng tử hóa int8; (2) mô hình đa ngữ nhỏ mmarco-mMiniLMv2.
# Mỗi lần: 12 ứng viên, câu gốc và câu tách từ, 256 token, trên tập chỉnh.
cd "$(dirname "$0")/../../../.."
export PYTHONIOENCODING=utf-8 PYTHONPATH=backend
D=docs/value/optimize-chatviga
LOG=$D/ket-qua/quet-tham-so/fast.log
wait_health() { until curl -sf http://127.0.0.1:8090/health > /dev/null; do sleep 5; done; curl -s http://127.0.0.1:8090/health >> $LOG; echo >> $LOG; }
echo "[$(date +%T)] int8" >> $LOG
RERANK_INT8=1 bash $D/scripts/run_reranker.sh start 6 > /dev/null; wait_health
SWEEP_TAG=_int8 SWEEP_TOP=12 SWEEP_VARIANTS=natural_256,lexical_256 backend/.venv/Scripts/python.exe $D/scripts/sweep_rerank.py 2>&1 | grep -v Warning | tail -6 >> $LOG
echo "[$(date +%T)] minilm" >> $LOG
RERANK_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 bash $D/scripts/run_reranker.sh start 6 > /dev/null; wait_health
SWEEP_TAG=_minilm SWEEP_TOP=12 SWEEP_VARIANTS=natural_256,lexical_256 backend/.venv/Scripts/python.exe $D/scripts/sweep_rerank.py 2>&1 | grep -v Warning | tail -6 >> $LOG
echo "XONG thử nhanh" >> $LOG
