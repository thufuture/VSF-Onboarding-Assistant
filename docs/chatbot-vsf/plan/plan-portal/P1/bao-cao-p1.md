# Báo cáo P1 — Data model + migration + RBAC/scope nền tảng

> Thực hiện theo kế hoạch ở [P1.md](P1.md). Đã code, chạy migration thật và kiểm bằng test tích hợp trên PostgreSQL/ParadeDB thật qua Docker — không chỉ viết tài liệu.

## 1. Đã làm gì

### 1.1 Enum mới (`backend/src/model/enums.py`)
Thêm 4 `StrEnum` theo đúng convention `check_in()` (VARCHAR + CHECK, không dùng Postgres native ENUM):
- `JourneyTemplateStatus` (DRAFT, PUBLISHED)
- `EmployeeTaskStatus` (LOCKED, READY, IN_PROGRESS, WAITING_EXTERNAL, BLOCKED, DONE, SKIPPED — **đã bỏ** `NOT_APPLICABLE` và `WAITING_APPROVAL` theo quyết định P0A D1/D4)
- `ReferenceStatus` (DRAFT, APPROVED — dùng chung cho contact_channels/approved_links)
- `TicketStatus` (OPEN, IN_PROGRESS, RESOLVED, CLOSED)

### 1.2 Model mới (`backend/src/model/`, 11 file)
`journey_template.py`, `journey_stage.py`, `task_template.py`, `task_dependency.py`, `employee_journey.py`, `employee_task.py`, `task_source_mapping.py`, `contact_channel.py`, `approved_link.py`, `ticket.py`, `ticket_message.py`, `content_gap.py`. Mỗi file có docstring trỏ ngược về đúng quyết định P0A liên quan (D1, D4, D5, D6, D8, D9, D10) để sau này đọc code hiểu ngay lý do.

Đăng ký đầy đủ vào `model/__init__.py` (từ 12 lên 23 entity trong `Base.metadata`).

### 1.3 Migration (`backend/alembic/versions/0002_portal_core.py`)
Sinh bằng `alembic revision --autogenerate` (không viết tay để tránh lệch với model), rồi đổi tên/revision id cho khớp văn phong `0001_core.py`. Tạo 10 bảng mới, toàn bộ FK/index dùng đúng `NAMING_CONVENTION` sẵn có.

### 1.4 RBAC/scope (`backend/src/api/dependencies.py`)
Thêm `require_team_scope(team_id, user, db)`: HR phải có dòng khớp trong `team_members` (bảng **có sẵn từ trước**, không tạo mới) mới qua được; `ADMIN` luôn qua. Tái dùng `require_role()` đã có, không viết lại.

### 1.5 Router mẫu (`backend/src/api/routers/portal_router.py`, đăng ký trong `main.py`)
`GET /api/v1/portal/journeys` (chặn role + team scope) và `GET /api/v1/portal/me` (mọi role đăng nhập) — khung để P2 trở đi thêm route nghiệp vụ thật lên trên, không cần dựng lại RBAC.

### 1.6 Test tích hợp (`backend/tests/integration/test_portal_api.py`, 5 test)
Test qua HTTP thật (không mock), dùng `httpx.ASGITransport` + PostgreSQL thật: role `USER` bị chặn (403 `FORBIDDEN_ROLE`), HR đúng team qua được (200), HR khác team bị chặn (403 `FORBIDDEN_TEAM_SCOPE`), `ADMIN` luôn qua dù khác team, `/portal/me` mọi role đều gọi được.

## 2. Đã sửa gì so với kế hoạch trước đó

Khi bắt tay viết P1 mới đọc kỹ code backend thật và phát hiện 2 giả định sai ở `ke-hoach-trien-khai-portal.md`/`P0A.md` (đã tự sửa lại 2 file đó luôn, không chờ hỏi vì là sai lệch với sự thật code, không phải quyết định nghiệp vụ):

| Giả định cũ | Thực tế | Đã sửa |
|---|---|---|
| Thêm role `EMPLOYEE` mới | `users.role` đã có sẵn `USER`/`HR`/`ADMIN` | Dùng `USER` cho "nhân viên", không thêm role nào |
| Thêm cột `users.primary_team_id` | Bảng `teams`/`team_members` **đã tồn tại** từ `0001_core.py`, đang dùng ở `auth_service.department_name()` | Không thêm cột nào — `require_team_scope` query thẳng `team_members` |
| Enum viết dạng `ENUM(...)` | Dự án dùng `StrEnum` + `CHECK` qua `check_in()` | Toàn bộ enum Portal viết theo đúng pattern này |

## 3. Kiểm tra đã chạy (không chỉ code xong là xong)

| Bước | Lệnh | Kết quả |
|---|---|---|
| Import model | `python -c "import src.model"` | OK, 22 bảng đăng ký |
| Lint | `ruff check src/model/ src/api/ tests/integration/test_portal_api.py` | Sạch (đã fix 2 lỗi import-sort) |
| Format | `ruff format` | Đã format lại 3 file |
| Type check | `mypy src/` | 91 file, không lỗi |
| Migration thật | `alembic upgrade head` trên PostgreSQL/ParadeDB (Docker) | `0001 → 0002` chạy sạch |
| Round-trip | `alembic downgrade -1` rồi `upgrade head` | Sạch, không lỗi |
| Model khớp DB | `alembic check` | "No new upgrade operations detected" |
| Test tích hợp Portal | `pytest tests/integration/test_portal_api.py` (DB thật) | **5/5 PASS** |
| Toàn bộ test suite backend | `pytest` (188 test) | 180 pass, **8 fail — không liên quan Portal** (xem mục 4) |
| Docker rebuild | `docker compose build backend migrate` | Build thành công |
| Docker chạy migration | `docker compose run --rm migrate alembic current` | `0002 (head)` |
| Docker backend chạy code mới | `docker compose up -d backend` | Container `healthy`, `/api/v1/health` trả `ok` |
| Route Portal qua HTTP thật | `curl /api/v1/portal/journeys`, `/api/v1/portal/me` | `401` (đúng — chưa đăng nhập, route đã đăng ký) |

## 4. 8 test fail — xác nhận không liên quan tới Portal

Không đụng tới `tests/integration/test_core_schema.py` hay `tests/test_ingest/test_parser.py` trong phiên làm việc này. Nguyên nhân:
- **6 fail ở `test_core_schema.py`/`test_ingest_service.py`**: dữ liệu `document_categories` (slug `nghi-phep`, ...) đã tồn tại sẵn trong DB dev từ trước (kiểm bằng `SELECT slug, count(*) FROM document_categories`, ra 12 dòng có sẵn) — các test này insert lại cùng slug và dính `UniqueViolationError`, không phải lỗi do thay đổi ở phiên này.
- **2 fail ở `test_parser.py`**: `UnicodeEncodeError` khi ghi file tạm có dấu tiếng Việt trên Windows (codec `cp1252` mặc định của Python trên máy này) — lỗi môi trường Windows cục bộ, không liên quan schema/code Portal.

## 5. Danh sách file thay đổi

**Mới (14 file):**
```
backend/alembic/versions/0002_portal_core.py
backend/src/api/routers/portal_router.py
backend/src/model/{approved_link,contact_channel,content_gap,employee_journey,
  employee_task,journey_stage,journey_template,task_dependency,
  task_source_mapping,task_template,ticket,ticket_message}.py
backend/tests/integration/test_portal_api.py
```

**Sửa (6 file):**
```
backend/src/api/dependencies.py       (+require_team_scope)
backend/src/main.py                   (đăng ký portal_router)
backend/src/model/__init__.py         (export 11 model mới)
backend/src/model/enums.py            (+4 enum)
docs/.../plan-portal/P0A/P0A.md       (sửa mục 4: bỏ primary_team_id/EMPLOYEE)
docs/.../plan-portal/ke-hoach-trien-khai-portal.md  (sửa mục 3, ghi nhận đã kiểm tra code thật)
```

## 6. Chưa làm ở P1 (để lại cho P2 trở đi)

- Chưa có API nghiệp vụ thật (tạo journey, tạo task, CRUD) — P1 chỉ có 1 route mẫu để chứng minh RBAC.
- Chưa có seed dữ liệu giả lập cho Portal (team/user mẫu) — có thể mở rộng `backend/src/services/auth/seed.py` ở P2/P3 khi cần demo.
- Chưa viết state machine tính `READY`/`LOCKED` từ `task_dependencies` — đó là việc của P2.
- 8 test fail nêu ở mục 4 vẫn tồn tại, không thuộc phạm vi P1, cần dọn riêng khi rảnh (xóa dữ liệu `document_categories` cũ trong DB dev, và chỉnh `test_parser.py` ghi file bằng UTF-8 tường minh trên Windows).
