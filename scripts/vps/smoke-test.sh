#!/usr/bin/env bash
# Kiểm tra công khai theo hợp đồng route (system design mục 9.1).
# Dùng: smoke-test.sh https://vsf-demo.duckdns.org
# SMOKE_AUTH_ME=1 bật kiểm /api/v1/auth/me = 401 (từ Phase 4; trước đó route chưa tồn tại).
set -uo pipefail

BASE="${1:?Cần URL gốc, ví dụ https://vsf-demo.duckdns.org}"
BASE="${BASE%/}"
fail=0

check() { # tên, mã mong đợi, mã thực tế
  if [ "$3" = "$2" ]; then echo "OK   $1 = $3"; else echo "FAIL $1: mong $2, nhận $3"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@" || echo 000; }

check "GET /api/v1/health" 200 "$(code "$BASE/api/v1/health")"
body="$(curl -s --max-time 10 "$BASE/api/v1/health" || true)"
case "$body" in *'"ok"'*) echo "OK   health trả status ok" ;; *) echo "FAIL health body: $body"; fail=1 ;; esac
check "GET /vi/login" 200 "$(code "$BASE/vi/login")"
check "GET / (chuyển hướng)" 307 "$(code "$BASE/")"
loc="$(curl -s -o /dev/null -w '%{redirect_url}' --max-time 10 "$BASE/" || true)"
case "$loc" in */vi) echo "OK   / chuyển tới /vi" ;; *) echo "FAIL / chuyển tới '$loc'"; fail=1 ;; esac
check "GET /api/v1/ready từ ngoài" 404 "$(code "$BASE/api/v1/ready")"
if [ "${SMOKE_AUTH_ME:-0}" = "1" ]; then
  check "GET /api/v1/auth/me (chưa đăng nhập)" 401 "$(code "$BASE/api/v1/auth/me")"
fi

exit "$fail"
