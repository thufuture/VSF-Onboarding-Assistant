#!/usr/bin/env bash
# Chạy lại cặp image trước (state/previous-image). DB không downgrade.
set -euo pipefail
ROOT="${VSF_ROOT:-/opt/vsf}"
prev="$(cat "$ROOT/state/previous-image" 2>/dev/null || true)"
[ -n "$prev" ] || { echo "Không có previous-image." >&2; exit 1; }
# shellcheck disable=SC2086
exec "$(dirname "$0")/deploy.sh" $prev
