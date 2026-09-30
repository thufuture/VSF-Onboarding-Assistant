# Nạp tài liệu, chatbot Viga và tạo task bằng AI — công nghệ, luồng đầy đủ, hiện trạng

> Cập nhật 30/09/2026, đối chiếu với code trong `backend/src` và `frontend/src` ở nhánh `feat/portal-plan`.
> Mô tả **những gì code đang làm thật**. Mục 10 liệt kê riêng **lỗi đã xác minh** và **phần chưa làm**.
> Không ghi khóa API hay mật khẩu; giá trị cấu hình nằm trong `backend/.env` (đã bị `.gitignore`).
> Các sơ đồ dưới đây vẽ bằng ký tự để xem được ở mọi trình soạn thảo; mũi tên `--->` là chiều dữ liệu hoặc chiều xử lý.

## Mục lục

1. Bức tranh chung
2. Công nghệ và thư viện
3. Luồng nạp tài liệu (ingest)
4. Chatbot Viga: lấy tài liệu để trả lời như thế nào
5. Quy chế hoạt động của Viga
6. Bộ nhớ (memory) của chatbot
7. Tạo task bằng AI
8. Luồng hoàn chỉnh từ tài liệu tới nhân viên
9. Dữ liệu được lưu ở đâu
10. Hiện trạng: đã làm, lỗi đã xác minh, chưa làm
11. Cách kiểm tra nhanh

## 1. Bức tranh chung

Một lần nạp tài liệu phục vụ **hai việc**: Viga trả lời có nguồn (dùng `document_chunks`) và AI đề xuất task (dùng
`document_sections`). Không có kho dữ liệu riêng cho từng việc.

```text
                        +-----------------------------------------------+
                        |          KHO TÀI LIỆU (PostgreSQL)            |
  HR tải file           |  documents -> document_versions               |
  .docx .pdf .md        |     -> document_sections (đoạn cha)           |
        |               |         -> document_chunks (đoạn con)         |
        v               |            + vector 1024 chiều + BM25         |
  +-----------+  ghi    |  + file gốc (Cloudinary hoặc đĩa)             |
  |  INGEST   |-------->|                                               |
  +-----------+         +-----------+-------------------+---------------+
                                    |                   |
                      đọc section   |                   |  tìm kiếm hybrid trên chunk
                                    v                   v
                        +----------------+     +------------------+
                        | AI ĐỀ XUẤT TASK|     |   VIGA HỎI ĐÁP   |
                        +-------+--------+     +---------+--------+
                                |  HR duyệt              |  trả lời kèm nguồn
                                v                        v
                        LỘ TRÌNH ONBOARDING  --->  NHÂN VIÊN MỚI
```

## 2. Công nghệ và thư viện

| Việc | Công nghệ / thư viện | Cách dùng trong dự án | File |
|---|---|---|---|
| Nhận file từ trình duyệt | FastAPI `UploadFile` + `python-multipart` | Form `multipart/form-data`: file, tên, nhóm, mã nguồn, nhãn phiên bản, ngày hiệu lực | `api/routers/portal_router.py` |
| Đọc file thành Markdown | `markitdown[docx,pdf]` | `MarkItDown().convert()` cho `.docx`, `.pdf`, `.md`; chuẩn hóa Unicode NFC | `services/ingest/parser.py` |
| Phát hiện ảnh nhúng | `zipfile` (thư viện chuẩn) | Tìm `word/media/` trong `.docx`, chỉ ghi cờ cảnh báo | `services/ingest/parser.py` |
| Chia section và chunk | Python thuần (`re`) | Section theo heading H1 đến H3; chunk khoảng 256 từ theo ranh giới đoạn văn; token = số từ | `services/ingest/chunker.py` |
| Tách từ tiếng Việt cho BM25 | `underthesea` (`word_tokenize`) | Sinh `lexical_text`; lỗi thì lùi về tách theo khoảng trắng | `services/ingest/lexical.py` |
| Embedding | BGE-M3 (1024 chiều) trên **Modal**, gọi bằng `httpx` | `POST {endpoint}/embed`, tối đa 32 chuỗi mỗi lần, thử lại có giới hạn | `services/ingest/embedding/modal_adapter.py` |
| Embedding giả cho test | `FakeEmbeddingAdapter` | Vector tất định từ SHA-256, không gọi mạng | `services/ingest/embedding/fake_adapter.py` |
| Lưu file gốc | `cloudinary` hoặc đĩa cục bộ | Chọn bằng `STORAGE_PROVIDER`; tên file là checksum nội dung | `services/ingest/storage.py` |
| Cơ sở dữ liệu | PostgreSQL (image ParadeDB) + `pgvector` + `pg_search` + `btree_gist` | Vector với chỉ mục HNSW (cosine), chỉ mục BM25, ràng buộc chống chồng ngày hiệu lực | `alembic/versions/0001_core.py` |
| Truy cập DB | SQLAlchemy 2 (async) + `asyncpg`, `alembic` | Một transaction cho toàn bộ lần nạp | `services/ingest/ingest_service.py` |
| Tìm kiếm | SQL thô: BM25 (`@@@`) và vector (`<=>`), hợp nhất bằng Reciprocal Rank Fusion | Hai truy vấn, mỗi truy vấn lấy top 30 | `services/retrieval/hybrid_search.py` |
| LLM | DeepSeek (`deepseek-flash`) qua giao diện tương thích OpenAI, `httpx` | `POST /chat/completions`, `response_format: json_object`; bỏ phần suy luận nội bộ, chỉ lấy `content` | `infrastructure/ai/deepseek_adapter.py` |
| LLM giả cho test | `FakeChatCompletion` | Trả JSON cấu hình sẵn | `infrastructure/ai/fake_chat_completion.py` |
| Theo dõi từng bước | Langfuse (tùy chọn) | Bọc từng bước của luồng hỏi đáp; **ingest và tạo task chưa được trace** | `infrastructure/observability/langfuse_tracer.py` |
| Nhật ký thao tác | Bảng `audit_logs` | Ghi `INGEST_DOCUMENT` kèm số section và chunk | `services/ingest/ingest_service.py` |

Cấu hình đang chạy ở dev: embedding `modal-bge-m3`, lưu file `cloudinary`, LLM `deepseek-flash`, Langfuse bật. Test và
CI dùng adapter giả nên không tốn tiền và không cần mạng.

**Kiến trúc cổng (Port/Adapter):** `EmbeddingPort`, `StoragePort`, `ChatCompletionPort` là các `Protocol`. Service chỉ
biết cổng; adapter thật hay giả được chọn ở `services/ingest/factory.py` và `api/dependencies.py`. Đổi nhà cung cấp
(ví dụ đổi LLM) chỉ cần viết một adapter mới.

## 3. Luồng nạp tài liệu (ingest)

Điểm vào: HR bấm "Thêm tài liệu" hoặc "Tải phiên bản mới" ở trang Tài liệu, giao diện gọi
`POST /api/v1/portal/documents` (vai trò HR hoặc Admin).

### 3.1 Sơ đồ

```text
 Trình duyệt (HR)
      |  multipart: file + tên + nhóm + mã nguồn + nhãn phiên bản + ngày hiệu lực
      v
 [1] Ghi ra tệp tạm                              (luôn xóa tệp tạm, kể cả khi lỗi)
      |
      v
 [2] Kiểm tra file  ---- sai đuôi / rỗng / >20MB --------------------> LỖI 422 INGEST_FAILED
      |
      v
 [3] markitdown -> Markdown (NFC)  ---- <200 ký tự (file scan) ------> LỖI 422
      |
      v
 [4] Tính SHA-256 của file và của Markdown
      |
      v
 [5] Tra danh mục + người sở hữu  ---- không thấy -------------------> LỖI 422
      |
      v
 [6] Tìm/tạo `documents` theo source_key
      |
      v
 [7] Đã có version_label này chưa?
      |-- có, cùng nội dung ----------------------------------------> trả kết quả cũ (created=false)
      |-- có, khác nội dung ----------------------------------------> LỖI 422
      |-- chưa
      v
 [8] Chia section (H1-H3) -> chia chunk (~256 từ)  ---- 0 chunk ----> LỖI 422
      |
      v
 [9] Dựng embedding_text (tiêu đề + nội dung) và lexical_text (underthesea)
      |
      v
 [10] Gọi embedding Modal (lô 32, thử tối đa 4 lần: chờ 1s, 3s, 9s)
      |        401/403 -> dừng ngay;  sai số vector/số chiều -------> LỖI 422, KHÔNG ghi DB
      v
 [11] Lưu file gốc (Cloudinary / đĩa)  ---- lỗi ---------------------> LỖI 422, KHÔNG ghi DB
      |
      v
 [12] MỘT transaction: document_versions + sections + chunks + audit_logs
      |        lỗi bất kỳ -> rollback, không ghi nửa vời
      v
 Trả về: document_id, document_version_id, section_count, chunk_count, created
```

### 3.2 Giải thích từng bước

| Bước | Việc | Chi tiết |
|---|---|---|
| 1 | Ghi tệp tạm | `ingest_bridge.py` ghi `UploadFile` ra thư mục tạm vì bộ nạp cần đường dẫn |
| 2 | Kiểm tra file | Chỉ nhận `.docx`, `.pdf`, `.md`; không rỗng; không quá 20 MB |
| 3 | Parse | `markitdown` đọc file; cần ít nhất 200 ký tự, dưới ngưỡng coi như file scan và từ chối (chưa có OCR) |
| 4 | Checksum | SHA-256 file gốc (`file_checksum`) và của Markdown (`content_checksum`) |
| 5 | Tra danh mục, người sở hữu | Danh mục theo `category_slug`, người sở hữu là HR đang đăng nhập |
| 6 | Tài liệu | Cùng `source_key` là cùng một tài liệu |
| 7 | Trùng phiên bản | Cùng `version_label` và cùng `content_checksum` thì không nạp lại (idempotent) |
| 8 | Section và chunk | Không có heading thì cả văn bản là một section; đoạn quá dài (ví dụ bảng lớn) bị cắt cưỡng bức theo từ |
| 9 | Chuẩn bị văn bản | `embedding_text` dùng cho vector; `lexical_text` dùng cho BM25 |
| 10 | Embedding | Kiểm tra đủ vector và đủ 1024 chiều mới đi tiếp |
| 11 | Lưu file gốc | Cloudinary: thư mục `vsf-documents`, `public_id` là checksum kèm đuôi file |
| 12 | Ghi DB | Kèm toàn bộ Markdown vào `document_versions` để xem lại sau này |

**Đặc điểm cần biết:** nạp chạy **đồng bộ trong một request HTTP**. Không có hàng đợi, không có thanh tiến độ, không có
trạng thái `PROCESSING` hay `FAILED` được lưu. File lớn hoặc dịch vụ embedding chậm sẽ làm request lâu; timeout đọc
embedding là 120 giây mỗi lô.

### 3.3 Sau khi nạp, HR làm được gì (trang Tài liệu)

- Xem danh sách: nhóm, số section, trạng thái, task đang dùng, người phụ trách.
- **Xem nội dung** đã parse dạng trang giấy có mục lục đứng yên (`GET /chat/documents/{version_id}`).
- **Xem file gốc**: chuyển hướng tới Cloudinary hoặc trả file cục bộ (`GET /portal/documents/{id}/original`).
- **Sửa** tên và nhóm; **ngừng sử dụng** và **kích hoạt lại** (không xóa cứng, có modal xác nhận).

## 4. Chatbot Viga: lấy tài liệu để trả lời như thế nào

Điểm vào: nhân viên gõ câu hỏi ở trang chat, giao diện gọi `POST /api/v1/chat/ask` (bất kỳ vai trò nào, bắt buộc đã
đăng nhập). Phần mềm **không nhớ hội thoại** (xem mục 6): mỗi câu hỏi xử lý độc lập.

### 4.1 Sơ đồ toàn bộ luồng hỏi đáp

```text
 Nhân viên gõ: "Mai tôi nghỉ phép mấy ngày, thủ tục thế nào?"
      |
      v
 [A] Chống lạm dụng: đếm số câu hỏi của user_id trong 5 phút
      |-- quá 100 câu ------------------------------------------------> 429 TOO_MANY_QUESTIONS (kèm Retry-After)
      v
 [B] Viết lại câu hỏi (LLM lần 1)      bọc trong <user_input>, chống prompt injection
      |   -> tối đa 5 câu con độc lập, mỗi câu tối đa 300 ký tự, tiếng Việt có dấu
      |   -> LLM trả sai định dạng / quá 20 câu ------------------------> dùng nguyên câu gốc
      v
      +--> câu con 1: "Nhân viên được nghỉ phép năm bao nhiêu ngày?"
      +--> câu con 2: "Thủ tục đăng ký nghỉ phép gồm những bước nào?"
      |
      v
 [C] Embedding TẤT CẢ câu con trong MỘT lần gọi (BGE-M3, Modal)
      |
      v
 [D] Tìm kiếm hybrid SONG SONG cho từng câu con (mỗi câu một session DB riêng)
      |      +-------------------------------------------------+
      |      |  BM25 (pg_search)  top 30 chunk  ---+            |
      |      |                                    +--> RRF k=60 --> gộp về SECTION cha
      |      |  Vector (pgvector) top 30 chunk ---+            |    --> cắt theo ngân sách 3000 token
      |      +-------------------------------------------------+
      |      lọc: phiên bản ACTIVE, còn hiệu lực theo ngày, đúng phiên bản model embedding
      v
 [E] Rerank: chưa bật (chỉ trả lại nguyên danh sách)
      |
      v
 [F] Không câu con nào có đoạn tài liệu? ------------------------------> KHÔNG gọi LLM, trả NO_BASIS/no_evidence
      |
      v
 [G] Sinh câu trả lời (LLM lần 2, MỘT lần cho tất cả câu con)
      |   prompt: mỗi câu con nằm trong <question>, tài liệu tương ứng trong <context> đứng ngay trước
      |   LLM trả claims[]: ANSWER (text + quote nguyên văn + chunk_id) hoặc NO_BASIS
      |   LLM sai định dạng ------------------------------------------> mọi câu NO_BASIS/llm_contract_error
      |   LLM bỏ sót một câu con -------------------------------------> câu đó NO_BASIS/llm_skipped_question
      v
 [H] Kiểm từng claim (validator)
      |   chunk_id phải thuộc kết quả tìm của ĐÚNG câu con đó
      |   quote phải là chuỗi con nguyên văn của section chứa chunk (sau NFC, gộp khoảng trắng)
      |   không đạt -> ép về NO_BASIS/validation_failed
      v
 [I] Trả về claims[]: mỗi ý một claim, kèm nguồn (tên tài liệu, bản, mục, đường dẫn, version_id)
      |
      v
 Giao diện hiện từng ý: câu trả lời + nút mở nguồn -> modal xem toàn bộ tài liệu, cuộn tới đúng mục
```

### 4.2 Viga lấy tài liệu như thế nào (chi tiết bước D)

```text
 câu con ("nghỉ phép năm bao nhiêu ngày")
      |
      +--> to_lexical_text: NFC + chữ thường + underthesea  --->  BM25 trên cột document_chunks.lexical_text
      |
      +--> vector 1024 chiều (từ bước C)                    --->  cosine trên document_chunks.embedding
                                                                      |
                     hai danh sách xếp hạng (chunk_id)  <-------------+
                                   |
                                   v
          điểm RRF của chunk = tổng 1 / (60 + hạng) qua hai danh sách
                                   |
                                   v
          gộp chunk về section cha: điểm section = điểm cao nhất của chunk con
                                   |
                                   v
          lấy nội dung ĐẦY ĐỦ của section (không chỉ chunk) theo thứ tự điểm giảm dần,
          dừng khi vượt 3000 token (luôn giữ ít nhất 1 section nếu có kết quả)
```

Vì sao trả **section cha** thay vì chunk: chunk nhỏ (khoảng 256 từ) tốt cho việc tìm, section đầy đủ tốt cho việc trả
lời và trích nguồn nguyên văn, nên tìm bằng chunk và đọc bằng section.

### 4.3 Kết quả một câu trả lời

| Trường | Ý nghĩa |
|---|---|
| `question` | Câu con đã viết lại |
| `response_type` | `ANSWER` hoặc `NO_BASIS` |
| `reason_code` | Lý do khi `NO_BASIS`: `no_evidence`, `out_of_scope`, `validation_failed`, `llm_contract_error`, `llm_skipped_question` |
| `text`, `quote` | Câu trả lời ngắn và câu trích nguyên văn từ tài liệu |
| `source` | Tên tài liệu, nhãn phiên bản, tiêu đề mục, đường dẫn file, `version_id` để mở nội dung |

Một câu hỏi nhiều ý cho ra nhiều claim độc lập: ý nào có căn cứ thì trả lời, ý nào không thì nói thẳng "chưa có căn cứ".

## 5. Quy chế hoạt động của Viga

| Quy tắc | Nội dung | Nơi thực thi |
|---|---|---|
| Chỉ trả lời theo tài liệu | Prompt cấm suy diễn ngoài đoạn được cấp; không có căn cứ thì `NO_BASIS` | `answer_service.py` |
| Bắt buộc trích nguồn | Mỗi `ANSWER` phải có `quote` và `chunk_id`; quote phải khớp nguyên văn | `validator.py` |
| Không tin LLM một mình | Validator hậu kiểm ép về `NO_BASIS` nếu trích dẫn không kiểm chứng được | `validator.py` |
| Thông tin cá nhân | Câu hỏi về mentor, chỗ ngồi, lương, số dư phép riêng: `NO_BASIS/out_of_scope`, vì tài liệu chính sách chung không có | `answer_service.py` |
| Chống prompt injection | Câu hỏi bọc `<user_input>`, tài liệu bọc `<context>`; prompt dặn đó là dữ liệu chứ không phải chỉ dẫn | `guardrail_input.py` |
| Giới hạn câu con | Tối đa 5 câu con, mỗi câu tối đa 300 ký tự; quá 20 câu thì bỏ kết quả viết lại | `query_rewrite.py` |
| Giới hạn độ dài câu hỏi | Tối đa 2000 ký tự, không được chỉ có khoảng trắng | `chat_request_dto.py` |
| Chống lạm dụng | 100 câu hỏi mỗi 5 phút cho mỗi người dùng, đếm trong bộ nhớ tiến trình (một worker) | `chat_throttle.py` |
| Hiệu lực tài liệu | Chỉ lấy phiên bản `ACTIVE`, còn hiệu lực theo ngày (mặc định hôm nay theo múi giờ `Asia/Ho_Chi_Minh`), đúng phiên bản model embedding | `hybrid_search.py` |
| Đăng nhập | Bắt buộc; phiên hết hạn sau 30 phút | `api/dependencies.py`, `config.py` |
| Phạm vi tài liệu | **Toàn kho**, không lọc theo phòng ban, không có ACL theo tài liệu | `hybrid_search.py` |
| Theo dõi | Mỗi bước (`rewrite_query`, `embed_questions`, `retrieval`, `llm_answer`, `validate_claims`) là một span Langfuse, chỉ ghi số lượng và độ dài, không ghi nội dung câu hỏi | `chat_router.py` |
| Khi dịch vụ ngoài lỗi | Viết lại lỗi định dạng thì dùng câu gốc; LLM trả sai schema thì `NO_BASIS`; **lỗi mạng tới LLM hoặc embedding chưa có bộ xử lý riêng** nên trả lỗi 500, giao diện hiện "không khả dụng" | `chat_router.py` |

## 6. Bộ nhớ (memory) của chatbot

**Hiện tại chatbot không có bộ nhớ hội thoại.** Mỗi lần hỏi độc lập hoàn toàn.

```text
 Trình duyệt                          Backend                           LLM
 +----------------------+   chỉ gửi   +----------------------+   chỉ thấy  +-------------------+
 | turns[] trong state  | ----------> | question (+ as_of)   | ----------> | câu con hiện tại  |
 | React (mất khi F5)   |   1 câu     | KHÔNG lưu, KHÔNG có  |   + đoạn    | + đoạn tài liệu   |
 +----------------------+   hỏi       | session hội thoại    |   tìm được  | KHÔNG có lịch sử  |
                                      +----------------------+             +-------------------+
```

| Thành phần | Có nhớ không | Chi tiết |
|---|---|---|
| Lịch sử hội thoại trên giao diện | Chỉ trong tab | Mảng `turns` trong state React của `ChatShell`; tải lại trang là mất |
| Lịch sử gửi cho backend | Không | `ChatAskRequestDTO` chỉ có `question` và `as_of` |
| Lịch sử gửi cho LLM | Không | Prompt chỉ có câu hỏi hiện tại và đoạn tài liệu tìm được |
| Câu hỏi đã viết lại | Không lưu | Chỉ dùng tạm trong bộ nhớ của lượt đó |
| Hồ sơ người dùng (phòng ban, ngày vào làm, task đang làm) | Không đưa vào | Nên Viga không biết người hỏi đang kẹt ở task nào |
| Bộ đếm giới hạn câu hỏi | Trong bộ nhớ tiến trình | Mất khi khởi động lại; không dùng chung nếu chạy nhiều worker |
| Phiên đăng nhập | Cookie có chữ ký | Hết hạn sau 30 phút |
| Nhật ký Langfuse | Có, nhưng không có nội dung | Chỉ số lượng và độ dài |

**Hệ quả:** câu hỏi nối tiếp như "còn trường hợp thử việc thì sao?" sẽ **không hiểu** "trường hợp" đó nói về gì, vì Viga
không thấy câu trước. Người dùng phải hỏi lại đủ ý. Đây là giới hạn hiện tại, chưa phải tính năng đã làm.

## 7. Tạo task bằng AI

### 7.1 Cần gì (đầu vào)

| Thứ cần có | Vì sao |
|---|---|
| Một tài liệu đã nạp, `ACTIVE`, có phiên bản mới nhất | AI đọc các section của đúng phiên bản đó |
| Ít nhất một **giai đoạn (ngày) ở lộ trình nháp** thuộc phòng ban của HR | Nơi nhận task; lộ trình đã xuất bản bị khóa |
| Khóa LLM và mạng tới DeepSeek | Thiếu khóa thì API báo lỗi cấu hình |
| Vai trò HR hoặc Admin | Kiểm bằng `require_role`; HR chỉ thấy phòng ban của mình |

Không cần embedding hay tìm kiếm: bước này **đọc thẳng toàn bộ section** của phiên bản, không qua vector.

### 7.2 Sơ đồ luồng

```text
  HR (trang "Tạo task bằng AI")                Backend                                  DeepSeek
  ------------------------------                -------                                  --------
  [1] chọn 1..N tài liệu + ngày đích
        |
        | bấm "Phân tích"
        v
  với TỪNG tài liệu, lần lượt:
  POST /portal/ai/task-proposals
     { document_version_id }  ------------->  đọc TẤT CẢ section của phiên bản
                                                    |
                                                    v
                                              dựng prompt:
                                              - system: chỉ dùng nội dung được cấp,
                                                phải trích section_id + quote nguyên văn,
                                                LOW nếu không rõ, trả mảng JSON
                                              - user: từng section kèm section_id
                                                    |
                                                    | complete_json  ------------------>  sinh mảng đề xuất (JSON)
                                                    |  <---------------------------------
                                                    v
                                              parse JSON  --- sai JSON/không phải mảng ---> 422 AI_INVALID_JSON
                                                    |
                                                    v
                                              LỌC từng đề xuất:
                                              - sai schema                      -> bỏ
                                              - không có source_chunks          -> bỏ
                                              - section_id không thuộc phiên bản-> bỏ CẢ đề xuất
                                              - quote không nằm nguyên văn trong
                                                section                         -> bỏ CẢ đề xuất
                                                    |
     <---- danh sách đề xuất đã lọc  <--------------+      (CHƯA ghi gì vào DB)
        |
        v
  giao diện gộp kết quả các tài liệu, bỏ đề xuất trùng tên
        |
        v
  [2] HR xem từng thẻ: tên, độ tin cậy, tóm tắt, hướng dẫn, đoạn nguồn
        |
        | bấm "Chấp nhận" ở một thẻ
        v
  POST /portal/stages/{id}/tasks/from-proposal
     { title, instructions_markdown, required, source_chunks } ---> kiểm giai đoạn thuộc lộ trình NHÁP
                                                                    và đúng phạm vi phòng ban
                                                                          |
                                                                          v
                                                                    tạo task_templates
                                                                    tạo task_source_mappings
                                                                    (tài liệu, phiên bản, section)
        <---- task mới  <-------------------------------------------------+
        |
        v
  [3] HR sang "Quản lý task": sửa tên, hướng dẫn, gán nhóm màu, thêm tiên quyết  ---> [4] Xuất bản
```

### 7.3 Ra gì (một đề xuất)

| Trường | Ý nghĩa | Hiện được dùng ra sao |
|---|---|---|
| `title` | Tên task | Hiện trên thẻ, lưu làm tên task khi chấp nhận |
| `summary` | Tóm tắt | Hiện trên thẻ, **không lưu** |
| `instructions_markdown` | Hướng dẫn thực hiện | Hiện và **lưu làm nội dung task** |
| `done_criteria` | Danh sách điều kiện hoàn thành | Có trong kết quả API, **chưa hiện và chưa lưu** |
| `estimated_minutes` | Số phút ước tính hoặc rỗng | **Chưa hiện, chưa lưu** |
| `source_chunks[]` | `document_section_id` và `quote` nguyên văn | Hiện dưới thẻ; lưu thành `task_source_mappings` |
| `confidence` | `HIGH`, `MEDIUM`, `LOW` | Hiện nhãn độ tin cậy |
| `warnings[]` | Cảnh báo | **Chưa hiện, chưa lưu** |

### 7.4 Các lớp an toàn

1. Prompt yêu cầu chỉ dùng nội dung được cấp, không suy diễn thêm bước.
2. Bắt buộc trích ít nhất một section bằng đúng `section_id`.
3. Backend kiểm `quote` là chuỗi con nguyên văn của section; sai một trích dẫn thì loại cả đề xuất.
4. AI **không tự lưu**: chỉ khi HR bấm chấp nhận mới ghi DB.
5. Lộ trình đã xuất bản không nhận task mới (`409 TEMPLATE_ALREADY_PUBLISHED`).

### 7.5 Các bước trên giao diện

| Bước trên thanh bước | Việc của HR | Việc của hệ thống |
|---|---|---|
| 1. Chọn nguồn và đích | Chọn một hoặc nhiều tài liệu sẵn sàng; chọn giai đoạn đích (mặc định giai đoạn nháp đầu tiên) hoặc tạo giai đoạn mới | Liệt kê tài liệu `ACTIVE` có phiên bản; giai đoạn lấy từ `GET /portal/stages` |
| 2. AI dựng roadmap | Bấm "Phân tích N tài liệu và đề xuất roadmap" | Gọi API đề xuất **lần lượt cho từng tài liệu**, gộp kết quả, bỏ trùng tên |
| 3. HR chấp nhận | Xem từng thẻ, chấp nhận từng task | Mỗi lần chấp nhận gọi API `from-proposal`, thẻ đó biến khỏi danh sách |
| 4. Thêm vào quản lý task | Sang Quản lý task để hoàn thiện | Bước hiển thị chuyển sang bước cuối khi đã chấp nhận ít nhất một task |

## 8. Luồng hoàn chỉnh từ tài liệu tới nhân viên

```text
  HR                                   HỆ THỐNG                                     NHÂN VIÊN
  --                                   --------                                     ---------
  1. tải tài liệu  ------------------> ingest: parse -> section -> chunk
                                        -> embedding -> lưu file -> ghi DB
  2. xem nội dung đã parse  <---------- (trang giấy + mục lục)
        |
        v
  3. chọn tài liệu, bấm phân tích ---> LLM đề xuất task có trích nguồn
        |
        v
  4. chấp nhận từng task  ------------> task vào lộ trình NHÁP + ghi nguồn
        |
        v
  5. sửa ở Quản lý task: hướng dẫn, nhóm màu, tiên quyết, thứ tự
        |
        v
  6. xuất bản lộ trình  --------------> lộ trình đã xuất bản (khóa sửa)
                                                  |
                                                  v
                                        khi nhân viên mở lộ trình lần đầu:  <------ 7. mở "Lộ trình của tôi"
                                        tạo employee_tasks từ bản đã xuất bản
                                        task có tiên quyết -> LOCKED, còn lại READY
                                                  |
                                                  v
                                                                                  8. tự xác nhận hoàn thành task
                                        hoàn thành tiên quyết -> mở khóa task phụ thuộc  <------+
                                                                                        |
                                                                                        v
                                        Viga tìm trong các chunk đã nạp  <------- 9. hỏi Viga khi kẹt
                                        trả lời kèm nguồn, hoặc nói "chưa có căn cứ"
```

Ghi chú: lộ trình của nhân viên tạo khi họ mở `GET /portal/me/journey` lần đầu, từ lộ trình **đã xuất bản** của phòng
ban họ. Trạng thái task hiện chỉ dùng `LOCKED`, `READY`, `DONE`. Viga hiện **chưa biết** nhân viên đang ở task nào
(xem mục 6).

## 9. Dữ liệu được lưu ở đâu

| Bảng | Nội dung | Ai dùng |
|---|---|---|
| `documents` | Tên, nhóm, người sở hữu, `source_key` (duy nhất), trạng thái `ACTIVE`/`ARCHIVED` | Trang Tài liệu |
| `document_versions` | Nhãn phiên bản, số thứ tự, tên file gốc, `storage_key`, hai checksum, **toàn bộ Markdown**, ngày hiệu lực, phiên bản model embedding | Xem tài liệu, tìm kiếm (lọc hiệu lực) |
| `document_sections` | Tiêu đề, nội dung, số token | AI đề xuất task; Viga đọc và trích nguồn |
| `document_chunks` | Nội dung, `embedding_text`, `lexical_text`, `embedding` (vector 1024), hash | Viga tìm kiếm (BM25 và HNSW) |
| `task_source_mappings` | Task lấy từ tài liệu, phiên bản, section nào | Cột "Task sử dụng" của trang Tài liệu |
| `task_templates`, `journey_stages`, `journey_templates` | Lộ trình, ngày, task, nhóm, tiên quyết | Quản lý task, nhân viên |
| `employee_journeys`, `employee_tasks` | Lộ trình và trạng thái task của từng nhân viên | Trang lộ trình nhân viên, trang Nhân viên của HR |
| `audit_logs` | `INGEST_DOCUMENT` và các thao tác quản trị | Trang Nhật ký của Admin |

## 10. Hiện trạng: đã làm, lỗi đã xác minh, chưa làm

### 10.1 Đã làm và có kiểm chứng

- Toàn bộ luồng ở mục 8 chạy trên PostgreSQL thật; có test tích hợp cho upload
  (`test_portal_document_upload_api.py`), đề xuất và chấp nhận (`test_portal_ai_task_proposal_api.py`), quản lý task
  (`test_portal_task_management_api.py`).
- Đã nạp thật một tài liệu mẫu ("Chính sách nghỉ phép năm", 32 section, 34 chunk) bằng embedding Modal và lưu Cloudinary.
- Chatbot: viết lại và tách câu hỏi, tìm hybrid song song, trả `claims[]` có kiểm chứng nguồn, giao diện hiện nguồn và
  mở tài liệu cuộn tới đúng mục.
- Các lớp an toàn cho cả chatbot và tạo task: chỉ dùng nội dung được cấp, bắt buộc trích nguồn, kiểm nguồn nguyên văn.

### 10.2 Lỗi đã xác minh, chưa sửa

| # | Lỗi | Bằng chứng | Hậu quả |
|---|---|---|---|
| 1 | **Tải phiên bản mới của cùng một tài liệu thất bại.** Phiên bản cũ không bao giờ được đóng (`effective_to` trống, không chuyển `ARCHIVED`), trong khi DB cấm hai bản `ACTIVE` chồng ngày | Chèn thử bản mới trong một transaction rồi rollback: DB báo `ex_document_versions_active_no_overlap` | Nút "Tải phiên bản mới" lỗi; chỉ `IngestError` được bắt nên người dùng có thể thấy lỗi 500 |
| 2 | **Tài liệu "ngừng sử dụng" vẫn được Viga tìm thấy.** Nút chỉ đổi `documents.status`; truy vấn tìm kiếm chỉ lọc theo trạng thái phiên bản | Đọc `hybrid_search.py` và `set_document_status` | Thông báo trong modal ("không dùng nữa") đúng với danh sách chọn của AI nhưng không đúng với Viga |
| 3 | **Lỗi mạng tới LLM hoặc embedding trong `/chat/ask` không có bộ xử lý riêng** | `chat_router.py` không bắt `ChatCompletionError` và `EmbeddingServiceError`, `main.py` chỉ xử lý `AuthError` và `PortalError` | Người dùng thấy lỗi 500 thay vì thông báo "chưa trả lời được" |

### 10.3 Chưa làm hoặc còn thiếu

| Nhóm | Còn thiếu |
|---|---|
| Ingest | OCR cho file scan (đang từ chối); xử lý ảnh nhúng (chỉ cảnh báo); hàng đợi và tiến độ; trạng thái `PROCESSING`, `PENDING_REVIEW`, `FAILED` chưa dùng; trace Langfuse cho ingest |
| Đóng phiên bản cũ | Khi có phiên bản mới cần tự đặt `effective_to` cho bản cũ hoặc chuyển `ARCHIVED` (sửa lỗi 1) |
| Tìm kiếm | Lọc theo trạng thái tài liệu (sửa lỗi 2); rerank (đã chừa chỗ, chưa bật) |
| Chatbot | **Bộ nhớ hội thoại** (nối câu hỏi trước); đưa ngữ cảnh người hỏi (phòng ban, task đang làm); bộ đếm giới hạn dùng chung nhiều worker; ghi câu hỏi không có căn cứ vào `content_gaps` để HR bổ sung tài liệu; trang "Phản hồi Viga" cho HR |
| Tạo task bằng AI | Lưu `done_criteria`, `estimated_minutes`, `warnings`; ghi nội dung theo ba mục "Vì sao / Điều kiện hoàn thành / Các bước" để tab Hướng dẫn hiện đúng (hiện lưu nguyên văn, tab tách theo dòng); tự gán nhóm task từ danh mục tài liệu; đề xuất tiên quyết; "Chấp nhận tất cả"; xem trước dạng roadmap trước khi thêm |
| Chất lượng AI | Khi chấp nhận, backend chỉ kiểm section có tồn tại, không kiểm lại `quote`; prompt gửi **toàn bộ section**, không có ngân sách token nên tài liệu rất dài có thể vượt giới hạn ngữ cảnh; chưa đo độ chính xác trên nhiều tài liệu |
| Vận hành | Tài liệu thật cho 10 task ngày 1 (kế hoạch P4B) chưa nạp; chưa có màn hình theo dõi chi phí LLM và embedding |

## 11. Cách kiểm tra nhanh

1. Đăng nhập HR (`hr1@vsf-demo.example`, mật khẩu dev trong `docs/chatbot-vsf/data/registry/users.json`).
2. Trang Tài liệu: "Thêm tài liệu", chọn file `.docx` từ `docs/chatbot-vsf/data/documents/day1/`; sau vài giây danh
   sách hiện thêm dòng và số section.
3. Trang Tạo task bằng AI: chọn tài liệu, chọn giai đoạn nháp, bấm phân tích; xem các thẻ đề xuất và đoạn nguồn.
4. Chấp nhận một đề xuất, sang Quản lý task để thấy task mới ở lộ trình nháp.
5. Đăng nhập nhân viên, mở trang chat, hỏi một câu có trong tài liệu (ví dụ về nghỉ phép năm) và một câu không có;
   quan sát `ANSWER` kèm nguồn và `NO_BASIS`.
6. Chạy test: `pytest tests/integration/test_portal_ai_task_proposal_api.py tests/integration/test_portal_document_upload_api.py`
   với `VSF_TEST_DATABASE_URL` trỏ tới PostgreSQL thật.
