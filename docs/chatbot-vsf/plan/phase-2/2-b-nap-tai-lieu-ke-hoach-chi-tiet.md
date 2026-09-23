# 2-B — Nạp tài liệu: kế hoạch triển khai chi tiết (chưa làm, chờ bạn duyệt)

> Thuộc [phase-2.md](phase-2.md) mục 5, bước **2-B** (kế hoạch gốc, ước lượng ≈ 0,75 ngày). Tài liệu này khai triển 2-B thành kiến trúc, luồng dữ liệu, cây thư mục và danh sách file cụ thể để bạn duyệt **trước khi tôi viết code** — 2-B chưa bắt đầu.
> Phụ thuộc: **2-A đã xong** (`0001_core`, model SQLAlchemy, commit `68c3cb0`, nhánh `phase-4-auth`).
> Không lấn sang 2-C (tìm kiếm), 2-D (LLM), 2-E (endpoint/trang chat) — các bước đó có kế hoạch riêng trong [phase-2.md](phase-2.md).

## 1. Việc 2-B chứng minh được gì

Một file `.docx` thật → nằm trong Postgres, sẵn sàng để 2-C tìm kiếm được. Không hơn. Cụ thể: đọc **đúng một** tài liệu (`SYN_D03b_Chinh_sach_nghi_phep_nam_v2024.docx`), tách thành đoạn cha/con theo đúng ràng buộc của `0001_core`, gọi dịch vụ embedding lấy vector, ghi tất cả vào DB trong một giao dịch, chạy lại không nhân đôi.

## 2. Kiến trúc luồng dữ liệu

```text
                    ┌─────────────────────────────────────────────┐
                    │  backend/src/cli/ingest_file.py (CLI, D4)    │
                    │  python -m src.cli.ingest_file <đường dẫn>   │
                    └───────────────────┬───────────────────────────┘
                                        │ gọi
                                        ▼
        ┌───────────────────────────────────────────────────────────┐
        │        backend/src/services/ingest/ingest_service.py       │
        │  điều phối toàn bộ, mở MỘT transaction cho bước 4           │
        └──┬───────────┬───────────────┬───────────────┬─────────────┘
           │1. parse    │2. section/    │3. tách từ     │4. embed + ghi DB
           ▼            │  chunk         ▼               ▼
  ┌─────────────────┐   │        ┌──────────────┐  ┌─────────────────────┐
  │ parser.py        │   │        │ lexical.py   │  │ embedding/           │
  │ MarkItDown       │   │        │ (D3)         │  │  ├─ port.py          │
  │ .docx → Markdown │   │        │ underthesea  │  │  ├─ modal_adapter.py │
  │ + checksum       │   ▼        │  hoặc âm tiết│  │  └─ fake_adapter.py  │
  └─────────────────┘  ┌──────────┴──────┐        │        (D6)          │
                        │ chunker.py       │        └──────────┬───────────┘
                        │ section (H1-H3)  │                   │ gọi HTTP
                        │ chunk ~256 token │                   ▼
                        │ (D theo Ralion   │         Modal: EMBEDDING_ENDPOINT
                        │  policy_chunker) │         (BGE-M3, 1024 chiều)
                        └──────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────┐
                    │  Postgres/ParadeDB (0001_core, đã có)  │
                    │  documents → document_versions          │
                    │            → document_sections (cha)     │
                    │            → document_chunks (con, có     │
                    │              embedding + lexical_text)     │
                    │  + 1 dòng audit_logs                       │
                    └───────────────────────────────────────┘
```

**Nguyên tắc:** mỗi hộp trên là một hàm/module thuần, test được độc lập không cần DB hay mạng, trừ bước 4 (ghi DB) và lời gọi embedding thật.

## 3. Công nghệ dùng

| Việc | Thư viện | Lý do |
|---|---|---|
| Parse `.docx` → Markdown | `markitdown[docx]` | Ralion đã dùng, đọc bảng/danh sách tốt hơn tự viết parser |
| Gọi embedding | `httpx` (async) | Đã có sẵn trong dependency backend (dùng ở test tích hợp Phase 4) |
| Tách từ tiếng Việt (D3) | `underthesea`, lùi về tách âm tiết nếu nặng/lỗi | Theo quyết định D3 đã chốt trong `phase-2.md` |
| Đếm token | Xấp xỉ theo số từ (D6) | Không thêm `tiktoken`, giữ nhẹ theo quyết định đã chốt |
| Vector | `pgvector` (đã có trong `pyproject.toml`) | Không đổi |
| Kiểm schema | `pydantic` | Đồng bộ với DTO đã dùng ở Phase 4 |

**Không thêm** `tiktoken`, `openai` SDK (embedding gọi thẳng HTTP, không qua SDK) ở bước này — chỉ cần khi tới 2-D (LLM).

## 4. Cây file cụ thể

```text
backend/src/services/ingest/
    __init__.py
    parser.py              parse_docx(path) -> ParsedDocument (markdown, file_checksum, content_checksum)
    chunker.py              split_into_sections(markdown) -> list[SectionDraft]
                            split_into_chunks(section) -> list[ChunkDraft]   (~256 token, không bao giờ 0 chunk)
    lexical.py              to_lexical_text(text) -> str   (D3: underthesea hoặc tách âm tiết)
    embedding/
        __init__.py
        port.py             EmbeddingPort (Protocol): async embed(texts: list[str]) -> list[list[float]]
        modal_adapter.py     ModalEmbeddingAdapter(EmbeddingPort): gọi EMBEDDING_ENDPOINT, lô ≤ 32, retry
        fake_adapter.py      FakeEmbeddingAdapter(EmbeddingPort): vector xác định từ hash(text), dùng cho test/CI
    ingest_service.py       ingest_document(...) -> IngestResult: điều phối, 1 transaction cho bước ghi DB

backend/src/cli/
    ingest_file.py          CLI: python -m src.cli.ingest_file <đường dẫn> [--category nghi-phep] [--owner-email ...]

backend/tests/test_ingest/
    test_parser.py          đơn vị: parse D03b thật (không mock), kiểm markdown không rỗng, có bảng
    test_chunker.py         đơn vị: mục ngắn, bảng, danh sách, mục dài, không heading → không bao giờ 0 chunk
    test_lexical.py         đơn vị: tách từ, chuẩn hóa NFC
    test_embedding_fake.py  đơn vị: FakeEmbeddingAdapter xác định (cùng text → cùng vector)

backend/tests/integration/
    test_ingest_service.py  tích hợp (Postgres thật, FakeEmbeddingAdapter): nạp D03b, kiểm section/chunk > 0,
                            mọi chunk cùng version với section cha (INV14), nạp lại không nhân đôi (INV5)
```

**Đối chiếu quy ước đã có** (từ Phase 4): DTO tách `request`/`response` chỉ áp dụng cho API — 2-B **không có** endpoint HTTP nên không cần DTO ở bước này; `IngestResult` là kiểu nội bộ (dataclass/pydantic thường), không phải response DTO.

## 5. Cấu hình thêm vào `.env.example` và `config.py`

```text
# Ingest: gọi Modal lấy embedding (2-B)
INGESTION_EMBEDDING_CONNECT_TIMEOUT_SECONDS=5
INGESTION_EMBEDDING_READ_TIMEOUT_SECONDS=120
INGESTION_EMBEDDING_MAX_ATTEMPTS=4
INGESTION_EMBEDDING_BACKOFF_INITIAL_SECONDS=1
INGESTION_EMBEDDING_BACKOFF_MULTIPLIER=3
INGESTION_EMBEDDING_BACKOFF_MAX_SECONDS=9
```

(`EMBEDDING_PROVIDER`, `EMBEDDING_ENDPOINT`, `EMBEDDING_API_KEY` đã có sẵn trong `.env.example` từ Phase 0, chỉ cần bổ sung phần timeout/retry ở trên — số lấy từ `.env.example` của Ralion, phần dành riêng cho **ingest** (không phải phần `CHAT_EMBEDDING_*` dùng lúc chat, đó là việc của 2-E/Phase 7).)

## 6. Trạng thái khóa/endpoint — cần bạn xác nhận (khác với D1 mặc định trong `phase-2.md`)

`phase-2.md` mục 3, quyết định **D1** đề xuất mặc định: **triển khai app Modal riêng cho VSF** (`vsf-bge-m3-embedder`), không dùng chung với Ralion.

**Việc đã xảy ra ngoài kế hoạch:** trong phiên làm việc trước, theo yêu cầu của bạn, tôi đã **tạm chép endpoint và khóa của Ralion** (`ralion-bge-m3-embedder`) vào `.env` của VSF để có cái dùng thử ngay. Đây là lựa chọn "khác" trong bảng D1, không phải mặc định.

**Cần bạn chọn một trong hai** trước khi tôi chạy embedding thật ở 2-B:

| Lựa chọn | Việc phải làm | Đánh đổi |
|---|---|---|
| **A. Dùng tạm endpoint Ralion** (đang có sẵn trong `.env`) | Không cần làm gì thêm, code 2-B chạy được ngay | Chi phí Modal gộp chung với Ralion; app đó có thể bị tắt/xóa ngoài ý muốn của VSF |
| **B. Deploy app Modal riêng cho VSF** (đúng D1 mặc định) | Bạn cần: tài khoản Modal (đã có, cùng tài khoản `trananhthu270904`), tôi chép `modal_bge_m3/app.py` từ Ralion, đổi tên app, bạn chạy `modal deploy` (cần xác nhận trước khi chạy vì đây là hành động tạo tài nguyên ngoài) | Tốn thêm ~10–15 phút thiết lập, nhưng tách bạch chi phí và không phụ thuộc Ralion |

Tôi đề xuất **Lựa chọn A cho 2-B** (đã có sẵn, tiết kiệm thời gian, chi phí ingest 1 tài liệu rất nhỏ) rồi chuyển sang B khi làm 2-F (đo số liệu thật, cần ổn định lâu dài) hoặc trước khi triển khai production. Bạn xác nhận hoặc chọn khác trong câu hỏi ở cuối tài liệu này.

## 7. Cổng dữ liệu nền (bước 1 trong `phase-2.md`)

Trước khi parse, cần có sẵn trong DB (transaction riêng, trước ingest, hoặc phần đầu của `ingest_service`):
1. `document_categories` — đọc từ `registry/document_categories.json`, tạo nếu chưa có (dùng lại nếu 2-A/seed đã tạo).
2. Một `users` có `role=HR` làm `owner_id`/`uploaded_by` — dùng tài khoản dev `hr1@vsf-demo.example` đã seed từ Phase 4 (`seed_users`), **không** hard-code mật khẩu, chỉ tra theo email.

Không tạo user/category mới ngoài registry đã có.

## 8. Kế hoạch test (đối chiếu mục "Test" của `phase-2.md`)

| Loại | File | Không cần | Cần |
|---|---|---|---|
| Đơn vị (parser) | `test_parser.py` | DB, mạng | File D03b thật trên đĩa |
| Đơn vị (chunker) | `test_chunker.py` | DB, mạng, file thật | Markdown mẫu viết tay (mục ngắn/dài/bảng/danh sách/không heading) |
| Đơn vị (lexical) | `test_lexical.py` | DB, mạng | — |
| Đơn vị (embedding giả) | `test_embedding_fake.py` | DB, mạng | — |
| Tích hợp | `test_ingest_service.py` | Mạng (dùng `FakeEmbeddingAdapter`) | Postgres thật (`VSF_TEST_DATABASE_URL`, đã có sẵn từ Phase 4) |
| Kiểm tay (không tự động) | CLI chạy 1 lần | | Endpoint embedding thật (theo mục 6) — chỉ để xem số liệu, không phải cổng bắt buộc của 2-B |

**CI luôn dùng `EMBEDDING_PROVIDER=fake`** — không gọi mạng thật trong pipeline (đúng quyết định D6 trong `phase-2.md`).

## 9. Cổng hoàn thành 2-B (bám `phase-2.md` mục 5)

1. `ruff`, `ruff format --check`, `mypy strict` sạch.
2. `pytest` xanh (đơn vị + tích hợp với `FakeEmbeddingAdapter`).
3. Chạy `python -m src.cli.ingest_file docs/chatbot-vsf/data/documents/core/SYN_D03b_....docx` một lần thành công (dùng endpoint theo mục 6), đếm được: 1 `documents`, 1 `document_versions` (status `ACTIVE`), > 0 `document_sections`, > 0 `document_chunks` với `embedding` đủ 1024 chiều.
4. Chạy lại CLI lần hai với cùng file: không tạo thêm bản ghi (idempotent theo `content_checksum`).
5. Không phá CI hiện có (verify.yml vẫn xanh).

## 10. Rủi ro riêng của 2-B (bổ sung mục 9 của `phase-2.md`)

| Rủi ro | Xử lý |
|---|---|
| MarkItDown làm hỏng bảng trong D03b | Đã ghi trong `phase-2.md`; kiểm Markdown sinh ra trước khi viết chunker, nếu hỏng thì ghi nhận, không tự sửa tay |
| `underthesea` cài lỗi trên Windows | Thử cài trước tiên; lùi về tách âm tiết (D3) nếu lỗi, ghi rõ trong báo cáo |
| Endpoint Ralion (lựa chọn A mục 6) bị tắt giữa chừng | Vì dùng tạm, có rủi ro thật; nếu xảy ra, chuyển sang Lựa chọn B (deploy riêng) |
| Nạp tài liệu tốn hết `$1` free credit của Modal (đã kiểm ở phiên trước, gói Starter) | Ingest 1 tài liệu (~30-40 chunk) tốn rất ít so với $1; theo dõi qua Modal dashboard sau khi chạy |

## 11. Ingest "chuẩn đầy đủ": không chỉ đường vui (upload → xử lý → vector → DB)

Bạn yêu cầu kế hoạch phải đầy đủ, không chỉ chạy đúng với 1 file sạch. Mục này liệt kê **mọi điểm có thể sai** trong chuỗi "nhận file → parse → chunk → embed → ghi DB", và cách 2-B xử lý — kể cả phần thuộc Phase 5 (upload web) để bạn thấy toàn cảnh, có đánh dấu rõ cái nào làm ở 2-B, cái nào để dành.

### 11.1 Đầu vào: nhận file (2-B nhận qua CLI/đường dẫn; Phase 5 mới có upload web)

| Ca | 2-B (CLI, file cục bộ) | Phase 5 (upload web, chưa làm) |
|---|---|---|
| Sai đuôi file (`.exe`, `.zip`...) | Kiểm đuôi trước khi gọi MarkItDown; đuôi lạ → lỗi rõ ràng, không thử parse | Allowlist đuôi (`.docx`, `.pdf`, `.md`) chặn ở tầng API trước khi lưu file |
| File quá lớn | Kiểm `size_bytes` trước khi đọc hết vào bộ nhớ (giới hạn ví dụ 20 MB, đặt hằng số) | Giới hạn ở tầng upload (multipart), trả `413` |
| File rỗng (0 byte) | Từ chối ngay, không gọi MarkItDown | Như 2-B |
| File đặt tên giả (đuôi `.docx` nhưng thật ra là file khác/hỏng) | MarkItDown ném lỗi khi mở → bắt exception, trả lỗi rõ ràng ("không đọc được file, có thể hỏng hoặc sai định dạng"), **không** để traceback thô rơi ra ngoài | Lưu file vào `jobs` với `status=FAILED`, `failure_reason` |
| **Mã độc/macro nhúng** | MarkItDown chỉ trích chữ, không thực thi file (không mở bằng Word/LibreOffice) → rủi ro thực thi mã gần như không có ở 2-B vì chỉ đọc file cục bộ do bạn chỉ định | Rủi ro thật khi cho người ngoài upload; MVP **không** làm quét virus riêng (không có thư viện AV nào được thêm) — mức tối thiểu chấp nhận được: allowlist đuôi + giới hạn kích thước + parser chạy có timeout (một file cố ý phá cũng chỉ làm 1 job lỗi, không treo cả server). Ghi rõ đây là **rủi ro đã biết, chấp nhận cho MVP nội bộ**, không phải "đã xử lý an toàn" |

### 11.2 Parse: MarkItDown có thể trả về gì ngoài "thành công sạch sẽ"

| Ca | Xử lý ở 2-B |
|---|---|
| Chữ trích ra rỗng hoặc quá ngắn (< 200 ký tự) | **Cổng chất lượng** (đã có trong `phase-2.md` §2-B mục 3): từ chối, `status=FAILED`, lý do "có thể là file scan, cần OCR — OCR chưa bật ở Phase 2". Đây chính là chỗ nối với OCR của Phase 5 sau này: cùng một điều kiện, Phase 5 chỉ thêm nhánh gọi `easyocr` thay vì từ chối thẳng |
| Tài liệu có ảnh/sơ đồ nhúng (ví dụ hướng dẫn đường đi bằng hình) | **Dò và cảnh báo, không xử lý ảnh**: kiểm `.docx` có thư mục `word/media/` (hoặc MarkItDown trả placeholder ảnh) → ghi cờ vào `quality_report` (ví dụ `{"has_embedded_images": true}`). Không OCR ảnh, không mô tả ảnh — ghi nhận là giới hạn đã biết (mục đã nói ở lượt trước) |
| Bảng biểu bị hỏng khi convert (mất cột, dính chữ) | Không tự sửa; log cảnh báo "nghi ngờ bảng" vào `quality_report` (đúng thiết kế `system-design.md` §5.1); kiểm tay Markdown sinh ra từ D03b trước khi viết chunker, ghi vào báo cáo 2-F nếu có vấn đề |
| Ký tự lạ / encoding hỏng (mojibake) | Chuẩn hóa NFC là bắt buộc (đã có trong kế hoạch D3/D5); nếu sau NFC vẫn còn ký tự thay thế `` (U+FFFD) tỷ lệ cao → cảnh báo trong `quality_report`, không chặn cứng ở 2-B (dữ liệu giả lập hiện tại sạch) |
| MarkItDown ném exception không rõ nguyên nhân | Bắt tại `parser.py`, gói lại thành lỗi có ngữ cảnh (tên file, đuôi, kích thước), không để traceback thư viện lộ ra CLI |

### 11.3 Chunk: không bao giờ được 0 chunk hoặc chunk vô nghĩa

Đã có trong `phase-2.md` (mục 3–4 của 2-B) nhưng nhắc lại rõ vì đây là lỗi thật Ralion từng gặp:

- Không có heading nào → chia theo đoạn văn (đã có nhánh dự phòng).
- Một section dài bất thường (ví dụ 10.000 từ dồn vào một mục) → chunker vẫn phải cắt được thành nhiều chunk ~256 token, có test riêng cho ca "mục dài" (đã liệt kê ở mục 8 bảng test).
- Một chunk chỉ có tiêu đề, không có nội dung (heading cụt) → gộp vào chunk kế tiếp thay vì tạo chunk rỗng.
- **Cổng cứng:** nếu sau toàn bộ pipeline mà `len(chunks) == 0`, **không** cho phép version chuyển sang `ACTIVE` — dừng ở `FAILED` với lý do rõ ràng. Đây là cổng chất lượng tối thiểu đã ghi trong `phase-2.md`, nhắc lại để không bị bỏ sót khi code.

### 11.4 Embedding: dịch vụ ngoài có thể lỗi

| Ca | Xử lý |
|---|---|
| Modal endpoint timeout/lỗi mạng | Retry có giới hạn (đã có cấu hình `INGESTION_EMBEDDING_MAX_ATTEMPTS` ở mục 5), hết lượt vẫn lỗi → toàn bộ ingest **rollback** (không ghi DB nửa vời), version giữ `FAILED`, không tạo chunk nào thiếu embedding |
| Endpoint trả sai số chiều (không phải 1024) | Kiểm `dimension` trong response trước khi ghi DB (đã có trong bảng "Hiện trạng đã kiểm" của `phase-2.md`); sai thì coi như lỗi cấu hình, dừng ngay, không ghi vector sai kích thước (cột DB là `Vector(1024)` cố định, sai kích thước sẽ tự lỗi ở tầng DB nhưng nên bắt sớm hơn ở tầng service để thông báo rõ nghĩa) |
| Endpoint trả `401`/`403` (khóa sai/hết hạn) | Không retry vô ích (lỗi xác thực không tự hết bằng cách thử lại) — phát hiện mã trạng thái, dừng ngay với thông báo "kiểm tra EMBEDDING_API_KEY" |
| Batch > 32 chuỗi (giới hạn API Modal) | `ModalEmbeddingAdapter` tự chia lô ≤ 32 (đã có trong cây file mục 4), không phải lo ở tầng gọi |

### 11.5 Ghi DB: toàn vẹn dữ liệu

- **Một transaction** cho toàn bộ bước 4 (document_version + sections + chunks + audit_log) — lỗi ở bất kỳ đâu trong đó thì **rollback toàn bộ**, không để lại dữ liệu nửa vời (đã có trong kiến trúc mục 2, nhắc lại vì đây là điểm dễ quên khi viết code từng bước).
- **Idempotent theo `content_checksum`** (INV5, đã có): nạp lại file giống hệt → phát hiện checksum trùng, bỏ qua, không tạo bản ghi mới, trả kết quả "đã tồn tại" thay vì lỗi.
- **Cùng `version_label` nhưng nội dung khác** (ai đó sửa file rồi nạp lại với cùng nhãn phiên bản) → từ chối theo INV5, không ghi đè âm thầm.

### 11.6 Trạng thái lỗi có sẵn trong model — dùng đúng, không tự bịa thêm

`VersionStatus` (`backend/src/model/enums.py`, đã có từ 2-A) đã có sẵn `PROCESSING`, `PENDING_REVIEW`, `ACTIVE`, `ARCHIVED`, `FAILED` — mọi ca lỗi ở trên đều kết thúc ở `FAILED` với `failure_reason` (cột đã có trong `document_versions`), **không** cần thêm cột hay enum mới cho 2-B.

### 11.7 Việc rõ ràng KHÔNG làm ở 2-B (để tránh phình phạm vi, đúng cảnh báo đã có trong `phase-2.md` mục 9)

- Không viết OCR thật (chỉ viết đúng điều kiện phát hiện + từ chối kèm lý do, đã đủ để Phase 5 cắm `easyocr` vào sau mà không sửa lại cổng chất lượng).
- Không viết quét virus/mã độc.
- Không xử lý ảnh nhúng (chỉ gắn cờ cảnh báo).
- Không có upload API/job nền (CLI đồng bộ, đúng quyết định D4).

## 12. Việc cần bạn quyết trước khi tôi code

1. **Mục 6:** chọn Lựa chọn A (dùng tạm endpoint Ralion) hay B (deploy riêng cho VSF) — hay để tôi tự quyết theo đề xuất (A cho 2-B, B trước production)?
2. Xác nhận phạm vi CLI-only (D4 trong `phase-2.md`) — không viết API upload ở bước này (đúng, để dành Phase 5)?
3. Nhánh làm việc: tiếp tục trên `phase-4-auth` (đang có, chưa push) hay tách nhánh mới `phase-2-b-ingest`?
4. **Mục 11:** xác nhận danh sách xử lý ngoại lệ trên là đủ cho 2-B (CLI, file cục bộ do bạn chỉ định) — đồng ý để quét virus/OCR thật/xử lý ảnh nằm lại ở Phase 5, chỉ làm phần "gắn cờ cảnh báo + từ chối rõ lý do" ở 2-B?

Bạn duyệt (kể cả trả lời "dùng mặc định hết") thì tôi bắt đầu viết code theo đúng cây file ở mục 4, cộng các nhánh xử lý lỗi ở mục 11.
