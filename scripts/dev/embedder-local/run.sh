#!/usr/bin/env bash
# Chạy embedding BGE-M3 trên máy dev. Dùng: run.sh build | start | stop | status | logs
# Không sửa docker-compose: dùng `docker run` riêng, chỉ mở cổng cho máy này (127.0.0.1:8080).
# Khóa dưới đây chỉ để dịch vụ không chạy trần trên máy dev (đã bind 127.0.0.1), không phải bí mật.
set -Eeuo pipefail

NAME="vsf-embedder-local"
IMAGE="vsf-embedder:local"
KEY="${EMBEDDER_LOCAL_KEY:-dev-local-key}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"

case "${1:-status}" in
  build)
    docker build -t "$IMAGE" -f "$HERE/Dockerfile" "$ROOT/deploy/aws/embedder"
    docker builder prune -f > /dev/null || true # bộ nhớ đệm build có thể lên tới ~10 GB
    ;;
  start)
    docker image inspect "$IMAGE" > /dev/null 2>&1 || { echo "Chưa có ảnh $IMAGE: chạy '$0 build' trước." >&2; exit 1; }
    docker rm -f "$NAME" > /dev/null 2>&1 || true
    # fp32: CPU máy dev không có AMX nên bf16 không nhanh hơn. HF_HUB_OFFLINE: chạy hoàn toàn từ mô hình đã nạp trong ảnh.
    docker run -d --name "$NAME" -p 127.0.0.1:8080:8080 --restart unless-stopped \
      -e EMBEDDING_API_KEY="$KEY" -e DTYPE=fp32 -e HF_HUB_OFFLINE=1 "$IMAGE" > /dev/null
    echo "Đang khởi động $NAME (nạp mô hình khoảng 30 đến 60 giây)..."
    for _ in $(seq 1 60); do
      if curl -fs http://127.0.0.1:8080/health 2> /dev/null | grep -q '"status":"ok"'; then
        curl -s http://127.0.0.1:8080/health; echo
        exit 0
      fi
      sleep 3
    done
    echo "Quá thời gian chờ: xem '$0 logs'." >&2
    exit 1
    ;;
  stop) docker rm -f "$NAME" ;;
  status)
    docker ps -a --filter "name=$NAME" --format "{{.Names}} {{.Status}}"
    curl -s http://127.0.0.1:8080/health 2> /dev/null && echo || echo "(chưa trả lời /health)"
    ;;
  logs) docker logs --tail 40 "$NAME" ;;
  *) echo "Dùng: $0 build | start | stop | status | logs" >&2; exit 2 ;;
esac
