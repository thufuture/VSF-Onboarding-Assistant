#!/usr/bin/env bash
# Deploy có khóa và tự rollback (deployment-ci mục 6).
# Dùng: deploy.sh <backend-image> <frontend-image>
#   ảnh dạng ghcr.io/<org>/vsf-backend@sha256:<64 hex> (bản thử cục bộ: DEPLOY_ALLOW_TAGS=1 cho phép tag).
set -Eeuo pipefail

ROOT="${VSF_ROOT:-/opt/vsf}"
STATE="$ROOT/state"
BACKEND_IMAGE="${1:?Cần image backend}"
FRONTEND_IMAGE="${2:?Cần image frontend}"
IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/}" # tham số hóa tổ chức, ví dụ ghcr.io/<org>/
SMOKE_URL="${SMOKE_URL:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"

COMPOSE_FILE="$ROOT/deploy/compose.vps.yml"
ENV_FILE="$ROOT/env/compose.env"
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

mkdir -p "$STATE"
exec 9>"$STATE/deploy.lock"
flock -n 9 || { echo "Đang có deploy khác chạy." >&2; exit 1; }

# 1. Kiểm tra đầu vào
digest_re='@sha256:[0-9a-f]{64}$'
for img in "$BACKEND_IMAGE" "$FRONTEND_IMAGE"; do
  [[ "$img" == "$IMAGE_PREFIX"* ]] || { echo "Image không thuộc $IMAGE_PREFIX: $img" >&2; exit 1; }
  if [ "${DEPLOY_ALLOW_TAGS:-0}" != "1" ] && ! [[ "$img" =~ $digest_re ]]; then
    echo "Image phải ghim theo digest: $img" >&2
    exit 1
  fi
done
set -a; . "$ENV_FILE"; set +a

previous=""
[ -f "$STATE/current-image" ] && previous="$(cat "$STATE/current-image")"

run_stack() { # $1 backend, $2 frontend
  export BACKEND_IMAGE="$1" FRONTEND_IMAGE="$2"
  compose up -d --remove-orphans backend frontend caddy
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
  "$HERE/smoke-test.sh" "$SMOKE_URL"
}

rollback() {
  trap - ERR
  echo "Deploy thất bại, chạy lại bản trước." >&2
  if [ -n "$previous" ]; then
    # shellcheck disable=SC2086
    set -- $previous
    run_stack "$1" "$2" || true
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

# 2. Kéo image (backend/frontend theo digest; caddy, db theo tag ghim)
export BACKEND_IMAGE FRONTEND_IMAGE
compose pull backend frontend caddy db

# 3. Khởi động db, chờ healthy
compose up -d --wait db

# 4. Backup trước migrate (bỏ qua lần deploy đầu)
if [ -n "$previous" ]; then "$HERE/backup-db.sh"; fi

# 5. Migrate
compose --profile tools run --rm migrate

# 6. Khởi động, 7. chờ sẵn sàng, 8. smoke test
run_stack "$BACKEND_IMAGE" "$FRONTEND_IMAGE"
wait_ready
smoke

# 9. Ghi trạng thái
if [ -n "$previous" ]; then echo "$previous" > "$STATE/previous-image"; fi
echo "$BACKEND_IMAGE $FRONTEND_IMAGE" > "$STATE/current-image"

# 10. Dọn
docker image prune -af --filter "until=168h" > /dev/null || true
docker logout "${IMAGE_PREFIX%%/*}" > /dev/null 2>&1 || true
echo "Deploy xong: $BACKEND_IMAGE $FRONTEND_IMAGE"
