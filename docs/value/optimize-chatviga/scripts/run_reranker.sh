#!/usr/bin/env bash
# Khởi chạy dịch vụ rerank thử nghiệm (bge-reranker-v2-m3) trong Docker, giới hạn CPU để sát máy chạy thật.
# Dùng: run_reranker.sh start [số_CPU=2] | stop | status
# Chỉ lắng nghe 127.0.0.1:8090. Mô hình tải về lần đầu (khoảng 2,2 GB) vào volume `vsf-reranker-hf`.
set -Eeuo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
NAME=vsf-reranker-bench
CPUS="${2:-2}"
export MSYS_NO_PATHCONV=1
case "${1:-status}" in
  start)
    docker rm -f "$NAME" > /dev/null 2>&1 || true
    docker run -d --name "$NAME" --cpus "$CPUS" -p 127.0.0.1:8090:8090 \
      -e RERANK_THREADS="$CPUS" -e RERANK_INT8="${RERANK_INT8:-0}" -e RERANK_MODEL="${RERANK_MODEL:-BAAI/bge-reranker-v2-m3}" -e HF_HOME=/hf -v vsf-reranker-hf:/hf -v "$(cygpath -w "$HERE"):/app:ro" \
      --entrypoint python vsf-embedder:local -m uvicorn --app-dir /app rerank_server:app --host 0.0.0.0 --port 8090
    echo "đang khởi động; tải mô hình lần đầu có thể mất vài phút. Kiểm tra: curl http://127.0.0.1:8090/health"
    ;;
  stop) docker rm -f "$NAME" ;;
  status) curl -fs http://127.0.0.1:8090/health || echo "chưa chạy" ;;
esac
