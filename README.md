# VSF Onboarding Assistant

Trợ lý onboarding cho nhân sự mới: trả lời **từ tài liệu đã được duyệt, có trích dẫn nguồn**, chỉ đúng quy trình, đúng đầu mối và biểu mẫu; khi thiếu căn cứ thì nói thẳng là chưa có thay vì đoán.

> **Trạng thái:** Phase 0 xong; Phase 1a đã có khung backend (FastAPI + PostgreSQL/ParadeDB) và frontend (Next.js) chạy cục bộ; đã có CI (`verify.yml`) và khung triển khai VPS (`deploy/`, `scripts/vps/`, chạy thử cục bộ; chưa chạy trên máy chủ thật). **Bản demo thực tập, chưa phải sản phẩm chính thức.** Chưa có tính năng nghiệp vụ nào (Phase 2 trở đi).

## Tài liệu

Toàn bộ nằm trong [docs/chatbot-vsf/](docs/chatbot-vsf/). Đọc theo thứ tự:

| Tài liệu | Vai trò |
|---|---|
| [PRD chuẩn](docs/chatbot-vsf/vsf-onboarding-assistant-prd.md) | Yêu cầu, chỉ số mục tiêu, tiêu chí hoàn thành |
| [Thiết kế hệ thống](docs/chatbot-vsf/vsf-onboarding-assistant-system-design.md) | Kiến trúc, pipeline, API, hợp đồng route, frontend |
| [Thiết kế cơ sở dữ liệu](docs/chatbot-vsf/vsf-onboarding-assistant-database-design.md) | Bảng, ràng buộc, migration |
| [Triển khai và CI](docs/chatbot-vsf/vsf-onboarding-assistant-deployment-ci.md) | VPS, Compose, Caddy, GitHub Actions |
| [Kế hoạch](docs/chatbot-vsf/plan/README.md) | Phase 0–12, timebox 4 tuần, bắt buộc/stretch |
| [Bộ dữ liệu test](docs/chatbot-vsf/data/README.md) | 45 tệp PDF/DOCX giả lập, registry, 242 câu vàng |

**Chuẩn và lưu trữ.** Chỉ các tài liệu ở bảng trên là chuẩn. Hai tệp trong [docs/chatbot-vsf/archive/](docs/chatbot-vsf/archive/) (`prd-v2.md`, `prd.docx`) chỉ để tra cứu lịch sử, **không dùng làm yêu cầu**. Khi mâu thuẫn, PRD chuẩn thắng.

## Dữ liệu là giả lập

Mọi tài liệu `SYN_*` và `PUBSUM_*` trong bộ seed là **dữ liệu giả lập** (nhãn `SYNTHETIC` ở chân trang), dùng để kiểm chứng kỹ thuật. Chúng **không** phải chính sách hay quy trình thật của VSF và không chứng minh bot đúng với quy trình thật.

## Chạy cục bộ (backend và frontend)

Cần Docker Desktop đang chạy, Python 3.12 và Node 22.

```powershell
# 1) PostgreSQL (ParadeDB) + migration + backend
docker compose up -d --build
curl http://localhost:8000/api/v1/health     # {"status":"ok"}
curl http://localhost:8000/api/v1/ready      # kiểm DB, migration, ba extension

# 2) Frontend (chạy trên máy, Next dev tự chuyển /api/* sang backend)
cd frontend
npm install
npm run dev                                  # http://127.0.0.1:3000 (/ chuyển tới /vi)
```

| Dịch vụ | Cổng máy bạn | Đổi bằng |
|---|---|---|
| PostgreSQL (ParadeDB) | 5434 | `POSTGRES_HOST_PORT` |
| Backend | 8000 | `BACKEND_HOST_PORT` |
| Frontend (dev) | 3000 | `next dev --port` |

### Đăng nhập thử (dữ liệu dev)

```powershell
cd backend
.\.venv\Scripts\python -m src.cli.seed_users   # nạp 4 đội và 9 người dùng dev (chạy lại không nhân đôi; từ chối ở production)
```

Mở `http://localhost:3000` hoặc `http://127.0.0.1:3000` rồi đăng nhập, ví dụ `it.staff@vsf-demo.example` (nhân sự mới, vào `/vi/chat`) hoặc `hr1@vsf-demo.example` (HR, vào `/vi/admin`), mật khẩu dev `ChangeMe!123`. Sau khi sửa backend, chạy lại `docker compose up -d --build backend` để cổng 8000 có `/api/v1/auth/*`.

Dự án dùng tên project, volume và cổng DB riêng (`vsf-onboarding`, `vsf-onboarding_pgdata`, 5434), nên chạy được cùng lúc với Ralion; chỉ cổng backend 8000 trùng, hãy đặt `BACKEND_HOST_PORT` nếu chạy cả hai. `docker compose down` giữ dữ liệu; `docker compose down -v` **xóa** volume.

**Không ghi đè `command` của image ParadeDB** trong compose: lệnh mặc định đã nạp `pg_search` và `pg_cron`; ghi đè thiếu `pg_cron` làm image không khởi động.

### Kiểm thử

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m mypy
$env:VSF_TEST_DATABASE_URL = "postgresql+asyncpg://vsf:vsf@localhost:5434/vsf"   # bỏ dòng này thì test tích hợp tự bỏ qua
.\.venv\Scripts\python -m pytest

# Frontend
cd ..\frontend
npm run lint; npm run typecheck; npm test; npm run build
```

## Kiểm tra bộ dữ liệu

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r docs\chatbot-vsf\data\tools\requirements.txt
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python docs\chatbot-vsf\data\tools\validate_seed.py
```

- Thư mục `data/documents/real_public/` (PDF luật công khai) **không được commit**; validator coi nó là tùy chọn.
- **Chỉ chạy `generate_seed.py` trên máy có `real_public/`.** Trên máy thiếu nó, script bỏ các dòng `real_public` khỏi manifest và làm manifest bị đổi.

## Cấu hình

Sao chép `.env.example` thành `.env` và điền giá trị. **Không bao giờ commit `.env`** hay khóa API vào repo. Mật khẩu `ChangeMe!123` trong dữ liệu seed chỉ là mật khẩu dev.

## Đóng góp

Mỗi phase là một hoặc vài PR nhỏ; dùng [mẫu PR](.github/pull_request_template.md). Không sửa migration đã áp dụng. Bảo vệ nhánh `main`: *(chưa cấu hình; cập nhật sau khi kiểm tính năng của gói GitHub — nếu gói không hỗ trợ thì giữ quy ước "không commit thẳng `main`" bằng tay)*.
