#!/usr/bin/env bash
# Đổi nguồn embedding của backend DEV giữa Modal và máy local. Dùng: embedding-switch.sh local | modal | status
# Chỉ sửa hai dòng EMBEDDING_ENDPOINT, EMBEDDING_API_KEY trong .env (không in khóa), rồi tạo lại container backend dev.
# Khi đổi sang local, giá trị đang dùng (Modal) được cất vào .env.embedding-modal.bak (đã nằm trong .gitignore: .env.*).
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$ROOT/.env"
BACKUP="$ROOT/.env.embedding-modal.bak"
LOCAL_ENDPOINT="http://host.docker.internal:8080"
LOCAL_KEY="${EMBEDDER_LOCAL_KEY:-dev-local-key}"

current_endpoint() { grep -E '^EMBEDDING_ENDPOINT=' "$ENV_FILE" | head -1 | cut -d= -f2-; }

set_env() { # $1 endpoint, $2 key
  python - "$ENV_FILE" "$1" "$2" << 'PYEOF'
import re, sys
path, endpoint, key = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
for name, value in (("EMBEDDING_ENDPOINT", endpoint), ("EMBEDDING_API_KEY", key)):
    if re.search(rf"^{name}=", text, re.M):
        text = re.sub(rf"^{name}=.*$", lambda m, n=name, v=value: f"{n}={v}", text, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n{name}={value}\n"
open(path, "w", encoding="utf-8", newline="").write(text)
PYEOF
}

recreate() { (cd "$ROOT" && docker compose up -d --force-recreate backend 2>&1 | tail -1); }

case "${1:-status}" in
  local)
    if [ "$(current_endpoint)" != "$LOCAL_ENDPOINT" ]; then
      { grep -E '^EMBEDDING_(ENDPOINT|API_KEY)=' "$ENV_FILE" || true; } > "$BACKUP"
      chmod 600 "$BACKUP" 2> /dev/null || true
    fi
    curl -fs http://127.0.0.1:8080/health > /dev/null || { echo "Embedder local chưa chạy: chạy scripts/dev/embedder-local/run.sh start" >&2; exit 1; }
    set_env "$LOCAL_ENDPOINT" "$LOCAL_KEY"
    recreate
    echo "Backend dev dùng embedding LOCAL ($LOCAL_ENDPOINT)."
    ;;
  modal)
    [ -s "$BACKUP" ] || { echo "Không có $BACKUP để khôi phục Modal." >&2; exit 1; }
    endpoint="$(grep -E '^EMBEDDING_ENDPOINT=' "$BACKUP" | head -1 | cut -d= -f2-)"
    key="$(grep -E '^EMBEDDING_API_KEY=' "$BACKUP" | head -1 | cut -d= -f2-)"
    set_env "$endpoint" "$key"
    recreate
    echo "Backend dev dùng embedding MODAL ($(echo "$endpoint" | sed -E 's#(https?://[^/]+).*#\1#'))."
    ;;
  status)
    case "$(current_endpoint)" in
      "$LOCAL_ENDPOINT") echo "Đang dùng: LOCAL ($LOCAL_ENDPOINT)" ;;
      *) echo "Đang dùng: $(current_endpoint | sed -E 's#(https?://[^/]+).*#\1#') (Modal hoặc nơi khác)" ;;
    esac
    ;;
  *) echo "Dùng: $0 local | modal | status" >&2; exit 2 ;;
esac
