#!/usr/bin/env bash
# Deploy có khóa và tự rollback — bản AWS của scripts/vps/deploy.sh, CHỈ 1 image (backend), không có
# frontend (frontend chạy trên Vercel, không phải máy này).
# Dùng: deploy.sh <backend-image>
#   ảnh dạng ghcr.io/<org>/vsf-backend@sha256:<64 hex> (bản thử cục bộ: DEPLOY_ALLOW_TAGS=1 cho phép tag).
set -Eeuo pipefail

ROOT="${VSF_ROOT:-/opt/vsf-aws}"
STATE="$ROOT/state"
BACKEND_IMAGE="${1:?Cần image backend}"
IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/}" # tham số hóa tổ chức, ví dụ ghcr.io/<org>/
SMOKE_URL="${SMOKE_URL:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
VPS_SCRIPTS="$HERE/../vps" # backup-db.sh dùng lại nguyên văn từ đây, xem ghi chú ở bước 4

COMPOSE_FILE="$ROOT/deploy/aws/compose.aws.yml"
ENV_FILE="$ROOT/env/compose.env"
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

mkdir -p "$STATE"
exec 9>"$STATE/deploy.lock"
flock -n 9 || { echo "Đang có deploy khác chạy." >&2; exit 1; }

# 1. Kiểm tra đầu vào
digest_re='@sha256:[0-9a-f]{64}$'
[[ "$BACKEND_IMAGE" == "$IMAGE_PREFIX"* ]] || { echo "Image không thuộc $IMAGE_PREFIX: $BACKEND_IMAGE" >&2; exit 1; }
if [ "${DEPLOY_ALLOW_TAGS:-0}" != "1" ] && ! [[ "$BACKEND_IMAGE" =~ $digest_re ]]; then
  echo "Image phải ghim theo digest: $BACKEND_IMAGE" >&2
  exit 1
fi
set -a; . "$ENV_FILE"; set +a

previous=""
[ -f "$STATE/current-image" ] && previous="$(cat "$STATE/current-image")"

run_stack() { # $1 backend
  export BACKEND_IMAGE="$1"
  compose up -d --remove-orphans backend caddy
}

wait_ready() { # 7. /api/v1/ready nội bộ qua mạng Docker
  for _ in $(seq 1 30); do
    if compose exec -T backend python -c \
      "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/ready').status==200 else 1)" \
      >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

smoke() {
  [ -n "$SMOKE_URL" ] || { echo "SMOKE_URL chưa đặt: bỏ qua smoke test công khai."; return 0; }
  # Miền AWS chỉ phục vụ /api/* (frontend ở Vercel) — dùng smoke test API-only, không phải bản VPS đầy đủ.
  "$HERE/smoke-test.sh" "$SMOKE_URL"
}

rollback() {
  trap - ERR
  echo "Deploy thất bại, chạy lại bản trước." >&2
  if [ -n "$previous" ]; then
    run_stack "$previous" || true
    if wait_ready && smoke; then
      echo "Đã rollback về: $previous" >&2
    else
      echo "CẢNH BÁO: rollback cũng chưa qua kiểm tra." >&2
    fi
  else
    echo "Chưa có bản trước để rollback." >&2
  fi
  exit 1
}
trap rollback ERR

# 2. Kéo image (backend theo digest; caddy, db theo tag ghim)
export BACKEND_IMAGE
compose pull backend caddy db

# 3. Khởi động db, chờ healthy
compose up -d --wait db

# 4. Backup trước migrate (bỏ qua lần deploy đầu). backup-db.sh (scripts/vps/) nhận VSF_ROOT + COMPOSE_FILE
# để trỏ đúng thư mục/compose file AWS — không cần bản riêng.
if [ -n "$previous" ]; then VSF_ROOT="$ROOT" COMPOSE_FILE="$COMPOSE_FILE" "$VPS_SCRIPTS/backup-db.sh"; fi

# 5. Migrate
compose --profile tools run --rm migrate

# 6. Khởi động, 7. chờ sẵn sàng, 8. smoke test
run_stack "$BACKEND_IMAGE"
wait_ready
smoke

# 9. Ghi trạng thái
if [ -n "$previous" ]; then echo "$previous" > "$STATE/previous-image"; fi
echo "$BACKEND_IMAGE" > "$STATE/current-image"

# 10. Dọn
docker image prune -af --filter "until=168h" > /dev/null || true
docker logout "${IMAGE_PREFIX%%/*}" > /dev/null 2>&1 || true
echo "Deploy xong: $BACKEND_IMAGE"
