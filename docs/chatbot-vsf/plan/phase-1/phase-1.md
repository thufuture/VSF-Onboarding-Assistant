# Phase 1 — Kế hoạch chi tiết (chưa thực hiện, chờ bạn duyệt)

> Trạng thái: **1a-A và 1a-B ĐÃ THỰC HIỆN (2026-09-21)**, kết quả ở [bao-cao-phase-1.md](bao-cao-phase-1.md); 1a-C (CI) và 1b (triển khai) chưa làm. Nội dung dưới là kế hoạch gốc, giữ nguyên để đối chiếu. (Ghi chú cũ: tôi đã tạo rồi **xóa** 3 tệp cấu hình trong `backend/` của repo mới khi bạn yêu cầu lập kế hoạch trước; repo mới đang sạch ở commit `d8195e2`.)
> Thuộc [master-plan.md](../master-plan.md): **Phase 1a** (khung cục bộ, 1 ngày) và **Phase 1b** (khung triển khai, 1 ngày, giới hạn cứng). Trước đó: [phase-0.md](../phase-0/phase-0.md).
> Theo yêu cầu của bạn: **hôm nay làm khung cục bộ (1a-A, 1a-B); CI GitHub (1a-C) và triển khai (1b) làm ngày mai.**
> Mọi đoạn mã bên dưới là **bản dự kiến**, chưa áp dụng vào đâu.

## 0. Trả lời nhanh: database là gì?

Đúng, là **PostgreSQL**. Cụ thể là PostgreSQL 16 (bản 16.15) trong image `paradedb/paradedb:v0.25.4-pg16`, một máy chủ duy nhất cho mọi việc:

| Thành phần | Bản đã kiểm | Dùng để |
|---|---|---|
| PostgreSQL | 16.15 | Lưu dữ liệu nghiệp vụ (người dùng, tài liệu, quy trình, hội thoại, ticket) |
| `pgvector` | 0.8.4 | Tìm theo vector (embedding BGE-M3 1024 chiều), chỉ mục HNSW |
| `pg_search` (ParadeDB) | 0.25.4 | Tìm từ khóa BM25 (kết hợp với vector bằng RRF) |
| `btree_gist` | 1.7 | Ràng buộc `EXCLUDE USING gist` để chặn hai bản tài liệu/quy trình/link chồng ngày hiệu lực |
| SQLAlchemy 2 (async) + `asyncpg` + Alembic | (theo `requirements`) | Truy cập DB và migration |

Không dùng cơ sở dữ liệu vector riêng: một Postgres cho cả dữ liệu, vector và từ khóa giúp một lần sao lưu, một lần migration, và lọc theo ngày hiệu lực ngay trong truy vấn. Ralion dùng cùng bộ này.

## 1. Mục tiêu, ranh giới, lịch

**Mục tiêu.** Có khung chạy được ở máy cục bộ và trong CI, rồi lên máy chủ thật qua HTTPS, để Phase 2 chỉ việc cắm lát cắt dọc vào và để rủi ro hạ tầng lộ sớm.

| Phần | Nội dung | Khi nào | Ước lượng |
|---|---|---|---|
| **1a-A** | Backend FastAPI, `GET /api/v1/health` và `/api/v1/ready`, Alembic khung, Dockerfile, `docker-compose.yml` với ParadeDB | **Hôm nay** | ≈ 0,5 ngày |
| **1a-B** | Frontend Next.js khung: i18n `vi`, token thiết kế, trang khung `/`, `/vi`, `/vi/login`, test | **Hôm nay** | ≈ 0,4 ngày |
| **1a-C** | CI GitHub Actions (`verify.yml`): backend, frontend, images | **Ngày mai** | ≈ 0,1–0,2 ngày |
| **1b** | Triển khai khung lên VPS: `bootstrap.sh`, Dockerfile frontend, `compose.vps.yml`, Caddy, `deploy.sh`, smoke test, GHCR | **Ngày mai**, giới hạn cứng 1 ngày | ≈ 1 ngày |

| Có trong Phase 1 | **Không** có trong Phase 1 |
|---|---|
| Khung mã, cấu hình, hai endpoint sức khỏe, Alembic **trống** | Không có bảng nghiệp vụ nào (`0001_core` viết ở Phase 2) |
| Trang khung, chuyển hướng ngôn ngữ, token thiết kế | Không có đăng nhập, không phiên, không chat, không worker, không Langfuse |
| Compose cục bộ, CI, deploy tay lên VPS | Không tự động deploy (Phase 11b), không rollback tự động, không backup định kỳ |

## 2. Hiện trạng đã kiểm (bằng chứng, không suy đoán)

| Mục | Kết quả | Ảnh hưởng |
|---|---|---|
| Docker | Docker Desktop 29.2.1 đang chạy, cấp 10 GB RAM | Kiểm được extension và compose thật |
| Image ParadeDB có sẵn | `v0.25.4-pg16` (1,39 GB) và `v0.23.4-pg16` (2,26 GB) | Không phải tải lại |
| **Ba extension** | Có sẵn: `pg_search 0.25.4`, `vector 0.8.4`, `btree_gist 1.7`. **`vector` và `pg_search` đã được image cài sẵn** trong DB mặc định; `btree_gist` cần `CREATE EXTENSION` (sẽ nằm trong `0001_core`) | Câu hỏi mở "btree_gist có trong image không" đã có đáp án: **có** |
| **Ràng buộc chống chồng ngày** | `CREATE TABLE … EXCLUDE USING gist (code WITH =, daterange(s,e,'[]') WITH &&) WHERE (status='ACTIVE')` chạy được và **từ chối** bản chồng ngày (`conflicting key value violates exclusion constraint`) | Thiết kế INV1/INV17 khả thi trên đúng image này |
| **Lệnh khởi động** | Lệnh mặc định của image (`CMD ["postgres"]`) đã nạp `shared_preload_libraries = pg_search,pg_cron,pg_stat_statements`. **Ghi đè lệnh chỉ với `pg_search` làm image lỗi** (script khởi tạo chạy `CREATE EXTENSION pg_cron` và cần preload) | Compose và CI **không ghi đè `command`**. Compose của Ralion có ghi đè tường minh nhưng không cần thiết |
| RAM khi rảnh | ≈ 105 MiB | Nhẹ; VPS 4 GB đủ cho khung |
| Cổng | 3000, 5433, 5434, 8000 đều **trống**; không container nào đang chạy | Ralion dùng 5433 và 8000 |
| Ralion | Compose dùng volume ngoài `p-040_pgdata`, tên project `ralion-onboarding`, Python 3.11, Node 24.x | VSF dùng **tên project, volume, cổng DB riêng** để không đụng nhau |
| Node | Cục bộ 22.18, npm 11.6. `next 16.3.0` cần Node ≥ 20.9; `vitest 4.1.10` chạy Node 20/22/≥24 | Dùng Node 22 (cục bộ và CI); không cần 24 |
| Phiên bản Ralion dùng được | `next 16.3.0`, `react 19.2.8`, `next-intl 4.13.7`, `tailwindcss 4.3.3`, `eslint-config-next 16.3.0`, `typescript 5.9.3` | Dùng đúng các bản này (đã chạy được trên Ralion) |
| Python | 3.12.10 cục bộ | Trùng image `python:3.12-slim` |
| `alembic` trên Windows | Ralion phải đặt `WindowsSelectorEventLoopPolicy` trong `env.py` | Giữ lại trong VSF |

## 3. Quyết định cần bạn chốt (mặc định in đậm)

| # | Quyết định | Mặc định đề xuất | Lựa chọn khác |
|---|---|---|---|
| P1 | Bản image ParadeDB | **`v0.25.4-pg16`** (đã kiểm ba extension; một biến `PARADEDB_TAG` dùng chung cho compose, CI, VPS) | `v0.23.4-pg16` (bản Ralion đang chạy trên VPS của họ) |
| P2 | Cổng trên máy bạn | **DB `5434`, backend `8000`, frontend `3000`** (đặt lại qua `POSTGRES_HOST_PORT`, `BACKEND_HOST_PORT`); nếu chạy Ralion cùng lúc thì đổi cổng backend | Cổng khác |
| P3 | Quản lý phụ thuộc Python | **`requirements.txt` + `requirements-dev.txt` có cận trên** (như Ralion); khóa phiên bản chính xác cho image ở Phase 1b | `uv`/`pyproject` lockfile ngay bây giờ |
| P4 | Phụ thuộc frontend | **`package.json` + `package-lock.json`, `npm ci` trong CI**, Node `>=22` | pnpm/yarn |
| P5 | Font Inter | **Dùng chuỗi font hệ thống trước** (không tải font lúc build); tự host Inter ở phase sau | Tải Inter qua `next/font/google` (cần mạng lúc build) |
| P6 | Chế độ tối | **Khai báo token tối cơ bản** (chưa có công tắc) | Bỏ hẳn đến khi cần |
| P7 | Mức nghiêm của `/ready` | **Kiểm extension "có sẵn"; chỉ kiểm "đã cài" và phiên bản migration khi đã có migration** (tự siết chặt từ Phase 2) | Luôn kiểm "đã cài" (sẽ đỏ ngay ở Phase 1) |
| P8 | Frontend trong compose | **Không** (chạy `npm run dev` trên máy; Dockerfile frontend ở 1b) | Thêm service frontend vào compose ngay |
| P9 | Nhánh làm việc | **Nhánh `phase-1a-skeleton` → PR vào `main`** khi CI đã có (ngày mai); hôm nay chỉ commit cục bộ | Commit thẳng `main` |
| P10 | Đẩy CI/deploy | **Ngày mai** như bạn nói | — |

## 4. Cấu trúc repo sau Phase 1

```text
backend/
  pyproject.toml  requirements.txt  requirements-dev.txt  Dockerfile  .dockerignore
  alembic.ini
  alembic/  env.py  script.py.mako  versions/README.md
  src/
    main.py  config.py
    api/  dependencies.py  routers/health_router.py
    services/  readiness_service.py
    model/  base.py
    infrastructure/persistence/  engine.py
  tests/  conftest.py  test_config.py  test_api/  test_services/  integration/
frontend/
  package.json  package-lock.json  tsconfig.json  next.config.ts  eslint.config.mjs
  postcss.config.mjs  vitest.config.mts  vitest.setup.ts  Dockerfile (1b)
  messages/vi.json
  src/
    app/globals.css
    app/[locale]/  layout.tsx  page.tsx  login/page.tsx
    i18n/  routing.ts  request.ts  navigation.ts
    proxy.ts
    (+ test cạnh mã)
docker-compose.yml
deploy/  compose.vps.yml  Caddyfile                       (1b)
scripts/vps/  bootstrap.sh  deploy.sh  smoke-test.sh      (1b)
.github/workflows/  verify.yml                            (1a-C)
```

Chỉ tạo thư mục và tệp cần dùng ngay; không `.gitkeep`, không thư mục rỗng ([system design mục 3](../../vsf-onboarding-assistant-system-design.md)).

## 5. 1a-A — Backend, Alembic, Docker (hôm nay)

### A1. Công cụ
`backend/pyproject.toml`: `ruff` (py312, dòng 120, chọn `E,F,I,N,W,UP,B`, cho phép `Depends` làm giá trị mặc định), `mypy` (strict + plugin pydantic), `pytest` (`asyncio_mode=auto`, marker `integration`). `requirements.txt`: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `asyncpg`, `alembic`, `tzdata` (bắt buộc để `ZoneInfo("Asia/Ho_Chi_Minh")` chạy trên Windows và image slim), đều có cận trên. `requirements-dev.txt`: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `httpx`.

### A2. `config.py`
`Settings` (pydantic-settings): `app_env` (`development|test|production`), `app_timezone` (mặc định `Asia/Ho_Chi_Minh`, **kiểm hợp lệ** bằng `ZoneInfo`), `log_level`, `database_url` (mặc định `postgresql+asyncpg://vsf:vsf@localhost:5434/vsf`, mật khẩu `vsf` chỉ là của dev). Đọc `../.env` (gốc repo khi chạy trong `backend/`) rồi `.env`. `get_settings()` có cache. Các biến LLM/embedding/session **chưa** khai báo (thêm ở phase dùng chúng).

### A3. Hạ tầng và `main.py`
`infrastructure/persistence/engine.py`: `create_engine(url)` (`pool_pre_ping=True`) và `create_session_factory(engine)` (`expire_on_commit=False`). `main.py`: `lifespan` tạo engine và session factory, lưu vào `app.state`, đóng khi tắt; middleware `X-Request-ID` (nhận giá trị của client hoặc tạo mới, trả lại ở header); đăng ký `health_router`. Không CORS (cùng origin qua Caddy/rewrite dev).

### A4. `api/dependencies.py`
`get_db` (mở `AsyncSession` từ `app.state.session_factory`), `get_readiness_service` (dựng `ReadinessService` từ session).

### A5. `services/readiness_service.py`
`ReadinessService.check()` trả `ReadinessReport(ready, checks)`:

| Kiểm | Quy tắc |
|---|---|
| `database` | `SELECT 1`; lỗi thì `ok=false`, chỉ ghi **tên loại lỗi**, không ghi nội dung (không lộ chuỗi kết nối) |
| `migration` | Đọc `head` từ `alembic.ini` (`ScriptDirectory`). **Chưa có migration** thì `ok=true` (ghi "chưa có migration"). Có migration thì so `alembic_version` với head; bảng chưa tồn tại thì `ok=false` (dùng `to_regclass`, không để lỗi làm hỏng transaction) |
| `extensions` | `vector`, `pg_search`, `btree_gist` phải **có sẵn** (`pg_available_extensions`). Khi đã có migration, phải **đã cài** (`pg_extension`) |

`ready` chỉ đúng khi cả ba đúng. Đường dẫn `alembic.ini` tính từ vị trí tệp (đúng cả khi chạy trong Docker ở `/app`).

### A6. `api/routers/health_router.py`
`GET /api/v1/health` → `200 {"status":"ok"}` (không chạm DB). `GET /api/v1/ready` → `200 {"status":"ready","checks":{…}}` hoặc `503 {"status":"not_ready","checks":{…}}`. **Không có** `/health` hay `/ready` ở gốc (hợp đồng route, [system design mục 9.1](../../vsf-onboarding-assistant-system-design.md)). Caddy sẽ chặn `/api/v1/ready*` từ bên ngoài ở 1b.

### A7. `model/base.py`
`Base(DeclarativeBase)` với `naming_convention` cho khóa/ràng buộc (`ix`, `uq`, `ck`, `fk`, `pk`) để tên ràng buộc ổn định khi Alembic sinh migration ở Phase 2. `Base.metadata` **trống**.

### A8. Alembic
`alembic.ini` (`script_location = %(here)s/alembic`, không lưu URL); `alembic/env.py` chạy **async**, lấy URL từ `get_settings()`, đặt `WindowsSelectorEventLoopPolicy` khi chạy trên Windows, `target_metadata = Base.metadata`; `script.py.mako` chuẩn; `alembic/versions/README.md` (Alembic cần thư mục này tồn tại; dùng tệp giải thích thay cho `.gitkeep`). **Không có migration.** `alembic upgrade head` và `alembic check` phải chạy được và không làm gì.

### A9. Docker
`backend/Dockerfile` (Phụ lục C): nhiều tầng, `python:3.12-slim-bookworm`, cài phụ thuộc vào `/opt/venv`, người dùng không root (uid 10001), chép `src`, `alembic`, `alembic.ini`, `HEALTHCHECK` gọi `/api/v1/health`, chạy `uvicorn src.main:app`. `.dockerignore` loại `.venv`, `tests`, `__pycache__`, `.env`.

### A10. `docker-compose.yml` và `.env.example`
Compose ở Phụ lục B: `db` (ParadeDB, **không ghi đè `command`**, volume riêng `vsf-onboarding_pgdata` không phải volume ngoài, cổng host 5434), `migrate` (`alembic upgrade head`, chạy một lần), `backend` (cổng 8000, chờ `db` khỏe và `migrate` xong). Tên project `vsf-onboarding`. Cập nhật `.env.example`: `DATABASE_URL` trỏ cổng 5434, thêm `PARADEDB_TAG`, `POSTGRES_HOST_PORT`, `BACKEND_HOST_PORT`, `API_UPSTREAM_URL`.

### A11. Test backend (danh sách ở Phụ lục E)
Đơn vị (không cần DB thật): cấu hình, health, readiness với session giả, route `ready` 200/503. Tích hợp (đánh dấu `integration`, **tự bỏ qua** nếu thiếu `VSF_TEST_DATABASE_URL`): readiness thật, ba extension, ràng buộc `EXCLUDE` chống chồng ngày trên bảng tạm.

## 6. 1a-B — Frontend (hôm nay)

### B1. Gói và cấu hình
`package.json`: tên `vsf-frontend`, `engines.node >= 22`; phụ thuộc chạy: `next 16.3.0`, `react`/`react-dom 19.2.8`, `next-intl ^4.13.7`; dev: `typescript ^5`, `@types/node ^22`, `@types/react ^19`, `@types/react-dom ^19`, `eslint ^9`, `eslint-config-next 16.3.0`, `tailwindcss ^4`, `@tailwindcss/postcss ^4`, `vitest ^4.1.10`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/dom`. **Chưa** thêm `@tanstack/react-query`, `lucide-react`, `gsap`, `sass`, `playwright` (thêm khi dùng). Scripts: `dev`, `build`, `start`, `lint`, `typecheck`, `test`. `package-lock.json` được commit.
`tsconfig.json` (strict, alias `@/*`), `eslint.config.mjs` (core-web-vitals + typescript), `postcss.config.mjs`, `vitest.config.mts` (môi trường `jsdom` mặc định; test của `proxy` dùng `node`), `vitest.setup.ts` (jest-dom).

### B2. `next.config.ts`
`output: "standalone"` (cho image ở 1b); plugin `next-intl`; **`rewrites` `/api/:path*` → `API_UPSTREAM_URL` (mặc định `http://127.0.0.1:8000`) chỉ khi `NODE_ENV !== "production"`** (production do Caddy đảm nhiệm). Chưa nâng `proxyTimeout` hay `proxyClientMaxBodySize` (Ralion cần cho upload; thêm ở Phase 5/8).

### B3. i18n
`src/i18n/routing.ts`: `locales = ["vi"]`, `defaultLocale = "vi"`, `isLocale`, `stripLocale`. `request.ts`: nạp `messages/vi.json`. `navigation.ts`: `Link`, `useRouter`… của next-intl. Chỉ `vi`, cấu trúc sẵn cho `en`.

### B4. `src/proxy.ts`
Chỉ xử lý ngôn ngữ: `/` → `/vi`; `/x` → `/vi/x` (chuyển hướng 307); bỏ qua `/api`, `/_next`, tệp có đuôi. **Chưa có cổng đăng nhập** (Phase 4 thêm, cookie `vsf_session`).

### B5. Trang khung
`app/[locale]/layout.tsx` (là root layout: `<html lang>`, `NextIntlClientProvider`, nhập `globals.css`, `generateStaticParams`); `page.tsx` (tên sản phẩm, nhãn "Bản demo thực tập", liên kết tới `/vi/login`); `login/page.tsx` (trang khung: "Trang đăng nhập sẽ được làm ở Phase 4"). Mọi chuỗi qua `messages/vi.json`.

### B6. Token thiết kế
`app/globals.css`: `@import "tailwindcss"`, khối `:root` theo [system design mục 11.2](../../vsf-onboarding-assistant-system-design.md), ánh xạ sang Tailwind bằng `@theme inline`, token tối cơ bản dưới `:root[data-theme="dark"]`, chuỗi font hệ thống (P5), kiểu nền cơ sở. **Không SCSS, không CSS Modules, không bộ token thứ hai.**

### B7. Test frontend (Phụ lục E)
`routing.test.ts`, `proxy.test.ts` (môi trường `node`), `messages.test.ts` (khóa bắt buộc có mặt, không chuỗi rỗng), `page.test.tsx` (trang chủ hiển thị tên và liên kết đăng nhập).

## 7. 1a-C — CI GitHub Actions (ngày mai)

`.github/workflows/verify.yml` (Phụ lục D), chạy trên `pull_request`, `push` vào `main` và `workflow_call` (để `release.yml` ở 11b gọi lại). Ba job:

| Job | Việc |
|---|---|
| `backend` | Python 3.12, `pip install -r requirements-dev.txt`, `ruff check`, `ruff format --check`, `mypy`, khởi động ParadeDB bằng **service container (không cần `command`)**, đợi kết nối TCP thành công, `alembic upgrade head`, `alembic check`, `pytest` kể cả `integration` (đặt `VSF_TEST_DATABASE_URL`) |
| `frontend` | Node 22, `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` |
| `images` | `docker build` backend; chạy container và `curl /api/v1/health`; (khi có Dockerfile frontend ở 1b: build cả frontend) |

Ghi chú: trong container, `pg_isready` qua socket có thể thấy máy chủ **tạm** lúc khởi tạo (vì vậy Ralion kiểm thêm `postmaster.pid`); kết nối **TCP từ ngoài** chỉ thành công khi máy chủ thật đã chạy (lúc khởi tạo image chỉ lắng nghe socket), nên vòng đợi bằng kết nối TCP đủ chính xác trong CI. Các bước `docker compose` không dùng trong CI ở phase này. Gói Free có 2.000 phút Actions/tháng cho repo private ([GitHub Docs](https://docs.github.com/en/actions/concepts/billing-and-usage)); ước lượng mỗi lần chạy 5–8 phút, cần đo.

## 8. 1b — Khung triển khai (ngày mai, giới hạn cứng 1 ngày)

**Điều kiện cần từ bạn (chưa xong thì 1b không bắt đầu được):** VPS chạy (Oracle Always Free ARM là máy chính, quá khoảng 1 giờ không tạo được thì Hetzner CX23), SSH bằng khóa được, DuckDNS trỏ đúng IP, trang `hello` qua HTTPS đã chạy ([huong-dan-thiet-lap-may-chu.md](../huong-dan-thiet-lap-may-chu.md)). Cần thêm một token GitHub để VPS kéo image riêng tư (`read:packages`), xem D6.

| # | Việc | Chi tiết |
|---|---|---|
| D1 | `scripts/vps/bootstrap.sh` | Chạy một lần trên VPS: cập nhật, `ufw` 22/80/443, người dùng `deploy` (nhóm `docker`), SSH chỉ dùng khóa, Docker (Phụ lục F) |
| D2 | `frontend/Dockerfile` | Nhiều tầng, `output: standalone`, người dùng không root |
| D3 | `deploy/compose.vps.yml` | `caddy`, `frontend`, `backend`, `db`, `migrate`; **chỉ Caddy publish cổng**; image tham chiếu bằng biến/digest; mật khẩu DB riêng của VPS (không phải `vsf:vsf`) |
| D4 | `deploy/Caddyfile` | `/api/*` → backend, còn lại → frontend, **một origin**; chặn `/api/v1/ready*` từ ngoài (404); HSTS và header bảo mật cơ bản; HTTPS tự động cho `<tên>.duckdns.org` |
| D5 | `scripts/vps/deploy.sh`, `smoke-test.sh` | `deploy.sh`: `flock`, kéo image, chờ DB, `migrate`, khởi động, chờ `/api/v1/ready` **nội bộ**, gọi smoke test. `smoke-test.sh`: kiểm công khai theo hợp đồng route |
| D6 | Đẩy image lên GHCR | Workflow `publish-images.yml` chạy thủ công (`workflow_dispatch`) bằng `GITHUB_TOKEN`, ghi digest; VPS đăng nhập GHCR bằng token `read:packages` chỉ trong lúc kéo rồi `docker logout` |
| D7 | Bí mật trên VPS | `/opt/vsf/env/compose.env` và `backend.env` tạo tay (không qua GitHub, không vào repo); mật khẩu DB ngẫu nhiên |
| D8 | Deploy tay lần đầu | Chạy `deploy.sh`, rồi `smoke-test.sh` từ **máy khác** |
| D9 | Kiểm ba extension trên VPS | Trong DB tạm: `CREATE EXTENSION` cho `btree_gist` và thử ràng buộc `EXCLUDE` như đã làm cục bộ |

**Nếu máy là Oracle (ARM).** (a) D6 build ảnh đa kiến trúc `linux/amd64` + `linux/arm64` (buildx/QEMU, đo thời gian); (b) D1 mở 80/443 (TCP) và 443 (UDP) ở cả Security List lẫn `iptables` trong máy, người dùng mặc định là `ubuntu`; (c) D9 kiểm ParadeDB chạy được trên arm64 (image có manifest arm64); (d) ghi RAM thực đo bằng `docker stats` để chỉnh cấu hình (giữ mức dùng bộ nhớ không quá thấp, tránh bị coi là nhàn rỗi và thu hồi); (e) tạo máy Oracle quá khoảng 1 giờ không được thì dùng Hetzner, không tính vào giới hạn 1 ngày của 1b. Chi tiết ở [phụ lục](../phu-luc-may-chu-va-chi-phi.md) và [hướng dẫn](../huong-dan-thiet-lap-may-chu.md) mục 3A.

**Giới hạn cứng:** nếu quá 1 ngày, dừng, ghi nguyên nhân (DNS, chứng chỉ, extension, RAM, kéo image) vào nhật ký, tiếp tục Phase 2 cục bộ và dời deploy thủ công sang Phase 11a.

**Không làm ở 1b:** tự động deploy (11b), rollback tự động, backup định kỳ, giám sát.

## 9. Kiểm chứng và cổng hoàn thành

### 9.1 Cổng 1a-A (hôm nay, backend)
- [ ] `ruff check`, `ruff format --check`, `mypy` (strict) không lỗi.
- [ ] `pytest` (đơn vị) xanh; test tích hợp xanh khi đặt `VSF_TEST_DATABASE_URL` trỏ compose DB.
- [ ] `docker compose config` hợp lệ; `docker compose up -d --build`: `db` khỏe, `migrate` thoát mã 0, `backend` khỏe.
- [ ] `curl http://localhost:8000/api/v1/health` → `200 {"status":"ok"}`; `/api/v1/ready` → `200 ready` (database ok, ba extension có sẵn, migration "chưa có").
- [ ] `curl http://localhost:8000/health` → `404` (không có route gốc).
- [ ] Dừng `db` rồi gọi `/api/v1/ready` → `503`, nội dung **không** chứa chuỗi kết nối hay mật khẩu.
- [ ] `alembic upgrade head` và `alembic check` chạy được, không làm gì.
- [ ] `docker compose down` không xóa dữ liệu mặc định; volume có tên riêng, không đụng volume của Ralion.

### 9.2 Cổng 1a-B (hôm nay, frontend)
- [ ] `npm run lint`, `npm run typecheck`, `npm test` xanh.
- [ ] `npm run build` xong, có `.next/standalone`.
- [ ] `npm run start` (hoặc `dev`): `/` → 307 tới `/vi`; `/vi` → 200; `/vi/login` → 200; `/x` → 307 tới `/vi/x`.
- [ ] Ở chế độ dev, `/api/v1/health` qua Next (rewrite) trả `ok` khi backend đang chạy.
- [ ] Không còn chuỗi giao diện viết cứng trong component (đều từ `vi.json`).

### 9.3 Cổng 1a-C (ngày mai, CI)
- [ ] PR đầu tiên: ba job `backend`, `frontend`, `images` xanh trên GitHub.
- [ ] Cố ý làm hỏng một test rồi xác nhận CI **đỏ**, sửa lại thì xanh.
- [ ] Tổng thời gian một lần chạy được ghi lại (để tính hạn mức 2.000 phút).

### 9.4 Cổng 1b (ngày mai, triển khai)
- [ ] Từ **máy khác**: `https://<host>/api/v1/health` = 200 `ok`; `https://<host>/vi/login` = 200; `https://<host>/` chuyển hướng tới `/vi`; `https://<host>/api/v1/ready` = **404**.
- [ ] Trên VPS: `/api/v1/ready` **nội bộ** = 200; ba extension tạo được; ràng buộc `EXCLUDE` từ chối bản chồng ngày.
- [ ] Không có bí mật trong repo, trong lớp image (`docker history`), hay trong log deploy.
- [ ] `docker stats` trên VPS ghi lại RAM khi rảnh (ghi vào nhật ký, cho quyết định nâng gói nếu cần).

## 10. Điểm dừng để bạn duyệt

| Điểm | Khi nào | Bạn xác nhận |
|---|---|---|
| **CP1** | Bây giờ | Duyệt kế hoạch và quyết định P1–P10 |
| **CP2** | Sau 1a-A (backend chạy trong compose) | Xem kết quả cổng 9.1 |
| **CP3** | Sau 1a-B (frontend) | Xem kết quả cổng 9.2; đồng ý commit vào nhánh `phase-1a-skeleton` (cục bộ) |
| **CP4** | Ngày mai, trước khi đẩy nhánh và mở PR | Đồng ý đẩy (hành động ra ngoài) |
| **CP5** | Sau khi CI xanh | Đồng ý merge PR; đồng ý bắt đầu 1b |
| **CP6** | Trước khi chạy lệnh trên VPS | Xác nhận VPS sẵn sàng, tôi chỉ chạy lệnh khi bạn đưa thông tin/đồng ý |

Ở mỗi điểm dừng tôi không làm bước kế tiếp cho tới khi bạn nói.

## 11. Rủi ro và cách xử lý

| # | Rủi ro | Xử lý |
|---|---|---|
| R1 | Ghi đè `command` của image làm DB không khởi động | Không ghi đè; có test tích hợp và cổng 9.1 bắt lỗi này |
| R2 | Cổng 8000 trùng Ralion nếu chạy cả hai | `BACKEND_HOST_PORT`; ghi rõ trong README |
| R3 | Vòng lặp sự kiện của `asyncpg`/Alembic trên Windows | Giữ `WindowsSelectorEventLoopPolicy` trong `env.py` (như Ralion) |
| R4 | `alembic` lỗi khi thư mục `versions/` không có trong git | `alembic/versions/README.md` thay `.gitkeep`; kiểm bằng clone thử |
| R5 | `/ready` lộ thông tin nội bộ | Chỉ tên loại lỗi, không chuỗi kết nối; Caddy chặn từ ngoài ở 1b |
| R6 | `mypy` strict gây nhiều lỗi với SQLAlchemy async | Dùng kiểu `Mapped`; chỉ nới cục bộ có ghi chú, không tắt toàn cục |
| R7 | CI: ParadeDB service chưa sẵn sàng khi test chạy | Vòng đợi kết nối TCP có thời hạn; nếu chập chờn thì dùng `docker run` trong bước riêng |
| R8 | Image ParadeDB nặng (1,39 GB) làm CI/kéo về VPS chậm | Chấp nhận cho khung; ghi thời gian thật; disk VPS 40 GB đủ |
| R9 | Phụ thuộc Python không được khóa, image build lệch theo thời gian | Cận trên trong `requirements`; khóa phiên bản ở 1b (P3) |
| R10 | Xuống dòng CRLF/LF lệch trên Windows | `.gitattributes` đã đặt LF; cảnh báo `git add` là bình thường |
| R11 | Token GHCR nằm lại trên VPS | Đăng nhập chỉ lúc kéo, rồi `docker logout` (theo [deployment-ci mục 6](../../vsf-onboarding-assistant-deployment-ci.md)) |
| R12 | Quá 1 ngày ở 1b | Giới hạn cứng và đường lui ở mục 8 |
| R13 | Khóa Ralion lẫn vào repo | Phase 1 không cần khóa LLM/embedding; `.env` bị `.gitignore`; quét bí mật trước mỗi commit |

## 12. Cập nhật tài liệu sau khi xong (thuộc Phase 1)

- [database-design mục 6, câu hỏi mở số 7](../../vsf-onboarding-assistant-database-design.md): ghi kết quả đã kiểm (`btree_gist` có sẵn, `EXCLUDE` chạy đúng trên `v0.25.4-pg16`).
- [deployment-ci](../../vsf-onboarding-assistant-deployment-ci.md): ghi chú "không ghi đè `command` của image ParadeDB; CI dùng được service container".
- `README.md` gốc: mục "Chạy cục bộ" (lệnh `docker compose`, cổng, biến môi trường, chạy test).
- [master-plan.md](../master-plan.md): đánh dấu Phase 1a/1b đã xong kèm ngày công thật.
- Nhật ký ngắn của Phase 1 (giờ công thật, số liệu CI/RAM) làm dữ liệu hiệu chỉnh lịch **sau Phase 2**.

## 13. Bàn giao cho Phase 2

Phase 2 bắt đầu từ: backend có `Settings`, engine/session, `ReadinessService`, Alembic trống, compose chạy; frontend có i18n và token; CI xanh; VPS chạy `/api/v1/health`. Phase 2 viết `0001_core` đầy đủ (extension, `users`, `teams`, `team_members`, bảng tài liệu, `jobs`, `audit_logs`), khi đó `/ready` **tự siết** sang kiểm "đã cài" và phiên bản migration.

---

## Phụ lục A — Hợp đồng `health` và `ready`

```json
GET /api/v1/health          → 200 {"status": "ok"}

GET /api/v1/ready           → 200
{
  "status": "ready",
  "checks": {
    "database":   {"ok": true},
    "migration":  {"ok": true, "head": null, "current": null, "note": "chưa có migration"},
    "extensions": {"ok": true, "available": ["btree_gist", "pg_search", "vector"], "installed": ["pg_search", "vector"], "missing": []}
  }
}

GET /api/v1/ready (DB tắt) → 503
{"status": "not_ready", "checks": {"database": {"ok": false, "error": "ConnectionRefusedError"}, "migration": {"ok": false}, "extensions": {"ok": false}}}
```

## Phụ lục B — `docker-compose.yml` dự kiến

```yaml
name: ${COMPOSE_PROJECT_NAME:-vsf-onboarding}

services:
  db:
    # PostgreSQL 16 + pgvector + ParadeDB pg_search. KHÔNG ghi đè `command`: lệnh mặc định của image đã nạp
    # pg_search,pg_cron,pg_stat_statements; ghi đè thiếu pg_cron làm script khởi tạo của image lỗi.
    image: paradedb/paradedb:${PARADEDB_TAG:-v0.25.4-pg16}
    restart: unless-stopped
    environment:
      POSTGRES_USER: vsf
      POSTGRES_PASSWORD: vsf          # chỉ cho dev; VPS dùng mật khẩu riêng trong env file
      POSTGRES_DB: vsf
    ports:
      - "${POSTGRES_HOST_PORT:-5434}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      # Máy chủ tạm lúc khởi tạo cũng trả lời pg_isready qua socket; postmaster.pid = 1 xác nhận máy chủ thật.
      test:
        - CMD-SHELL
        - >-
          test "$$(head -n 1 /var/lib/postgresql/data/postmaster.pid)" = "1" &&
          pg_isready -U vsf -d vsf
      interval: 5s
      timeout: 5s
      retries: 20

  migrate:
    build: ./backend
    command: ["alembic", "upgrade", "head"]
    environment:
      DATABASE_URL: postgresql+asyncpg://vsf:vsf@db:5432/vsf
    depends_on:
      db:
        condition: service_healthy
    restart: "no"

  backend:
    build: ./backend
    ports:
      - "${BACKEND_HOST_PORT:-8000}:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://vsf:vsf@db:5432/vsf
    depends_on:
      db:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
    init: true
    restart: unless-stopped

volumes:
  pgdata:
    name: ${POSTGRES_DATA_VOLUME:-vsf-onboarding_pgdata}
```

## Phụ lục C — `backend/Dockerfile` dự kiến

```dockerfile
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=builder /opt/venv /opt/venv
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser alembic ./alembic
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Phụ lục D — `.github/workflows/verify.yml` dự kiến

```yaml
name: verify
on:
  pull_request:
  push:
    branches: [main]
  workflow_call:
permissions:
  contents: read
jobs:
  backend:
    runs-on: ubuntu-24.04
    services:
      db:
        image: paradedb/paradedb:v0.25.4-pg16       # đồng bộ với PARADEDB_TAG
        env: { POSTGRES_USER: vsf, POSTGRES_PASSWORD: vsf, POSTGRES_DB: vsf }
        ports: ["5432:5432"]
    defaults: { run: { working-directory: backend } }
    env:
      DATABASE_URL: postgresql+asyncpg://vsf:vsf@localhost:5432/vsf
      VSF_TEST_DATABASE_URL: postgresql+asyncpg://vsf:vsf@localhost:5432/vsf
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip, cache-dependency-path: backend/requirements-dev.txt }
      - run: pip install -r requirements-dev.txt
      - run: ruff check . && ruff format --check .
      - run: mypy
      - name: Đợi ParadeDB (kết nối TCP)
        run: |
          for i in $(seq 1 60); do (echo > /dev/tcp/localhost/5432) 2>/dev/null && break; sleep 2; done
      - run: alembic upgrade head && alembic check
      - run: pytest
  frontend:
    runs-on: ubuntu-24.04
    defaults: { run: { working-directory: frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - run: npm run lint && npm run typecheck && npm test
      - run: npm run build
  images:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t vsf-backend:ci backend
      - run: |
          docker run -d --name be -p 8000:8000 vsf-backend:ci
          for i in $(seq 1 30); do curl -fsS localhost:8000/api/v1/health && break; sleep 1; done
```

(Phiên bản action và cú pháp sẽ đối chiếu lại khi viết thật; ghim theo tag chính, cân nhắc ghim theo SHA.)

## Phụ lục E — Danh sách test dự kiến

**Backend (đơn vị):**
- `test_config`: giá trị mặc định; múi giờ sai bị từ chối; biến môi trường ghi đè được.
- `test_api/test_health_router`: `/api/v1/health` = 200 `{"status":"ok"}`; có header `X-Request-ID`; ID của client được trả lại; `/health` gốc = 404.
- `test_api/test_ready_route`: khi service báo sẵn sàng = 200; khi không = 503 (ghi đè dependency).
- `test_services/test_readiness_service` (session giả): mọi thứ tốt → ready; `execute` ném lỗi → không ready và **không lộ nội dung lỗi**; thiếu extension → không ready; chưa có migration → bỏ qua yêu cầu "đã cài"; có head mà `alembic_version` lệch hoặc thiếu bảng → không ready.

**Backend (tích hợp, cần `VSF_TEST_DATABASE_URL`, tự bỏ qua nếu thiếu):**
- `readiness` thật trả ready; `btree_gist`, `pg_search`, `vector` có sẵn; trong schema tạm: tạo bảng có `EXCLUDE USING gist` và xác nhận **từ chối** bản chồng ngày, **chấp nhận** bản không chồng hoặc không `ACTIVE`; dọn schema tạm sau test.

**Frontend:**
- `i18n/routing.test`: mặc định `vi`; `isLocale`; `stripLocale`.
- `proxy.test` (môi trường `node`): `/` → 307 tới `/vi`; `/login` → `/vi/login`; `/vi/login` đi tiếp; `matcher` không khớp `/api/...`.
- `messages.test`: các khóa bắt buộc có mặt, không chuỗi rỗng.
- `app/[locale]/page.test`: hiển thị tên sản phẩm, nhãn "Bản demo thực tập" và liên kết tới `/vi/login`.

## Phụ lục F — Phác thảo tệp của 1b

- `scripts/vps/bootstrap.sh`: `set -euo pipefail`; `apt-get update && upgrade`; `ufw allow 22/80/443` và bật; swap 2 GB; tạo người dùng `deploy` và chép `authorized_keys`; cài Docker theo apt repository chính thức, thêm `deploy` vào nhóm `docker`; tắt đăng nhập root và mật khẩu SSH **sau khi** xác nhận đăng nhập bằng `deploy` (bước thủ công, không tự động để khỏi tự khóa mình).
- `deploy/compose.vps.yml`: `caddy` (publish 80/443, `caddy_data`), `frontend`, `backend`, `db` (không publish cổng), `migrate`; mạng `private`; `env_file` trỏ `/opt/vsf/env/*.env`.
- `deploy/Caddyfile`: `{$PUBLIC_HOST} { @ready path /api/v1/ready* ; respond @ready 404 ; handle /api/* { reverse_proxy backend:8000 } ; handle { reverse_proxy frontend:3000 } ; header { Strict-Transport-Security … } }`.
- `scripts/vps/deploy.sh`: `flock`; đăng nhập GHCR; `docker compose pull`; khởi động `db` và chờ khỏe; `migrate`; khởi động phần còn lại; chờ `/api/v1/ready` nội bộ tối đa 30 lần; gọi `smoke-test.sh`; `docker logout`.
- `scripts/vps/smoke-test.sh`: `curl` theo hợp đồng route (health 200, `auth/me` sẽ là 401 từ Phase 4, `/vi/login` 200, `/` chuyển hướng, `ready` ngoài = 404).
