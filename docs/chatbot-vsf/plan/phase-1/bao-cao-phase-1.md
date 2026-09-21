# Báo cáo Phase 1 — tình hình (1a-A và 1a-B)

> Thực hiện: đêm 20 → 21/09/2026, trên nhánh `phase-1a-skeleton` của repo. **Chưa commit.** Kế hoạch gốc: [phase-1.md](phase-1.md).
> **Kết luận: 1a-A (backend, DB, Docker) và 1a-B (frontend) đã xong và được kiểm chứng cục bộ. 1a-C (CI) và 1b (triển khai) chưa làm, đúng như bạn yêu cầu (làm ngày mai).**

## 1. Tóm tắt

| Hạng mục | Trạng thái |
|---|---|
| 1a-A Backend FastAPI, `/api/v1/health` và `/ready`, Alembic khung, Dockerfile, `docker-compose.yml` với ParadeDB | **Xong**, cổng 9.1 đạt |
| 1a-B Frontend Next.js: i18n `vi`, token thiết kế, trang khung `/`, `/vi`, `/vi/login`, test | **Xong**, cổng 9.2 đạt |
| 1a-C CI GitHub Actions (`verify.yml`) | **Chưa** (ngày mai) |
| 1b Khung triển khai lên VPS | **Chưa** (ngày mai; cần VPS của bạn) |
| Commit và đẩy nhánh | **Chưa**: chờ bạn xác nhận (CP3, CP4) |

## 2. Đã làm

| Nhóm | Nội dung |
|---|---|
| Backend (`backend/`, 29 tệp) | `config.py` (pydantic-settings, kiểm múi giờ), `main.py` (lifespan, middleware `X-Request-ID`, tắt `/api/docs` ở production), `api/routers/health_router.py`, `api/dependencies.py`, `services/readiness_service.py`, `model/base.py` (naming convention), `infrastructure/persistence/engine.py`; Alembic async (chưa có migration); `Dockerfile` nhiều tầng không root; `requirements(-dev).txt`, `pyproject.toml` (ruff, mypy strict, pytest) |
| Frontend (`frontend/`, 26 tệp không tính lockfile) | Next 16.3.0, React 19.2.8, next-intl, Tailwind 4; `proxy.ts` (chỉ chuyển hướng ngôn ngữ), token thiết kế trong `globals.css` (sáng + tối cơ bản), trang khung `/vi` và `/vi/login`; `next.config.ts` (`output: standalone`, rewrite `/api` chỉ ở dev); `package-lock.json` |
| Gốc | `docker-compose.yml` (`db`, `migrate`, `backend`; project `vsf-onboarding`, volume riêng, cổng DB 5434), cập nhật `.env.example`, `.gitignore` |
| Tài liệu | Đồng bộ `plan/` từ `P-040` sang repo; cập nhật README gốc (mục "Chạy cục bộ"), database-design (câu hỏi mở về `btree_gist` đã có đáp án), deployment-ci (không ghi đè `command`, CI dùng được service container), master-plan và [phase-1.md](phase-1.md) (trạng thái) |
| Test | Backend **26** (24 đơn vị + 2 tích hợp); frontend **13** (5 tệp) |

## 3. Kiểm chứng (cổng của [phase-1.md](phase-1.md) mục 9)

**Cổng 1a-A (backend)**
- [x] `ruff check`, `ruff format --check`, `mypy` (strict, 20 tệp): không lỗi.
- [x] `pytest`: 24 test đơn vị xanh; **26 xanh** khi đặt `VSF_TEST_DATABASE_URL` (gồm readiness thật và ràng buộc `EXCLUDE` chặn chồng ngày).
- [x] `docker compose up -d --build`: `db` khỏe (~15 giây), `migrate` thoát mã 0, `backend` khỏe (~9 giây).
- [x] `GET /api/v1/health` → `200 {"status":"ok"}`; `GET /api/v1/ready` → `200` (database ok, ba extension có sẵn, migration "chưa có migration").
- [x] `GET /health` và `/ready` ở gốc → `404`.
- [x] `X-Request-ID`: giá trị hợp lệ của client được trả lại; giá trị xấu (`bad id`) bị thay bằng ID mới.
- [x] Tắt `db`: `/health` vẫn `200`, `/ready` → `503` với `"error":"gaierror"` và **không** chứa chuỗi kết nối hay mật khẩu; bật lại thì `/ready` trở về `200` sau ~4 giây.
- [x] `alembic upgrade head` (thật và `--sql` offline) và `alembic check`: chạy được, không có thay đổi.
- [x] `docker compose down` **giữ dữ liệu** (ghi 42 vào bảng thử, tắt, bật lại, đọc lại được); volume `vsf-onboarding_pgdata` còn; volume `p-040_pgdata` của Ralion không bị đụng.

**Cổng 1a-B (frontend)**
- [x] `npm run lint`, `npm run typecheck` (`next typegen && tsc --noEmit`), `npm test`: xanh.
- [x] `npm run build` xong, có `.next/standalone/server.js`.
- [x] Server standalone (cách image sẽ chạy): `/` → 307 tới `/vi`; `/vi` → 200; `/vi/login` → 200 (`lang="vi"`, có chữ "Đăng nhập", title đúng); `/login` và `/x` → 307; đường dẫn `/vi` không tồn tại → 404; `/api/v1/health` → 404 ở production (rewrite chỉ dành cho dev, Caddy sẽ lo).
- [x] Chế độ dev: `/api/v1/health` qua Next (rewrite) tới backend trong Docker → `200 {"status":"ok"}`; `/api/v1/ready` → 200.
- [x] Không có chuỗi giao diện tiếng Việt viết cứng trong component (chỉ trong `messages/vi.json`).

**Kiểm tra bổ sung:** cây Git sạch (57 tệp sẽ được thêm, không có `.venv`, `node_modules`, `.next`, `next-env.d.ts`, `tsbuildinfo`).

## 4. Phát hiện và lỗi đã sửa trong lúc làm

| # | Phát hiện | Xử lý |
|---|---|---|
| 1 | Ghi đè `command` của image ParadeDB chỉ với `pg_search` làm image thoát ngay (script khởi tạo chạy `CREATE EXTENSION pg_cron`). Lệnh mặc định đã nạp `pg_search,pg_cron,pg_stat_statements` | Compose không ghi đè `command`; ghi vào tài liệu; CI dùng được service container |
| 2 | **Lỗi trong mã của tôi, test bắt được:** `ZoneInfoNotFoundError` là `KeyError`, không phải `ValueError`, nên pydantic không đổi thành lỗi xác thực khi múi giờ sai | Bắt và ném `ValueError`; sửa chú thích sai |
| 3 | `alembic check` **đỏ** trên image thật: image cài sẵn PostGIS nên có `spatial_ref_sys` và `_typmod_cache`, Alembic tưởng phải xóa (đúng chỗ Ralion đã phải lọc) | Thêm `include_object` với `EXTENSION_MANAGED_TABLES` trong `alembic/env.py`; danh sách này có thể cần cập nhật khi đổi phiên bản image |
| 4 | `next dev` tự sinh `frontend/AGENTS.md` và `CLAUDE.md` (hướng dẫn cho AI về Next 16) và tạo lại mỗi lần chạy | Giữ và commit thay vì để cây luôn bẩn |
| 5 | `next-intl` cài ra `4.14.5` (Ralion dùng `4.13.7`) vì khoảng `^`; `vitest` `4.1.11` | `package-lock.json` được commit nên bản đã kiểm được giữ nguyên |
| 6 | npm cảnh báo **`eslint 9.x` đã hết hỗ trợ** | Chưa đổi; xem mục 7 |
| 7 | Test tích hợp tạo `btree_gist` trong DB dev, nên `/ready` báo `installed` gồm cả `btree_gist` | Vô hại (`0001_core` dùng `IF NOT EXISTS`); ghi để khỏi ngạc nhiên |

## 5. Sai lệch so với kế hoạch

1. **Layout:** kế hoạch ghi `app/[locale]/layout.tsx` là root layout. Thực tế theo mẫu Ralion đã chạy được: root `app/layout.tsx` (`<html>`, metadata, đọc header ngôn ngữ) cộng `app/[locale]/layout.tsx` chỉ chứa provider next-intl.
2. **Hằng số header ngôn ngữ** (`x-vsf-locale`) đặt ở `i18n/routing.ts` để `proxy`, `request` và root layout dùng chung (proxy không nên import `next/headers`).
3. **`alembic/env.py`** có thêm bộ lọc bảng extension (phát hiện 3, không có trong kế hoạch).
4. **Không làm** ở 1a: `import-linter` (chưa có đủ mã để có luật ý nghĩa), quét image (Trivy), Playwright, `@tanstack/react-query`, `lucide-react`. Đúng phạm vi đã nêu.
5. **Quyết định P1–P10 dùng đúng mặc định** (image `v0.25.4-pg16`, cổng 5434/8000/3000, `requirements.txt`, Node 22, font hệ thống, token tối cơ bản, `/ready` tự siết khi có migration, frontend ngoài compose, nhánh `phase-1a-skeleton`).

## 6. Số liệu (dữ liệu hiệu chỉnh lịch, chưa đo chi tiết)

| Mục | Giá trị |
|---|---|
| Image backend | 319 MB |
| DB khỏe sau khi `up` | ~15 giây (image đã có sẵn trên máy) |
| Backend khỏe sau khi `up` | ~9 giây |
| `npm install` (604 gói) | ~4 phút |
| `next build` | biên dịch ~21 giây + TypeScript ~9 giây |
| `vitest run` (13 test) | ~29 giây (phần lớn là khởi tạo `jsdom`) |
| RAM DB khi rảnh | ~105 MiB |
| Phiên bản đã cài | next 16.3.0 · react 19.2.8 · next-intl 4.14.5 · tailwindcss 4.3.3 · vitest 4.1.11 · typescript 5.9.3 · fastapi 0.141.1 · sqlalchemy 2.0.54 · asyncpg 0.31.0 · alembic 1.20.0 · pydantic 2.13.5 |
| Thời gian thao tác của tôi cho 1a-A + 1a-B | khoảng 1–1,5 giờ liên tục (chưa đo chính xác), so với ước lượng 0,9 ngày công |

Chưa nên suy ra tốc độ cho các phase sau: Phase 1a là khung ít logic. Hiệu chỉnh lịch thật sự làm **sau Phase 2**.

## 7. Việc theo dõi (không chặn)

- **`eslint 9` hết hỗ trợ:** cân nhắc nâng lên bản mới khi `eslint-config-next` hỗ trợ; kiểm ở PR CI.
- **Khóa phiên bản Python** cho image (P3): hiện chỉ có cận trên; làm ở 1b.
- **Font Inter:** đang dùng chuỗi font hệ thống; tự host Inter ở phase sau.
- **Chế độ tối:** token đã có nhưng chưa có công tắc và chưa kiểm tương phản.
- **Cổng backend 8000 trùng Ralion:** đặt `BACKEND_HOST_PORT` khi chạy cả hai.
- **`EXTENSION_MANAGED_TABLES`** phụ thuộc phiên bản image ParadeDB.

## 8. Còn lại và bước tiếp theo

| # | Việc | Ai | Ghi chú |
|---|---|---|---|
| 1 | **CP3:** commit 1a-A và 1a-B vào nhánh `phase-1a-skeleton` (cục bộ) | Bạn xác nhận, tôi làm | 57 tệp mã + cập nhật tài liệu; nên tách hai commit (mã, tài liệu) |
| 2 | **1a-C:** viết `verify.yml` (backend, frontend, images) | Tôi | Ngày mai |
| 3 | **CP4:** đẩy nhánh, mở PR, xem CI xanh | Bạn xác nhận; tôi làm nếu có `gh`, còn không bạn bấm và báo kết quả | Đẩy là hành động ra ngoài |
| 4 | **1b:** Dockerfile frontend, `compose.vps.yml`, Caddyfile, `bootstrap.sh`, `deploy.sh`, `smoke-test.sh`, GHCR | Tôi viết; **bạn cần VPS (Oracle trước, dự phòng Hetzner) + DuckDNS + khóa SSH trước**; nếu Oracle (ARM) thì phải build image `linux/arm64` | Giới hạn cứng 1 ngày; xem [phase-1.md](phase-1.md) mục 8 |
| 5 | Việc tồn từ Phase 0: VPS, thư mentor, bảo vệ nhánh | Bạn | [bao-cao-phase-0.md](../phase-0/bao-cao-phase-0.md) mục 8 |
