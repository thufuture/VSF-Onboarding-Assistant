# P4B — Seed data + HR tạo Journey/Task + upload tài liệu (ingest) + AI đề xuất task

> Đổi thứ tự so với [ke-hoach-trien-khai-portal.md §5](../ke-hoach-trien-khai-portal.md) bản gốc: bản gốc tách P4A (tài liệu)/P4B (task thủ công)/P6 (AI) làm 3 phase riêng, sau P2/P3. Theo yêu cầu, **gộp cả 3 vào P4B và làm trước P2/P3**: Employee chỉ hiển thị cái HR tạo ra, nên "core" là HR tạo được nội dung — kể cả nội dung tạo bằng AI từ tài liệu thật — trước khi có nhân viên demo.
> Đã đọc code thật (`backend/src/services/ingest/`, `backend/src/cli/ingest_file.py`, `backend/src/infrastructure/ai/chat_completion_port.py`) trước khi viết — mục 0 ghi lại phát hiện quan trọng làm thay đổi thiết kế.

## 0. Phát hiện quan trọng từ code thật

| Giả định trước | Thực tế | Hệ quả cho P4B |
|---|---|---|
| Ingest "đã có sẵn, chỉ cần gọi" | Ingest **chỉ chạy qua CLI** (`python -m src.cli.ingest_file`), đây là quyết định có chủ đích của chatbot (D4, `docs/chatbot-vsf/plan/phase-2/2-b-nap-tai-lieu-ke-hoach-chi-tiet.md`) — **chưa có API HTTP upload nào**. Portal cần HR tự upload qua web, không chạy CLI hộ → phải viết **API upload mới**, không phải chỉ "gọi lại cái có sẵn" | Thêm 1 route `POST /portal/documents` gọi thẳng hàm `ingest_document()` đã có (không viết lại pipeline parse/chunk/embed) |
| `documents.team_id` sẽ có (đã ghi nhầm ở P0A/P1) | `Document` model có comment rõ **INV9: không có ACL tài liệu theo thiết kế** (cố ý — kho tài liệu dùng chung toàn công ty) | **Không thêm `team_id` vào `documents`**. Tài liệu vẫn dùng chung; scope theo team nằm ở `TaskTemplate.team_id` (task tạo ra từ tài liệu mới bị giới hạn team, không phải tài liệu) |
| AI gọi LLM tự viết code mới | `ChatCompletionPort.complete_json(system_prompt, user_prompt) -> str` đã có sẵn (dùng cho chat), có cả bản giả `FakeChatCompletion` để test không tốn tiền | Tái dùng thẳng port này cho AI đề xuất task, không tạo adapter LLM riêng |

## 1. Phạm vi

**Có:**
1. Bổ sung seed data thật (newhire vào phòng ban).
2. HR tạo Journey/Task **thủ công** qua API (viết tay `body_markdown`).
3. HR **upload tài liệu** qua API (tái dùng `ingest_document()`).
4. HR chọn 1 tài liệu đã upload → **AI đề xuất task** (gọi LLM qua `ChatCompletionPort`, output có citation theo đúng contract [v14 §14](../../portal/dac-ta-tong-the-portal-onboarding-v14.md#14-ai-tạo-task-input-output-và-kiểm-tra), đã bỏ field `completion_mode` vì P0A D1 chỉ còn tự-hoàn-thành) → HR xem/sửa/chấp nhận → tạo `TaskTemplate` **DRAFT** kèm `TaskSourceMapping` trỏ về đúng section đã trích.
5. Publish journey template (DRAFT → PUBLISHED).

**Không có ở P4B (để sau):**
- Validate publish phức tạp (chặn dependency vòng) — để đơn giản: publish chỉ chặn "còn task nào chưa có `body_markdown`", chưa kiểm cycle (thêm sau nếu dữ liệu thật phức tạp hơn).
- `ContactChannel`/`ApprovedLink` DRAFT→APPROVED UI — chưa cần cho luồng AI đề xuất task cơ bản.
- UI React thật — chỉ API, test qua HTTP.
- Đo chất lượng AI (Recall@5...) — theo đúng cảnh báo ở kế hoạch chính, chỉ bật thật sau khi có số liệu.

## 2. Luồng cụ thể

```
HR upload file (POST /portal/documents)
  → ingest_document() có sẵn: parse → chunk → embed → lưu documents/document_versions/document_sections
  → trả document_version_id

HR chọn document_version_id (POST /portal/ai/task-proposals)
  → lấy nội dung section (đã có, dùng lại hybrid_search hoặc đọc thẳng document_sections theo version)
  → gọi ChatCompletionPort.complete_json(system_prompt, user_prompt) — prompt yêu cầu JSON theo schema §14 (đã bỏ completion_mode)
  → parse JSON, validate: title không rỗng, mọi source_chunk thuộc đúng version đã chọn, quote khớp nguyên văn section (giống INV13 kiểm chứng citation ở chat)
  → trả về danh sách đề xuất (chưa lưu DB) cho HR xem

HR duyệt 1 đề xuất (POST /portal/ai/task-proposals/{proposal_ref}/accept, hoặc gửi lại JSON đã sửa)
  → tạo TaskTemplate (DRAFT, thuộc stage HR chỉ định) + TaskSourceMapping trỏ đúng document_version_id/document_section_id đã trích

HR publish journey template như luồng thủ công (mục 3 kế hoạch chính)
```

## 3. API

| Route | Việc | Quyền |
|---|---|---|
| `POST /api/v1/portal/journey-templates` | Tạo `JourneyTemplate` (DRAFT) | `require_role(HR, ADMIN)` |
| `POST /api/v1/portal/journey-templates/{id}/stages` | Thêm `JourneyStage` (template còn DRAFT) | HR cùng team, hoặc ADMIN |
| `POST /api/v1/portal/stages/{id}/tasks` | Thêm `TaskTemplate` thủ công | như trên |
| `POST /api/v1/portal/tasks/{id}/dependencies` | Gắn `TaskDependency` | như trên |
| `POST /api/v1/portal/documents` | Upload file (multipart), gọi `ingest_document()` | `require_role(HR, ADMIN)` — **không giới hạn theo team** (tài liệu dùng chung, mục 0) |
| `POST /api/v1/portal/ai/task-proposals` | Input: `document_version_id`, `stage_id` đích. Gọi LLM, trả **danh sách đề xuất chưa lưu DB** | HR cùng team với `stage_id`, hoặc ADMIN |
| `POST /api/v1/portal/stages/{id}/tasks/from-proposal` | HR gửi lại 1 đề xuất (đã xem/sửa) → tạo `TaskTemplate` DRAFT + `TaskSourceMapping` | như route thêm task thủ công |
| `POST /api/v1/portal/journey-templates/{id}/publish` | DRAFT → PUBLISHED | như trên |

## 4. DTO & Service

- `dto/request/portal_request_dto.py`: thêm `CreateAiTaskProposalRequestDTO` (`document_version_id`, `stage_id`), `AcceptAiTaskProposalRequestDTO` (toàn bộ field đề xuất, HR có thể sửa trước khi gửi lại).
- `dto/response/portal_response_dto.py`: thêm `AiTaskProposalResponseDTO` (title, summary, instructions_markdown, done_criteria, estimated_minutes, prerequisite_keys, source_chunks, confidence, warnings — **không có `completion_mode`**).
- `backend/src/services/portal/ingest_bridge.py` — wrapper mỏng gọi `ingest_document()` có sẵn, không viết lại logic parse/chunk.
- `backend/src/services/portal/ai_task_service.py` — `propose_tasks()` (build prompt, gọi `ChatCompletionPort`, validate output theo §14), `create_task_from_proposal()` (ghi `TaskTemplate` + `TaskSourceMapping`).
- Prompt: hệ thống nhắc rõ "chỉ dùng nội dung được cung cấp, không suy diễn thêm bước không có trong tài liệu, `confidence: LOW` nếu tài liệu không nói rõ cách làm".

## 5. Test tích hợp

- `test_portal_document_upload_api.py`: HR upload 1 file `.md` mẫu → có `document_version_id`; role `USER` upload → 403.
- `test_portal_ai_task_proposal_api.py`: dùng `FakeChatCompletion` (có sẵn, không gọi LLM thật, tất định) trả JSON mẫu hợp lệ → propose ra đúng cấu trúc; JSON có `source_chunks` trỏ ngoài version đã chọn → bị validate chặn, không tạo task; HR accept 1 đề xuất → tạo đúng `TaskTemplate` + `TaskSourceMapping`.
- Giữ nguyên các test đã lên kế hoạch trước (tạo template thủ công, scope, publish) — xem lịch sử mục 3 bản trước.

## 6. Definition of Done

- [ ] Seed data: newhire có team qua `team_members`.
- [ ] HR upload được 1 file thật (`.md`/`.docx`) qua API, ra đúng `document_version_id`, dữ liệu khớp bảng `document_sections`.
- [ ] HR gọi AI đề xuất task (dùng `FakeChatCompletion` trong test) → nhận đề xuất có `source_chunks` hợp lệ.
- [ ] HR accept đề xuất → `TaskTemplate` DRAFT + `TaskSourceMapping` đúng, không tự publish (vẫn cần bước publish riêng — nguyên tắc P0A §3 "AI chỉ đề xuất, HR quyết").
- [ ] JSON có source_chunk sai (ngoài tài liệu đã chọn, hoặc quote không khớp) → bị chặn, có lỗi rõ, không tạo task.
- [ ] Toàn bộ route thủ công (tạo template/stage/task/dependency/publish) vẫn hoạt động như thiết kế cũ.
- [ ] `ruff` + `mypy` sạch; test chạy qua Docker trên PostgreSQL thật.
- [ ] Không có cột `documents.team_id` nào được thêm (đối chiếu mục 0) — nếu thấy trong diff là sai lệch cần sửa lại.

## 7. Sau P4B mới làm P2/P3

Giữ như bản trước: P2 (state machine) dùng dữ liệu do P4B tạo ra qua API thật (thủ công hoặc từ AI đã HR duyệt), không tự chèn thẳng vào DB qua fixture.

## 8. Chi tiết kỹ thuật — làm trước: upload + AI đề xuất task

Đã đọc thêm code thật (`ingest_service.py`, `storage.py`, `factory.py`, `fake_chat_completion.py`, `fake_adapter.py`, `tests/integration/test_ingest_service.py`) để chốt chữ ký hàm chính xác trước khi viết. Thứ tự build: **upload → tạo template/stage tối thiểu (chỉ để có chỗ nhận task) → AI đề xuất → accept**, vì accept cần có sẵn 1 `stage_id` để gắn task vào.

### 8.1 File mới/sửa

```
backend/src/api/dependencies.py           (+get_storage_port — build_storage_port(settings), mẫu giống get_embedding_port)
backend/src/dto/request/portal_request_dto.py   (mới)
backend/src/dto/response/portal_response_dto.py (mở rộng — đã có EmployeeTask/EmployeeJourney từ P2)
backend/src/services/portal/ingest_bridge.py    (mới)
backend/src/services/portal/template_service.py (mới, TỐI THIỂU: create_journey_template + add_stage)
backend/src/services/portal/ai_task_service.py  (mới)
backend/src/api/routers/portal_router.py        (mở rộng)
backend/tests/integration/test_portal_document_upload_api.py    (mới)
backend/tests/integration/test_portal_ai_task_proposal_api.py   (mới)
```

### 8.2 DTO cụ thể

`dto/response/portal_response_dto.py` thêm (giữ nguyên 2 class đã có từ P2):
```python
class JourneyTemplateResponseDTO(BaseModel):
    id: int; code: str; version: int; title: str
    status: Literal["DRAFT", "PUBLISHED"]; team_id: int | None

class JourneyStageResponseDTO(BaseModel):
    id: int; journey_template_id: int; title: str; sort_order: int

class DocumentUploadResponseDTO(BaseModel):
    document_id: int; document_version_id: int
    section_count: int; chunk_count: int
    created: bool  # False = cùng content_checksum đã có sẵn (idempotent)

class AiTaskSourceChunkDTO(BaseModel):
    document_section_id: int; quote: str

class AiTaskProposalResponseDTO(BaseModel):
    # Theo v14 §14, ĐÃ BỎ completion_mode (P0A D1)
    title: str; summary: str; instructions_markdown: str
    done_criteria: list[str]; estimated_minutes: int | None
    source_chunks: list[AiTaskSourceChunkDTO]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]; warnings: list[str]

class TaskTemplateResponseDTO(BaseModel):
    id: int; journey_stage_id: int; title: str; body_markdown: str
    required: bool; team_id: int | None
```

`dto/request/portal_request_dto.py` (mới):
```python
class CreateJourneyTemplateRequestDTO(BaseModel):
    code: str; title: str; description: str | None = None

class CreateJourneyStageRequestDTO(BaseModel):
    title: str; sort_order: int = 0

class CreateAiTaskProposalRequestDTO(BaseModel):
    document_version_id: int

class AcceptAiTaskProposalRequestDTO(BaseModel):
    title: str; instructions_markdown: str; required: bool = True
    source_chunks: list[AiTaskSourceChunkRequestDTO]  # HR có thể bớt chunk trước khi lưu
```

### 8.3 `POST /api/v1/portal/documents` — upload

Nhận `multipart/form-data`: `file: UploadFile`, `title`, `category_slug`, `source_key`, `version_label`, `effective_from` (date). Xử lý:
1. Đọc bytes từ `UploadFile`, ghi ra file tạm (`tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False)`) — `ingest_document()` cần `file_path: Path`, không nhận bytes trực tiếp.
2. Gọi `ingest_document(db, file_path=tmp_path, category_slug=..., owner_email=user.email, title=..., source_key=..., version_label=..., effective_from=..., content_kind=ContentKind.GENERAL.value, confidentiality=Confidentiality.INTERNAL.value, embedding=embedding_port, storage=storage_port)`.
3. Xóa file tạm ở `finally` (kể cả khi lỗi).
4. `IngestError` → bắt và raise `PortalError(422, "INGEST_FAILED", "portal.ingest_failed")` (thông báo lỗi gốc trong log, không lộ chi tiết nội bộ ra response — theo mẫu `AuthError`/`PortalError` hiện có).
5. Quyền: `require_role(HR, ADMIN)`, **không kiểm team** (mục 0: tài liệu dùng chung).
6. `category_slug` dùng tạm `"onboarding-ngay-dau"` cho việc test file day1 — cần xác nhận danh mục này đã có trong `document_categories` (seed hoặc tạo mới nếu chưa, xem `docs/chatbot-vsf/data/registry/document_categories.json`).

### 8.4 `POST /api/v1/portal/ai/task-proposals` — đề xuất

1. Input: `document_version_id`.
2. Đọc toàn bộ `DocumentSection` của version đó (`SELECT ... WHERE version_id = ? ORDER BY section_index`) — không dùng `hybrid_search` (đó là tìm kiếm theo câu hỏi, ở đây đã biết đúng version, đọc thẳng).
3. Build `user_prompt` gồm toàn bộ section (heading + content + section_id thật, để LLM trích đúng `document_section_id`).
4. `system_prompt` nêu rõ: chỉ dùng nội dung được cung cấp; mỗi đề xuất phải có `source_chunks` trỏ đúng `document_section_id` đã đưa; `confidence: LOW` nếu tài liệu không nói rõ cách làm; **không có field `completion_mode`**.
5. Gọi `llm.complete_json(system_prompt=..., user_prompt=...)`, `json.loads()` kết quả, validate bằng Pydantic (`list[AiTaskProposalResponseDTO]`).
6. Kiểm thêm ngoài schema: mọi `document_section_id` trong `source_chunks` phải thuộc đúng `document_version_id` đã chọn (so với tập đã đọc ở bước 2); `quote` phải là chuỗi con nguyên văn của `content` section đó (giống INV13 ở `validator.py` bên chat — có thể tái dùng logic so khớp nếu tách được thành hàm dùng chung, không thì viết lại ngắn gọn).
7. Đề xuất nào fail kiểm tra ở bước 6 → loại khỏi danh sách trả về, không raise lỗi cả request (1 đề xuất sai không chặn các đề xuất đúng).
8. Không ghi DB ở bước này.

### 8.5 `POST /api/v1/portal/stages/{stage_id}/tasks/from-proposal` — accept

1. Load `JourneyStage` → `JourneyTemplate` (qua `journey_stage_id`), kiểm `status == DRAFT` (không cho thêm task vào template đã publish — P0A §5 bất biến).
2. `require_team_scope(template.team_id, user, db)` — nếu `team_id is None` (template dùng chung) thì chỉ ADMIN được thêm (ghi rõ trong code, chưa có quyền riêng cho "HR sửa nội dung dùng chung" — P0A D10 nói "chỉ ADMIN sửa").
3. Tạo `TaskTemplate(journey_stage_id=stage_id, title=..., body_markdown=instructions_markdown, team_id=template.team_id)`.
4. Với mỗi `source_chunks[i]`: tạo `TaskSourceMapping(task_template_id=task.id, document_id=<suy từ section→version→document>, document_version_id=<từ section>, document_section_id=source.document_section_id)` — cần join `DocumentSection → DocumentVersion` để lấy `document_id`/`document_version_id`, không nhận thẳng từ request (tránh HR gửi sai/giả).
5. Commit, trả `TaskTemplateResponseDTO`.

### 8.6 Test tích hợp — kịch bản chính xác

`test_portal_document_upload_api.py`:
- Chuẩn bị 1 file `.md` tối thiểu 200 ký tự (do `MIN_TEXT_LENGTH`) làm fixture nhỏ, KHÔNG dùng file day1 thật to (giữ test nhanh, độc lập).
- HR (role HR) upload → 200, `section_count >= 1`.
- Role `USER` upload → 403 `FORBIDDEN_ROLE`.
- Upload lại đúng file đó (cùng nội dung) → `created: false` (idempotent — INV5).

`test_portal_ai_task_proposal_api.py`:
- Dùng `FakeChatCompletion(response=...)` với hàm trả JSON cấu hình theo `document_section_id` thật đã ingest ở bước trước (không hardcode id — phải đọc từ kết quả ingest test trước đó).
- Case JSON hợp lệ → propose trả đúng field, không có `completion_mode`.
- Case JSON có `document_section_id` không thuộc version đã chọn → bị lọc khỏi kết quả.
- Case `quote` không khớp nguyên văn section → bị lọc khỏi kết quả.
- Accept 1 đề xuất hợp lệ vào 1 stage có sẵn (tạo trước bằng `template_service.create_journey_template` + `add_stage` trong test, hoặc gọi thẳng 2 API mới) → `TaskTemplate` + đúng số `TaskSourceMapping` được tạo.
- Accept vào stage của template **đã publish** → 409.

### 8.7 Definition of Done bổ sung cho mục 8

- [ ] `get_storage_port` thêm vào `dependencies.py`, dùng `LocalStorageAdapter` mặc định (không cần Cloudinary thật để test).
- [ ] Upload file tạm được dọn sạch kể cả khi `ingest_document` raise lỗi (test có case file hỏng/quá ngắn → 422, không để lại file rác trong temp dir).
- [ ] `category_slug` dùng cho test đã tồn tại trong `document_categories` (kiểm tra hoặc tạo trước khi test, không giả định có sẵn).
- [ ] Toàn bộ response DTO khớp `test_dto_layout.py` (đúng hậu tố `RequestDTO`/`ResponseDTO`, đúng thư mục).
