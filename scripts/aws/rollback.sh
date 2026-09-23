#!/usr/bin/env bash
# Chạy lại image backend trước (state/previous-image). DB không downgrade. Bản AWS của scripts/vps/rollback.sh.
set -euo pipefail
ROOT="${VSF_ROOT:-/opt/vsf-aws}"
prev="$(cat "$ROOT/state/previous-image" 2>/dev/null || true)"
[ -n "$prev" ] || { echo "Không có previous-image." >&2; exit 1; }
exec "$(dirname "$0")/deploy.sh" "$prev"
