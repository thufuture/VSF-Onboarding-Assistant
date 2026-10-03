# Nạp tài liệu, chatbot Viga và tạo task bằng AI — công nghệ, luồng đầy đủ, hiện trạng

> Cập nhật 01/10/2026, đối chiếu với code trong `backend/src` và `frontend/src` ở nhánh `feat/portal-plan`.
> **Cập nhật cuối 01/10/2026: toàn bộ thứ tự thực hiện ở mục 0.3 đã được cài đặt và kiểm thử; kết quả, kiến trúc thật và số đo
> thật nằm ở mục 18.** Mục 1 đến 11 mô tả hệ thống **trước đợt cài đặt này** (giữ lại để đối chiếu); mục 12 đến 17 là bản thiết kế
> gốc, mỗi mục có ghi chú trạng thái ở đầu. Mục 0 là bảng quyết định đã chốt.
> Không ghi khóa API hay mật khẩu; giá trị cấu hình nằm trong `backend/.env` (đã bị `.gitignore`).
> Các sơ đồ dưới đây vẽ bằng ký tự để xem được ở mọi trình soạn thảo; mũi tên `--->` là chiều dữ liệu hoặc chiều xử lý.

## Mục lục

0. Bảng quyết định đã chốt và thứ tự thực hiện
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
12. Đo lường, baseline, benchmark và giám sát (giai đoạn A đã cài đặt; B và C chưa làm)
13. Lộ trình xử lý tài liệu từ có cấu trúc đến rối (bậc 1, 2, 3, 5 đã cài đặt)
14. Chạy nền và hiện tiến trình phần trăm cho nạp tài liệu và tạo task bằng AI (đã cài đặt)
15. Phân tích chức năng của Viga: làm gì, dùng công cụ nào (đã cài đặt)
16. Quản lý tài liệu theo phiên bản (đã cài đặt, trừ so sánh khác biệt và nối lại nguồn của task)
17. Viga dạng agent LLM chọn công cụ, các đường thoát và gợi ý tạo ticket cho HR (đã cài đặt)
18. Kết quả cài đặt, kiến trúc thật, số đo thật và những gì chưa làm

## 0. Bảng quyết định đã chốt và thứ tự thực hiện

> Gom từ các câu "điểm cần anh quyết" rải ở các mục 4.2b, 6.2, 12.9, 13.7, 14.9, 15, 16.9, 17.10. **Khi một câu ở mục con mâu thuẫn với bảng
> này thì theo bảng này.** Các câu chưa có trong bảng vẫn mở ở mục con tương ứng.

### 0.1 Quyết định đã chốt (01/10/2026)

| # | Chủ đề | Quyết định | Mục chi tiết |
|---|---|---|---|
| 1 | Định tuyến Viga | **LLM định tuyến là chính** (chọn công cụ trong danh sách đóng) + **lối tắt luật cho 3 câu**: "hôm nay làm gì", "tiếp theo làm gì", "tiến độ của tôi". Luật ở 15.3c chỉ còn làm lối tắt | 17, 15.3c |
| 2 | Lưu hội thoại | **Có**, trong PostgreSQL (`chat_conversations`, `chat_messages`); giao diện chỉ gửi `conversation_id`. Bỏ cách "giao diện gửi lịch sử" (M1 cũ) | 6.2 |
| 3 | Dữ liệu cho LLM định tuyến | **Có, tối thiểu**: chỉ mã việc, tên việc, trạng thái. **Không gửi** tên, email, phòng ban của nhân viên | 15.3b, 17.1 |
| 4 | Tải file và embedding | **Hai bước**: (a) tải file = đọc, lưu file gốc, tạo **bản nháp** (nhanh, chưa embedding); (b) **kích hoạt** = cắt chunk, embedding, đóng bản cũ, chạy nền có phần trăm. Tài liệu mới hoàn toàn có ô "tải và kích hoạt luôn" | 14, 16 |
| 5 | Sửa bản cũ | **Bản đầu chỉ làm**: sao chép thành bản mới rồi sửa, và sửa trực tiếp **bản nháp**. Sửa tại chỗ bản cũ **hoãn** | 16.2b |
| 6 | "Việc hiện tại" | Ghi `last_opened_task_id` và `last_opened_at` trên `employee_journeys`, hiệu lực **30 phút**; **không** thêm trạng thái "đang làm" | 15.3e |
| 7 | Ticket cho HR | Gửi tới **HR phòng ban** của nhân viên; nhân viên **xem và sửa** trước khi gửi; **5 ticket/người/ngày**; chặn câu giống nhau trong 10 phút | 17.5 |
| 8 | Lưu nội dung hội thoại | **Có**, giữ **90 ngày** rồi tự xóa; người dùng xóa được cuộc của mình; không gửi nội dung sang Langfuse; HR **không đọc** hội thoại cá nhân, chỉ thấy câu chưa trả lời được đã **ẩn danh** | 6.2 |
| 9 | Đo lường | **Làm trước** (giai đoạn A: token, độ trễ, bảng `llm_calls`); code đã viết đang cất trong `git stash` (tên `do-luong-llm-calls-chua-duyet`) để dùng lại | 12 |
| 10 | Đơn giá | **DeepSeek đã tra (01/10/2026)**, xem 12.11: `deepseek-flash` giờ cao điểm 0,30 USD vào (cache miss) và 1,20 USD ra mỗi 1 triệu token, giờ thấp điểm bằng một nửa. **Modal (embedding) chưa có giá**: anh cung cấp cách tính tiền; chưa có thì cột chi phí embedding hiện 0 | 12.9, 12.11 |
| 11 | Rerank | **Hoãn** đến khi kho đủ lớn và có bộ câu hỏi chuẩn | 4.2b |
| 12 | OCR | **Hoãn**; giai đoạn này chỉ docx và PDF có lớp chữ. **LLM fallback chia mục có làm** | 13 |
| 13 | Khoảng cách và bố cục | Đã dựng xong khu nhân viên `/me`; Viga của nhân viên hiện là **bản dựng** | 15.1 |

### 0.2 Các mâu thuẫn và lỗ hổng đã xử lý trong tài liệu này

| Chỗ cấn | Cách xử lý |
|---|---|
| 15.3c (luật làm chính) và mục 17 (LLM làm chính) | Theo mục 17; 15.3c chỉ còn là lối tắt luật |
| 6.1 và 6.2 nói hai cách lưu hội thoại | Gộp theo 6.2 (máy chủ lưu), bỏ M1 |
| Mục 14 và 16 mâu thuẫn về lúc embedding | Theo quyết định 4 ở trên |
| Snapshot "không gửi LLM ngoài" và LLM định tuyến cần nhận | Theo quyết định 3 (chỉ mã/tên/trạng thái việc) |
| Nhân viên không còn dùng trang chat thật | Sửa mục 4, 8, 10.1, 11 |
| Bản cũ không tìm được khi đổi model embedding | Embedding lại trong job kích hoạt (16.2b) |
| Vòng đời thiếu ARCHIVED → ACTIVE | Thêm ở 16.3 |
| Trùng tên file Cloudinary khi sao chép bản | Tên theo `file_checksum`; bản sao chép không tải lại (16.7) |
| Ai quyết `OUT_OF_SCOPE` | Bộ lọc từ khóa trước LLM + kiểm tra trong prompt (17.5b) |
| Phần trăm thiếu bước LLM chia mục | Thêm ở 14.4 |
| Lệch số bậc trong mục 13 | Thống nhất "sau bậc 1 đến 4" |

### 0.3 Thứ tự thực hiện

> **Cả 7 bước dưới đây đã làm xong ngày 01/10/2026; trạng thái chi tiết, chỗ nằm trong code và phần chưa làm: xem 18.1.**

| Thứ tự | Việc | Phụ thuộc |
|---|---|---|
| 1 | **Đo lường giai đoạn A** (mục 12), dùng lại code đã cất | Không |
| 2 | Sửa lỗi 1, 2, 3 ở mục 10.2 (đóng bản cũ, lọc tài liệu ngừng sử dụng, đường lỗi `/chat/ask`) | Không |
| 3 | Khung hội thoại (6.2) và ghi "việc vừa mở" (15.3e) | 1 |
| 4 | Công cụ lộ trình, LLM định tuyến, đường thoát (15, 17) | 1, 3 |
| 5 | Ticket cho HR và trang "Ticket sự cố", "Phản hồi Viga" (17.5) | 4 |
| 6 | Tải nháp và kích hoạt có tiến trình (14, 16) | 1 |
| 7 | Xử lý file thiếu heading (13) | 1 |

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

### 1.1 Ba khái niệm hay bị hỏi: markitdown, SHA-256 hai lần, file gốc lên Cloudinary

Một file HR tải lên đi ra **ba thứ khác nhau**, mỗi thứ phục vụ một việc:

```text
                          file .docx / .pdf / .md  (bytes gốc)
                                     |
          +--------------------------+---------------------------+
          |                          |                           |
          v                          v                           v
   SHA-256 của FILE            markitdown                 đẩy bytes gốc lên
   -> file_checksum            file -> Markdown           Cloudinary (hoặc đĩa)
   ("dấu vân tay" của          (chữ thuần, có tiêu đề,    -> storage_key = URL
    đúng bộ byte đã tải)        bảng; chuẩn hóa NFC)         để HR "Xem file gốc"
                                     |
                                     v
                             SHA-256 của MARKDOWN
                             -> content_checksum
                             ("dấu vân tay" của NỘI DUNG chữ)
                                     |
                                     v
                  chia section -> chunk -> embedding -> ghi DB (nội dung để Viga đọc)
```

**markitdown là gì và làm gì.** Thư viện Python (`markitdown[docx,pdf]`) đọc file văn phòng rồi trả về **Markdown thuần**:
tiêu đề thành `#`, danh sách thành `-`, bảng thành bảng Markdown. Hệ thống cần bước này vì cả cắt đoạn, tìm kiếm và hiển
thị trang giấy đều làm việc trên **chữ**, không đọc được `.docx` hay `.pdf` thô. Sau khi đọc, văn bản được chuẩn hóa
Unicode NFC (cùng một chữ có dấu chỉ có một cách mã hóa, nếu không thì cùng nội dung có thể cho hai checksum khác nhau và
phép so khớp trích dẫn nguyên văn bị lệch). Giới hạn cần biết: không có OCR, nên file scan (chữ nằm trong ảnh) cho ra
dưới 200 ký tự và bị từ chối; ảnh nhúng trong `.docx` chỉ được đánh cờ cảnh báo chứ không được đọc.

**SHA-256 là gì và vì sao tính hai lần.** SHA-256 biến một chuỗi byte bất kỳ thành 64 ký tự hex; đổi một byte thì kết quả
đổi hoàn toàn, cùng đầu vào luôn ra cùng kết quả. Đó là "dấu vân tay". Hệ thống lấy **hai** dấu vân tay vì trả lời hai
câu hỏi khác nhau:

| Checksum | Tính trên | Câu hỏi nó trả lời | Dùng ở đâu |
|---|---|---|---|
| `file_checksum` | **bytes của file gốc** | "File này có đúng là file đã tải không, có bị đổi byte nào không?" | Lưu trong `document_versions` để đối chiếu, truy vết |
| `content_checksum` | **chữ Markdown** sau markitdown và NFC | "**Nội dung chữ** có thật sự khác bản trước không?" | Chặn nạp trùng (cùng nhãn phiên bản + cùng nội dung thì không nạp lại, `created=false`); đặt tên file trên Cloudinary hoặc đĩa |

Vì sao không chỉ dùng một: có những thay đổi làm **byte đổi nhưng chữ y nguyên**, ví dụ chỉ sửa định dạng (font, màu,
căn lề), lưu lại bằng công cụ khác, hoặc "Save as" ra bản mới (Word ghi lại cả thời gian sửa và thông tin tác giả trong
file). Chỉ có `file_checksum` thì hệ thống tưởng đó là nội dung mới và tốn tiền embedding nạp lại vô ích. Chỉ có
`content_checksum` thì mất khả năng chứng minh file lưu trữ là bản byte-nguyên-vẹn. Hai cái bổ sung cho nhau.
(Ngoài ra mỗi chunk còn có `content_hash` riêng, cũng SHA-256, để biết chunk nào không đổi.)

**File gốc lên Cloudinary.** Mục đích duy nhất của việc lưu file gốc là cho HR **xem hoặc tải lại đúng file đã nạp**
(nút "Xem file gốc"); Viga và AI tạo task **không đọc file gốc**, chúng đọc phần Markdown đã nằm trong PostgreSQL. Cách lưu:

- Chọn bằng cấu hình `STORAGE_PROVIDER`: `cloudinary` (dev hiện tại) hoặc `local` (đĩa, mặc định cho CI).
- Cloudinary: bytes được đẩy vào thư mục `vsf-documents/` **bên trong Cloudinary** (không phải nơi lưu thứ hai; chỉ để tách
  file của dự án này khỏi dự án Ralion đang dùng chung tài khoản), `public_id` là `<content_checksum><đuôi file>`, bật
  `overwrite`; DB chỉ lưu `secure_url`, không lưu file. Đuôi file **phải** nằm trong tên, nếu thiếu thì trình duyệt tải về
  một file toàn mã băm không có `.docx` (lỗi thật đã gặp).
- Lưu file xảy ra **trước** khi ghi DB; lưu lỗi thì không ghi gì (không để lại bản ghi trỏ vào file không tồn tại).
- Tên file theo checksum nên nạp lại cùng nội dung không sinh file trùng.

**Có bắt buộc file Word hoặc PDF phải có tiêu đề (heading) không?** Không. File chỉ cần đúng đuôi (`.docx`, `.pdf`,
`.md`), không rỗng, dưới 20 MB và đọc ra được ít nhất 200 ký tự chữ. Không có heading vẫn nạp được, nhưng chất lượng giảm:

| Tình huống | Hệ thống làm gì | Hệ quả |
|---|---|---|
| Có heading (Word dùng kiểu Heading 1 đến 3) | Cắt thành nhiều section theo `#`, `##`, `###`, mỗi section cắt tiếp thành chunk ~256 từ | Tốt nhất: trích nguồn đúng mục, có mục lục khi xem tài liệu |
| Không có heading | **Cả văn bản là một section**; chunk vẫn cắt theo đoạn văn nên tìm kiếm vẫn chạy | Viga lấy cả section để đọc và trích nguồn nên section khổng lồ làm nguồn kém chính xác, ăn hết ngân sách 3000 token, không có mục lục; AI tạo task cũng kém vì không có mốc "mục nào" để trích |
| Tiêu đề chỉ in đậm hoặc cỡ chữ lớn, không dùng kiểu Heading | markitdown **không** coi là heading | Giống trường hợp không có heading |
| PDF | Thường chỉ ra chữ thuần, ít khi giữ được heading | Thường thành một section lớn; nên ưu tiên `.docx` hoặc `.md` có heading chuẩn |

Khuyến nghị cho HR: dùng kiểu **Heading 1, 2, 3** của Word cho các mục. Có thể bổ sung một **cảnh báo khi tải lên** nếu file
chỉ ra một section (hiện chưa có), để HR biết trước thay vì phát hiện khi Viga trích dẫn kém.

**Một điểm cần lưu ý (rủi ro thật, chưa xử lý):** tên file trên Cloudinary lấy từ `content_checksum` (checksum của
**chữ**), không phải `file_checksum` (checksum của **byte**). Hai file khác nhau về byte nhưng cùng chữ (ví dụ cùng một
tài liệu lưu thành `.docx` rồi xuất `.pdf`, hoặc đã sửa định dạng) mà cùng đuôi sẽ cùng `public_id`, và `overwrite` làm file
sau **ghi đè** file trước. Với `.docx` và `.pdf` thì đuôi khác nên không đụng nhau; với hai `.docx` cùng chữ khác định dạng
thì file gốc của phiên bản cũ bị thay mà DB vẫn ghi `file_checksum` cũ. Cách sửa gọn: đặt tên theo `file_checksum`. Chưa sửa,
chờ anh quyết.

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

**Đặc điểm cần biết (đang là điểm yếu, sẽ sửa — xem mục 14):** nạp chạy **đồng bộ trong một request HTTP**. Không có
hàng đợi, không có thanh tiến độ, không có trạng thái `PROCESSING` hay `FAILED` được lưu. File lớn hoặc dịch vụ embedding
chậm làm request lâu (timeout đọc embedding là 120 giây mỗi lô) và **người dùng chỉ thấy vòng xoay, không biết đang ở đâu,
còn bao lâu, hay đã hỏng**. **Yêu cầu đã chốt: giao diện phải có tiến trình theo phần trăm cho cả "nạp tài liệu" và
"tạo task bằng AI".**

### 3.3 Sau khi nạp, HR làm được gì (trang Tài liệu)

- Xem danh sách: nhóm, số section, trạng thái, task đang dùng, người phụ trách.
- **Xem nội dung** đã parse dạng trang giấy có mục lục đứng yên (`GET /chat/documents/{version_id}`).
- **Xem file gốc**: chuyển hướng tới Cloudinary hoặc trả file cục bộ (`GET /portal/documents/{id}/original`).
- **Sửa** tên và nhóm; **ngừng sử dụng** và **kích hoạt lại** (không xóa cứng, có modal xác nhận).

## 4. Chatbot Viga: lấy tài liệu để trả lời như thế nào

Điểm vào: `POST /api/v1/chat/ask` (bất kỳ vai trò nào, bắt buộc đã đăng nhập). **Hiện chỉ trang chat của HR và Admin gọi API này;**
nhân viên vào `/chat` bị chuyển về `/me`, và ngăn Viga của nhân viên hiện là **bản dựng chưa gọi API** (mục 15.1). Phần mềm **không nhớ hội thoại** (xem mục 6): mỗi câu hỏi xử lý độc lập.

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
      |      (RRF lấy ~30 chunk ứng viên mỗi câu con)
      v
 [E] RERANK (ĐỀ XUẤT, chưa bật; hiện chỉ trả lại nguyên danh sách)
      |   cross-encoder chấm lại từng cặp (câu con, chunk) -> giữ top ~8 chunk -> mới gộp về SECTION cha
      |   chỉ rerank khi có >= 2 chunk ứng viên; lỗi / quá hạn -> LÙI VỀ thứ tự RRF, không làm hỏng câu trả lời
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

### 4.2b Rerank (đề xuất — **HOÃN, làm sau khi có số đo**)

> **Quyết định: chưa làm rerank ở giai đoạn này.** Hai lý do:
> 1. **Rerank làm mỗi câu hỏi chậm hơn và tốn thêm**: thêm một lần gọi mô hình chấm điểm cho cả tập ứng viên (khoảng 30 chunk),
>    nằm trên đường đi của mọi câu hỏi. Chậm thêm bao nhiêu **phải đo**, không đoán.
> 2. **Bài toán chưa cần nó.** Kho hiện mới có **một tài liệu (34 chunk)** trong khi tìm kiếm lấy tới top 30 mỗi đường, nên gần
>    như mọi chunk đã là ứng viên và thứ tự xếp lại không đổi được gì. Rerank chỉ đáng khi kho đủ lớn để đoạn đúng bị đẩy ra
>    ngoài top ứng viên hoặc ngoài ngân sách 3000 token.
>
> **Khi nào quay lại:** có bộ câu hỏi chuẩn (mục 12.6) và kho đã lớn; đo `hit@k` và tỉ lệ trích đúng đoạn. Chỉ bật khi so với
> baseline **cải thiện rõ** và độ trễ thêm nằm trong ngưỡng. Cổng `RerankPort` vẫn chừa chỗ ở bước [E], nên làm sau không phải sửa luồng.
> Nội dung bên dưới giữ lại làm tài liệu thiết kế cho lần so sánh đó.

**Vì sao cần:** RRF trộn hai danh sách xếp hạng (BM25 và vector) rất tốt để *tìm ứng viên*, nhưng không "đọc" cặp câu hỏi và
đoạn văn cùng lúc nên đôi khi đoạn đúng nằm ở hạng 6–15 và bị cắt khỏi ngân sách 3000 token. Rerank chấm lại **chỉ tập ứng
viên nhỏ** (khoảng 30 chunk) bằng mô hình đọc cả hai, rồi giữ phần đứng đầu.

```text
  BM25 top 30  +  Vector top 30
            \      /
             RRF (k=60)  ->  ~30 chunk ứng viên
                   |
                   v
        RERANK: cross-encoder chấm điểm (câu con, chunk)  -> sắp lại -> giữ top ~8
                   |   (lỗi, quá hạn, hoặc < 2 ứng viên -> dùng nguyên thứ tự RRF)
                   v
        gộp về section cha  ->  cắt theo ngân sách 3000 token  ->  LLM trả lời
```

| Phương án | Ưu | Nhược | Ghi chú |
|---|---|---|---|
| **Cross-encoder đa ngôn ngữ** (cùng họ BGE: bộ rerank chạy trên Modal như BGE-M3 hiện tại) | Rẻ hơn LLM, nhanh, tất định, đã quen hạ tầng Modal | Thêm một dịch vụ để vận hành; chất lượng tiếng Việt **phải đo, không giả định** | **Đề xuất thử trước** |
| LLM rerank (cho DeepSeek xếp hạng) | Không thêm hạ tầng | Tốn token, chậm, không tất định, dễ lộ ra thêm một lần gọi mỗi câu | Chỉ để so sánh |
| Không rerank, chỉ chỉnh top_k/RRF | Không thêm gì | Giới hạn chất lượng | Mốc so sánh |

Cổng đã chừa sẵn ở bước [E] nên đổi nhỏ: thêm một `RerankPort` (adapter thật và giả) như `EmbeddingPort`.

**Điều kiện bật (đo, không cảm tính):** chạy bộ câu hỏi chuẩn ở mục 12.6 với ba cấu hình (RRF, RRF + cross-encoder, RRF + LLM
rerank), so `hit@1/3/5`, tỉ lệ trích đúng đoạn, thêm độ trễ (p95) và chi phí mỗi câu. **Chỉ bật khi cải thiện rõ** so với
baseline và độ trễ thêm nằm trong ngưỡng anh chốt. Mọi lần gọi rerank ghi vào số liệu (mục 12).

**Điểm cần anh quyết:** (1) thử cross-encoder trên Modal trước hay đi thẳng so cả LLM rerank; (2) ngưỡng độ trễ thêm tối đa cho
rerank (ví dụ thêm bao nhiêu mili-giây thì còn chấp nhận); (3) giữ top bao nhiêu chunk sau rerank (đề xuất ~8, chỉnh theo đo).

### 4.3 Kết quả một câu trả lời

| Trường | Ý nghĩa |
|---|---|
| `question` | Câu con đã viết lại |
| `response_type` | `ANSWER` hoặc `NO_BASIS` |
| `reason_code` | Lý do khi `NO_BASIS`: `no_evidence`, `out_of_scope`, `validation_failed`, `llm_contract_error`, `llm_skipped_question` |
| `text`, `quote` | Câu trả lời ngắn và câu trích nguyên văn từ tài liệu |
| `source` | Tên tài liệu, nhãn phiên bản, tiêu đề mục, đường dẫn file, `version_id` để mở nội dung |

Một câu hỏi nhiều ý cho ra nhiều claim độc lập: ý nào có căn cứ thì trả lời, ý nào không thì nói thẳng "chưa có căn cứ".

### 4.4 Viga tìm trong phiên bản nào (đã đối chiếu `hybrid_search.py`)

Cả hai truy vấn (BM25 và vector) dùng chung một bộ lọc cứng trên phiên bản:

```text
 v.status = 'ACTIVE'
 AND v.effective_from <= ngày_hỏi
 AND (v.effective_to IS NULL OR v.effective_to >= ngày_hỏi)
 AND chunk.embedding_model_version = phiên bản model embedding hiện tại
```

| Loại | Viga có tìm thấy không |
|---|---|
| Phiên bản `ARCHIVED`, `PROCESSING`, `FAILED`, `PENDING_REVIEW` | **Không** |
| Phiên bản cũ đã có `effective_to` trước ngày hỏi | **Không** |
| Phiên bản chưa tới `effective_from` | **Không** |
| Phiên bản `ACTIVE` đúng khoảng hiệu lực | **Có** |
| Tài liệu "ngừng sử dụng" (`documents.status = ARCHIVED`) mà phiên bản vẫn `ACTIVE` | **Có, đây là lỗi 2 (mục 10.2)** |
| Cột `confidentiality` (độ nhạy cảm) | **Không dùng làm bộ lọc**: mọi người dùng đăng nhập thấy chung toàn kho (đúng quyết định không lọc theo phòng ban) |

**Không có logic "ưu tiên bản mới nhất".** Việc chỉ thấy bản đang áp dụng đến từ một ràng buộc khác: DB cấm hai phiên bản `ACTIVE`
**chồng ngày hiệu lực** (`btree_gist EXCLUDE`), nên tại một ngày hỏi mỗi tài liệu chỉ có tối đa một bản hợp lệ. Xếp hạng chỉ dựa trên độ
liên quan (BM25 + vector + RRF), không cộng điểm cho bản mới hơn.

Các chỗ hở: (1) lỗi 1, nạp bản mới đang thất bại vì bản cũ không được đóng; khi sửa phải đóng bản cũ đúng ngày, nếu không sẽ bị DB
chặn hoặc để hở một khoảng không có bản nào (Viga trả "chưa có căn cứ"); (2) lỗi 2, tài liệu ngừng sử dụng vẫn bị tìm thấy;
(3) hai **tài liệu khác nhau** nói cùng một việc (ví dụ bản 2024 nạp thành tài liệu riêng chứ không phải phiên bản mới) đều `ACTIVE`,
Viga có thể trích cả hai mà không biết cái nào mới hơn; chỉ quản lý đúng khi nạp bản mới như **phiên bản** của cùng `source_key`
(xem mục 16).

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

### 6.1 Kế hoạch bộ nhớ (đề xuất gọn, chưa code)

Làm **từng mức**, mức sau chỉ làm khi mức trước chạy ổn và có số đo.

| Mức | Việc | Cách làm | Trạng thái |
|---|---|---|---|
| ~~M1. Giao diện gửi lịch sử~~ | | | **Bỏ**, thay bằng 6.2 (máy chủ lưu và tự đọc theo `conversation_id`) |
| **M2. Biết người hỏi là ai và đang ở đâu** | Viga biết ngày đang làm, việc làm được, việc bị khóa, việc vừa mở | Backend tự lấy từ lộ trình thật; chỉ dùng cho bước định tuyến (mục 17), **không** vào bước trích dẫn tài liệu. Gửi cho LLM chỉ **mã, tên, trạng thái việc** (quyết định 3) | Đã chốt, làm theo 15.3b và 15.3e |
| **M3. Lưu lịch sử trên máy chủ** | Tải lại trang vẫn còn; nhiều cuộc trò chuyện | Theo 6.2 | Đã chốt (quyết định 2 và 8) |

Không làm: bộ nhớ dài hạn "học về người dùng", và không đưa lịch sử vào bước tìm kiếm.
Đo: tỉ lệ câu nối tiếp được hiểu đúng (thêm nhóm câu nối tiếp vào bộ câu hỏi chuẩn, mục 12.6), token thêm mỗi câu, độ trễ thêm.

### 6.2 Hội thoại kiểu ChatGPT: nhiều cuộc trò chuyện, xem lại, mở cuộc mới (đề xuất, chưa code)

Mục tiêu giao diện: thanh bên danh sách **cuộc hội thoại** của chính người dùng (xem lại, mở lại, mở **cuộc mới**, đổi tên, xóa),
và trong một cuộc thì Viga **nhớ vài lượt gần nhất** để hiểu câu nối tiếp.

**Lưu ở đâu để vừa nhanh vừa bền** — không cần công nghệ mới:

| Lớp | Nơi lưu | Dùng để | Vì sao |
|---|---|---|---|
| **Gần (vài lượt cuối)** | State trong trình duyệt (để hiển thị) **và** đọc lại từ DB theo `conversation_id` khi cần dựng ngữ cảnh | Đưa 4–6 lượt gần nhất vào bước viết lại câu hỏi | Một truy vấn có chỉ mục theo `conversation_id` + thời gian chỉ mất vài mili-giây, **nhỏ hơn nhiều so với một lần gọi LLM**, nên không cần bộ nhớ đệm riêng |
| **Lâu (toàn bộ)** | **PostgreSQL**: bảng `chat_conversations` (chủ sở hữu, tiêu đề, thời gian) và `chat_messages` (vai, nội dung, `response_type`, nguồn trích, thời gian) | Danh sách cuộc hội thoại, mở lại, thống kê, tìm câu hỏi chưa trả lời được | Đã có sẵn PostgreSQL; một nguồn sự thật |
| Bản tóm tắt cuộc dài (sau này) | Cột `summary` trong `chat_conversations`, cập nhật theo lô | Cuộc quá dài: tóm tắt phần cũ + giữ nguyên vài lượt cuối | Giữ token ổn định; chỉ làm khi đo thấy cuộc dài làm tốn tiền |
| Redis hoặc cache ngoài | **Chưa cần** | | Chỉ cân nhắc khi chạy nhiều worker **và** đo thấy đọc DB là điểm nghẽn |

**Cách nhớ vài câu trong ngữ cảnh (không làm nhiễm nguồn):**

```text
 câu hỏi mới + conversation_id
      |
      v
 đọc N lượt gần nhất của cuộc đó (N nhỏ, cắt độ dài mỗi lượt)
      |
      v
 CHỈ bước viết lại câu hỏi (LLM lần 1) nhận lịch sử  ->  câu hỏi độc lập
      |      ví dụ: "còn trường hợp thử việc thì sao?"  ->  "Nhân viên thử việc được nghỉ phép năm không?"
      v
 tìm kiếm, trả lời, kiểm chứng như hiện tại, chỉ trên CÂU ĐỘC LẬP
      |
      v
 ghi 2 dòng vào chat_messages (câu hỏi, câu trả lời kèm nguồn); cập nhật tiêu đề cuộc nếu là lượt đầu
```

Lịch sử **không bao giờ đưa vào bước tìm kiếm hay trích dẫn**, nên câu trả lời trước không thể bị coi là "bằng chứng" cho câu sau.

**Bảo mật và quyền riêng tư (cần anh chốt):**
- Mỗi người **chỉ thấy cuộc hội thoại của chính mình**; HR không đọc được nội dung hội thoại cá nhân, chỉ thấy **danh sách câu hỏi không trả lời được** đã ẩn danh (để bổ sung tài liệu).
- Lưu nội dung câu hỏi vào DB là **đổi quy tắc đang giữ** (hiện hệ thống không lưu câu hỏi, chỉ số lượng và độ dài). Cần anh chốt: lưu bao lâu (ví dụ 90 ngày), người dùng có xóa được không, có lưu cho câu hỏi về thông tin cá nhân không.
- Nội dung hội thoại **không gửi** cho dịch vụ giám sát bên ngoài (Langfuse vẫn chỉ nhận số liệu).

**Điểm cần anh quyết:**
1. Có lưu hội thoại trên máy chủ (bảng `chat_conversations`/`chat_messages`) không? Đề xuất: **có**, vì anh muốn xem lại và mở cuộc mới như ChatGPT.
2. Hạn lưu và quyền xóa của người dùng.
3. Số lượt gần nhất đưa vào bước viết lại (đề xuất 4–6, chỉnh theo đo).
4. Tiêu đề cuộc hội thoại: lấy từ câu hỏi đầu (rẻ) hay nhờ LLM đặt (tốn thêm một lần gọi)? Đề xuất: lấy từ câu hỏi đầu.
5. Có cần tóm tắt cuộc dài ngay không, hay để sau khi đo?

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
(xem mục 6 và 15.3e). Bước 9 của sơ đồ trên mô tả đích đến: hiện nhân viên chưa hỏi được Viga thật (mục 17).

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

### 9.1 Metadata trong DB và phần LLM thật sự nhìn thấy (đã đối chiếu code)

| Bảng | Metadata | Ý nghĩa |
|---|---|---|
| `documents` | `title`, `category_id`, `owner_id`, `source_key`, `language`, `tags`, `confidentiality`, `content_kind`, `status` | Tài liệu là gì, của ai, nhóm nào, có nhạy cảm không, còn dùng không |
| `document_versions` | `version_label`, `revision_no`, `status`, `effective_from/to`, `original_filename`, `mime_type`, `file_checksum`, `content_checksum`, `parser`, `page_count`, `quality_report` (JSON), `embedding_model_version`, `summary`, `sample_questions`, `aliases` | Phiên bản nào đang hiệu lực, file gốc, chất lượng đọc file |
| `document_sections` | `heading`, `section_path`, `page_start/end`, `token_count` | Mục nào trong tài liệu |
| `document_chunks` | `heading`, `chunk_index`, `page_start/end`, `anchor`, `embedding_text`, `lexical_text`, `embedding` (vector 1024), `content_hash`, `token_count` | Đoạn nhỏ để **tìm kiếm** |

Nhiều cột (`summary`, `sample_questions`, `aliases`, `tags`, `page_*`, `anchor`, `section_path`) **có trong schema nhưng code hiện chưa điền**,
vì chưa có bước sinh tóm tắt hay câu hỏi mẫu khi nạp.

**Metadata dùng để tìm (máy dùng, LLM không thấy):** `embedding_text` = tiêu đề mục + nội dung chunk (đưa vào embedding, nên tiêu đề giúp
vector biết chunk thuộc mục nào); `lexical_text` = nội dung đã tách từ tiếng Việt cho BM25; `status`, `effective_from/to`,
`embedding_model_version` dùng làm bộ lọc (mục 4.4).

**Metadata thật sự đưa cho LLM (hỏi đáp Viga):** với mỗi section tìm được, prompt chỉ có một dòng đầu rồi tới nội dung:

```text
[Đoạn — chunk_id=123 — <tên tài liệu> — bản <nhãn phiên bản> — <tiêu đề mục>]
<toàn bộ nội dung section>
```

LLM chỉ nhận: `chunk_id` (để trích nguồn), **tên tài liệu**, **nhãn phiên bản**, **tiêu đề mục** và nội dung. Nó **không** thấy loại tài liệu, chủ sở hữu,
tag, độ nhạy cảm, ngày hiệu lực, số trang. Lúc **tạo task bằng AI** còn ít hơn: chỉ `section_id`, tiêu đề mục, nội dung.

Hệ quả: **tiêu đề mục là metadata quan trọng nhất** cho cả tìm kiếm lẫn LLM, nên tài liệu không có heading (mục 13) làm Viga kém đi đúng ở chỗ này.
Ngày hiệu lực không được đưa vào prompt nên câu "chính sách này còn hiệu lực không?" LLM không có dữ kiện để tự trả lời. Đề xuất bổ sung (chờ anh quyết):
nhóm tài liệu, ngày hiệu lực, và `summary` sinh khi nạp.

## 10. Hiện trạng trước đợt cài đặt 01/10/2026: đã làm, lỗi đã xác minh, chưa làm

> **Cập nhật 01/10/2026:** ba lỗi ở 10.2 **đã sửa và có test hồi quy**; phần lớn 10.3 đã làm. Xem 18.1 và 18.8 để biết hiện trạng mới và những gì còn thiếu.

### 10.1 Đã làm và có kiểm chứng

- Toàn bộ luồng ở mục 8 chạy trên PostgreSQL thật; có test tích hợp cho upload
  (`test_portal_document_upload_api.py`), đề xuất và chấp nhận (`test_portal_ai_task_proposal_api.py`), quản lý task
  (`test_portal_task_management_api.py`).
- Đã nạp thật một tài liệu mẫu ("Chính sách nghỉ phép năm", 32 section, 34 chunk) bằng embedding Modal và lưu Cloudinary.
- Chatbot (đường `/chat/ask`, dùng ở trang chat của HR và Admin): viết lại và tách câu hỏi, tìm hybrid song song, trả `claims[]` có
  kiểm chứng nguồn, giao diện hiện nguồn và mở tài liệu cuộn tới đúng mục.
- Các lớp an toàn cho cả chatbot và tạo task: chỉ dùng nội dung được cấp, bắt buộc trích nguồn, kiểm nguồn nguyên văn.

### 10.2 Lỗi đã xác minh (đã sửa ngày 01/10/2026, xem 18.1)

| # | Lỗi | Bằng chứng | Hậu quả |
|---|---|---|---|
| 1 | **Tải phiên bản mới của cùng một tài liệu thất bại.** Phiên bản cũ không bao giờ được đóng (`effective_to` trống, không chuyển `ARCHIVED`), trong khi DB cấm hai bản `ACTIVE` chồng ngày | Chèn thử bản mới trong một transaction rồi rollback: DB báo `ex_document_versions_active_no_overlap` | Nút "Tải phiên bản mới" lỗi; chỉ `IngestError` được bắt nên người dùng có thể thấy lỗi 500 |
| 2 | **Tài liệu "ngừng sử dụng" vẫn được Viga tìm thấy.** Nút chỉ đổi `documents.status`; truy vấn tìm kiếm chỉ lọc theo trạng thái phiên bản | Đọc `hybrid_search.py` và `set_document_status` | Thông báo trong modal ("không dùng nữa") đúng với danh sách chọn của AI nhưng không đúng với Viga |
| 3 | **Lỗi mạng tới LLM hoặc embedding trong `/chat/ask` không có bộ xử lý riêng** | `chat_router.py` không bắt `ChatCompletionError` và `EmbeddingServiceError`, `main.py` chỉ xử lý `AuthError` và `PortalError` | Người dùng thấy lỗi 500 thay vì thông báo "chưa trả lời được" |

### 10.3 Chưa làm hoặc còn thiếu (trước đợt cài đặt; còn lại xem 18.8)

| Nhóm | Còn thiếu |
|---|---|
| Ingest | OCR cho file scan (đang từ chối, hoãn — mục 13); xử lý ảnh nhúng (chỉ cảnh báo); **hàng đợi và tiến trình phần trăm trên giao diện (yêu cầu đã chốt, mục 14)**; trạng thái `PROCESSING`, `PENDING_REVIEW`, `FAILED` chưa dùng; trace Langfuse cho ingest |
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
5. Đăng nhập **HR hoặc Admin** (nhân viên hiện không dùng trang chat thật), mở trang chat, hỏi một câu có trong tài liệu (ví dụ về nghỉ phép năm) và một câu không có;
   quan sát `ANSWER` kèm nguồn và `NO_BASIS`.
6. Chạy test: `pytest tests/integration/test_portal_ai_task_proposal_api.py tests/integration/test_portal_document_upload_api.py`
   với `VSF_TEST_DATABASE_URL` trỏ tới PostgreSQL thật.

## 12. Đo lường, baseline, benchmark và giám sát (giai đoạn A đã cài đặt; B và C chưa làm)

> **Cập nhật 01/10/2026: phần này đã được cài đặt, xem 18.1 (giai đoạn A: `llm_calls`, `/admin/metrics`, trang Admin Chi phí AI) và 18.6 (số đo thật).** Nội dung bên dưới giữ nguyên bản thiết kế gốc để đối chiếu.
> Giai đoạn B (bộ câu hỏi chuẩn, `tests/eval`) và giai đoạn C (Prometheus, Grafana) **chưa làm**.

> **Trạng thái ban đầu: đề xuất đã chốt hướng làm (quyết định 9); code giai đoạn A từng nằm trong `git stash` và nay đã vào nhánh (xem 18.1).** Mục này nói *đang đo được gì*, *thiếu gì*, *đề
> xuất đo gì và đo bằng cách nào*, và liệt kê **các điểm cần anh quyết** ở 12.9. Chốt xong mới code.

### 12.1 Mục tiêu

| Câu hỏi cần trả lời được | Hiện trả lời được chưa |
|---|---|
| Một câu hỏi của nhân viên **tốn bao nhiêu tiền** (LLM, embedding)? | Chưa: không ghi token, không có đơn giá |
| Câu hỏi **chậm ở bước nào** (viết lại, embed, tìm kiếm, LLM, kiểm chứng)? | Một phần: Langfuse có thời gian từng span nếu bật |
| Ingest một file **tốn bao lâu, bao nhiêu tiền**, chậm ở parse hay embedding? | Chưa: ingest không có trace |
| Tạo task bằng AI **tốn bao nhiêu**, bao nhiêu đề xuất bị lọc? | Chưa |
| Đổi prompt, model, kích thước chunk có **làm Viga tốt hơn hay tệ đi**? | Chưa: không có bộ câu hỏi chuẩn, không có baseline |
| Một câu trả lời sai thì **hỏng ở khâu nào**? | Khó: phải đoán, không xem được số liệu từng khâu |
| Chi phí tháng này, ngày nào đột biến? | Chưa |

### 12.2 Hiện trạng đo lường (đã đối chiếu code)

| Thành phần | Có gì | Còn thiếu |
|---|---|---|
| `LangfuseTracer` (`infrastructure/observability/langfuse_tracer.py`) | Span có thời gian cho 5 bước của `/chat/ask`; chỉ ghi số lượng và độ dài, **không ghi nội dung** (INV8); tắt thì không làm gì; lỗi Langfuse không làm hỏng chat | Chỉ bọc chat; span là loại `span` thường nên Langfuse **không tính được cost** |
| `DeepSeekChatCompletion` | Gọi LLM, bắt lỗi mạng/xác thực/định dạng | Chỉ trả `content`; **bỏ phần `usage`** (số token) của phản hồi |
| `ModalEmbeddingAdapter` | Thử lại có backoff, kiểm số chiều | Không đo thời gian, không đếm số chuỗi |
| Mã request | Middleware sinh `X-Request-ID` và trả về header | Không truyền vào log hay span nên **không nối được** request với trace |
| Giới hạn chat | 100 câu/5 phút/người, trong bộ nhớ | Không thống kê |
| Log | Dùng `logging` mặc định | Không có log có cấu trúc; lỗi 500 từ LLM/embedding không có bộ xử lý riêng (lỗi 3, mục 10.2) |

### 12.3 Kiến trúc quan sát đề xuất

Giữ Langfuse đã có (không thay), thêm một lớp mỏng ghi **số liệu từng lần gọi dịch vụ ngoài** và một bảng nhỏ để portal tự hiện số liệu mà không phụ thuộc dịch vụ ngoài.

```text
 Request (X-Request-ID, user_id)
      |
      v
 router / service  ---- đặt "ngữ cảnh thao tác" (vd chat.answer) ---->  contextvar
      |
      v
 ADAPTER (DeepSeek / Modal)  --- đo thời gian, đọc usage --->  CallRecord
      |                                                           |
      |                                       +-------------------+----------------+
      |                                       |                                    |
      |                                       v                                    v
      |                              Langfuse generation                  bảng llm_calls (PostgreSQL)
      |                              (model, token, cost)                 chỉ SỐ LIỆU, không nội dung
      |                                       |                                    |
      v                                       v                                    v
   kết quả trả về                    xem từng trace khi debug        GET /admin/metrics -> màn Admin
```

Nguyên tắc giữ nguyên: **không gửi và không lưu nội dung** câu hỏi, câu trả lời, tài liệu (INV8). Đo lường **không bao giờ**
được làm hỏng luồng chính (mọi lỗi của lớp đo bị nuốt và log).

### 12.4 Metric đề xuất

| Nhóm | Metric | Định nghĩa | Nguồn | Dùng để |
|---|---|---|---|---|
| Latency | `chat_total_ms` | Tổng thời gian `/chat/ask` | span gốc | Trải nghiệm người dùng |
| Latency | `step_ms{rewrite,embed,retrieval,llm_answer,validate}` | Thời gian từng bước | span | Tìm khâu chậm |
| Latency | `ingest_ms{parse,chunk,embed,store,db}` | Thời gian từng bước ingest | span ingest (mới) | Tìm khâu chậm khi nạp |
| Latency | p50, p95, p99 | Phân vị theo thao tác, theo ngày | `llm_calls` | Nhìn đuôi chậm, không bị trung bình che |
| Cost | `prompt_tokens`, `completion_tokens` | Token mỗi lần gọi LLM | `usage` của DeepSeek | Tính tiền LLM |
| Cost | `embed_inputs` | Số chuỗi gửi embedding | adapter | Tính tiền embedding |
| Cost | `cost_usd` (ước tính) | token × đơn giá cấu hình | `llm_calls` | Chi phí mỗi câu, mỗi ngày, mỗi tài liệu |
| Chất lượng | `answer_rate`, `no_basis_rate{reason_code}` | Tỉ lệ ANSWER và lý do NO_BASIS | validator | Phát hiện Viga "từ chối quá nhiều" |
| Chất lượng | `citation_valid_rate` | Tỉ lệ claim qua kiểm chứng trích dẫn | validator | Viga có bịa nguồn không |
| Chất lượng | `retrieval_hit@k` | Đoạn đúng có nằm trong top k không | benchmark (12.6) | Đánh giá tìm kiếm |
| Độ tin cậy | `error_rate{llm,embedding}` | Tỉ lệ lần gọi lỗi theo mã | adapter | Cảnh báo sớm |
| Độ tin cậy | `retry_count` | Số lần embedding phải thử lại | adapter | Dịch vụ ngoài chập chờn |
| Tạo task AI | `proposal_kept_rate` | Đề xuất còn lại sau lọc / tổng sinh ra | ai_task_service | AI bịa quote bao nhiêu |
| Tạo task AI | `accept_rate` | Đề xuất HR bấm chấp nhận / tổng hiển thị | portal | AI có hữu ích không |

### 12.5 Baseline

Baseline là **số đo trước khi đổi bất cứ gì**, để mọi thay đổi sau so với nó. Đề xuất:

1. Nạp sẵn một **bộ tài liệu chuẩn** (tài liệu nghỉ phép hiện có + tài liệu ngày 1 thật) và cố định phiên bản model, prompt, tham số chunk (256 từ), `top_k` (30), ngân sách 3000 token.
2. Chạy **bộ câu hỏi chuẩn** (12.6) 3 lần, lấy trung vị, ghi vào `tests/eval/baseline.json` kèm ngày, mã commit, tên model.
3. Mỗi lần đổi prompt, model, chunking, top_k hay bật rerank: chạy lại và so với baseline. **Tệ hơn ngưỡng thì chặn** (ngưỡng cụ thể xin anh chốt ở 12.9).

Chưa có con số nào ở đây là số thật: **mọi baseline phải đo, không điền theo cảm tính.**

### 12.6 Benchmark

| Benchmark | Đo gì | Cách chạy |
|---|---|---|
| **Bộ câu hỏi chuẩn (golden set)** | Với ~30–50 câu: ANSWER/NO_BASIS có đúng như mong đợi không; trích dẫn có đúng đoạn không; thời gian; token; tiền | Script gọi `POST /chat/ask` thật qua HTTP bằng tài khoản thử, so với đáp án mong đợi |
| Các nhóm câu trong bộ chuẩn | (a) có đáp án rõ; (b) nhiều ý; (c) không có trong tài liệu → phải `NO_BASIS`; (d) câu cá nhân → `out_of_scope`; (e) câu cố tiêm lệnh; (f) viết tắt, sai chính tả | Mỗi nhóm một tỉ lệ đúng riêng |
| **Tìm kiếm** | `hit@1/3/5`, MRR: đoạn đúng có ở đầu danh sách không; so BM25 riêng, vector riêng và hybrid | Chạy riêng bước retrieval, không gọi LLM nên **rẻ** |
| **Ingest** | Thời gian và tiền theo cỡ file (1, 10, 50 trang), số chunk, số lần embedding thử lại | Nạp file mẫu vào DB thử |
| **Tạo task AI** | Số đề xuất, tỉ lệ bị lọc vì sai quote, thời gian, token | Chạy trên 3–5 tài liệu có sẵn kết quả tham chiếu do người viết |
| **Tải đồng thời** | p95 khi 5, 10, 20 người hỏi cùng lúc; điểm vỡ của 1 worker | Công cụ tải đơn giản trên bản chạy thử, không chạy trên dữ liệu thật |

Đo bằng **adapter thật** thì tốn tiền thật nên chỉ chạy khi cần; CI vẫn dùng adapter giả (không đo được chất lượng thật,
chỉ kiểm hợp đồng).

### 12.7 Cách debug một câu trả lời sai

```text
 Câu trả lời sai / "chưa có căn cứ" mà đáng ra có
      |
      v
 [1] Lấy X-Request-ID  --> tìm trace tương ứng (Langfuse) hoặc dòng llm_calls cùng request
      |
      v
 [2] rewrite_query: số câu con và độ dài có hợp lý không? (câu gốc bị tách sai?)
      |
      v
 [3] retrieval: có section nào được trả không? (section_counts = 0  ->  lỗi tìm kiếm, không phải lỗi LLM)
      |
      v
 [4] llm_answer: LLM trả mấy claim? có `llm_contract_error` / `llm_skipped_question` không?
      |
      v
 [5] validate_claims: claim bị ép NO_BASIS vì `validation_failed`? (quote không khớp nguyên văn)
      |
      v
 Kết luận: hỏng ở tìm kiếm  /  prompt  /  kiểm chứng  /  dữ liệu thiếu  -> sửa đúng khâu
```

Vì không lưu nội dung, khi cần xem **đúng câu hỏi** thì chạy lại trên môi trường thử bằng chính câu đó, hoặc bật chế độ
ghi nội dung **chỉ ở dev** (tắt mặc định, không bao giờ bật ở production) — cần anh quyết (12.9).

### 12.8 Các giai đoạn đề xuất

| Giai đoạn | Việc | Kết quả | Tốn tiền? |
|---|---|---|---|
| **A. Đo được** | Adapter trả usage và thời gian; Langfuse dùng `generation` (có model, token); span cho ingest và tạo task; truyền `X-Request-ID` vào span và log; bảng `llm_calls` (chỉ số liệu); endpoint `GET /admin/metrics` | Thấy cost và latency thật từng thao tác | Không |
| **B. Baseline và benchmark** | Bộ câu hỏi chuẩn, script chạy và so baseline, benchmark tìm kiếm, ingest, tạo task | Biết đổi gì thì tốt lên hay tệ đi | Có, vài chục lượt gọi mỗi lần chạy |
| **C. Giám sát** | Màn "Chi phí và hiệu năng" cho Admin; (tùy chọn) xuất Prometheus và dashboard Grafana, cảnh báo ngưỡng | Nhìn một chỗ, báo khi bất thường | Không |

Nên làm **A trước** vì B cần số liệu của A mới đáng tin, và A không tốn tiền, không đổi hành vi nào của người dùng.

### 12.9 Điểm cần anh quyết (câu đã chốt: xem mục 0.1)

1. **Nơi xem cost và latency:** chỉ Langfuse (nhanh nhất, nhưng phụ thuộc dịch vụ ngoài) hay thêm bảng `llm_calls` và màn Admin trong portal (chủ động hơn, thêm 1 migration)? Đề xuất: **cả hai**.
2. **Đơn giá:** anh có bảng giá DeepSeek (mỗi 1 triệu token vào/ra) và chi phí Modal (theo giờ GPU hay theo lượt) không? Chưa có thì cấu hình để 0 và cột chi phí hiện 0, **tôi sẽ không tự điền số**.
3. **Có ghi nội dung câu hỏi để debug không?** Đề xuất: **không** ở production (INV8); chỉ cho phép bật ở dev bằng cờ riêng.
4. **Ngưỡng chặn khi tệ hơn baseline:** ví dụ giảm quá bao nhiêu điểm chính xác, hoặc p95 tăng quá bao nhiêu phần trăm thì coi là hỏng? Anh muốn nghiêm đến đâu?
5. **Ai viết đáp án cho bộ câu hỏi chuẩn?** Cần người biết nội dung thật (HR hoặc người phụ trách tài liệu) xác nhận đáp án mong đợi; tôi chỉ soạn bản nháp.
6. **Giai đoạn C:** có cần Prometheus và Grafana (tự host) ngay không, hay màn Admin trong portal là đủ cho giai đoạn này?
7. **Phạm vi ban đầu:** làm cả ba luồng (Viga, ingest, tạo task AI) cùng lúc, hay bắt đầu bằng Viga (luồng tốn tiền nhất, người dùng cuối chạm vào)? Đề xuất: **Viga trước**.
8. **Dữ liệu `llm_calls` giữ bao lâu?** (ví dụ 90 ngày rồi xóa) để bảng không phình.

### 12.10 Rủi ro và lưu ý

- `usage` trả về do nhà cung cấp tự khai, có thể lệch so với hóa đơn thật; chi phí ước tính **chỉ để so sánh và nhìn xu hướng**, không thay hóa đơn.
- Ghi `llm_calls` chạy nền với phiên DB riêng nên không làm chậm câu trả lời, nhưng nếu tiến trình bị tắt đột ngột có thể mất vài bản ghi cuối.
- Bộ câu hỏi chuẩn nhỏ thì kết quả dao động; cần chạy nhiều lần lấy trung vị và đừng đọc quá sâu vào chênh lệch vài phần trăm.
- Đo bằng adapter thật tốn tiền và phụ thuộc mạng; kết quả có thể khác giữa các lần do LLM không hoàn toàn tất định.
- Bộ đếm giới hạn câu hỏi vẫn nằm trong bộ nhớ một worker; nếu chạy nhiều worker, số liệu "người hỏi nhiều" cần lấy từ `llm_calls` thay vì bộ đếm này.

### 12.11 Ước lượng ban đầu về chi phí và độ trễ (CHƯA ĐO, chỉ để định hướng)

> Ước lượng **số token và thời gian** từ code và kiến thức, **sai số khoảng ±50%**, thay bằng số đo thật khi xong giai đoạn A. **Đơn giá DeepSeek là giá thật tra được** (12.11a); đơn giá Modal chưa có.

**Một câu hỏi đáp tài liệu, có căn cứ** (viết lại → embedding → tìm kiếm → trả lời → kiểm chứng):

| Bước | Token ước lượng | Thời gian ước lượng | Ghi chú |
|---|---|---|---|
| Viết lại (LLM) | ~350 vào, ~50 ra | 0,8 – 2,5 giây | Câu ngắn |
| Embedding (Modal) | 1–3 chuỗi ngắn | 0,1 – 0,4 giây khi nóng; **5 – 30 giây khi khởi động lạnh** | Nguồn dao động lớn nhất |
| Tìm kiếm (PostgreSQL) | — | vài chục mili-giây | Kho nhỏ; kho lớn vẫn nhanh nhờ chỉ mục |
| Trả lời (LLM) | ~2.000 vào, ~250 ra | 1,5 – 6 giây | Ngữ cảnh tối đa 3000 "từ", tiếng Việt ra nhiều token hơn số từ |
| Kiểm chứng | — | mili-giây | So chuỗi |
| **Tổng** | **~2.400 vào, ~300 ra** | **thường 3 – 10 giây; xấu 15 – 30 giây** | Xấu = Modal lạnh hoặc LLM chậm |

Chi phí LLM = `(token vào × giá vào + token ra × giá ra) / 1 triệu`. Giá thật xem 12.11a ngay dưới.

#### 12.11a Bảng giá DeepSeek (tra ngày 01/10/2026)

Nguồn: trang giá chính thức `api-docs.deepseek.com/quick_start/pricing`. Model đang dùng trong cấu hình là **`deepseek-flash`**. Đơn vị: USD cho 1 triệu token.

| Model | Vào, cache trúng (cao điểm / thấp điểm) | Vào, cache trượt (cao điểm / thấp điểm) | Ra (cao điểm / thấp điểm) | Ngữ cảnh tối đa |
|---|---|---|---|---|
| **`deepseek-flash`** | 0,006 / 0,003 | **0,30 / 0,15** | **1,20 / 0,60** | 1 triệu token |
| `deepseek-v4-pro` | 0,044 / 0,022 | 1,32 / 0,66 | 3,96 / 1,98 | 1 triệu token |

- **Thấp điểm bằng một nửa cao điểm.** Cao điểm theo UTC là **01:00 đến 04:00 và 06:00 đến 10:00, thứ Hai đến thứ Sáu**, trừ ngày lễ Trung Quốc; còn lại (cuối tuần, ngày lễ Trung Quốc) là thấp điểm.
- Đổi sang **giờ Việt Nam (UTC+7)**: cao điểm là **08:00 đến 11:00 và 13:00 đến 17:00, thứ Hai đến thứ Sáu**. Nghĩa là **phần lớn giờ làm việc của nhân viên rơi vào giá cao điểm**, nên khi tính chi phí lấy giá cao điểm làm mức tham chiếu.
- Tên model cũ (`deepseek-v4-flash`) vẫn được nhận nhưng tính theo giá của Flash.
- **Cần kiểm lại trước khi dùng làm số liệu tài chính:** giá lấy bằng một lần đọc trang, bảng giá có thể đổi; ghi lại ngày tra và dán đúng số vào cấu hình.

**Chi phí một câu theo giá thật (giá cao điểm, cache trượt; tỉ giá giả định 25.000 đồng/USD):**

| Kịch bản | Token ước lượng | Chi phí (cao điểm) | Chi phí (thấp điểm) |
|---|---|---|---|
| Hỏi đáp tài liệu, một ý | ~2.400 vào, ~300 ra | ~0,0011 USD (**~27 đồng**) | ~0,0005 USD (~14 đồng) |
| Câu nhiều ý (1,5 đến 3 lần) | | ~0,0016 đến 0,0032 USD (~40 đến 81 đồng) | ~0,0008 đến 0,0016 USD |
| Không có căn cứ (chỉ bước viết lại) | ~350 vào, ~50 ra | ~0,00017 USD (~4 đồng) | ~0,00008 USD |
| Một lần LLM định tuyến (mục 17) | ~900 vào, ~50 ra | ~0,00033 USD (~8 đồng), tức **+30%** so với một câu hỏi đáp | ~0,00016 USD |
| Câu dữ liệu lộ trình qua công cụ hoặc lối tắt luật | 0 | 0 | 0 |

Quy mô: **1.000 câu hỏi đáp một ý ≈ 1,1 USD (khoảng 27.000 đồng) ở giá cao điểm.** Với giá trị này chi phí LLM **rất nhỏ**; điểm đáng lo hơn là **độ trễ**
(hai lần gọi LLM chiếm phần lớn thời gian) và **chi phí embedding trên Modal** (chưa có giá). Nếu trúng bộ nhớ đệm của DeepSeek (phần system prompt giống nhau
giữa các lần gọi) thì phần vào còn thấp hơn nữa; chưa tính vì chưa biết tỉ lệ trúng.

**Cấu hình đề xuất cho phần đo lường** (3 biến đã thiết kế ở giai đoạn A): `LLM_PRICE_INPUT_PER_MILLION_USD=0.30`, `LLM_PRICE_OUTPUT_PER_MILLION_USD=1.20`
(giá cao điểm, là mức bảo thủ); `EMBEDDING_PRICE_PER_THOUSAND_USD` để trống cho tới khi có giá Modal.

| Kịch bản | Số lần gọi LLM | Thời gian | Chi phí tương đối |
|---|---|---|---|
| Hỏi đáp tài liệu, một ý | 2 | 3 – 10 giây | 1× |
| Câu nhiều ý | 2 (ngữ cảnh lớn hơn) | 5 – 15 giây | 1,5 – 3× |
| Không có căn cứ ở mọi câu con | 1 | 1 – 3,5 giây | ~0,2× |
| Câu dữ liệu lộ trình qua công cụ tất định hoặc lối tắt luật | 0 | 20 – 100 mili-giây | ~0 |
| Câu dữ liệu lộ trình qua LLM định tuyến | 1 | +0,8 – 2,5 giây | ~0,25× |
| Hỏi đáp tài liệu qua agent định tuyến | 3 | +0,8 – 2,5 giây so với hiện tại | +20 – 40% |
| Rerank (hoãn) | +0 | +0,1 – 0,5 giây | rất nhỏ nhưng thêm một dịch vụ |

Bằng chứng trong code: cấu hình Next đã phải nâng timeout lên 60 giây vì câu nhiều ý "có thể mất hơn 10 giây". Adapter DeepSeek bỏ qua phần `reasoning_content`, nên mỗi lần gọi có thể chậm
và tốn token đầu ra hơn ước lượng. Hai lần gọi LLM chiếm khoảng 70 đến 85% tổng thời gian. Đây là lý do lối tắt luật (quyết định 1) đáng giữ.

## 13. Lộ trình xử lý tài liệu từ có cấu trúc đến rối (bậc 1, 2, 3, 5 đã cài đặt)

> **Cập nhật 01/10/2026: phần này đã được cài đặt, xem 18.1 và 18.5.** Nội dung bên dưới giữ nguyên bản thiết kế gốc để đối chiếu.
> Bậc 4 (PDF suy tiêu đề theo cỡ chữ) **chưa làm**; OCR (bậc 6) vẫn hoãn.

> **Trạng thái: đề xuất để thảo luận, chưa có dòng code nào.** Giải quyết vấn đề ở mục 1.1: file không có tiêu đề
> (heading) khiến cả văn bản thành một section khổng lồ, làm Viga trích nguồn kém và tạo task bằng AI thiếu mốc.

### 13.0 Phạm vi giai đoạn này

| | Trong phạm vi (làm trước) | Ngoài phạm vi (để sau, theo số đo) |
|---|---|---|
| Loại file | **`.docx` và PDF có lớp chữ** (chọn bôi đen được chữ), và `.md` | **OCR**: ảnh nhúng trong `.docx`, PDF scan, ảnh chụp |
| Việc | Chia cấu trúc: heading thật, tiêu đề giả, chia section phụ, cảnh báo, **LLM fallback chia mục** | Đọc chữ trong ảnh |
| Hành vi file scan | Giữ như hiện tại: từ chối kèm thông báo rõ ("file scan, chưa hỗ trợ OCR") | Sẽ nạp được khi làm OCR |

LLM fallback **không phải OCR**: nó nhận chữ đã có sẵn và chỉ chỉ ra chỗ nào là tiêu đề. Nên vẫn nằm trong phạm vi.

### 13.1 Nguyên tắc

- **Rule-based trước, AI là phương án cuối.** Từ bậc 1 đến bậc 4 chỉ dùng **luật cố định** (đếm từ, nhận dạng định dạng, so
  khớp mẫu): cùng đầu vào luôn ra cùng kết quả, không tốn tiền, không phụ thuộc mạng, kiểm thử được. **LLM chỉ chạy khi mọi
  luật đã thử mà cấu trúc vẫn kém** (xem 13.2b), và OCR chỉ ở bậc 5.
- **Không bao giờ đổi chữ của tài liệu.** Mọi bậc chỉ quyết định *cắt ở đâu* và *đặt tên gì*, không viết lại nội dung, nên
  kiểm chứng trích dẫn nguyên văn (INV6/INV13) luôn còn đúng.
- **Mỗi bậc phải có số đo** trên cùng một bộ file thử; bậc sau không được làm tệ đi số của bậc trước.
- **Luôn cho nạp, nhưng nói rõ chất lượng:** file kém cấu trúc vẫn nạp được, kèm cảnh báo cho HR.

### 13.2 Sơ đồ luồng xử lý cấu trúc (thay cho bước 8 ở mục 3.1)

```text
 Markdown sau markitdown
        |
        v
 [S1] Có heading thật (# ## ###) không?
        |-- CÓ ---------------------------------------------------------+
        |                                                               |
        |-- KHÔNG                                                       |
        v                                                               |
 [S2] (Bậc 2) Nhận tiêu đề "giả": dòng ngắn chỉ in đậm, dòng đánh số    |
      1. / 2.1, dòng toàn chữ hoa đứng riêng  --> thăng thành heading   |
        |   (chỉ áp dụng khi file KHÔNG có heading thật nào)            |
        |-- nhận được ≥ 2 tiêu đề ---------------------------------------+
        |
        |-- vẫn không có tiêu đề nào
        v                                                               |
 [S3] (Bậc 3) Coi cả văn bản là một khối, đánh dấu "kém cấu trúc"       |
        |                                                               |
        v                                                               |
 [S3b] (Bậc 5, PHƯƠNG ÁN CUỐI) LLM đề xuất vị trí tiêu đề                |
        |   chỉ khi: vẫn "kém cấu trúc" VÀ tài liệu đủ dài VÀ còn ngân sách|
        |   LLM lỗi / trả sai / đề xuất không kiểm chứng được            |
        |        --> bỏ kết quả AI, GIỮ nguyên kết quả của S3             |
        |-- đề xuất hợp lệ --> thăng thành heading, đánh dấu "AI đề xuất" |
        +---------------------------------------------------------------+
        |
        v
 [S4] Cắt theo heading thành section
        |
        v
 [S5] (Bậc 1) Section nào dài hơn ngưỡng (đo ở bậc 0 rồi mới chốt số)?
        |-- không -----------------------------------------------+
        |-- có: cắt thêm theo ranh giới đoạn văn thành           |
        |        SECTION PHỤ, đặt tên "<tiêu đề> (phần 2)" hoặc   |
        |        câu đầu / "Phần N" nếu không có tiêu đề          |
        v                                                        v
 [S6] Cắt section thành chunk ~256 từ (như hiện tại)  <----------+
        |
        v
 [S7] Trả kết quả nạp kèm CHẤT LƯỢNG CẤU TRÚC:
        tốt (có heading thật) / trung bình (heading suy ra hoặc đã chia phụ) / kém (chỉ chia theo đoạn)
        --> giao diện hiện cảnh báo cho HR nếu "kém"
```

### 13.2b LLM fallback (phương án cuối) — quy tắc

LLM chỉ được dùng để **chỉ ra tiêu đề nằm ở đâu**, không được tạo ra hay sửa bất kỳ chữ nào của tài liệu.

```text
 Khi nào chạy:  chất lượng cấu trúc vẫn "kém" sau bậc 1-4
                VÀ tài liệu dài hơn một ngưỡng (ngắn thì một section là đủ)
                VÀ chưa vượt ngân sách chi phí LLM (ngày / mỗi tài liệu)

 Gửi cho LLM:   tài liệu chia thành các đoạn đánh số (§1, §2, ...), mỗi đoạn cắt ngắn
 LLM trả về:    JSON: danh sách { "paragraph": số đoạn, "level": 1-3, "title": "..." }
                (tức "đoạn số N là mục mới, cấp mấy, tên gì")

 Kiểm bằng code (không tin LLM):
   1. số đoạn phải tồn tại, không trùng, tăng dần
   2. nếu LLM trích `title` từ văn bản thì phải là chuỗi con NGUYÊN VĂN của đoạn đó; nếu LLM tự đặt tên
      thì tên chỉ dùng để HIỂN THỊ, không đưa vào nội dung section
   3. số mục hợp lý (không quá nhiều, không quá ít so với độ dài)
   4. chữ của tài liệu sau khi chia phải **y hệt** trước khi chia (so checksum nội dung ghép lại)
   -> sai bất kỳ điều nào: bỏ toàn bộ kết quả AI, giữ kết quả rule-based

 Sau khi nhận:  chèn dấu `##` vào đúng đoạn; section sinh ra mang nhãn "do AI đề xuất"
 Bảo vệ:        lưu kết quả theo content_checksum nên nạp lại cùng nội dung KHÔNG gọi LLM lần nữa
                ghi mỗi lần gọi vào số liệu chi phí (mục 12); có hạn mức ngày và mỗi tài liệu
                LLM hoặc mạng lỗi thì ingest vẫn thành công với kết quả rule-based (không bao giờ làm hỏng nạp)
```

Vì sao đặt ở cuối chứ không dùng ngay: tốn tiền, chậm hơn, không tất định (hai lần chạy có thể ra hai cách chia khác nhau, nên
phải lưu kết quả), và gửi **nội dung tài liệu** tới dịch vụ ngoài (cần anh xác nhận ở 13.7 mục 7). Luật cố định xử lý được
phần lớn file nên LLM chỉ gánh phần còn lại.

### 13.3 Lộ trình theo độ rối của file

| Bậc | Loại file | Việc làm | Loại luật | Đạt khi |
|---|---|---|---|---|
| **0** | Tất cả | Dựng **bộ file thử 6 loại** (xem 13.4), nạp và đo hiện trạng: số section, section lớn nhất, chunk | Không đổi code | Có bảng "hiện hỏng đến đâu" làm mốc |
| **1** | Word chuẩn, có heading nhưng một mục quá dài | Chia section phụ khi vượt ngưỡng; sửa lỗi "luôn gửi ít nhất 1 section" vượt ngân sách 3000 token (section quá lớn thì chỉ gửi chunk khớp và chunk liền kề) | Đếm từ, ranh giới đoạn | Không section nào vượt ngưỡng; quote vẫn khớp nguyên văn |
| **2** | Word dùng in đậm / đánh số thay Heading | Nhận tiêu đề "giả" (S2); chỉ khi file không có heading thật | So khớp mẫu định dạng | Số section gần mục lục thật; đo tỉ lệ nhận nhầm |
| **3** | Word không có cấu trúc nào | Đặt tên phần tạm; **cảnh báo lúc tải lên**; vẫn cho nạp | Đếm từ + ngưỡng cảnh báo | HR thấy cảnh báo; Viga trích "Phần N" thay vì cả tài liệu |
| **4** | PDF có chữ | Thử suy ra tiêu đề từ cỡ chữ và vị trí; **phải thử trên PDF thật** rồi mới chọn thư viện | Luật theo cỡ chữ | Ra số section hợp lý, hoặc kết luận "không khả thi" và quay về bậc 3 kèm khuyến nghị nạp `.docx` |
| **5** | File có chữ nhưng vẫn "kém cấu trúc" sau bậc 1–4 (docx và PDF) | **LLM fallback** (13.2b): đề xuất vị trí tiêu đề, code kiểm chứng, lỗi thì giữ kết quả rule-based | **Có AI**, tốn tiền | File thử loại 4 và 5 ra cấu trúc dùng được; chữ không đổi; chi phí ghi nhận; có hạn mức |
| **6 (hoãn)** | Ảnh nhúng trong `.docx`, PDF scan | **OCR** — chưa làm ở giai đoạn này; file scan tiếp tục bị từ chối kèm thông báo rõ | Có | Quyết sau khi bậc 0–5 xong và có số đo |

### 13.4 Bộ file thử (bậc 0)

| Loại | Mô tả | Dùng để kiểm bậc |
|---|---|---|
| 1 | Word chuẩn, Heading 1–3 đầy đủ | 1 (không được hỏng) |
| 2 | Word có heading nhưng một mục rất dài | 1 |
| 3 | Word dùng in đậm, đánh số thay Heading | 2 |
| 4 | Word chỉ có đoạn chữ liền nhau | 3 |
| 5 | PDF xuất từ Word (có chữ) | 4 |
| 6 | PDF scan (chữ trong ảnh) | **6, hoãn**: chỉ dùng để xác nhận hệ thống từ chối đúng và báo rõ |

### 13.5 Cách đo "đạt" xuyên suốt

Dùng **cùng bộ file thử và cùng bộ câu hỏi chuẩn** (nối với benchmark ở mục 12.6), đo bốn số: (1) số section và độ dài
section lớn nhất; (2) tỉ lệ câu hỏi được trích **đúng đoạn**; (3) tỉ lệ quote qua kiểm chứng nguyên văn; (4) token và tiền
mỗi câu hỏi. Chỉ đi tiếp bậc sau khi bậc trước đạt và các số không tệ đi.

### 13.6 Thứ tự đề xuất và công sức (ước lượng thô)

| Bậc | Công sức | Tốn tiền khi chạy | Ghi chú |
|---|---|---|---|
| 0 | nhỏ | gần như không | Làm đầu tiên |
| 1 + 3 | vừa | không | Làm cùng đợt vì cùng chạm phần chia section và giao diện tải lên |
| 2 | nhỏ đến vừa | không | Cần đo tỉ lệ nhận nhầm |
| 4 | vừa, **chưa chắc làm được** | không | Phụ thuộc kết quả thử PDF thật |
| 5 (LLM fallback) | vừa | **có** | Làm sau cùng trong phạm vi giai đoạn này |
| 6 (OCR) | lớn | **có** | **Hoãn**, quyết sau |

### 13.7 Điểm cần anh quyết (câu đã chốt: xem mục 0.1)

1. Làm đủ bậc 1 đến 3 (như đề xuất) hay chỉ 1 và 3 cho gọn?
2. **Ngưỡng chia section phụ** (vài trăm từ?): đề xuất đo trên tài liệu thật ở bậc 0 rồi mới chốt, không chọn cảm tính.
3. Bộ file thử: dùng **file thật của HR** (đáng tin hơn, nhất là PDF scan và file rối) hay tôi tự dựng file mẫu cho loại 3 đến 6?
4. Áp dụng cho **tài liệu đã nạp** (phải nạp lại để chia) hay chỉ tài liệu nạp từ giờ?
5. **Đã chốt:** LLM fallback chia mục là **có**; OCR (ảnh trong docx, PDF scan) **để sau**, giai đoạn này chỉ docx và PDF có lớp chữ.
6. Khi file ra chất lượng cấu trúc "kém", chỉ **cảnh báo** hay **chặn nạp** cho đến khi HR sửa? Đề xuất: chỉ cảnh báo.
7. **LLM fallback gửi nội dung tài liệu tới nhà cung cấp LLM** (DeepSeek). Tạo task bằng AI hiện cũng đã gửi section của tài liệu
   đi, nên cùng mức rủi ro, nhưng vẫn cần anh xác nhận: tài liệu nào được phép gửi? (ví dụ bỏ qua tài liệu có nhãn nhạy cảm).
8. Fallback chạy **tự động** khi đủ điều kiện, hay HR **bấm "Dùng AI chia mục"** sau khi thấy cảnh báo? Đề xuất: tự động
   cho tài liệu dài, kèm nhãn "AI đề xuất" và cho HR xem trước hoặc hoàn tác.
9. Hạn mức chi phí cho fallback (mỗi tài liệu, mỗi ngày) là bao nhiêu? Chưa có đơn giá thì đặt theo **số lần gọi và số token**.

### 13.8 Rủi ro

- Luật nhận tiêu đề giả (bậc 2) có thể **nhận nhầm** câu in đậm bình thường thành tiêu đề; giảm bằng cách chỉ áp dụng khi file
  không có heading thật và đo tỉ lệ nhầm trên bộ file thử.
- Chia section phụ đổi **số section** của tài liệu; tài liệu đã nạp sẽ khác tài liệu nạp lại. Cần quyết ở 13.7 mục 4.
- Task đã tạo từ section cũ (`task_source_mappings`) trỏ vào section theo mã; nạp lại phiên bản mới tạo section mới nên cần
  kiểm tra liên kết nguồn không bị mất.
- **LLM fallback:** có thể chỉ sai vị trí tiêu đề (kết quả hợp lệ về kỹ thuật nhưng chia chưa đẹp); không tất định nên phải lưu
  kết quả theo `content_checksum`; chậm hơn và tốn tiền, nên bị chặn bởi hạn mức; không bao giờ được làm ingest thất bại.
- PDF có thể không bao giờ có cấu trúc đáng tin; khi đó giải pháp thật là hướng dẫn HR nạp `.docx` hoặc `.md`.

## 14. Chạy nền và hiện tiến trình phần trăm cho nạp tài liệu và tạo task bằng AI (đã cài đặt)

> **Cập nhật 01/10/2026: phần này đã được cài đặt, xem 18.2 và 18.6.** Nội dung bên dưới giữ nguyên bản thiết kế gốc để đối chiếu.

> **Trạng thái: đề xuất để thảo luận, chưa có dòng code nào.** Yêu cầu đã chốt: giao diện phải hiện **tiến trình phần
> trăm** khi nạp tài liệu và khi tạo task bằng AI. Muốn vậy phải đổi cách chạy từ "đồng bộ trong một request" sang
> "chạy nền, giao diện hỏi tiến độ".

### 14.1 Vấn đề hiện tại

| | Nạp tài liệu | Tạo task bằng AI |
|---|---|---|
| Cách chạy | Một request giữ mở tới khi xong | Một request **cho từng tài liệu**, giao diện gọi lần lượt |
| Người dùng thấy | Vòng xoay, không biết bước nào | Vòng xoay, không biết tài liệu nào xong |
| Rủi ro | Đóng tab, mất mạng, proxy ngắt giữa chừng thì không biết kết quả; file lớn hoặc embedding chậm thì rất lâu | Một tài liệu lỗi, không rõ phải làm lại từ đâu |
| Trạng thái lưu lại | Không có (chỉ có kết quả cuối) | Không có |

### 14.2 Tận dụng cái đã có

Code **đã có sẵn bảng `jobs`** (hàng đợi bằng PostgreSQL, thiết kế để worker lấy việc bằng `FOR UPDATE SKIP LOCKED`, có
`status` PENDING/RUNNING/SUCCEEDED/FAILED, `attempts`, `max_attempts`, `locked_at`, `last_error`, khóa chống trùng
`idempotency_key`). Hiện **chưa có code nào dùng** nó. Đề xuất dùng lại, không thêm hạ tầng mới (không cần Redis hay Celery).
Thiếu: cột tiến độ (`progress_percent`, `stage`), cột kết quả (`result`), người tạo (`created_by`), và loại việc cho tạo task
bằng AI (cần mở rộng ràng buộc `JobKind`).

### 14.3 Luồng đề xuất

```text
 Trình duyệt (HR)                       Backend                                   Worker nền
 ----------------                       -------                                   ----------
 chọn file, bấm Nạp
   |  POST /portal/documents
   |----------------------------------> kiểm tra nhanh (đuôi, cỡ, quyền)
   |                                     lưu file gốc vào kho (không còn tệp tạm)
   |                                     tạo job INGEST (idempotency_key = checksum + nhãn bản)
   |  <---- 202 { job_id } ------------   (trả về NGAY, vài trăm ms)
   |
   |  GET /portal/jobs/{id}  (hỏi mỗi ~1 giây)        ......... lấy job (SKIP LOCKED) ...
   |  <---- { status, percent, stage }                 [parse]    10%
   |  <---- { RUNNING, 10, "Đang đọc file" }           [chunk]    15%
   |  <---- { RUNNING, 38, "Embedding 12/34" }         [embed]    15% -> 75% (theo từng lô 32)
   |  <---- { RUNNING, 80, "Đang lưu file gốc" }       [lưu file] 85%
   |  <---- { RUNNING, 95, "Đang ghi dữ liệu" }        [ghi DB]   95% (một transaction)
   |  <---- { SUCCEEDED, 100, result }                 xong -> ghi result, cập nhật percent=100
   |
   v
 giao diện hiện kết quả (số section, số chunk), danh sách tài liệu tự làm mới
```

Giữ nguyên nguyên tắc hiện tại: **không ghi nửa vời**. Dữ liệu tài liệu vẫn chỉ ghi ở bước cuối trong một transaction; tiến độ
nằm trong bảng `jobs`, tách khỏi dữ liệu tài liệu. Job lỗi thì DB tài liệu **sạch**, `jobs` ghi `FAILED` kèm lý do.

### 14.4 Cách tính phần trăm (nạp tài liệu)

Phần trăm là **trọng số theo bước**, riêng bước embedding tính theo từng lô thật nên thanh tiến độ chạy mượt:

| Bước | Khoảng % | Cách tính |
|---|---|---|
| Kiểm tra và nhận file | 0 → 5 | Cố định |
| Đọc file (markitdown) | 5 → 15 | Cố định khi xong |
| Cắt section, chunk | 15 → 20 | Cố định khi xong |
| **Embedding** | 20 → 80 | `20 + 60 × (lô đã xong / tổng lô)`, mỗi lô tối đa 32 chuỗi |
| Lưu file gốc (Cloudinary) | 80 → 90 | Cố định khi xong |
| Ghi DB (một transaction) | 90 → 99 | Cố định khi xong |
| Hoàn tất | 100 | Khi transaction xong |

**Hai điều chỉnh theo quyết định đã chốt:** (1) từ mục 16, tải file chỉ tạo **bản nháp** (không embedding); bảng phần trăm trên áp dụng cho bước
**kích hoạt** (hoặc "tải và kích hoạt luôn"). (2) Khi **LLM chia mục** (mục 13.2b) chạy, thêm một bước chiếm khoảng 15 đến 30% rồi dồn lại các bước sau;
bước này chỉ chạy với file kém cấu trúc nên không phải lần nào cũng có.

Trọng số trên là **giả định ban đầu**: chốt sau khi đo thời gian thật từng bước (nối với mục 12). Thời gian còn lại ước tính
chỉ hiện khi đã có đủ số mẫu, nếu không thì chỉ hiện phần trăm và tên bước.

### 14.5 Tạo task bằng AI

Đã nói thẳng một giới hạn: **mỗi tài liệu chỉ gọi LLM một lần và lời gọi đó không có tiến độ chi tiết bên trong**, nên không thể
có phần trăm "thật" trong riêng bước này. Đề xuất:

- Phần trăm **tổng** theo số tài liệu: nếu chọn N tài liệu, mỗi tài liệu chiếm `100/N`.
- Trong mỗi tài liệu: đọc section 0 → 10%, **chờ LLM 10 → 90%** (hiển thị dạng "đang chờ AI" kèm thời gian đã trôi, thanh
  tiến độ chạy chậm dần theo thời gian trung bình đã đo thay vì nhảy bậc), lọc và kiểm chứng trích dẫn 90 → 100%.
- Hiển thị **từng tài liệu một dòng** với trạng thái riêng (chờ / đang chạy / xong, số đề xuất / lỗi, nút thử lại), kèm thanh
  tổng ở trên. Một tài liệu lỗi **không làm hỏng** các tài liệu khác.
- Kết quả đề xuất lưu trong `jobs.result` (JSON) để HR tải lại trang vẫn xem tiếp được; tự xóa sau một thời gian.
- Nếu muốn tiến độ mịn hơn: bật chế độ **streaming** của LLM và ước lượng theo số token đã nhận (cần kiểm tra DeepSeek hỗ trợ
  và schema JSON còn hợp lệ khi nhận từng phần). Để giai đoạn sau.

### 14.6 Giao diện

| Nơi | Hiển thị |
|---|---|
| Hộp "Thêm tài liệu" | Sau khi bấm Nạp: thanh phần trăm, tên bước ("Embedding 12/34"), nút **Chạy nền** (đóng hộp mà việc vẫn tiếp tục), nút **Hủy** (nếu chọn làm) |
| Bảng Tài liệu | Dòng đang nạp hiện nhãn "Đang xử lý 45%" và cập nhật tự động; xong thì chuyển thành trạng thái thường; lỗi hiện nhãn đỏ kèm lý do và nút **Thử lại** |
| Trang Tạo task bằng AI | Thanh tổng + một dòng cho mỗi tài liệu như 14.5; đóng trang rồi mở lại vẫn thấy việc đang chạy |
| Chung | Hỏi tiến độ bằng **polling mỗi ~1 giây** (đơn giản, chạy qua mọi proxy); thông báo toast khi xong hoặc lỗi; ngừng hỏi khi job kết thúc hoặc rời trang |

### 14.7 Xử lý lỗi và an toàn

- **Chống bấm hai lần:** `idempotency_key` + chỉ mục duy nhất đã có (INV10) nên cùng một lần nạp không chạy chồng.
- **Job treo / worker chết:** job `RUNNING` quá hạn (`locked_at` cũ) được đưa về hàng đợi; tối đa `max_attempts` lần với chờ tăng dần;
  quá số lần thì `FAILED` kèm `last_error` (chỉ mã và mô tả ngắn, không chứa nội dung tài liệu).
- **Khởi động lại backend:** việc đang chạy được nhận lại, không mất; file gốc đã nằm trong kho nên không phụ thuộc tệp tạm.
- **Giới hạn đồng thời:** tối đa 1–2 job nạp cùng lúc để không dồn tải lên Modal embedding và DeepSeek.
- **Quyền:** chỉ người tạo job (hoặc ADMIN) xem được tiến độ; HR chỉ thấy job thuộc phạm vi phòng ban của mình.
- Tiến độ và lỗi **không chứa nội dung tài liệu** (INV8).

### 14.8 Các bước thực hiện đề xuất

| Bước | Việc | Ghi chú |
|---|---|---|
| 1 | Migration: thêm `progress_percent`, `stage`, `result`, `created_by` vào `jobs`; mở rộng `JobKind` | Nhỏ |
| 2 | Worker nền chạy trong tiến trình backend (vòng lặp lấy job bằng `SKIP LOCKED`), tách ra container riêng sau nếu cần | Chưa cần hạ tầng mới |
| 3 | Tách `ingest_document` thành các bước có "móc báo tiến độ"; embedding báo theo từng lô | Giữ nguyên transaction cuối |
| 4 | API: `POST /portal/documents` trả `202 + job_id`; `GET /portal/jobs/{id}`; `GET /portal/jobs?active=1`; tạo task AI tương tự | Giữ tương thích test cũ |
| 5 | Giao diện: thanh tiến trình ở hộp tải tài liệu, bảng Tài liệu, trang Tạo task bằng AI; polling | Dùng lại modal và toast sẵn có |
| 6 | Test: tiến độ tăng đơn điệu, lỗi không để lại dữ liệu nửa vời, job treo được nhận lại, không chạy chồng | Dùng adapter giả |

### 14.9 Điểm cần anh quyết (câu đã chốt: xem mục 0.1)

1. **Worker trong tiến trình backend** (nhanh, đủ cho một container) hay **container worker riêng** ngay từ đầu?
2. Hỏi tiến độ bằng **polling 1 giây** (đề xuất) hay **SSE** (mượt hơn nhưng phức tạp hơn qua proxy)?
3. Có nút **Hủy** job không? (Hủy giữa chừng cần dọn file đã lưu; đề xuất bản đầu chưa có.)
4. Thanh phần trăm tạo task bằng AI: chấp nhận **ước lượng theo thời gian** ở bước chờ LLM, hay muốn làm streaming ngay?
5. Giữ kết quả job (đề xuất task, lịch sử nạp) **bao lâu**?
6. Số job chạy đồng thời tối đa là mấy?
7. Có hiện **thời gian còn lại ước tính** không, hay chỉ phần trăm và tên bước? (Đề xuất: chỉ hiện khi đã đo đủ mẫu.)

### 14.10 Rủi ro

- Chuyển sang chạy nền là thay đổi hợp đồng API (`POST /portal/documents` trả 202 thay vì kết quả); cần sửa giao diện và test cùng lúc.
- Phần trăm theo trọng số là **ước lượng**; nếu trọng số lệch thanh có thể đứng lâu ở một mốc. Cần đo thật rồi chỉnh.
- Worker chạy chung tiến trình backend dùng chung CPU và vòng lặp sự kiện: ingest nặng (markitdown, underthesea chạy đồng bộ) có thể làm chậm các request khác; có thể phải chạy các bước nặng trong luồng riêng hoặc tách container.
- Backend nhiều worker thì mỗi worker đều lấy việc được (nhờ `SKIP LOCKED`), nhưng bộ đếm giới hạn chat vẫn nằm trong bộ nhớ từng tiến trình.

## 15. Phân tích chức năng của Viga: làm gì, dùng công cụ nào (đã cài đặt)

> **Cập nhật 01/10/2026: phần này đã được cài đặt, xem 18.2 và 18.4.** Nội dung bên dưới giữ nguyên bản thiết kế gốc để đối chiếu.

> **Trạng thái: phân tích và đề xuất, chưa code.** Trả lời câu hỏi "Viga thật sự làm gì, có dùng tool không".

### 15.1 Hiện trạng: Viga là một đường ống cố định, **không có tool, không có agent**

Backend (`/chat/ask`) chỉ có **một chức năng**: hỏi đáp trên tài liệu đã nạp, có trích nguồn. Luồng cố định, không có quyết định
"gọi công cụ nào":

```text
 câu hỏi -> viết lại/tách -> embed -> tìm hybrid -> (rerank) -> LLM trả lời có trích dẫn -> kiểm chứng -> kết quả
```

LLM chỉ được dùng đúng 2 lần (viết lại, trả lời) và **không tự gọi hàm nào**. Viga hiện **không biết** người hỏi là ai,
đang ở việc nào, việc nào bị khóa; không tra được đầu mối, mẫu email, đường dẫn; không tạo ticket; không ghi lại câu hỏi
chưa trả lời được.

Ở giao diện nhân viên, ngăn Viga hiện là **bản dựng**: một bộ định tuyến luật (`vigaMock.ts`) suy ra câu trả lời từ lộ trình
thật. Nó chính là mẫu của loại chức năng "theo lộ trình" mà prototype v15 mô tả nhưng **chưa có ở backend**.

### 15.2 Hai nhóm chức năng, bản chất khác nhau

| Nhóm | Câu hỏi ví dụ | Dữ liệu cần | Cách làm hợp lý |
|---|---|---|---|
| **A. Hỏi đáp tài liệu** (đã có) | "Nghỉ phép năm bao nhiêu ngày?" | Kho tài liệu (RAG) | Giữ nguyên: tìm, trả lời, trích nguồn, kiểm chứng |
| **B. Dẫn đường theo lộ trình** (chưa có ở backend) | "Hôm nay tôi làm gì?", "Sao tôi chưa làm được việc ảnh đại diện?" | **Lộ trình và trạng thái thật** của người hỏi | **Không cần LLM tìm kiếm**: đây là tra cứu dữ liệu có cấu trúc, trả lời xác định |
| C. Hành động hỗ trợ (chưa có) | "Cho mình mẫu email xin phê duyệt", "Ai phụ trách nhận laptop?", "Báo giúp mình đang kẹt" | Đầu mối, mẫu, đường dẫn do HR duyệt; ticket | Tra cứu dữ liệu HR đã duyệt; tạo ticket **có người xác nhận** |

Nhóm B không nên đi qua RAG: câu trả lời đúng nằm trong cơ sở dữ liệu lộ trình, đưa qua tìm kiếm và LLM chỉ thêm tốn kém và
sai sót. Nên là **công cụ tất định**.

### 15.3 Kiến trúc đề xuất: **bộ định tuyến ý định + công cụ có kiểm soát**, không phải agent tự do

```text
 câu hỏi (+ ngữ cảnh người hỏi: phòng ban, ngày, việc đang mở — mục 6.1 M2)
      |
      v
 [R1] Định tuyến ý định BẰNG LUẬT (từ khóa, mẫu câu, như v15): "hôm nay / làm gì tiếp" -> DAY_PLAN,
      "vì sao chưa làm được X" -> PREREQUISITE, "ai phụ trách / mẫu email" -> tra cứu, còn lại -> hỏi đáp tài liệu
      |-- khớp luật --------------------> gọi CÔNG CỤ tất định tương ứng
      |-- không khớp, câu mơ hồ ---------> [R2] LLM phân loại ý định vào MỘT trong danh sách đóng (chỉ chọn nhãn)
      |                                          lỗi / không chắc -> mặc định hỏi đáp tài liệu (nhóm A)
      v
 CÔNG CỤ (chỉ ĐỌC, trừ khi ghi rõ)                                          trả về
   get_next_tasks / get_day_plan / explain_lock  (lộ trình thật)   ------>  response_type + message + blocking_tasks
   search_documents (RAG hiện có, kèm rerank)                       ------>  claims[] có nguồn
   get_contact / get_template / get_approved_link (HR đã duyệt)     ------>  thông tin có nguồn là mục HR đã duyệt
   log_content_gap (ghi câu hỏi chưa trả lời được)                  ------>  để HR bổ sung tài liệu
   create_ticket (CẦN nhân viên xác nhận)                           ------>  ticket thật
      |
      v
 kiểm chứng như hiện tại (nhóm A) / không cần (nhóm B vì đã là dữ liệu thật) -> kết quả + suggested_actions
```

**Vì sao không dùng agent tự do** (LLM tự quyết gọi hàm nào, nhiều vòng): khó kiểm soát và khó kiểm thử, tốn token, không tất
định, và dễ vi phạm nguyên tắc "không đoán, không có nguồn thì nói thẳng". Bộ định tuyến luật cho kết quả **dự đoán được và đo
được**; LLM chỉ là phương án dự phòng chọn *nhãn* (R2), không sinh nội dung dẫn đường.

### 15.3b Cá nhân hóa: biết người hỏi đang ở đâu thì gọi đúng và nhanh hơn

Ý tưởng: trước khi làm gì, backend lấy một **ảnh chụp tình hình của người hỏi** bằng **một truy vấn DB nhẹ** (không LLM):

```text
 ảnh chụp (snapshot) của người hỏi, tính tại chỗ từ lộ trình thật
   - đang ở ngày nào, tiến độ bao nhiêu phần trăm
   - việc làm được ngay (READY): tên, mã
   - việc đang khóa và việc nào chặn (tiên quyết chưa xong)
   - việc vừa xong
   - phòng ban
```

**Dữ liệu gửi cho LLM định tuyến (đã chốt, quyết định 3):** chỉ **mã việc, tên việc, trạng thái**; **không** gửi tên, email, phòng ban của nhân viên.
Phần còn lại của snapshot (tiến độ, ngày) dùng trong code, không đi ra ngoài.

Nó giúp ba việc:

| Việc | Cách | Lợi |
|---|---|---|
| **Chọn đường đi, không phải chọn nội dung** | Bộ định tuyến luật (R1) dùng snapshot để biết câu "tiếp theo làm gì" hay "sao chưa làm được X" trả lời được **bằng dữ liệu lộ trình** | **Bỏ hẳn** viết lại bằng LLM, embedding, tìm kiếm và LLM trả lời: một truy vấn DB thay cho cả đường ống nên nhanh hơn nhiều bậc và **không tốn tiền LLM**; con số cụ thể sẽ đo (mục 12) |
| **Biết nên gọi API nào** | Snapshot cho biết người đó đang bị khóa vì việc nào, đang ở ngày mấy, nên gợi ý hành động đúng (`OPEN_TASK`, `OPEN_DAY`) | Câu trả lời ngắn, có nút bấm, không bắt người dùng tự tìm |
| **Hiểu câu mơ hồ** | "Cái này làm sao?": **backend tự xác định "việc hiện tại"** của người hỏi từ dữ liệu (xem 15.3e), giao diện không phải gửi gì thêm | Đỡ phải hỏi lại |

Giữ nguyên ranh giới: snapshot chỉ dùng để **chọn công cụ và gợi ý**; nội dung chính sách vẫn **chỉ** lấy từ tài liệu có nguồn (nhóm A).
Snapshot chỉ gửi cho LLM phần tối thiểu đã chốt ở bảng mục 0 (mã, tên, trạng thái việc). Chỉ đọc đúng lộ trình của chính người hỏi.

### 15.3c Bộ định tuyến ý định bằng luật: câu cá nhân hóa gọi thẳng API (đề xuất, chưa code)

> **Đã được mục 17 thay thế một phần (quyết định 1):** LLM là bộ định tuyến chính. Luật dưới đây **chỉ còn làm lối tắt** cho 3 câu
> ("hôm nay làm gì", "tiếp theo làm gì", "tiến độ của tôi") để các câu này không tốn LLM; bảng ý định còn lại dùng làm **danh sách công cụ** cho LLM chọn.

**Hiện trạng:** ở backend **chưa có** bộ định tuyến ý định nào; `/chat/ask` luôn đi đường hỏi đáp tài liệu. Chỉ có một **bản mô phỏng ở
giao diện** (`vigaMock.ts`) làm đúng loại việc này: một biểu thức chính quy nhận câu "hôm nay / làm gì", và hàm khớp tên việc theo từ
chung. Nó dùng được cho bản dựng nhưng đặt ở trình duyệt thì không an toàn và không kiểm thử tập trung được. Đề xuất **chuyển sang
backend**, mở rộng, và gọi **công cụ tất định** (một truy vấn DB), không qua LLM.

```text
 câu hỏi + conversation_id        (KHÔNG cần giao diện gửi task_id: backend tự biết người này đang ở việc nào, xem 15.3e)
      |
      v
 [1] CHUẨN HÓA: chữ thường, bỏ dấu để so khớp (giữ bản có dấu để hiển thị), bỏ từ đệm ("cho mình hỏi", "nhé", "ạ")
      |
      v
 [2] ĐỊNH TUYẾN BẰNG LUẬT  ->  một ý định trong DANH SÁCH ĐÓNG
      |      khớp rõ ràng ----------------------------------------> GỌI CÔNG CỤ (không LLM)
      |      khớp nhưng thiếu việc cụ thể (vd "việc này") ---------> lấy "việc hiện tại" backend tự suy ra (15.3e)
      |      không khớp luật nào ---------------------------------> hỏi đáp tài liệu (đường RAG hiện có)
      |      (sau này, nếu đo thấy rơi nhiều: LLM chỉ chọn NHÃN ý định, không viết câu trả lời)
      v
 [3] TRÍCH THAM SỐ: việc nào (xem 15.3d), ngày nào
      v
 [4] CÔNG CỤ chạy bằng snapshot / truy vấn DB của chính người hỏi  ->  response_type + message + blocking_tasks + suggested_actions
```

**Danh sách ý định đề xuất (bản đầu, đóng):**

| Ý định | Câu mẫu | Công cụ gọi | `response_type` |
|---|---|---|---|
| `NEXT_STEP` | "Tiếp theo tôi làm gì?", "Bắt đầu từ đâu?", "Việc nào làm ngay được?" | `get_next_tasks` | `NEXT_STEP` |
| `DAY_PLAN` | "Hôm nay làm gì?", "Ngày mai có việc gì?", "Tuần này thế nào?" | `get_day_plan` | `DAY_PLAN` |
| **`WHY_LOCKED`** | **"Sao tôi chưa làm được task ảnh đại diện?", "Vì sao việc này bị khóa?", "Task này sao không bấm được?"** | `explain_lock` | `PREREQUISITE_REQUIRED` |
| `HOW_TO_DO_TASK` | "Việc nhận laptop làm thế nào?", "Hướng dẫn làm task này" | `get_task_detail` | `INFO` |
| `PROGRESS` | "Tôi làm được bao nhiêu rồi?", "Còn bao nhiêu việc?" | `get_progress` | `INFO` |
| `WHO_TO_ASK` | "Ai phụ trách nhận laptop?" | `get_contact` | `INFO` (khi HR đã có đầu mối) |
| `GET_TEMPLATE` | "Cho mình mẫu email xin phê duyệt" | `get_template` | `INFO` (khi có mẫu) |
| `REPORT_STUCK` | "Tôi bị kẹt", "Báo giúp là tôi chưa nhận được laptop" | `create_ticket` (cần xác nhận) | `INFO` |
| (không khớp) | "Nghỉ phép năm bao nhiêu ngày?" | `search_documents` (RAG) | `ANSWER` / `NO_BASIS` |

**Ví dụ chạy thật cho câu "task này sao chưa làm được":**

```text
 giao diện gửi: question="task này sao chưa làm được"  (chỉ câu hỏi; backend tự xác định việc hiện tại = việc 15)
      |
      v
 luật: có "sao ... chưa làm được" + "task này"  ->  ý định WHY_LOCKED, tham số task = ngữ cảnh (15)
      |
      v
 explain_lock(user, task 15):  1 truy vấn: trạng thái việc 15 + tiên quyết chưa xong
      |
      +-- việc 15 đang LOCKED, thiếu "Nhận laptop" -> "Bạn chưa làm được vì cần hoàn thành 'Nhận laptop' trước."
      |                                               + blocking_tasks [Nhận laptop] + nút "Mở: Nhận laptop"
      +-- việc 15 đã READY                         -> "Việc này đang mở, bạn làm được ngay." + nút "Mở việc"
      +-- việc 15 đã DONE                          -> "Bạn đã hoàn thành việc này."
      +-- không phải việc của người hỏi            -> "Việc này không có trong lộ trình của bạn." (NOT_IN_JOURNEY)
      |
      v
 trả lời ngay, KHÔNG gọi LLM, KHÔNG embedding, KHÔNG tìm kiếm
```

**Quy tắc để an toàn và đo được:**
- Luật chỉ chọn trong **danh sách đóng**; không bao giờ để LLM tự bịa tên công cụ.
- Mọi công cụ nhóm B **chỉ đọc đúng lộ trình của người đang đăng nhập** (lấy `user_id` từ phiên, không nhận từ câu hỏi).
- **Không khớp chắc chắn thì rơi về hỏi đáp tài liệu**, không đoán ý định; nếu câu vừa giống hai ý định thì ưu tiên ý định **không có tác dụng phụ** (chỉ đọc).
- Ghi lại ý định đã chọn và đường đi (luật / RAG) vào số liệu (mục 12) để biết bao nhiêu phần trăm câu được trả lời **không tốn LLM**, và
  những câu nào rơi nhầm.
- Có **bộ câu hỏi chuẩn riêng cho định tuyến** (hàng chục câu tiếng Việt: có dấu, không dấu, viết tắt, hỏi lai) để đo độ chính xác trước khi bật.

### 15.3d Xác định "việc nào" khi người dùng nói

| Cách người dùng nói | Cách xác định | Ghi chú |
|---|---|---|
| "task này", "việc này", "cái này" | **Backend tự suy ra "việc hiện tại"** của người hỏi (15.3e); không xác định được thì hỏi lại "Bạn đang nói về việc nào?" | Người dùng không phải làm gì thêm |
| Nêu tên: "task ảnh đại diện", "việc nhận laptop" | So khớp tên việc trong **lộ trình của người hỏi** bằng từ chung (không dấu, chữ thường), có ngưỡng; thua ngưỡng thì rơi về hỏi lại | Bản mô phỏng hiện cần khớp tối thiểu 2 từ hoặc toàn bộ từ nếu câu rất ngắn |
| Nêu số thứ tự: "việc số 3", "task 03" | Thứ tự trong ngày đang xem | Nhờ số thứ tự đã có trên roadmap |
| Mơ hồ, khớp nhiều việc | Liệt kê tối đa 3 việc khớp nhất kèm nút chọn | Không tự chọn bừa |

**Điểm cần anh quyết (bổ sung cho 15.7):**
1. Đồng ý chuyển bộ định tuyến luật từ giao diện sang backend và gọi công cụ tất định (không LLM) cho các ý định ở bảng trên?
2. Danh sách ý định bản đầu: thêm hay bớt? Tôi đề xuất bản đầu chỉ `NEXT_STEP`, `DAY_PLAN`, `WHY_LOCKED`, `HOW_TO_DO_TASK`, `PROGRESS` (đều dùng dữ liệu đã có);
   `WHO_TO_ASK`, `GET_TEMPLATE`, `REPORT_STUCK` để sau khi HR có trang đầu mối, mẫu, ticket.
3. Câu không khớp luật: **rơi về hỏi đáp tài liệu** (đề xuất) hay **hỏi lại** người dùng muốn xem việc cần làm hay hỏi chính sách?
4. Có dùng LLM chọn nhãn ý định cho câu mơ hồ không, hay chỉ luật cho đến khi đo thấy rơi nhiều?

### 15.3e Backend tự biết "việc hiện tại" của người hỏi (không cần giao diện gửi `task_id`)

Yêu cầu: nhân viên chỉ gõ câu hỏi; Viga **tự gọi dữ liệu** để biết người đó đang ở đâu, không phụ thuộc giao diện gửi kèm `task_id`.

**Giới hạn thật của dữ liệu hiện tại (nêu thẳng):** hệ thống chỉ có ba trạng thái việc `LOCKED`, `READY`, `DONE`. **Không có trạng thái "đang làm"**
và **không ghi lại nhân viên vừa mở việc nào**. Nên backend **chưa thể biết chắc** người đó "đang làm việc gì" lúc này; chỉ biết việc nào làm
được ngay, việc nào bị khóa, việc nào đã xong. Vì vậy cần một quy tắc suy ra, và (khuyến nghị) một chút dữ liệu thêm:

| Cách xác định "việc hiện tại" | Cách làm | Độ chắc | Cần thêm dữ liệu? |
|---|---|---|---|
| **1. Việc vừa mở gần nhất** | Mỗi lần nhân viên mở trang chi tiết một việc, backend ghi `last_opened_task_id` và thời điểm (một cột trên `employee_journeys`, hoặc bảng nhỏ) | Cao: đúng việc người đó đang nhìn | **Có**: một cột và một lần ghi khi mở trang (không tốn LLM) |
| **2. Việc làm được ngay đầu tiên** | Từ snapshot: việc `READY` đầu tiên theo thứ tự ngày và số thứ tự, ưu tiên việc bắt buộc | Trung bình: là "việc kế tiếp hợp lý", chưa chắc là việc người đó đang nghĩ tới | Không |
| **3. Việc chặn nhiều việc nhất** | Việc `READY` mà nhiều việc `LOCKED` đang chờ | Phụ trợ để gợi ý "nên làm việc này trước" | Không |
| **4. Hỏi lại** | Khi không đủ chắc: "Bạn đang nói về việc nào?" kèm tối đa 3 việc để bấm | Chắc | Không |

**Thứ tự áp dụng đề xuất:** (1) nếu có `last_opened_task_id` trong một khoảng ngắn gần đây (ví dụ 30 phút, anh chọn) thì dùng; (2) nếu câu hỏi **nêu tên
hoặc số thứ tự** việc thì **ưu tiên cái đó** hơn mọi suy đoán; (3) nếu không có gì thì dùng việc `READY` đầu tiên **và nói rõ** trong câu trả lời
("Mình đang hiểu bạn nói về việc 'Nhận laptop'"), để người dùng sửa được; (4) câu mơ hồ kiểu "cái này" mà có nhiều ứng viên thì hỏi lại.

```text
 câu hỏi: "task này sao chưa làm được"
      |
      v
 backend tự gọi (từ phiên đăng nhập):  snapshot + last_opened_task_id
      |
      v
 xác định việc:  câu có nêu tên/số?  -> dùng
                 else có việc vừa mở (trong N phút)?  -> dùng
                 else việc READY đầu tiên  -> dùng, NÓI RÕ "mình đang hiểu bạn nói về ..."
                 else  -> hỏi lại
      |
      v
 explain_lock(user, task đã xác định)  ->  trả lời
```

Giữ nguyên an toàn: **`user_id` luôn lấy từ phiên**, mọi `task_id` (kể cả do backend suy ra hoặc do LLM đưa ra) phải được kiểm là thuộc lộ trình của người hỏi
trước khi dùng.

**Điểm cần anh quyết:**
1. Có thêm **ghi nhận "việc vừa mở"** (một cột, một lần ghi khi mở trang việc) để Viga biết chắc việc hiện tại không? Đề xuất: **có**, chi phí rất nhỏ.
2. Khoảng thời gian coi là "vừa mở" (đề xuất 30 phút).
3. Khi phải suy bằng việc `READY` đầu tiên: **nói rõ giả định rồi trả lời** (đề xuất) hay **hỏi lại** trước?
4. Có muốn thêm trạng thái **"đang làm"** (người dùng bấm "Bắt đầu") thay vì suy ra? Chính xác hơn nhưng thêm một thao tác cho nhân viên và đổi máy trạng thái việc (hiện cố ý chỉ có ba trạng thái).

### 15.4 Danh sách công cụ đề xuất

| Công cụ | Việc | Dữ liệu | Quyền | Có sẵn? | Ưu tiên |
|---|---|---|---|---|---|
| `search_documents` | Hỏi đáp tài liệu có nguồn | `document_chunks` | đọc | **Có** (cần rerank) | Giữ |
| `get_next_tasks` | "Làm gì tiếp" | `employee_tasks` (READY) | đọc, của chính người hỏi | Dữ liệu có; chưa có công cụ | **Cao** |
| `get_day_plan` | Kế hoạch ngày | `employee_tasks`, `journey_stages` | đọc | Dữ liệu có | **Cao** |
| `explain_lock` | Vì sao việc bị khóa, cần xong gì | `task_dependencies`, `employee_tasks` | đọc | Dữ liệu có (API `/me/journey` đã trả tiên quyết) | **Cao** |
| `get_task_detail` | Hướng dẫn một việc | `task_templates` | đọc | Dữ liệu có | Trung bình |
| `get_contact` / `get_approved_link` | Ai phụ trách, đường dẫn đã duyệt | `contact_channels`, `approved_links` | đọc | **Bảng có, chưa có router và giao diện HR** | Trung bình (phụ thuộc mục 3 của báo cáo tiến độ) |
| `get_template` | Mẫu email điền sẵn | (chưa có bảng mẫu) | đọc | **Chưa có** | Thấp |
| `log_content_gap` | Ghi câu hỏi chưa trả lời | `content_gaps` | ghi | Bảng có, chưa router | Trung bình (mở đường cho trang "Phản hồi Viga") |
| `create_ticket` | Báo kẹt thành ticket | `tickets` | ghi, **cần xác nhận** | Bảng có, chưa router | Thấp, làm sau |

Mọi công cụ **đọc đúng phạm vi của chính người hỏi** (nhân viên chỉ thấy lộ trình của mình). **Viga không có công cụ ghi vào
trạng thái việc**: không tự đánh dấu hoàn thành, không duyệt, không cấp quyền (đúng quy tắc v15 "AI không tự chốt").

### 15.5 Định dạng trả lời (nối với giao diện đã dựng)

Giao diện nhân viên đã dùng sẵn hình dạng dữ liệu của v15, nên backend chỉ cần trả đúng hình dạng đó:

| Trường | Giá trị |
|---|---|
| `response_type` | `NEXT_STEP`, `PREREQUISITE_REQUIRED`, `DAY_PLAN`, `INFO`, `NOT_IN_JOURNEY`, và `ANSWER`/`NO_BASIS` cho nhóm A |
| `message` | Câu trả lời |
| `blocking_tasks[]` | Việc đang chặn |
| `suggested_actions[]` | `OPEN_TASK`, `OPEN_DAY`, (sau này `COPY_TEMPLATE`, `OPEN_APPROVED_LINK`) |
| `sources[]` | Việc, mục tài liệu hay đầu mối đã dùng |

### 15.6 Lộ trình triển khai đề xuất

> **Đã chỉnh theo quyết định ở mục 0.1:** thứ tự thực hiện tổng thể nằm ở mục 0.3. Bảng dưới là phần riêng của Viga; "bộ định tuyến luật" ở bước 1 nay là
> **công cụ lộ trình tất định cộng lối tắt luật cho 3 câu**, còn **LLM định tuyến (mục 17) là bộ định tuyến chính**; bước 7 (R2) không còn là "nếu cần" mà là phần cốt lõi.

| Bước | Việc | Phụ thuộc |
|---|---|---|
| 1 | Chuyển bộ định tuyến luật từ giao diện (`vigaMock.ts`) **sang backend**, thêm 3 công cụ ưu tiên cao đọc dữ liệu lộ trình; trả đúng hình dạng 15.5 | Không |
| 2 | Bật **ngữ cảnh người hỏi** (mục 6.1 M2, 15.3e) và **bộ nhớ hội thoại** theo 6.2 (máy chủ lưu; M1 cũ đã bỏ) | Bước 1 |
| 3 | **Rerank (mục 4.2b): HOÃN**, chỉ làm khi kho đủ lớn và có số đo | Mục 12 (đo lường, bộ câu hỏi chuẩn) |
| 4 | `log_content_gap` + trang "Phản hồi Viga" cho HR | Router `content_gaps` |
| 5 | `get_contact`, `get_approved_link`, `get_template` | Trang "Đầu mối và đường dẫn" của HR |
| 6 | `create_ticket` có xác nhận | Trang "Ticket sự cố" |
| 7 | **LLM định tuyến** (mục 17) là bộ định tuyến chính; bộ câu hỏi chuẩn để đo độ chính xác định tuyến | Bước 1, mục 12 |

### 15.7 Điểm cần anh quyết (câu đã chốt: xem mục 0.1)

1. Đồng ý hướng **"bộ định tuyến luật + công cụ có kiểm soát"** thay vì agent tự do?
2. Nhóm B (dẫn đường theo lộ trình) có đi cùng `/chat/ask` (một cửa, thêm `response_type`) hay tách endpoint riêng cho nhân viên?
3. Giữ bộ định tuyến luật **chỉ ở backend** (nguồn sự thật, kiểm thử được) và bỏ bản mô phỏng ở giao diện khi xong?
4. Ưu tiên bước nào trước: dẫn đường theo lộ trình (bước 1) hay rerank cho hỏi đáp (bước 3)? Tôi đề xuất bước 1 vì không tốn tiền,
   không cần đo trước, và nhân viên cảm nhận được ngay.
5. Câu hỏi mơ hồ không khớp luật: mặc định đẩy sang hỏi đáp tài liệu, hay hỏi lại người dùng "bạn muốn xem việc cần làm hay hỏi về chính sách?"
6. Viga có được **ghi** (`log_content_gap`, `create_ticket`) không, hay giai đoạn này chỉ đọc?

### 15.8 Rủi ro

- Luật từ khóa tiếng Việt có thể **định tuyến sai** (câu lai giữa hai nhóm); cần bộ câu hỏi chuẩn riêng cho định tuyến và theo dõi tỉ lệ rơi vào "mặc định".
- Công cụ đọc lộ trình phải kiểm quyền chặt (mỗi người chỉ thấy của mình), nếu không là rò dữ liệu giữa nhân viên.
- Thêm ngữ cảnh người hỏi làm phát sinh thông tin cá nhân đi qua bước xử lý; cho LLM định tuyến chỉ gửi **mã, tên, trạng thái việc**, không gửi tên, email, phòng ban của nhân viên (quyết định 3, mục 0.1).

## 16. Quản lý tài liệu theo phiên bản (đã cài đặt, trừ so sánh khác biệt và nối lại nguồn của task)

> **Cập nhật 01/10/2026: phần này đã được cài đặt, xem 18.1 và 18.5.** Nội dung bên dưới giữ nguyên bản thiết kế gốc để đối chiếu.
> **Chưa làm:** giai đoạn 4 (so sánh khác biệt hai phiên bản; cảnh báo "nguồn đã đổi" và tự nối lại nguồn của task, mục 16.6).

> **Trạng thái: đề xuất để thảo luận, chưa có dòng code nào.** Yêu cầu: một **tài liệu** có **nhiều phiên bản**; người dùng
> chọn một phiên bản để xem, **chỉnh sửa**, hoặc **sao chép từ bản cũ thành bản mới rồi sửa và lưu**.

### 16.1 Hiện trạng và khoảng cách

| | Hiện có | Còn thiếu |
|---|---|---|
| Dữ liệu | Mỗi `documents` đã có nhiều `document_versions` (nhãn, số thứ tự `revision_no`, trạng thái, ngày hiệu lực, **toàn bộ Markdown**, section, chunk, file gốc) | Không nhớ bản nào sinh ra từ bản nào; chưa có trạng thái "bản nháp" dùng được |
| Giao diện trang Tài liệu | **Mỗi dòng là một tài liệu**, chỉ hiện bản mới nhất; sửa chỉ đổi **tên và danh mục**; "Tải phiên bản mới" là tải một file | Không có danh sách phiên bản, không xem được bản cũ, không sửa được **nội dung** |
| Nạp bản mới | Chỉ có đường tải file lên | Bản cũ không được đóng nên **đang lỗi** (lỗi 1, mục 10.2) |

### 16.2 Khái niệm

```text
 TÀI LIỆU (documents)  = vỏ chứa: tên, danh mục, người phụ trách, trạng thái dùng/ngừng dùng
      |
      +-- PHIÊN BẢN (document_versions) = nội dung có ngày hiệu lực
             v1  Đã thay thế     01/01 - 30/06     (chỉ xem)
             v2  Đang áp dụng    01/07 -            (chỉ xem)
             v3  Bản nháp        (chưa có hiệu lực) (sửa được, chưa ảnh hưởng ai)
```

**Nguyên tắc cốt lõi:** *bản đang áp dụng và bản đã thay thế không bị sửa tại chỗ.* Muốn sửa nội dung thì **tạo bản
nháp mới** (sao chép từ bất kỳ bản nào), sửa trên bản nháp, rồi **kích hoạt**. Lý do:

1. Viga đang trả lời bằng bản đang áp dụng; sửa tại chỗ là đổi câu trả lời của mọi người **ngay lập tức, không qua duyệt**.
2. Task đã tạo trỏ vào **section cụ thể của một phiên bản** (`task_source_mappings`); sửa tại chỗ làm mất căn cứ trích dẫn.
3. Giữ được lịch sử "lúc đó chính sách ghi gì" để đối chiếu và truy vết.

"Chỉnh sửa phiên bản cũ" vì thế được hiểu là: **sao chép bản cũ thành bản nháp mới rồi sửa** (đúng cách anh mô tả); không sửa
đè lên bản cũ. Nếu muốn **quay về bản cũ** thì cũng là sao chép bản cũ thành bản mới rồi kích hoạt (số thứ tự luôn tăng, lịch sử
không bị viết lại).

### 16.2b Chọn bản áp dụng và sửa bản cũ (chỉnh theo góp ý mới nhất)

Mô hình chốt lại: **một tài liệu, nhiều phiên bản, đúng một bản đang áp dụng (active) tại một thời điểm, và HR là người chọn
bản nào áp dụng.** Viga và task chỉ dùng bản đang áp dụng.

| Việc HR muốn | Cách làm | Ghi chú |
|---|---|---|
| **Chọn một phiên bản (kể cả bản cũ) làm bản áp dụng** | Nút **"Đặt làm bản áp dụng"** trên bất kỳ phiên bản nào | Đóng bản đang áp dụng, bật bản được chọn; đây cũng là cách **quay về bản cũ** mà không cần tải lại file. Không phải nạp lại nếu bản đó đã có section và chunk |
| **Xem** bất kỳ phiên bản nào | Mở thẳng, có ô chọn nhanh phiên bản | Chỉ đọc |
| **Sửa một phiên bản cũ** | Hai lựa chọn, **anh chọn ở 16.9 mục 1**: (a) **sửa tại chỗ** bản cũ (chỉ khi bản đó **không** đang áp dụng); (b) **sao chép thành bản mới rồi sửa** | Xem so sánh bên dưới |
| **Sao chép bản cũ thành bản mới rồi sửa** | **"Tạo bản mới từ bản này"** → bản nháp mới → sửa → lưu → (tuỳ chọn) đặt làm bản áp dụng | An toàn nhất, giữ nguyên lịch sử |
| Sửa bản **đang áp dụng** | Không sửa tại chỗ; tạo bản mới từ nó rồi sửa, hoặc sửa bản nháp | Tránh đổi câu trả lời của Viga ngay lập tức |

**Hai cách sửa bản cũ, so sánh để anh chọn:**

| | (a) Sửa tại chỗ bản cũ (không đang áp dụng) | (b) Sao chép thành bản mới rồi sửa |
|---|---|---|
| Đơn giản với HR | Rất đơn giản: sửa đâu lưu đó | Thêm một bước sao chép |
| Lịch sử | **Bị ghi đè**: không còn biết bản đó từng ghi gì | **Giữ nguyên** mọi bản |
| Task đã trỏ vào bản đó (`task_source_mappings`) | Section bị cắt lại nên **mã section đổi**, liên kết nguồn có thể mất; cần nối lại theo đoạn trích | Không ảnh hưởng, bản cũ còn nguyên |
| Viga | Không ảnh hưởng nếu bản đó không áp dụng; nếu sau đó đặt làm bản áp dụng thì dùng nội dung đã sửa | Không ảnh hưởng đến khi kích hoạt |
| Chi phí | Cắt lại và embedding lại **khi lưu** nếu bản đó từng có chunk | Embedding **khi kích hoạt** bản mới |

Đề xuất: **cho phép cả hai nhưng mặc định là (b)**; (a) chỉ dành cho bản **nháp** và bản **đã thay thế chưa có task nào dùng**, kèm
cảnh báo rõ khi bản đó đang được task dùng. Nếu anh muốn (a) cho **mọi** bản cũ thì phải chấp nhận rủi ro mất liên kết nguồn
của task và mất lịch sử.

**Quy tắc "đúng một bản đang áp dụng":** DB đã có ràng buộc không cho hai bản `ACTIVE` chồng ngày hiệu lực. "Đặt làm bản áp dụng" sẽ:
đóng bản hiện tại (`effective_to` = hôm qua), đặt bản được chọn có `effective_from` = hôm nay và `effective_to` rỗng, ghi nhật
ký. Khoảng hiệu lực cũ của bản được chọn **được thay bằng khoảng mới** (lịch sử "ai áp dụng khi nào" nằm ở nhật ký kiểm toán).

### 16.3 Vòng đời một phiên bản

```text
  tải file (= đọc + lưu file gốc + tạo NHÁP, nhanh, chưa embedding)  --->  [NHÁP]  <----- sao chép từ bản bất kỳ
                     |  sửa nội dung, tên nhãn, ngày hiệu lực; lưu nhiều lần, KHÔNG tốn tiền embedding
                     v
                 [kích hoạt]  = chạy nền có tiến trình phần trăm (mục 14):
                     cắt section, chunk, embedding  ->  trong MỘT transaction:
                     đóng bản đang áp dụng (effective_to = ngày trước ngày hiệu lực mới)
                     + bật bản này thành ĐANG ÁP DỤNG
                     |
                     v
              [ĐANG ÁP DỤNG]  --(có bản mới kích hoạt)-->  [ĐÃ THAY THẾ]
                                                    |
                                                    +--("Đặt làm bản áp dụng")-->  [ĐANG ÁP DỤNG]
                                                        (embedding lại nếu model embedding khi đó khác model hiện tại)
                     |
                     +-- hoặc đặt ngày hiệu lực ở tương lai -> [SẮP HIỆU LỰC] -> tự thành ĐANG ÁP DỤNG tới ngày
```

| Trạng thái hiển thị | Ứng với (cột `status` hiện có) | Sửa nội dung | Viga tìm thấy |
|---|---|---|---|
| **Bản nháp** | `PENDING_REVIEW` (hoặc thêm giá trị `DRAFT` nếu muốn tách rõ) | Có | Không |
| **Đang xử lý** | `PROCESSING` | Không | Không |
| **Sắp hiệu lực** | `ACTIVE` với `effective_from` ở tương lai | Không | Chỉ khi tới ngày |
| **Đang áp dụng** | `ACTIVE`, trong khoảng hiệu lực | Không | **Có** (duy nhất một bản tại một ngày) |
| **Đã thay thế** | `ARCHIVED` | Không | Không |
| **Lỗi** | `FAILED` (kèm `failure_reason`) | Không (thử lại hoặc xóa) | Không |

Các giá trị `PROCESSING`, `PENDING_REVIEW`, `FAILED` đã có trong enum nhưng **chưa được dùng**; kế hoạch này dùng chúng.

### 16.4 Trang quản lý đề xuất

**Danh sách tài liệu** giữ như hiện nay (mỗi dòng một tài liệu) nhưng bấm vào dòng thì mở **trang chi tiết tài liệu**
(`/admin/documents/{id}`), không còn chỉ có nút "xem".

```text
 Chính sách nghỉ phép năm                         [Sửa tên, danh mục]  [Ngừng sử dụng]
 Nhóm: Nghỉ phép và nghỉ lễ · 3 phiên bản

 PHIÊN BẢN                       TRẠNG THÁI        HIỆU LỰC          NGƯỜI    HÀNH ĐỘNG
 v3  Cập nhật tháng 10          [Bản nháp]         (chưa đặt)        Hồng     Xem · Sửa · So sánh · Kích hoạt · Xóa nháp
 v2  Phiên bản 2025             [Đang áp dụng]     01/07/2025 -      Hồng     Xem · So sánh · Tạo bản mới từ bản này · File gốc
 v1  Phiên bản 2024             [Đã thay thế]      01/01/2024 - 30/06/2025   Hồng     Xem · So sánh · Tạo bản mới từ bản này · File gốc

 [ + Tải file thành phiên bản mới ]   [ + Tạo bản nháp từ bản đang áp dụng ]
```

| Hành động | Làm gì |
|---|---|
| **Đặt làm bản áp dụng** | Chọn **bất kỳ** phiên bản (kể cả cũ) làm bản Viga và task dùng; hộp xác nhận nêu rõ bản nào ngừng áp dụng và số task đang dùng nguồn khác |
| **Xem** | Mở trang giấy có mục lục (đã có) cho **đúng phiên bản được chọn**, có ô chọn nhanh sang phiên bản khác |
| **So sánh** | Hiện khác biệt chữ giữa hai phiên bản (thêm, xóa, sửa theo dòng); giai đoạn 2 |
| **Tạo bản mới từ bản này** | Sao chép Markdown của bản đó thành **bản nháp mới** (nhãn gợi ý "bản X (sao chép)") rồi mở trình soạn thảo |
| **Sửa** (bản nháp; bản cũ nếu anh chọn cho phép — 16.2b) | Trình soạn thảo Markdown có xem trước bên cạnh; sửa nhãn; **Lưu** nhiều lần. Bản đang áp dụng không sửa tại chỗ |
| **Kích hoạt** | Hộp xác nhận nói rõ: "Bản đang áp dụng sẽ ngừng hiệu lực từ ngày …; Viga sẽ trả lời theo bản này; N task đang dùng nguồn từ bản cũ"; rồi chạy nền có thanh phần trăm |
| **Xóa nháp** | Chỉ xóa được bản nháp chưa từng kích hoạt |
| **File gốc** | Mở file đã tải của đúng phiên bản đó (bản sao chép từ chữ thì ghi rõ "file gốc thuộc bản X") |

### 16.5 Việc kích hoạt làm gì (chi tiết)

1. Kiểm tra: bản nháp không rỗng, đủ độ dài, có cấu trúc (mục 13), nhãn không trùng, ngày hiệu lực hợp lệ.
2. Chạy nền (mục 14): cắt section và chunk, embedding, lưu file nếu có.
3. **Một transaction duy nhất:** ghi section và chunk; đặt `effective_to` của bản đang áp dụng = ngày trước `effective_from` của bản mới;
   chuyển bản cũ sang `ARCHIVED`; chuyển bản mới sang `ACTIVE`; ghi `audit_logs`. Có lỗi thì **không đổi gì**, bản cũ vẫn chạy
   (chính là cách sửa lỗi 1 ở mục 10.2).
4. Ràng buộc DB đã có (không chồng ngày hiệu lực của hai bản `ACTIVE`) vẫn là lưới an toàn cuối cùng.
5. Kiểm tra **task đang dùng nguồn từ bản cũ** (16.6).

### 16.6 Ảnh hưởng tới task đã tạo

`task_source_mappings` trỏ vào section **của bản cũ**. Khi có bản mới:

| Tình huống | Xử lý đề xuất |
|---|---|
| Đoạn trích (quote) của task vẫn nằm **nguyên văn** trong bản mới | Tự nối lại sang section tương ứng của bản mới |
| Quote không còn hoặc đã đổi | Task được đánh dấu **"nguồn đã đổi, cần xem lại"** ở trang Quản lý task và cột "Task sử dụng" của trang Tài liệu; HR mở so sánh để quyết |
| Task trỏ vào bản đã thay thế mà HR chưa xử lý | Vẫn dùng được (không tự đổi nội dung task); chỉ cảnh báo |

Không bao giờ tự sửa nội dung task khi tài liệu đổi; chỉ **cảnh báo và hỗ trợ nối lại**.

### 16.7 Thay đổi dữ liệu và API (dự kiến)

| Thành phần | Thay đổi |
|---|---|
| `document_versions` | Thêm `parent_version_id` (bản này sao chép từ bản nào, rỗng nếu tải file), `source` (`UPLOAD` hoặc `EDITED`), `updated_by`; dùng `status` như 16.3; kiểm tra có ràng buộc nào chặn trùng `content_checksum` giữa các phiên bản của cùng tài liệu (sao chép chưa sửa sẽ trùng) |
| API đọc | `GET /portal/documents/{id}/versions` (danh sách, trạng thái, hiệu lực); `GET /portal/documents/{id}/versions/{vid}` (nội dung, kể cả bản không còn áp dụng, chỉ HR và Admin) |
| API ghi | `POST .../versions/{vid}/copy` (tạo nháp); `PATCH .../versions/{vid}` (sửa nháp: nội dung, nhãn, ngày hiệu lực; khóa lạc quan theo `updated_at` để hai người không đè nhau); `POST .../versions/{vid}/activate` (chạy nền, trả `job_id` — mục 14); `DELETE .../versions/{vid}` (chỉ nháp) |
| Tải file | `POST /portal/documents` giữ nguyên nhưng khi tài liệu đã có thì **tạo bản nháp** thay vì kích hoạt ngay (người dùng xem trước rồi mới kích hoạt) |
| Nhật ký | Ghi `audit_logs` cho: tạo nháp, sửa nháp, kích hoạt, xóa nháp |

**Bổ sung đã chốt cho 16.7:**
- **Tên file Cloudinary theo `file_checksum`** (không theo `content_checksum`) để hai bản khác byte không ghi đè nhau (rủi ro ở mục 1.1). Bản **sao chép** không
  tải file lên lại: nó trỏ tới file gốc của bản nguồn qua `parent_version_id`.
- **Embedding lại khi kích hoạt** nếu `embedding_model_version` của bản đó khác model hiện tại (tìm kiếm lọc theo model, nên bản cũ chưa embedding lại sẽ không tìm thấy).
- Bản đầu **không** có sửa tại chỗ bản cũ; chỉ sao chép và sửa nháp (quyết định 5).

### 16.8 Các giai đoạn đề xuất

| Giai đoạn | Việc | Ghi chú |
|---|---|---|
| **1. Xem và lịch sử** | Trang chi tiết tài liệu, danh sách phiên bản, xem đúng phiên bản được chọn; sửa lỗi 1 và 2 (mục 10.2) | Không đổi hành vi nào của Viga, rủi ro thấp |
| **2. Sao chép và sửa nháp** | Tạo bản nháp từ bản bất kỳ, trình soạn thảo Markdown có xem trước, lưu nháp, xóa nháp | Nháp không tốn tiền embedding và Viga không thấy |
| **3. Kích hoạt** | Kích hoạt chạy nền có tiến trình (mục 14), đóng bản cũ trong một transaction, lên lịch hiệu lực ở tương lai | Phụ thuộc mục 14 |
| **4. So sánh và task** | Xem khác biệt hai phiên bản; tự nối lại và cảnh báo task nguồn đã đổi | Phụ thuộc giai đoạn 3 |

### 16.9 Điểm cần anh quyết (câu đã chốt: xem mục 0.1)

1. **Sửa bản cũ theo cách nào?** (a) sửa tại chỗ, (b) sao chép thành bản mới rồi sửa, hay **cho phép cả hai, mặc định (b)** (đề xuất)? Bản **đang áp dụng** vẫn không sửa tại chỗ (nếu sửa phải chấp nhận Viga đổi câu trả lời ngay).
1b. **Có nút "Đặt làm bản áp dụng" cho bất kỳ phiên bản nào** (kể cả cũ) để quay về bản trước không? (Đề xuất: có.)
2. Trình soạn thảo: **Markdown thuần có xem trước** (đơn giản) hay soạn thảo giàu định dạng giống Word? (Đề xuất Markdown trước; soạn thảo giàu định dạng tốn công nhiều và dễ làm hỏng bảng.)
3. Sau khi sửa chữ thì **file gốc không còn khớp**. Chấp nhận ghi rõ "file gốc thuộc bản X", hay xuất lại ra `.docx` mới?
4. Cho phép **lên lịch hiệu lực ở tương lai** (bản "Sắp hiệu lực") hay chỉ kích hoạt có hiệu lực từ hôm nay?
5. Một tài liệu có được có **nhiều bản nháp cùng lúc**, hay tối đa một bản nháp?
6. Ai được kích hoạt: mọi HR, hay cần **người duyệt** thứ hai (dùng trạng thái `PENDING_REVIEW` thật sự làm bước duyệt)?
7. Có cần **so sánh khác biệt** ngay giai đoạn đầu không, hay để giai đoạn 4?
8. Khi bản mới làm task cũ mất nguồn: chỉ **cảnh báo** (đề xuất) hay chặn kích hoạt cho đến khi HR xử lý?

### 16.10 Rủi ro

- Sao chép rồi sửa nội dung làm **embedding phải làm lại toàn bộ** tài liệu lúc kích hoạt (tốn tiền và thời gian theo cỡ tài liệu, nên cần mục 14).
- Trình soạn thảo Markdown có thể làm HR **vô tình xóa cấu trúc** (heading, bảng); cần xem trước và nhắc cảnh báo cấu trúc (mục 13) trước khi kích hoạt.
- Hai HR cùng sửa một bản nháp: cần khóa lạc quan, nếu không người lưu sau ghi đè người trước.
- Đóng bản cũ sai ngày có thể để hở khoảng không có bản nào hiệu lực (Viga trả "chưa có căn cứ") hoặc chồng ngày (DB chặn); phải có test kỹ các mốc ngày.
- Tài liệu đã ngừng sử dụng (`documents.status = ARCHIVED`) vẫn bị Viga tìm thấy (lỗi 2); phải sửa trước hoặc cùng giai đoạn 1.

## 17. Viga dạng agent LLM chọn công cụ, các đường thoát và gợi ý tạo ticket cho HR (đã cài đặt)

> **Cập nhật 01/10/2026: phần này đã được cài đặt, xem 18.2, 18.4 và 18.6.** Nội dung bên dưới giữ nguyên bản thiết kế gốc để đối chiếu.

> **Trạng thái: đề xuất flow để thảo luận, chưa có dòng code nào.** Theo yêu cầu mới nhất: **đưa câu hỏi vào LLM để nó phân loại và chọn
> công cụ (kiểu agent)**, rồi có **đường thoát rõ ràng**; câu nào tra không ra thì nói thẳng là không có và **gợi ý tạo ticket cho HR**.
> Mục này **thay đổi so với đề xuất ở 15.3c** (luật làm trước, LLM chỉ dự phòng): ở đây LLM là bộ định tuyến chính. Hai hướng được
> so sánh ở 17.9 để anh chọn.

### 17.1 Agent ở đây nghĩa là gì (có giới hạn, không phải agent tự do)

LLM **chỉ làm một việc ở bước đầu: chọn công cụ và điền tham số** từ một **danh sách đóng**. Công cụ chạy bằng code tất định. Câu trả lời
cuối cùng đến từ **dữ liệu của công cụ** (lộ trình, tài liệu có nguồn), không phải từ trí nhớ của LLM. Agent bị chặn bởi:

| Giới hạn | Giá trị đề xuất |
|---|---|
| Số lần gọi công cụ tối đa mỗi câu hỏi | 2 (ví dụ `get_next_tasks` rồi `search_documents`) |
| Số vòng LLM tối đa | 2 (chọn công cụ, và một lần soạn nếu ghép nhiều kết quả) |
| Thời gian tổng tối đa | Có hạn; quá hạn thì thoát bằng đường lỗi (17.4) |
| Ngân sách token mỗi câu | Có hạn, đo theo mục 12 |
| Công cụ ghi (tạo ticket) | **Chỉ chạy sau khi người dùng bấm xác nhận**, LLM không tự gọi |

### 17.2 Flow chuẩn

```text
 Nhân viên gõ câu hỏi (chỉ câu hỏi + conversation_id; KHÔNG gửi task_id)
      |
      v
 [0] AN TOÀN VÀO CỬA
      throttle theo người dùng · giới hạn độ dài · bọc <user_input> chống tiêm lệnh
      |-- quá giới hạn ------------------------------------------------> THOÁT: 429 "hỏi nhanh quá, thử lại sau"
      v
 [1] NGỮ CẢNH (truy vấn DB, KHÔNG LLM)
      BACKEND TỰ GỌI dữ liệu của chính người hỏi (từ phiên đăng nhập), không chờ giao diện báo:
        ngày hiện tại, việc làm được ngay, việc bị khóa và việc chặn, tiến độ
        + "việc hiện tại" (việc người này đang xem/làm, suy ra theo 15.3e)
      + vài lượt hội thoại gần nhất (mục 6.2)
      v
 [2] LLM ĐỊNH TUYẾN (1 lần gọi, trả JSON theo schema cố định)
      vào: câu hỏi · lượt gần nhất · tóm tắt snapshot (mã và tên việc, không dữ liệu thừa) · danh mục công cụ
      ra:  { "tool": <một tên trong danh sách đóng>, "args": {...}, "confidence": 0..1,
             "clarify": null | "câu hỏi lại ngắn" }
      v
 [3] KIỂM LẠI BẰNG CODE (không tin LLM)
      tool có trong danh sách? tham số đúng kiểu? task_id có thuộc lộ trình CỦA NGƯỜI HỎI?
      |-- sai / không parse được / confidence thấp --> THOÁT mềm: rơi về hỏi đáp tài liệu (17.4 đường R)
      |-- cần làm rõ -------------------------------> THOÁT: hỏi lại đúng MỘT câu (ví dụ "bạn đang nói về việc nào?")
      v
 [4] CHẠY CÔNG CỤ (tất định, chỉ đọc, đúng phạm vi của người hỏi)
      +---------------------------+------------------------------+----------------------------+
      | dữ liệu lộ trình          | tài liệu                     | đầu mối, mẫu (khi HR có)   |
      | get_next_tasks            | search_documents             | get_contact                |
      | get_day_plan              | -> tìm hybrid -> trả lời     | get_template               |
      | explain_lock              |    có trích dẫn -> kiểm      | get_approved_link          |
      | get_task_detail           |    chứng nguyên văn          |                            |
      | get_progress              |                              |                            |
      +-------------+-------------+---------------+--------------+--------------+-------------+
                    |                             |                              |
                    v                             v                              v
 [5] KẾT QUẢ CÓ NGUỒN?  ----------- CÓ ----------->  SOẠN CÂU TRẢ LỜI
      |                                  nhóm dữ liệu lộ trình: dùng mẫu câu cố định (không LLM, nhanh, không bịa)
      |                                  nhóm tài liệu: câu trả lời đã kiểm chứng (như hiện nay)
      |                                  + suggested_actions (mở việc, mở ngày) + nguồn
      |                                  -> ghi hội thoại -> THOÁT: ANSWER / dữ liệu
      |
      +-- KHÔNG ------------------------------------------------------->  [6] KHÔNG TRA ĐƯỢC
                                                                              |
                                                                              v
 [6] ĐƯỜNG "KHÔNG TRA ĐƯỢC" (xem 17.3)
      nói thẳng "Mình chưa có căn cứ để trả lời" (KHÔNG đoán)
      + nút  [ Gửi câu hỏi này cho HR ]   <-- người dùng bấm mới tạo ticket
      + ghi câu hỏi vào danh sách "câu hỏi chưa trả lời được" (cho HR bổ sung tài liệu)
```

### 17.3 Các đường thoát (mọi câu hỏi đều phải kết thúc ở đúng một trong các đường này)

| Đường thoát | Khi nào | Người dùng thấy | Ghi lại |
|---|---|---|---|
| **ANSWER** | Hỏi đáp tài liệu có nguồn, qua kiểm chứng | Câu trả lời + nguồn mở được | Hội thoại, số liệu |
| **DATA** (`NEXT_STEP`, `DAY_PLAN`, `PREREQUISITE_REQUIRED`, `INFO`) | Công cụ lộ trình trả được | Câu trả lời từ dữ liệu thật + nút mở việc | Hội thoại, số liệu |
| **CLARIFY** | LLM thấy thiếu tham số (không biết việc nào) | Một câu hỏi lại kèm tối đa 3 lựa chọn bấm | Hội thoại |
| **NOT_IN_JOURNEY** | Việc nêu ra không thuộc lộ trình của người hỏi | "Việc này không có trong lộ trình của bạn." | Số liệu |
| **NO_BASIS** | Tìm tài liệu không ra căn cứ, hoặc câu trả lời không qua kiểm chứng | "Mình chưa có căn cứ…" + **gợi ý gửi HR** | Câu hỏi chưa trả lời được |
| **OUT_OF_SCOPE** | Thông tin cá nhân không có trong tài liệu chung (lương, số dư phép riêng, mentor) | "Thông tin này không có trong tài liệu chung, bạn hỏi HR phụ trách" + **gợi ý gửi HR** | Số liệu |
| **ERROR** | LLM hoặc dịch vụ ngoài lỗi, quá hạn | "Viga tạm thời chưa trả lời được" + thử lại + **gợi ý gửi HR**; trước đó tự lùi: định tuyến lỗi thì rơi về hỏi đáp tài liệu | Lỗi (mã ngắn), số liệu |
| **THROTTLED** | Quá 100 câu / 5 phút | Thông báo chờ | Số liệu |

Hiện lỗi mạng tới LLM hoặc embedding đang trả **500** (lỗi 3, mục 10.2); flow này đưa nó về đường **ERROR** có thông báo rõ.

### 17.4 Lùi dần khi có sự cố (không bao giờ bỏ rơi người dùng)

```text
 LLM định tuyến lỗi / quá hạn / trả sai schema
      -> lùi: hỏi đáp tài liệu (RAG hiện có)
            -> RAG lỗi (embedding/LLM)
                  -> THOÁT: ERROR có thông báo rõ + [ Gửi câu hỏi này cho HR ]
```

### 17.5 Gợi ý và tạo ticket cho HR

Bảng `tickets` và `ticket_messages` **đã có trong DB** nhưng **chưa có router và giao diện** (mục 10.3 và báo cáo tiến độ); trang "Ticket sự cố"
của HR đang hiện "Sắp có". Cần làm cùng nhau để đường thoát này có nơi đến.

```text
 [ Gửi câu hỏi này cho HR ]  (nút dưới câu trả lời "chưa có căn cứ" / "ngoài phạm vi" / "lỗi")
      |
      v
 hộp xác nhận (nhân viên XEM và SỬA trước khi gửi):
      câu hỏi gốc · ngữ cảnh đính kèm (việc đang mở, ngày) · ô ghi chú thêm · ai sẽ nhận (HR phòng ban)
      |  [ Gửi ]
      v
 POST /portal/tickets -> tạo ticket (gắn người hỏi, phòng ban, việc liên quan, nguồn "từ Viga")
      |
      +--> HR thấy ở trang "Ticket sự cố": danh sách, trạng thái, trả lời
      +--> ghi câu hỏi vào "câu hỏi chưa trả lời được" (trang "Phản hồi Viga" của HR) để bổ sung tài liệu
      +--> HR trả lời -> chuông thông báo của nhân viên báo có phản hồi
      v
 Nhân viên thấy "Đã gửi cho HR (mã #123)" ngay trong cuộc hội thoại
```

Quy tắc: **Viga không tự tạo ticket**, chỉ gợi ý; nhân viên bấm xác nhận. Không gợi ý ticket cho câu chỉ cần nói lại (CLARIFY) hoặc câu đã trả lời được.
Chống spam: giới hạn số ticket mỗi người mỗi ngày; câu giống nhau đã gửi trong thời gian ngắn thì nhắc "bạn đã gửi câu này rồi".

### 17.5b Ai quyết `OUT_OF_SCOPE` (đã chốt)

Hai lớp, để không phụ thuộc vào một chỗ:
1. **Bộ lọc từ khóa nhẹ trước LLM** cho nhóm thông tin cá nhân (lương, mentor, chỗ ngồi, số dư phép riêng): khớp thì trả thẳng đường **OUT_OF_SCOPE** kèm gợi ý gửi HR,
   **không tốn LLM** và không cho LLM định tuyến "đoán" câu đó là câu hỏi tài liệu.
2. Lớp thứ hai là kiểm tra có sẵn trong prompt trả lời tài liệu (`NO_BASIS/out_of_scope`) cho những câu lọt qua lớp một.

### 17.6 Danh mục công cụ đưa cho LLM (đóng)

| Công cụ | Tham số | Trả về | Có sẵn dữ liệu? |
|---|---|---|---|
| `get_next_tasks` | — | Việc làm được ngay | Có |
| `get_day_plan` | `day` (hôm nay / ngày N) | Việc của ngày kèm trạng thái | Có |
| `explain_lock` | `task_id` | Việc bị khóa vì việc nào | Có |
| `get_task_detail` | `task_id` | Hướng dẫn một việc | Có |
| `get_progress` | — | Tiến độ và số việc | Có |
| `search_documents` | `query` | Đoạn tài liệu có nguồn → trả lời đã kiểm chứng | Có |
| `get_contact` / `get_approved_link` | `task_id` hoặc `topic` | Đầu mối, đường dẫn HR đã duyệt | Chưa (chờ trang HR) |
| `get_template` | `template` | Mẫu điền sẵn | Chưa |
| `none` | — | Không công cụ nào hợp | — |

`create_ticket` **không nằm trong danh mục của LLM**: nó chỉ chạy sau nút xác nhận của người dùng ở giao diện.

### 17.7 Đo và kiểm soát agent

| Chỉ số | Vì sao |
|---|---|
| Độ chính xác định tuyến (công cụ LLM chọn có đúng không) trên bộ câu hỏi chuẩn riêng | Điều kiện để bật |
| Tỉ lệ mỗi đường thoát (ANSWER, DATA, NO_BASIS, ERROR…) | Thấy Viga trả lời được bao nhiêu |
| Phần trăm câu đi đường công cụ lộ trình (không RAG) | Đo hiệu quả cá nhân hóa |
| Token và độ trễ của **bước định tuyến** | Đây là chi phí thêm mỗi câu hỏi |
| Tỉ lệ bấm "Gửi HR" và tỉ lệ ticket sau đó dẫn tới bổ sung tài liệu | Vòng phản hồi có hiệu quả không |
| Số lần rơi về đường lùi (17.4) | Độ tin cậy của bộ định tuyến |

### 17.8 Các bước thực hiện đề xuất

| Bước | Việc | Phụ thuộc |
|---|---|---|
| 1 | Công cụ lộ trình tất định (`get_next_tasks`, `get_day_plan`, `explain_lock`, `get_task_detail`, `get_progress`) + snapshot, kiểm quyền | Dữ liệu đã có |
| 2 | Bộ định tuyến LLM trả JSON theo schema đóng + kiểm lại bằng code + đường lùi; thay thế bản mô phỏng ở giao diện | Bước 1, mục 12 (đo) |
| 3 | Đường thoát đầy đủ (NO_BASIS, OUT_OF_SCOPE, ERROR) và sửa lỗi 500 ở `/chat/ask` | Bước 2 |
| 4 | Tạo ticket và trang "Ticket sự cố" của HR; nút "Gửi câu hỏi này cho HR" | Router `tickets` |
| 5 | Ghi "câu hỏi chưa trả lời được" + trang "Phản hồi Viga" của HR | Router `content_gaps` |
| 6 | Hội thoại nhiều cuộc (mục 6.2) cung cấp lịch sử cho bộ định tuyến | Mục 6.2 |
| 7 | Công cụ đầu mối và mẫu | Trang "Đầu mối và đường dẫn" của HR |

### 17.9 Hai hướng, để anh chọn

| | **Hướng A: LLM định tuyến luôn** (theo yêu cầu mới) | **Hướng B: luật trước, LLM sau** (15.3c) |
|---|---|---|
| Linh hoạt với câu nói tự nhiên, sai chính tả, câu lai | **Tốt hơn** | Chỉ tốt với các mẫu đã viết luật |
| Độ trễ và chi phí mỗi câu | **Thêm một lần gọi LLM cho mọi câu**, kể cả câu đơn giản như "hôm nay làm gì" | Câu khớp luật: **0 lần gọi LLM, nhanh nhất** |
| Tất định, dễ kiểm thử | Kém hơn (LLM có thể chọn khác nhau giữa các lần) | **Cao** |
| Công sức viết | Ít luật phải viết | Phải viết và bảo trì luật tiếng Việt |
| Rủi ro chọn sai công cụ | Có, giảm bằng schema đóng + kiểm lại + bộ câu hỏi chuẩn | Thấp với câu khớp luật |

**Đề xuất:** làm **Hướng A làm chính**, nhưng chừa **lối tắt bằng luật** cho vài câu quá phổ biến và rõ ràng ("hôm nay làm gì", "tiếp theo làm gì", "tiến độ của tôi") để các câu này
nhanh và không tốn LLM; phần còn lại đi qua LLM định tuyến. Lối tắt thêm sau cũng được khi đo thấy đáng.

### 17.10 Điểm cần anh quyết (câu đã chốt: xem mục 0.1)

1. **Hướng A** (LLM định tuyến luôn, có thể thêm lối tắt luật sau) hay Hướng B?
2. Khi LLM định tuyến lỗi: lùi về hỏi đáp tài liệu (đề xuất) hay báo lỗi ngay?
3. Ngưỡng `confidence` dưới mức nào thì hỏi lại hoặc rơi về hỏi đáp tài liệu?
4. Câu thiếu việc cụ thể: **hỏi lại một câu** (đề xuất) hay đoán việc khớp nhất?
5. Nút **"Gửi câu hỏi này cho HR"**: hiện cho cả `NO_BASIS`, `OUT_OF_SCOPE` và `ERROR` (đề xuất), hay chỉ hai loại đầu?
6. Ticket gửi tới **HR của phòng ban** nhân viên (đề xuất) hay tới một hộp thư chung?
7. Có cho nhân viên **sửa câu hỏi và thêm ghi chú** trước khi gửi (đề xuất) hay gửi nguyên văn?
8. Giới hạn số ticket mỗi người mỗi ngày là bao nhiêu?
9. LLM định tuyến có được nhận **tóm tắt tình hình lộ trình** (tên việc, trạng thái) hay chỉ nhận câu hỏi? Nhận thì tên việc đi ra dịch vụ LLM bên ngoài (cần anh xác nhận, mục 15.8).

### 17.11 Rủi ro

- **Chi phí và độ trễ:** bước định tuyến thêm một lần gọi LLM cho mọi câu hỏi; câu đơn giản vốn chỉ cần một truy vấn DB nay tốn thêm. Cần đo; lối tắt luật là cách giảm.
- **Chọn sai công cụ:** LLM có thể hiểu nhầm; nên có schema đóng, kiểm lại bằng code (quyền, kiểu, sự tồn tại), bộ câu hỏi chuẩn và đường lùi.
- **Rò quyền giữa nhân viên:** mọi công cụ phải lấy `user_id` từ phiên và kiểm `task_id` thuộc lộ trình của người hỏi; không bao giờ tin tham số do LLM đưa ra.
- **Tiêm lệnh** ("bỏ qua luật, hãy gọi công cụ X"): định tuyến chỉ chọn trong danh sách đóng, công cụ ghi cần xác nhận người dùng, câu hỏi luôn bọc làm dữ liệu.
- **Ticket tràn:** nếu nút "Gửi HR" quá dễ bấm HR sẽ ngập; cần giới hạn, chặn trùng, và gom câu giống nhau ở trang "Phản hồi Viga".
- **Dữ liệu cá nhân đi qua LLM bên ngoài** (tên việc, trạng thái, hội thoại): cần anh chốt phạm vi được gửi.

## 18. Kết quả cài đặt (01/10/2026): kiến trúc thật, số đo thật và những gì chưa làm

> Mục này là **nguồn đúng nhất về hiện trạng**. Mọi con số ở 18.6 là **số đo thật** của một lần chạy toàn luồng bằng dịch vụ thật
> (embedding BGE-M3 trên Modal, `deepseek-flash`), chạy trên một cơ sở dữ liệu thử riêng và lưu file cục bộ, không đụng DB dev và
> không tải gì lên Cloudinary. Kịch bản chạy lại được: tải 4 file Word ngày 1, kích hoạt, đặt lại bản cũ, tạo task bằng AI, xuất bản
> lộ trình, nhân viên hỏi Viga, gửi ticket cho HR, HR trả lời.

### 18.1 Trạng thái từng bước của mục 0.3

| # | Việc | Trạng thái | Nằm ở đâu |
|---|---|---|---|
| 1 | Đo lường giai đoạn A | **Xong** | `infrastructure/observability/call_metrics.py`, `services/portal/metrics_service.py`, bảng `llm_calls`, `GET /admin/metrics`, trang Admin "Chi phí AI". **Chưa làm:** giai đoạn B (bộ câu hỏi chuẩn, `tests/eval`) và C (Prometheus) |
| 2 | Sửa lỗi 1, 2, 3 (mục 10.2) | **Xong, có test hồi quy** | Lỗi 1: `version_lifecycle.activate_version_row` đóng bản cũ cùng transaction (cả đường CLI `ingest_document`). Lỗi 2: `hybrid_search` lọc thêm `documents.status = 'ACTIVE'`. Lỗi 3: lỗi LLM/embedding trả `503 ASSISTANT_UNAVAILABLE` (`/chat/ask`) hoặc đường thoát `ERROR` (Viga), không còn 500 |
| 3 | Khung hội thoại và "việc vừa mở" | **Xong** | `chat_conversations`, `chat_messages`, `employee_journeys.last_opened_task_id/at`; `services/viga/conversations.py`; `POST /portal/me/tasks/{id}/opened` |
| 4 | Công cụ lộ trình, LLM định tuyến, đường thoát | **Xong** | `services/viga/{snapshot,tools,guard,router,service}.py`, `POST /viga/ask`. 5 công cụ lộ trình + `search_documents`. **Chưa có** `get_contact`, `get_approved_link`, `get_template` (chưa có trang HR đầu mối và mẫu để cấp dữ liệu) |
| 5 | Ticket cho HR, trang "Ticket sự cố" và "Phản hồi Viga" | **Xong** | `services/portal/ticket_service.py`, `services/viga/gaps.py`, `api/routers/ticket_router.py`, các trang `/admin/tickets`, `/admin/viga-feedback`, `/me/tickets` |
| 6 | Tải nháp và kích hoạt có tiến trình | **Xong** | `document_version_service.py`, `job_service.py`, `job_handlers.py`, `portal_document_router.py`; giao diện `DocumentVersionsModal`, `JobProgress` |
| 7 | Xử lý file thiếu heading | **Xong bậc 1, 2, 3, 5** | `services/ingest/structure.py`; bậc 4 (PDF theo cỡ chữ) **chưa làm**; OCR hoãn |
| (kèm) | Trang Tổng quan HR/Admin có biểu đồ đường, cột, tròn, chi phí và độ trễ mỗi lượt tạo task (7 biểu đồ chính) | **Xong** | `analytics_service.py`, `GET /portal/analytics`, migration `0007`, `components/charts/`, `features/portal-analytics/`. Chi tiết ở 18.4b |
| (kèm) | Chất lượng tạo task bằng AI (mục 10.3) | **Xong** | Ghép ba mục "Vì sao / Điều kiện hoàn thành / Các bước", lưu nhóm task, kiểm lại `quote` khi chấp nhận, ngân sách prompt, nhận JSON bọc object, "Chấp nhận tất cả", nhóm task tự suy từ danh mục |

### 18.2 Kiến trúc đã cài đặt

```text
 TÀI LIỆU
   HR chọn file ──> POST /portal/documents ──> đọc file (markitdown, luồng riêng) + nhận tiêu đề giả (bậc 2) + đo chất lượng cấu trúc
        (nhanh, ~0,5 giây)                      lưu file gốc (tên theo checksum FILE) ──> BẢN NHÁP (chưa chunk, chưa embedding)
                                                          |
                          xem / sửa Markdown (khóa lạc quan) / sao chép từ bản bất kỳ / xóa nháp
                                                          |
   Kích hoạt (hoặc "tải và kích hoạt luôn") ──> xếp JOB ACTIVATE_VERSION, bản chuyển PROCESSING ──> trả job_id (HTTP 202)
                                                          |
   worker trong tiến trình backend (SKIP LOCKED, tối đa 2 job) ──> 2%  kiểm tra
        5%  đọc cấu trúc ──> [LLM chia mục nếu cấu trúc POOR, đủ dài, còn hạn mức, 8-18%]
        20% cắt mục/chunk ──> 20→80% embedding theo TỪNG LÔ 32 (hoặc dùng lại vector cũ, hoặc tính lại vector cho chunk có sẵn)
        90% MỘT transaction: ghi section/chunk, đóng các bản ACTIVE khác, bật bản này ──> 100%
        lỗi ──> không đổi gì ở DB tài liệu; bản trả về trạng thái trước đó kèm lý do; job FAILED

 TẠO TASK BẰNG AI
   chọn N tài liệu ──> POST /portal/ai/task-proposal-jobs ──> job AI_TASK_PROPOSAL (mỗi tài liệu một phần 100/N, thanh chạy chậm dần
   khi chờ LLM) ──> result: từng tài liệu DONE/FAILED + đề xuất đã kiểm quote ──> HR chấp nhận từng cái hoặc tất cả

 VIGA CỦA NHÂN VIÊN  (POST /viga/ask: chỉ câu hỏi + conversation_id)
   [1] lưu câu hỏi, đọc 6 lượt gần nhất ──> [2] ảnh chụp lộ trình của chính người hỏi (DB)
   [3] bộ lọc thông tin cá nhân ──────────────────────────────> OUT_OF_SCOPE (0 LLM)
   [4] lối tắt luật: "hôm nay làm gì / tiếp theo / tiến độ" ───> công cụ lộ trình (0 LLM)
   [5] LLM định tuyến (1 lần, JSON đóng, code kiểm lại: tên công cụ, kiểu tham số, task_id thuộc lộ trình, confidence ≥ 0,55)
   [6] công cụ lộ trình (tất định, chỉ đọc)   HOẶC   pipeline tài liệu: viết lại (có lịch sử) → embedding → hybrid → trả lời → kiểm quote
   [7] không tra được ──> NO_BASIS / OUT_OF_SCOPE / ERROR + nút "Gửi câu hỏi này cho HR" (nhân viên xem và sửa rồi mới gửi)
   lùi dần: định tuyến lỗi/sai → hỏi đáp tài liệu → lỗi → ERROR (không bao giờ 500)
   ghi: tin nhắn + payload có cấu trúc (mở lại hiện đúng như lúc hỏi); câu NO_BASIS → "câu chưa trả lời được" ẩn danh cho HR
```

### 18.3 Dữ liệu mới (migration 0004 đến 0007)

| Migration | Thay đổi |
|---|---|
| `0004_llm_calls` | Bảng `llm_calls` (loại, thao tác, model, độ trễ, thành công/lỗi, token vào/ra, số chuỗi embed, chi phí ước tính, user, request). **Không có cột nội dung** (INV8) |
| `0005_document_drafts_and_job_progress` | `document_versions`: `parent_version_id`, `source` (UPLOAD/EDITED), `updated_by`, `updated_at` (khóa lạc quan), trạng thái `DRAFT`. `jobs`: `progress_percent`, `stage`, `result` (JSONB), `created_by`; loại việc `ACTIVATE_VERSION`, `AI_TASK_PROPOSAL` |
| `0006_viga_conversations_tickets` | `chat_conversations`, `chat_messages`; `employee_journeys.last_opened_task_id/last_opened_at`; `tickets.source` (MANUAL/VIGA), `tickets.conversation_id` |
| `0007_llm_calls_job_id` | `llm_calls.job_id` (BIGINT, có chỉ mục, không khóa ngoại): cộng chi phí và độ trễ theo từng lượt tạo task hoặc kích hoạt tài liệu |

### 18.4 API mới

| Nhóm | Endpoint |
|---|---|
| Tài liệu theo phiên bản (HR, Admin) | `POST /portal/documents` (tạo nháp, `activate=true` thì kích hoạt luôn), `GET .../documents/{id}/versions`, `GET|PATCH|DELETE .../versions/{vid}`, `POST .../versions/{vid}/copy`, `POST .../versions/{vid}/activate` |
| Việc nền | `GET /portal/jobs/{id}`, `GET /portal/jobs?active=true&kind=`, `POST /portal/ai/task-proposal-jobs` (người tạo hoặc Admin mới xem được) |
| Viga (mọi người đã đăng nhập) | `POST /viga/ask`, `GET /viga/conversations`, `GET|PATCH|DELETE /viga/conversations/{id}` |
| Việc vừa mở | `POST /portal/me/tasks/{id}/opened` |
| Ticket | `POST /portal/tickets`, `GET /portal/tickets/mine`, `GET /portal/tickets` (HR, Admin), `GET /portal/tickets/{id}`, `POST .../messages`, `POST .../claim`, `PATCH .../status` |
| Phản hồi Viga (HR, Admin) | `GET /portal/content-gaps`, `POST /portal/content-gaps/{id}/resolve` |
| Đo lường (Admin) | `GET /admin/metrics?days=` |
| Số liệu trang Tổng quan (HR: phòng ban của mình; Admin: tất cả) | `GET /portal/analytics?days=1..90` (18.4b) |
| Giữ nguyên nhưng đổi hợp đồng | `POST /portal/documents` giờ trả `201` (nháp) hoặc `202` + `job_id`, không còn `section_count`, `chunk_count`; `/chat/documents/{version_id}` chỉ cho nhân viên đọc **bản đang áp dụng** của tài liệu còn dùng (trước đây ai đăng nhập cũng đọc được cả bản nháp) |

### 18.4b Trang Tổng quan: API số liệu và biểu đồ (đợt 01/10/2026 buổi chiều)

**Mục tiêu:** HR và Admin nhìn một trang là biết người mới đang đi đến đâu, Viga được dùng ra sao, tài liệu đang ở trạng thái nào và **AI tốn
bao nhiêu tiền, chậm bao nhiêu, từng lượt tạo task một**.

**API:** `GET /api/v1/portal/analytics?days=1..90` (mặc định 14; chỉ HR và Admin). **HR chỉ thấy phòng ban của mình** (nhân viên, task, ticket, câu chưa
trả lời được, câu hỏi Viga, và lượt gọi AI do người trong phòng ban sinh ra); **Admin thấy toàn hệ thống**; tài liệu là dữ liệu chung nên cả hai cùng
thấy. HR chưa thuộc phòng ban nào nhận về toàn số 0, không lỗi. Phản hồi gồm `dates[]` (ngày theo múi giờ ứng dụng, cũ trước mới sau) và các danh
sách `*_per_day` **đúng bằng số ngày, ngày không có dữ liệu là 0** để vẽ đường không bị đứt. Chỉ có số liệu tổng hợp, **không có nội dung câu hỏi,
câu trả lời hay tài liệu** (INV8) và không lộ câu hỏi của từng người.

| Khối | Nội dung trả về |
|---|---|
| `people` | số nhân viên, % task xong, nhân viên theo tiến độ (chưa có lộ trình / chưa bắt đầu / đang làm / hoàn thành), task theo trạng thái, task theo nhóm, task hoàn thành mỗi ngày |
| `viga` | số câu hỏi, câu hỏi mỗi ngày, kết quả trả lời (9 loại), đường xử lý (lối tắt / bộ lọc / LLM / dự phòng), % không tốn LLM, % có nội dung trả lời |
| `tickets` | ticket theo trạng thái, ticket mới mỗi ngày, số câu chưa có căn cứ, thời gian phản hồi đầu tiên trung bình (giờ) |
| `documents` | số phiên bản theo 6 trạng thái hiển thị, tài liệu theo nhóm |
| `ai` | lượt gọi, lỗi, chi phí tổng và **theo ngày**, theo từng thao tác (số lượt, lỗi, p50, p95, token, chi phí), **20 lượt tạo task gần nhất** và **20 lượt kích hoạt tài liệu gần nhất** |

**Trang chỉ vẽ sáu biểu đồ quan trọng nhất** (bỏ biểu đồ kết quả trả lời của Viga theo góp ý ngày 02/10/2026) (anh yêu cầu bớt thẻ cho gọn; API vẫn trả đủ dữ liệu ở trên, cần thêm biểu đồ nào chỉ việc vẽ thêm, không phải sửa backend):

| # | Biểu đồ | Dạng | Nguồn |
|---|---|---|---|
| 1 | Tiến độ nhân viên | tròn | `people.by_progress` |
| 2 | Hoạt động mỗi ngày: task hoàn thành, câu hỏi Viga, ticket mới (cùng một đơn vị đếm nên chung một trục) | đường | `people.completed_per_day`, `viga.questions_per_day`, `tickets.created_per_day` |
| 3 | Chi phí AI mỗi ngày | đường | `ai.cost_per_day` |
| 4 | Chi phí theo thao tác (4 thao tác tốn nhất có màu riêng, còn lại gộp "Khác") | tròn | `ai.by_operation` |
| 5 | **Độ trễ mỗi lượt tạo task** (thời gian chạy so với thời gian chờ mô hình AI) | cột | `ai.task_runs` |
| 6 | **Chi phí mỗi lượt tạo task** | cột | `ai.task_runs` |

Trang **không có hàng thẻ chỉ số và không có tiêu đề mục** (mỗi biểu đồ đã có tên; anh yêu cầu bỏ cho gọn): chỉ còn thanh công cụ (nhãn phạm vi, chọn 7/14/30 ngày) rồi tới bảy biểu đồ. Số ticket, số câu chưa có căn cứ, tỉ lệ không tốn LLM, thời gian phản hồi đầu tiên vẫn có trong API nhưng giao diện hiện chưa hiện. Chưa có lượt tạo task nào thì hai thẻ 5 và 6 ghi rõ chưa có lượt nào thay vì vẽ biểu đồ trống; số trung bình các lượt thành công nằm trong phụ đề thẻ độ trễ.

**Độ trễ và chi phí mỗi lượt tạo task.** Trước đây `llm_calls` chỉ biết "thao tác nào", không biết "lượt nào", nên chỉ cộng được theo ngày. Migration
`0007` thêm `llm_calls.job_id` (có chỉ mục, **không khóa ngoại** để xóa job không làm mất số liệu). `job_service` chạy mỗi việc nền trong
`call_context(user_id=người tạo, job_id=...)`, mọi lời gọi LLM và embedding bên trong (kể cả bước chia mục bằng LLM) tự mang mã job. Số liệu một lượt
(`JobRunResponseDTO`): thời gian chạy thật (`finished_at − started_at`), **tổng thời gian chờ mô hình AI**, số lượt gọi, token vào/ra, chi phí, số tài liệu
và số đề xuất (hoặc số đoạn đã ghi với lượt kích hoạt). Trên giao diện, biểu đồ cột đặt cạnh nhau "thời gian chạy" và "chờ mô hình AI" để thấy ngay lượt
chậm do mô hình hay do phần còn lại; biểu đồ chi phí mỗi lượt riêng; lượt lỗi vẫn có cột (thời gian ngắn, chi phí 0). Trỏ chuột hoặc phím mũi tên
vào một cột hiện: trạng thái, số tài liệu, số đề xuất, số lượt gọi AI, token, chi phí. Phần đầu cụm ghi **trung bình các lượt thành công**
(giây mỗi lượt, USD, số đề xuất). Lượt chạy **trước** migration 0007 không có `job_id` nên chi phí và độ trễ AI của chúng hiện 0 (thời gian chạy vẫn đúng).

**Biểu đồ vẽ thế nào** (`frontend/src/components/charts/`, SVG thuần, không thêm thư viện): `LineChart`, `BarChart` (xếp chồng hoặc cạnh nhau),
`DonutChart`, `ChartCard`. Theo các nguyên tắc của skill dataviz: một trục y (không dùng hai
trục), đường 2px, cột bo đầu và cách nhau 2px khi xếp chồng, lưới mờ, **chú thích màu khi từ hai chuỗi trở lên**, trỏ chuột/phím mũi tên hiện chú giải,
mỗi biểu đồ có nút **"Xem dạng bảng"** (cùng số liệu, cho người đọc màn hình và để đối chiếu). Màu theo thứ tự cố định (xanh dương, cam, xanh ngọc, vàng,
hồng; xám cho "không có / đang khóa"), cùng một khái niệm giữ nguyên màu qua mọi biểu đồ (ví dụ "đã xong" luôn là xanh ngọc), có bộ riêng cho nền tối.
Bảng màu đã kiểm bằng `validate_palette.js`: bản sáng và tối đều đạt, riêng vài màu sáng (hồng, vàng, ngọc) trên nền sáng chưa đủ tương phản 3:1 nên
**mọi biểu đồ luôn có nhãn hoặc số bằng chữ** và bảng số liệu. Chữ trục đo theo bề rộng thật của khung (không bị co nhỏ trên màn hẹp), nhãn trục x tự
thưa đi khi dài.

**Đã xem bằng mắt:** dựng trang xem trước (không đụng `.next` của anh) bằng Vite và Chrome không đầu, chụp bản sáng, bản tối, trạng thái chưa có dữ liệu và
bề rộng điện thoại, có chú giải hiện. Hai lỗi hiển thị tìm được và đã sửa: nhãn trục chi phí lệch số chữ số (`0.0050` cạnh `0.010`), và nhãn trục x dài ("Chưa
phân nhóm", "25/09 10:10") chồng lên nhau trên thẻ hẹp (nay thưa nhãn theo độ dài). Phần xem bằng mắt làm trên bản 15 biểu đồ trước khi rút còn 7; bản rút gọn chỉ đổi bố cục nên mới kiểm bằng test.

### 18.5 Quyết định khi cài đặt (chi tiết hơn hoặc khác với bản thiết kế)

| Chủ đề | Đã làm như thế nào và vì sao |
|---|---|
| Kích hoạt lỗi | Không dùng trạng thái `FAILED` cho phiên bản: bản được **trả về trạng thái trước đó** (nháp vẫn sửa được, bản cũ vẫn là đã thay thế) kèm `failure_reason`; job mới là `FAILED`. Tránh ngõ cụt "FAILED không sửa được" |
| Ngày hiệu lực | Kích hoạt từ hôm nay trở về trước thì mọi bản ACTIVE khác chuyển `ARCHIVED`; hẹn ngày tương lai thì bản đang áp dụng **vẫn ACTIVE** tới hết ngày trước đó (Viga dùng bản cũ cho tới ngày hiệu lực). Trạng thái hiển thị tính từ ngày: nháp, đang xử lý, sắp hiệu lực, đang áp dụng, đã thay thế |
| Thứ tự ghi | Ràng buộc chống chồng ngày kiểm **ngay từng câu UPDATE**, nên phải `flush` việc đóng bản cũ trước khi bật bản mới (lỗi này do test tìm ra) |
| Embedding lại | Bản đã có chunk cùng model: dùng lại (0,4 giây). Khác model: tính lại vector **tại chỗ**, giữ nguyên section và chunk vì task có thể đang trỏ vào section đó |
| Cấu trúc | Tiêu đề giả được suy ra ngay lúc **tải nháp** và lưu vào Markdown của nháp, nên HR thấy và sửa được trước khi kích hoạt. LLM chia mục chạy lúc **kích hoạt** (bước 8-18%), tự động cho tài liệu POOR đủ dài, tối đa 30 lần/ngày, mọi lỗi đều lùi về kết quả bằng luật |
| Câu trả lời đa ngôn ngữ | Viga trả `message_key` + `message_params` để giao diện dịch vi/en; `message` tiếng Việt chỉ là dự phòng. Câu trả lời lấy từ tài liệu vẫn theo ngôn ngữ của tài liệu |
| Viga cho mọi vai trò | `POST /viga/ask` không khóa theo vai trò (HR, Admin cũng dùng được); giao diện hiện tại chỉ gắn nó vào khu nhân viên |
| Thông báo | Chuông nhân viên thêm thông báo "HR đã trả lời" từ ticket (hỏi lại mỗi phút); trạng thái đã đọc vẫn ở trình duyệt |
| Giới hạn hỏi | Dùng chung bộ đếm 100 câu/5 phút với `/chat/ask` (trong bộ nhớ một tiến trình, như cũ) |
| Retention | Tự xóa hội thoại quá 90 ngày không hoạt động, chạy định kỳ 6 giờ trong worker; người dùng xóa được cuộc của mình |
| Đơn giá | Mặc định cấu hình đặt theo bảng giá DeepSeek tra 01/10/2026 (0,30 vào, 1,20 ra, USD/triệu token, giờ cao điểm); đơn giá embedding vẫn 0 (chưa có giá Modal) |

### 18.6 Số đo thật (một lần chạy, 01/10/2026)

**Nạp và kích hoạt tài liệu** (Modal embedding thật, file Word ngày 1):

| Việc | Thời gian | Ghi chú |
|---|---|---|
| Tải file thành bản nháp (đọc + lưu file gốc) | 0,4 đến 0,7 giây | Đồng bộ, nhanh vì chưa embedding |
| Kích hoạt, file có heading (18 mục, 18 chunk) | 24,2 giây | **~18 giây là Modal khởi động nguội** (lần gọi đầu); thanh hiện "Kết nối dịch vụ embedding" |
| Kích hoạt, file không heading (687 từ → 7 mục, 8 chunk, tiêu đề suy từ dòng viết HOA) | 2,9 giây | Dịch vụ đã nóng |
| Kích hoạt "ngoại lệ" v1 (22 mục) và v2 | 5,1 và 4,3 giây | Một lô embedding chiếm 3 đến 3,5 giây |
| Đặt lại bản cũ làm bản áp dụng | 0,4 giây | Dùng lại embedding, không tốn tiền |
| Chuyển về bản mới | 1,3 giây | Đã có vector |

Embedding theo lô: p50 3,3 giây mỗi lô (tối đa 32 chuỗi), p95 3,7 giây (4 lô, 70 chuỗi).

**Tạo task bằng AI**: tài liệu 18 mục mất **48,3 giây**, ra 14 đề xuất (nhóm do AI chọn hoặc suy từ danh mục), 2.571 token vào,
**14.901 token ra** (model có suy luận nội bộ nên token ra nhiều hơn hẳn nội dung), chi phí ước tính 0,0187 USD. Thanh phần trăm
đã chỉnh thang thời gian lên 30 giây để không chạm trần sớm.

**Hỏi Viga** (độ trễ cả câu, đo từ phía nhân viên):

| Loại câu | Đường đi | Thời gian | LLM |
|---|---|---|---|
| "Hôm nay làm gì?", "Tiếp theo tôi làm gì?", "Tôi làm được bao nhiêu rồi?" | Lối tắt luật | 0,03 đến 0,08 giây | 0 lời gọi |
| "Sao tôi chưa làm được việc X?" | LLM định tuyến + công cụ | 1,1 giây | 1 lời gọi |
| "Mentor của mình là ai?" | Bộ lọc thông tin cá nhân | 0,05 giây | 0 lời gọi |
| Câu hỏi tài liệu có căn cứ ("không có VNeID, thay bằng CMND được không?") | Định tuyến → viết lại → embedding → tìm → trả lời → kiểm | 6 đến 8 giây | 3 lời gọi |
| Câu không có căn cứ ("quy định gửi xe máy tầng hầm?") | Như trên, trả `NO_BASIS` | 6 giây | 3 lời gọi |

Từng bước (p50 theo lời gọi): định tuyến 1,16 giây, viết lại 1,45 giây, embedding câu hỏi 1,62 giây, trả lời 1,71 giây.

**Chi phí và token** (19 lời gọi, 0 lỗi, tổng 0,0289 USD):

| Thao tác | Lượt | Token vào | Token ra | USD |
|---|---|---|---|---|
| `chat.answer` | 3 | 20.435 | 870 | 0,00717 |
| `chat.rewrite` | 3 | 2.358 | 551 | 0,00137 |
| `viga.route` | 4 | 4.488 | 308 | 0,00172 |
| `task.proposal` | 1 | 2.571 | 14.901 | 0,01865 |
| `chat.embed`, `ingest.embed`, `ingest.probe` | 3, 4, 1 | (embedding: 3, 70, 1 chuỗi) | | 0 (chưa có giá Modal) |

**So với ước lượng ở 12.11:** một câu hỏi tài liệu thực tế tốn khoảng **0,0033 USD (~82 đồng)**, gần **3 lần** ước lượng cũ (0,0011 USD).
Nguyên nhân: ngân sách 3.000 "từ" của đoạn tài liệu tương đương **~6.800 token** tiếng Việt, không phải ~2.400 như ước lượng; số lời gọi
đúng như dự kiến (3). Câu đi lối tắt luật hoặc bộ lọc tốn 0. Độ trễ đo thật (6 đến 8 giây cho 3 lời gọi LLM và 1 lần embedding) nằm trong khoảng
ước lượng 3 đến 10 giây, nhưng embedding câu hỏi mất ~1,6 giây dù Modal đã nóng (ước lượng cũ 0,1 đến 0,4 giây) do gọi qua mạng. Khi chạy thật nên cân nhắc: giảm
ngân sách đoạn, giữ Modal luôn nóng, hoặc bật rerank sau khi có bộ câu hỏi chuẩn.

### 18.7 Kiểm chứng

| Việc | Kết quả |
|---|---|
| Backend: `ruff check`, `ruff format --check`, `mypy` (181 file) | Sạch |
| Backend: `pytest` (PostgreSQL thật, DB test riêng) | **349 pass** (trước đợt này: 209). Mới: 45 công cụ/bộ lọc/định tuyến, 21 API Viga, 15 cấu trúc tài liệu, 14 đo lường, 10 ticket/phản hồi, 10 phiên bản, 10 job tạo task, 5 cấu trúc qua API, 5 tải nháp, 4 metrics qua API, **4 analytics qua API** (HR chỉ thấy phòng mình và số cộng đúng, chi phí cộng theo job, Admin thấy tất cả, HR chưa có phòng ban, quyền và kiểm tra `days`) |
| Frontend: `tsc --noEmit`, `eslint src` | Sạch |
| Frontend: `vitest run` | **224 pass** (trước đợt này: 183), 21 file. Mới: 14 thành phần biểu đồ, 12 trang số liệu (phạm vi, chú giải, bảng, chỉ đúng 7 biểu đồ và không có thẻ chỉ số hay tiêu đề mục, đổi khoảng ngày không gọi lặp), 2 trang Tổng quan HR/Admin |
| Chạy toàn luồng bằng dịch vụ thật | Đạt, số đo ở 18.6 |
| `build_analytics` trên DB dev thật (chỉ đọc), cho một Admin và một HR | Đạt: 14 ngày, danh sách theo ngày đủ độ dài, toàn số 0 vì dữ liệu đã dọn |
| Xem biểu đồ bằng mắt (Chrome không đầu): sáng, tối, trống, điện thoại, có chú giải | Đạt sau khi sửa 2 lỗi hiển thị (làm trên bản 15 biểu đồ, trước khi rút còn 7; xem 18.4b) |

**Lỗi thật do test tìm ra và đã sửa trong đợt này:** (1) bật bản mới trước khi đóng bản cũ trong cùng lượt ghi bị DB từ chối (ràng buộc
chống chồng ngày kiểm từng câu); (2) kết quả "AI từ chối đề xuất" không được ghi lại vì so sánh với chính dict đã bị sửa tại chỗ;
(3) sau "Tạo bản mới từ bản này" ô nhãn của trình soạn thảo trống vì chỉ khởi tạo khi bấm Sửa; (4) hàm `t` của next-intl đổi tham chiếu mỗi lần vẽ nên
các effect phụ thuộc `t` gọi lại API liên tục (đã đổi sang lưu khóa lỗi và dịch lúc hiển thị, có test chặn tái phát); (5) tên khóa dịch
chứa dấu chấm bị hiểu là cấp lồng nhau; (6) `/chat/documents/{id}` để nhân viên đọc được cả bản nháp chưa duyệt; (7) regex kiểm layout DTO bắt nhầm khóa
`"model"` của Langfuse và `response_model=list[...]`; (8) hai test cũ ghi file không chỉ định UTF-8 nên hỏng trên Windows.

### 18.8 Chưa làm và rủi ro còn lại

| Việc | Ghi chú |
|---|---|
| Đo lường giai đoạn B và C | Bộ câu hỏi chuẩn, `tests/eval`, baseline JSON, Prometheus/Grafana. Hiện chỉ có số đo chạy tay như 18.6 |
| Langfuse cho ingest, tạo task và bước định tuyến | Span Langfuse vẫn chỉ ở pipeline hỏi đáp tài liệu; các thao tác khác được đo ở `llm_calls` |
| So sánh khác biệt hai phiên bản; nối lại nguồn của task khi có bản mới | Mục 16.6. Hiện chỉ đếm số task đang dùng mỗi phiên bản, **chưa cảnh báo** "nguồn đã đổi" |
| Sửa tại chỗ bản cũ | Hoãn theo quyết định 5; chỉ sửa bản nháp và sao chép bản cũ thành bản mới |
| Hủy job đang chạy | Chưa có nút Hủy (14.9 câu 3) |
| Công cụ `get_contact`, `get_approved_link`, `get_template` | Chờ trang HR "Đầu mối và đường dẫn" (vẫn "Sắp có") |
| PDF theo cỡ chữ (bậc 4), OCR | PDF chỉ đi qua markitdown như file chữ; file scan vẫn bị từ chối rõ ràng |
| Rerank | Hoãn đến khi có bộ câu hỏi chuẩn |
| Worker chung tiến trình backend | Đủ cho một container; nhiều tiến trình vẫn an toàn nhờ `SKIP LOCKED`, nhưng bộ đếm giới hạn hỏi vẫn trong bộ nhớ từng tiến trình |
| Nội dung tài liệu gửi tới DeepSeek | Tạo task, LLM chia mục và hỏi đáp gửi nội dung tài liệu tới DeepSeek; chưa có nhãn loại trừ tài liệu nhạy cảm (13.7 câu 7) |
| Chi phí embedding | Chưa có đơn giá Modal nên cột chi phí embedding là 0 |
| Chi phí và độ trễ AI của lượt chạy cũ | Lượt tạo task/kích hoạt chạy trước migration `0007` không có `job_id` nên hiện 0 ở biểu đồ từng lượt (thời gian chạy vẫn đúng) |
| Trang số liệu | Chưa so sánh với kỳ trước, chưa xuất CSV, chưa lọc theo một phòng ban cụ thể cho Admin; mỗi lần mở trang tính lại từ bảng gốc (đủ cho quy mô hiện tại, cần bảng tổng hợp nếu dữ liệu lớn) |
| Langfuse trong container | Ảnh Docker backend chưa cài gói `langfuse` nên theo dõi Langfuse tự tắt (có log); số đo vẫn đầy đủ ở `llm_calls` |
| Cloudinary | Tên file theo checksum của file; file đã tải lên **không bị xóa** khi xóa dữ liệu trong DB |
