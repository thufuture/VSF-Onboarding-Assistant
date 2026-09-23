#!/usr/bin/env bash
# Kiểm tra công khai cho miền AWS — CHỈ /api/* (frontend chạy trên Vercel, không phải máy này, nên các
# kiểm tra /vi/login và "/" chuyển hướng của scripts/vps/smoke-test.sh không áp dụng được ở đây).
# Dùng: smoke-test.sh https://vsf-api.duckdns.org
# SMOKE_AUTH_ME=1 bật kiểm /api/v1/auth/me = 401.
set -uo pipefail

BASE="${1:?Cần URL gốc, ví dụ https://vsf-api.duckdns.org}"
BASE="${BASE%/}"
fail=0

check() { # tên, mã mong đợi, mã thực tế
  if [ "$3" = "$2" ]; then echo "OK   $1 = $3"; else echo "FAIL $1: mong $2, nhận $3"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@" || echo 000; }

check "GET /api/v1/health" 200 "$(code "$BASE/api/v1/health")"
body="$(curl -s --max-time 10 "$BASE/api/v1/health" || true)"
case "$body" in *'"ok"'*) echo "OK   health trả status ok" ;; *) echo "FAIL health body: $body"; fail=1 ;; esac
check "GET /api/v1/ready từ ngoài" 404 "$(code "$BASE/api/v1/ready")"
if [ "${SMOKE_AUTH_ME:-0}" = "1" ]; then
  check "GET /api/v1/auth/me (chưa đăng nhập)" 401 "$(code "$BASE/api/v1/auth/me")"
fi

exit "$fail"
