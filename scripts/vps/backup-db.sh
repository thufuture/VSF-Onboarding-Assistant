#!/usr/bin/env bash
# pg_dump -Fc + sha256 vào $BACKUP_DIR, giữ BACKUP_RETENTION_COUNT bản mới nhất.
set -euo pipefail

ROOT="${VSF_ROOT:-/opt/vsf}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
# COMPOSE_FILE cho phép AWS (compose.aws.yml, VSF_ROOT khác) dùng lại script này nguyên văn thay vì viết
# bản riêng — mặc định giữ đúng hành vi VPS cũ khi không đặt biến.
COMPOSE=(docker compose --env-file "$ROOT/env/compose.env" -f "${COMPOSE_FILE:-$ROOT/deploy/compose.vps.yml}")
set -a; . "$ROOT/env/compose.env"; set +a
KEEP="${BACKUP_RETENTION_COUNT:-7}"

mkdir -p "$BACKUP_DIR"
umask 077
file="$BACKUP_DIR/vsf-$(date -u +%Y%m%dT%H%M%SZ).dump"
"${COMPOSE[@]}" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$file"
(cd "$BACKUP_DIR" && sha256sum "$(basename "$file")" > "$(basename "$file").sha256")
echo "Đã sao lưu: $file"

# Giữ $KEEP bản mới nhất.
ls -1t "$BACKUP_DIR"/vsf-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
  rm -f "$old" "$old.sha256"
done
