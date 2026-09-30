# Báo cáo — Upload tài liệu + AI đề xuất task + tải file gốc (P4B mục 8)

> Theo đúng plan đã duyệt ở [P4B.md §8](P4B.md#8-chi-tiết-kỹ-thuật--làm-trước-upload--ai-đề-xuất-task), làm trước phần upload + AI (item 3+4), cộng bổ sung tải file gốc theo yêu cầu giữa phiên.

## 1. Đã làm gì

### API mới (`backend/src/api/routers/portal_router.py`)
| Route | Việc |
|---|---|
| `POST /api/v1/portal/journey-templates` | HR tạo JourneyTemplate (DRAFT) |
| `POST /api/v1/portal/journey-templates/{id}/stages` | Thêm JourneyStage |
| `POST /api/v1/portal/documents` | Upload file (multipart) → `ingest_document()` có sẵn |
| `GET /api/v1/portal/documents/{version_id}/original` | Tải/mở file gốc (Cloudinary: redirect tới `secure_url`; local: trả file trên đĩa) |
| `POST /api/v1/portal/ai/task-proposals` | AI đề xuất task từ 1 document_version, chưa lưu DB |
| `POST /api/v1/portal/stages/{id}/tasks/from-proposal` | HR chấp nhận 1 đề xuất → tạo TaskTemplate + TaskSourceMapping |

### Service mới
- `services/portal/template_service.py` — `create_journey_template`, `add_stage`, `get_journey_template`.
- `services/portal/ingest_bridge.py` — `ingest_uploaded_document()` (wrapper `ingest_document()` cho `UploadFile`), `resolve_original_document()` (tra `storage_key` theo `storage_provider`).
- `services/portal/ai_task_service.py` — `propose_tasks()` (gọi LLM, validate `source_chunks` đúng version + quote khớp nguyên văn), `load_stage_and_template()`, `create_task_from_proposal()`.

### DTO
- `dto/request/portal_request_dto.py` (mới): 5 request DTO.
- `dto/response/portal_response_dto.py` (mở rộng): +6 response DTO, đổi `AiTaskSourceChunkDTO` → `AiTaskSourceChunkResponseDTO` (đúng convention `test_dto_layout.py`).

### Dependency mới
`get_storage_port` trong `dependencies.py` (dùng `LocalStorageAdapter` mặc định dev/test).

## 2. Phát hiện & sửa trong lúc làm

| Vấn đề | Sửa |
|---|---|
| `response_model=None` và `response_model=list[X]` bị test `test_dto_layout.py` chặn (regex quy ước chỉ hiểu tên class đơn) | Route trả file: đổi return type thành `Response` (base class) — FastAPI tự bỏ qua model, không cần `response_model=None`. Route trả list: bỏ `response_model=` dư (đã có return type annotation `-> list[...]`, FastAPI vẫn hoạt động đúng) |
| `AiTaskSourceChunkDTO` không kết thúc bằng `ResponseDTO` | Đổi tên `AiTaskSourceChunkResponseDTO` |
| Thiếu `python-multipart` — FastAPI cần cho `File()`/`Form()` | Thêm vào `requirements.txt`, cài vào venv local |
| **Build lại Docker image bị lỗi `ModuleNotFoundError: greenlet`** — SQLAlchemy asyncio cần `greenlet` nhưng chưa từng khai rõ trong `requirements.txt` (trước đó được kéo vào gián tiếp qua resolver, image cũ "may mắn" có sẵn) | Thêm `greenlet>=3.0,<4` vào `requirements.txt` — sửa 1 lỗ hổng dependency thật, không chỉ vá cho qua |
| Test teardown: xóa `users` trước khi xóa `audit_logs` liên quan (do `ingest_document()` ghi audit log với `actor_id`) → FK RESTRICT chặn | Sửa fixture: xóa `AuditLog` theo `actor_id` trước khi xóa `User`, ở cả 2 file test mới |

## 3. Kiểm tra đã chạy

| Bước | Kết quả |
|---|---|
| `ruff format` + `ruff check` (toàn bộ `src/`, `tests/`) | Sạch |
| `mypy src/ tests/` (131 file) | `Success: no issues found` |
| Test tích hợp mới — `test_portal_document_upload_api.py` (3 test) | Pass: HR upload thành công, role USER bị 403, upload lại cùng nội dung idempotent |
| Test tích hợp mới — `test_portal_ai_task_proposal_api.py` (5 test) | Pass: JSON hợp lệ → đề xuất đúng (không có `completion_mode`); section sai version → bị loại; quote sai → bị loại; accept → tạo đúng TaskTemplate + TaskSourceMapping; accept vào template đã publish → 409 |
| Toàn bộ test suite backend | **188 pass, 8 fail** — 8 fail là tồn tại từ trước (dữ liệu `document_categories` có sẵn trong DB dev + lỗi encoding Windows cục bộ ở `test_parser.py`), đã xác nhận lại từ báo cáo P1, không liên quan thay đổi lần này |
| Docker rebuild (`docker compose build backend migrate`) | Build thành công sau khi thêm `greenlet` |
| Docker migration (`docker compose run --rm migrate alembic current`) | `0002 (head)` |
| Docker backend chạy code mới | Container `healthy`; `/api/v1/health` → `ok`; `/api/v1/portal/me`, `/portal/documents`, `/portal/ai/task-proposals` qua HTTP thật → đúng `401` (chưa đăng nhập, route đã đăng ký) |

## 4. Chưa làm (để lại lượt sau)

- Chưa làm `POST /journey-templates/{id}/publish`, `POST /tasks/{id}/dependencies` (item 2 — CRUD thủ công đầy đủ) — user chọn ưu tiên upload+AI trước; test "accept vào template đã publish" hiện giả lập bằng cách flip status trực tiếp qua SQL, chưa qua API publish thật.
- Chưa validate dependency vòng lúc publish (theo scope P4B mục 1 "Không có").
- Chưa test với Cloudinary thật (chỉ test `LocalStorageAdapter`) — `resolve_original_document()` nhánh Cloudinary chưa có test tích hợp thật (cần khóa Cloudinary thật để test, ngoài phạm vi hiện tại).
- Seed data thật (newhire vào phòng ban) — vẫn nằm trong mục 2.1 của P4B.md gốc, chưa làm ở lượt này.
