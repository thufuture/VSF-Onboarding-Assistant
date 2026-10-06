# Báo cáo tiến độ Portal — Nhân viên mới, HR và Quản trị hệ thống (cập nhật 01/10/2026)

> Nhánh `feat/portal-plan`. Phần khu nhân viên `/me` đã commit cục bộ (`99c17ce`); **toàn bộ đợt làm ngày 01/10/2026 dưới đây chưa commit, chưa push, chưa mở PR**.
> **Cập nhật 02/10/2026:** đã sửa Viga (so khớp trích dẫn, định tuyến, Markdown, trả lời một phần), tạo task bằng AI phủ đủ mục có tiên quyết và thứ tự, nút Nguồn tô đúng đoạn, Viga toàn trang `/me/viga`, trang Phản hồi Viga làm lại (bổ sung đáp án và tự kiểm lại), đánh giá 👍/👎. Chi tiết, sơ đồ luồng và số đo: [bao-cao-hoan-thanh-viga-task-ai.md](bao-cao-hoan-thanh-viga-task-ai.md). Kiểm chứng mới nhất: backend `pytest` **428 đạt**, frontend `vitest` **261 đạt**, `ruff`, `mypy`, `alembic check`, `tsc`, `eslint` sạch. Các con số 349 và 228 bên dưới là của ngày 01/10.
> Đối chiếu giao diện: [prototype-ui-flow-v15-shared-roadmap.html](../portal/prototype-ui-flow-v15-shared-roadmap.html).
> Thiết kế, quyết định và số đo chi tiết: [ingest-tai-lieu-va-tao-task-bang-ai.md](ingest-tai-lieu-va-tao-task-bang-ai.md) (mục 18 là hiện trạng mới nhất).

**Kết luận ngắn:** khu HR có 7 trang, khu Quản trị hệ thống (Admin) có 7 trang, khu nhân viên mới `/me` có 7 trang. **Mọi trang và ngăn
"Hỏi Viga" đều chạy với API thật, không còn bản dựng giao diện nào.** Luồng "tải tài liệu → xem lại bản nháp → kích hoạt (chạy nền, có phần
trăm) → AI đề xuất task → HR duyệt, xuất bản → nhân viên làm → Viga trả lời có nguồn hoặc dẫn đường theo lộ trình → chưa trả lời được thì gửi
HR → HR trả lời" chạy được từ đầu đến cuối và đã chạy thử bằng dịch vụ thật. Ba lỗi đã xác minh từ trước (tải phiên bản mới thất bại, tài liệu
ngừng sử dụng vẫn bị Viga tìm thấy, lỗi LLM/embedding trả 500) **đã sửa và có test hồi quy**. Còn một mục HR chưa làm (Đầu mối và đường dẫn).

## 1. Đã làm

### 1.1 Khu HR (7 trang)

| Trang | Đường dẫn | Nội dung chính |
|---|---|---|
| Tổng quan | `/admin` | Lời chào, 4 KPI số thật |
| Nhân viên | `/admin/employees` | Bảng tiến độ, task hiện tại, trạng thái |
| **Ticket sự cố** (mới) | `/admin/tickets` | Hàng đợi chung của phòng ban, lọc theo trạng thái, "Nhận xử lý", trả lời, đổi trạng thái kèm ghi chú kết quả; Admin thấy mọi phòng ban |
| **Phản hồi Viga** (mới) | `/admin/viga-feedback` | Câu nhân viên hỏi mà Viga chưa trả lời được: **ẩn danh**, chỉ của phòng ban mình, gom câu giống nhau và đếm, nút "Bổ sung tài liệu" và "Đã xử lý" |
| Quản lý task | `/admin/tasks` | Roadmap ngang, cây ngày dọc, thêm/sửa/nhân bản/xóa task, thứ tự, tiên quyết (chống vòng), nhóm task có màu, xuất bản |
| **Tài liệu** (làm lại) | `/admin/documents` | Mỗi tài liệu có **nhiều phiên bản**: tải file thành **bản nháp** (nhanh, chưa tốn tiền embedding), xem bản bất kỳ, sao chép thành bản nháp mới, sửa nháp (Markdown có xem trước, khóa lạc quan), xóa nháp, **kích hoạt chạy nền có thanh phần trăm**, **đặt lại bản cũ làm bản áp dụng**, ô "tải và kích hoạt luôn", cảnh báo chất lượng cấu trúc file, dòng "Đang xử lý 45%" |
| **Tạo task bằng AI** (làm lại) | `/admin/ai-tasks` | Chọn nhiều tài liệu → **chạy nền có phần trăm**, kết quả theo từng tài liệu (một tài liệu lỗi không làm hỏng các tài liệu khác, có nút thử lại), nhóm task, "Chấp nhận tất cả", nội dung task ghép ba mục Vì sao / Điều kiện hoàn thành / Các bước |

### 1.2 Khu nhân viên mới (7 trang, vai trò USER, đường dẫn `/me`)

Khung riêng: thanh tiêu đề ngang (logo, 5 mục chức năng, nút "Hỏi Viga", chuông thông báo, avatar mở thẻ tài khoản gồm Hồ sơ, sáng/tối, ngôn ngữ,
Đăng xuất). Mỗi trang có banner ảnh kèm ảnh đại diện của người đang đăng nhập.

| Trang | Đường dẫn | Nội dung chính | API |
|---|---|---|---|
| Tổng quan | `/me` | Lời chào, thẻ tiến độ, 4 KPI, biểu đồ tròn, việc làm được ngay | `GET /portal/me/journey` |
| Nhiệm vụ | `/me/tasks` | Cây ngày dọc; xem theo lộ trình (dùng chung roadmap với HR) hoặc danh sách | `GET /portal/me/journey` |
| Chi tiết việc | `/me/tasks/{id}` | Các bước, điều kiện hoàn thành, tiên quyết, tự xác nhận hoàn thành, nút hỏi Viga. **Mở trang thì ghi "việc vừa mở"** để Viga hiểu "việc này" | `.../complete`, `.../opened` |
| Theo dõi | `/me/progress` | 4 KPI, tiến độ từng ngày, cột theo nhóm, hoạt động gần đây | `GET /portal/me/journey` |
| Tài liệu | `/me/documents` | Thẻ tài liệu theo nhóm, đọc ngay trong trang (chỉ bản đang áp dụng) | `GET /portal/me/documents`, `GET /chat/documents/{id}` |
| **Yêu cầu** (mới) | `/me/tickets` | Ticket đã gửi HR, xem và trả lời tiếp, thấy phản hồi của HR | `GET /portal/tickets/mine` và các endpoint ticket |
| Hồ sơ | `/me/profile` | Thông tin tài khoản, đổi tên hiển thị, đổi mật khẩu | `GET`, `PATCH /portal/me/profile`, `POST /portal/me/password` |

**Hỏi Viga (ngăn bên phải mọi trang) giờ chạy API thật** (`POST /viga/ask`), thay cho bản dựng cũ:
- Giao diện chỉ gửi câu hỏi và `conversation_id`; backend tự biết "việc hiện tại" của người hỏi.
- Câu "hôm nay làm gì / tiếp theo / tiến độ" đi **lối tắt luật, không tốn LLM** (0,03 đến 0,08 giây); các câu khác do **LLM chọn công cụ** trong danh sách đóng rồi code kiểm lại.
- Câu về nội quy, chính sách: tra tài liệu, trả lời kèm **trích dẫn nguyên văn đã kiểm chứng** và nút mở tài liệu tới đúng mục.
- Tra không ra: nói thẳng "chưa có căn cứ", không đoán; kèm nút **"Gửi câu hỏi này cho HR"** (nhân viên xem và sửa trước khi gửi; Viga không tự gửi).
- Hội thoại **lưu trên máy chủ kiểu ChatGPT**: lịch sử, mở lại đúng như lúc hỏi, đổi tên, xóa, mở cuộc mới; giữ 90 ngày; chỉ chủ sở hữu xem được.
- Chuông thông báo thêm "HR đã trả lời" từ ticket.

### 1.3 Khu Quản trị hệ thống (7 trang, chỉ vai trò ADMIN)

Người dùng, Phòng ban, Thành viên, Lộ trình mẫu, Nhật ký như trước; thêm **Chi phí AI** (`/admin/metrics`): lượt gọi, lỗi, độ trễ p50/p95, token và chi phí
ước tính theo từng thao tác, chọn 7, 30 hay 90 ngày. Chỉ có số liệu, không có nội dung câu hỏi hay tài liệu.

**Tổng quan** (cả HR và Admin) nay có phần **số liệu theo thời gian**: **7 biểu đồ quan trọng nhất** (đã rút gọn theo góp ý, không có hàng thẻ chỉ số hay tiêu đề mục): tròn (tiến độ nhân viên, chi phí theo thao tác), đường (hoạt động mỗi
ngày gồm task hoàn thành, câu hỏi Viga và ticket mới; chi phí AI mỗi ngày) và hai biểu đồ cột **theo từng lượt tạo task AI**: độ trễ (thời gian chạy so
với thời gian chờ mô hình) và chi phí. HR chỉ thấy phòng ban của mình, Admin thấy toàn hệ thống; chọn 7, 14 hay 30 ngày; mỗi biểu đồ có chú giải khi trỏ
chuột, nút xem dạng bảng và bản tối. API `GET /portal/analytics` vẫn trả đủ số liệu (ticket, tài liệu, độ trễ theo thao tác, lượt kích hoạt...) nên thêm biểu
đồ sau này không phải sửa backend.

### 1.4 Backend

| Nhóm | Nội dung |
|---|---|
| Tài liệu theo phiên bản | `document_version_service` (nháp, sao chép, sửa có khóa lạc quan, xóa nháp, kích hoạt), `version_lifecycle` (một bản đang áp dụng tại một ngày, đóng bản cũ trong **cùng transaction** với ghi chunk, hẹn ngày hiệu lực tương lai) |
| Việc nền | `job_service` (hàng đợi PostgreSQL `SKIP LOCKED`, tiến độ đơn điệu, nhận lại job treo, tối đa 2 job, việc định kỳ), `job_handlers` (kích hoạt với phần trăm theo từng lô embedding; tạo task AI) |
| Cấu trúc tài liệu | `structure.py`: nhận tiêu đề giả (in đậm, đánh số, chữ HOA), đo chất lượng GOOD/MEDIUM/POOR, chia mục dài thành mục phụ, LLM chia mục là phương án cuối (có kiểm chứng, hạn mức, không bao giờ làm kích hoạt thất bại) |
| Viga | `services/viga/`: ảnh chụp lộ trình (chỉ mã, tên, trạng thái việc đi ra LLM), 5 công cụ lộ trình, bộ lọc thông tin cá nhân, lối tắt luật, LLM định tuyến, hội thoại, câu chưa trả lời được |
| Ticket | `ticket_service`: gửi tới HR phòng ban, **5 ticket/người/ngày**, chặn câu giống nhau trong 10 phút, HR nhận xử lý/trả lời/đổi trạng thái, đóng ticket không đổi task |
| Đo lường | `call_metrics`, `llm_calls` (nay có `job_id` để cộng theo từng lượt việc nền), `/admin/metrics`, **`analytics_service` + `GET /portal/analytics`** (số liệu Tổng quan, HR theo phòng ban, Admin toàn bộ); đơn giá DeepSeek tra 01/10/2026 |
| Cơ sở dữ liệu | Migration `0004` (llm_calls), `0005` (bản nháp, tiến độ job), `0006` (hội thoại, việc vừa mở, nguồn ticket), `0007` (`llm_calls.job_id`) |
| Bảo mật | Mọi công cụ Viga chỉ đọc lộ trình của chính người hỏi; mã việc do LLM đưa ra bị kiểm thuộc lộ trình; hội thoại, ticket, job chỉ chủ sở hữu (hoặc HR đúng phòng ban, Admin) đọc được; nhân viên không đọc được bản nháp tài liệu |

### 1.5 Giao diện dùng chung

Mới trong đợt này: `components/charts/` (biểu đồ đường, cột, tròn và khung có nút xem dạng bảng, vẽ bằng SVG thuần, có bản sáng và tối), `components/job-progress/JobProgress` (thanh phần trăm cho mọi việc nền), hook `useJob` (hỏi tiến độ mỗi giây, tự dừng), `DocumentReader`
(trình đọc có mục lục, dùng chung), `DocumentVersionsModal`, `TicketBoard` và `TicketThread` (dùng chung HR và nhân viên). Các thành phần cũ giữ nguyên
(modal xác nhận, thanh bên, bảng màu, icon phẳng, roadmap dùng chung, logo, avatar Viga, `vi` và `en`).

### 1.6 Kiểm chứng đã chạy

| Việc | Kết quả |
|---|---|
| Backend: `ruff check`, `ruff format --check`, `mypy` (181 file) | Sạch |
| Backend: `pytest` trên PostgreSQL thật (DB test riêng `vsf_test`) | **349 pass** (trước đợt này 209) |
| Frontend: `tsc --noEmit`, `eslint src` | Sạch |
| Frontend: `vitest run` | **228 pass**, 22 file (trước đợt này 183) |
| Chạy toàn luồng bằng **dịch vụ thật** (Modal embedding, DeepSeek) trên DB thử riêng, file lưu cục bộ | Đạt: tải 4 file Word, kích hoạt có phần trăm, đóng bản cũ, đặt lại bản cũ không tốn embedding, tạo 14 đề xuất task, chấp nhận 6, xuất bản, nhân viên hỏi 8 câu (lối tắt, LLM định tuyến, tài liệu có nguồn, không có căn cứ, ngoài phạm vi), gửi ticket, HR trả lời, số đo Admin |
| Lỗi thật do test tìm ra và đã sửa | 8 lỗi, liệt kê ở mục 18.7 của tài liệu thiết kế |
| Trang Tổng quan | Xem bằng mắt bản 15 biểu đồ (sáng, tối, trống, điện thoại, có chú giải) và sửa 2 lỗi hiển thị, sau đó rút còn 7 biểu đồ (bản rút gọn kiểm bằng test); `build_analytics` chạy được trên DB dev thật (chỉ đọc); migration `0007` đã áp dụng cho DB dev, các bảng tài liệu, task, job, ticket, hội thoại, llm_calls vẫn rỗng |

**Số đo thật (tóm tắt, chi tiết ở mục 18.6):** tải file thành nháp 0,4 đến 0,7 giây; kích hoạt 3 đến 5 giây khi dịch vụ embedding đã nóng (lần đầu 24 giây do Modal khởi
động nguội ~18 giây); đặt lại bản cũ 0,4 giây; tạo task bằng AI 48 giây cho tài liệu 18 mục (0,019 USD); hỏi Viga bằng lối tắt 0,03 đến 0,08 giây, bằng
tài liệu 6 đến 8 giây, khoảng **0,0033 USD (~82 đồng) một câu**, gần 3 lần ước lượng cũ vì ngữ cảnh tài liệu ~6.800 token.

## 2. API đã viết

### `/api/v1/portal/*` (HR) — phần mới trong đợt này

| Method | Đường dẫn | Việc |
|---|---|---|
| POST | `/documents` | Tạo bản nháp từ file (`activate=true` thì kích hoạt luôn, trả 202 + `job_id`) |
| GET | `/documents/{id}/versions`, `/documents/{id}/versions/{vid}` | Danh sách phiên bản kèm trạng thái, hiệu lực, chất lượng cấu trúc; nội dung một bản |
| POST, PATCH, DELETE | `/documents/{id}/versions/{vid}/copy`, `.../versions/{vid}`, `.../versions/{vid}` | Sao chép thành nháp; sửa nháp (khóa lạc quan); xóa nháp |
| POST | `/documents/{id}/versions/{vid}/activate` | Kích hoạt hoặc đặt lại bản cũ làm bản áp dụng (chạy nền) |
| GET | `/jobs/{id}`, `/jobs?active=true&kind=` | Tiến độ việc nền |
| POST | `/ai/task-proposal-jobs` | Tạo task bằng AI cho nhiều tài liệu (chạy nền) |
| POST, GET | `/tickets`, `/tickets/mine`, `/tickets`, `/tickets/{id}` | Gửi, xem ticket |
| POST, PATCH | `/tickets/{id}/messages`, `/tickets/{id}/claim`, `/tickets/{id}/status` | Trả lời, nhận xử lý, đổi trạng thái |
| GET, POST | `/content-gaps`, `/content-gaps/{id}/resolve` | Câu Viga chưa trả lời được (ẩn danh) |
| POST | `/me/tasks/{id}/opened` | Ghi "việc vừa mở" |

Các endpoint cũ (dashboard, employees, documents, stages, journey-templates, task, me/journey, me/profile...) giữ nguyên.
`POST /documents` đổi hợp đồng: trả 201 hoặc 202 thay vì kết quả nạp đồng bộ.

### `/api/v1/viga/*` (mọi người đã đăng nhập)

`POST /ask`, `GET /conversations`, `GET|PATCH|DELETE /conversations/{id}`.

### `/api/v1/admin/*` (chỉ ADMIN)

Như trước, thêm `GET /metrics?days=` (số liệu gọi LLM và embedding).

### `GET /api/v1/portal/analytics?days=1..90` (HR và Admin)

Số liệu Tổng quan: nhân viên và task, Viga, ticket, tài liệu, và AI (chi phí và lượt gọi theo ngày, theo thao tác, **20 lượt tạo task và 20 lượt kích hoạt gần nhất với thời
gian chạy, độ trễ và chi phí từng lượt**); trang hiện mới vẽ 6 biểu đồ trong số đó. HR: phòng ban của mình; Admin: tất cả. Chỉ số liệu tổng hợp, không có nội dung (INV8). Chi tiết: mục 18.4b của tài liệu thiết kế.

## 3. Chưa làm

| Việc | Ghi chú |
|---|---|
| Đầu mối và đường dẫn (HR) | **Hoãn theo yêu cầu (02/10/2026): đã thử làm rồi gỡ hết, không còn mục này trên giao diện, trong tab sửa task hay ở Viga.** Bảng `contact_channels`, `approved_links` vẫn nằm trong cơ sở dữ liệu (migration 0002); chưa có router và giao diện. Kéo theo công cụ Viga `get_contact`, `get_approved_link`, `get_template` chưa làm |
| So sánh khác biệt hai phiên bản; cảnh báo và nối lại nguồn của task khi có bản mới | Hiện chỉ đếm số task đang dùng mỗi phiên bản |
| Sửa tại chỗ bản cũ | Hoãn theo quyết định 5: chỉ sửa bản nháp và sao chép bản cũ thành bản mới |
| Hủy job đang chạy | Chưa có nút Hủy |
| Đo lường giai đoạn B và C | Bộ câu hỏi chuẩn, `tests/eval`, baseline, Prometheus; Langfuse chưa phủ ingest, tạo task và bước định tuyến |
| PDF theo cỡ chữ (bậc 4), OCR, rerank | PDF đi qua markitdown như file chữ; file scan bị từ chối rõ ràng; rerank hoãn |
| Nút "Nhắn" ở trang Nhân viên, nút "Xem task" lọc theo người, nhập người dùng từ CSV, mô tả ngắn cho tài liệu, ảnh đại diện tự tải lên | Như báo cáo trước |
| Giao diện | Icon nét mảnh còn ở ô KPI của Tài liệu, Tổng quan HR, Nhân viên và các trang Admin cũ |
| Dữ liệu thật | 10 task ngày 1 từ tài liệu thật chưa nạp; **DB dev hiện đã được dọn sạch tài liệu và task** để thao tác thủ công |

## 4. Lỗi đã xác minh

Ba lỗi của báo cáo trước **đã sửa và có test hồi quy**:

| # | Lỗi | Cách sửa |
|---|---|---|
| 1 | Tải phiên bản mới của cùng tài liệu thất bại (bản cũ không được đóng) | Đóng bản cũ cùng transaction với ghi chunk (cả đường CLI); test đổi bản, hẹn ngày, đặt lại bản cũ |
| 2 | Tài liệu "ngừng sử dụng" vẫn bị Viga tìm thấy | Tìm kiếm lọc thêm trạng thái tài liệu; test |
| 3 | Lỗi LLM hoặc embedding trong `/chat/ask` thành 500 | `503 ASSISTANT_UNAVAILABLE` (chat HR) và đường thoát `ERROR` kèm gợi ý gửi HR (Viga); test |

Chưa có lỗi mở nào đã xác minh. Một lần chạy toàn bộ `vitest` trong đợt này có 1 test rớt một lần khi máy đang tải nặng rồi qua ở 4 lần chạy lại liên tiếp; chưa xác định test nào, theo dõi thêm.

## 5. Rủi ro và lưu ý khác

| Mục | Nội dung |
|---|---|
| Nội dung tài liệu đi ra dịch vụ ngoài | Tạo task, LLM chia mục và hỏi đáp gửi nội dung tài liệu tới DeepSeek; chưa có nhãn loại trừ tài liệu nhạy cảm. Embedding gửi nội dung tới Modal |
| Modal khởi động nguội | Lần gọi đầu có thể mất ~18 giây; thanh tiến độ báo "Kết nối dịch vụ embedding". Câu hỏi đầu tiên của nhân viên sau thời gian dài cũng có thể chậm |
| Chi phí | Chi phí embedding chưa tính (chưa có giá Modal). Giá DeepSeek tra một lần ngày 01/10/2026, có thể đổi; ngữ cảnh tài liệu ~6.800 token mỗi câu là phần tốn nhất |
| Worker chung tiến trình backend | Đủ cho một container; ingest nặng chạy luồng riêng nên không chặn request khác; nhiều tiến trình vẫn an toàn (`SKIP LOCKED`) nhưng bộ đếm giới hạn hỏi vẫn trong bộ nhớ từng tiến trình |
| Hàm `t` của next-intl | Đổi tham chiếu mỗi lần vẽ: **không đưa `t` vào phụ thuộc của effect** (đã gặp và sửa lỗi gọi API lặp ở hai chỗ; có test chặn tái phát) |
| Cloudinary | Xóa dữ liệu trong DB **không** xóa file đã tải lên Cloudinary (tên file theo checksum, ghi đè khi tải lại) |
| Khóa bí mật | `.env` chứa khóa LLM, embedding, Cloudinary, Langfuse thật; đã được `.gitignore`. Không dán vào tài liệu hay tin nhắn |
| Docker | Đã dựng lại image backend và áp dụng migration `0004` đến `0006` trên DB dev; không đổi `docker-compose.yml` hay `Dockerfile` |
| Ảnh bìa khu nhân viên | Dùng lại 3 ảnh tòa nhà của trang chủ (Wikimedia Commons, CC BY 3.0 và CC BY-SA 4.0), chỉ minh họa, đã ghi công; không ngụ ý VSF làm việc tại tòa nhà đó |

## 6. Lịch sử commit trên nhánh (từ mới nhất)

| Commit | Nội dung |
|---|---|
| `99c17ce` | Khu nhân viên mới `/me` với API thật (Viga lúc đó là bản dựng giao diện) |
| `9b60597` | Giao diện HR/Admin kiểu doanh nghiệp, hiệu ứng trỏ chuột, cây ngày dọc, mốc Bắt đầu và Kết thúc |
| `c62c6f9` | Thẻ ngày ở thanh bên gọn một nửa, giãn cờ Bắt đầu và Kết thúc |
| `6935900` | Nút thu/mở thanh bên chuyển xuống dòng vai trò |
| `f948432` | Nút thu/mở thanh bên, khoảng cách 5px, icon trong thẻ task, cây ngày dạng thẻ |

**Chưa commit** (đợt 01/10/2026): thiết kế lại chuông thông báo (bỏ trang Thông báo riêng), toàn bộ phần tài liệu theo phiên bản, việc nền, cấu trúc tài liệu, Viga thật, ticket,
phản hồi Viga, trang Chi phí AI, migration `0004` đến `0006`, 10 file Word thử và README trong `docs/chatbot-vsf/data/documents/day1/` và cập nhật hai tài liệu này.

## 7. Ghi chú về phòng ban và Viga

Đã thống nhất: lộ trình onboarding gần như giống nhau cho mọi người nên dùng một lộ trình chung; phòng ban nào cần khác thì Admin sao bản mẫu rồi HR của phòng
ban đó sửa bản sao. Tài liệu để chung một kho, ai cần thì tải lên, Viga tìm trên toàn kho. **Không** gắn `team_id` vào `documents` và **không** lọc tài liệu
theo phòng ban khi Viga trả lời. Ticket và câu hỏi chưa trả lời được thì **có** phạm vi phòng ban (tới HR của phòng ban người hỏi).

## 8. Cập nhật 02/10/2026 (theo góp ý sau khi xem giao diện)

- **Khoảng cách tới chân trang:** mọi trang HR, Admin (và khung nhân viên mới) cho thẻ cuối chạm sát chân trang, chỉ cách 2px; đã đo bằng trình duyệt cho 15 trang HR/Admin (2px; hai trang Tổng quan dài nên cuộn, đáy cũng chỉ đệm 2px).
- **Chân trang dùng chung** (`components/portal-footer`): logo VSF giống logo đầu thanh bên, dùng cho HR, Admin và nhân viên mới; bỏ dòng ghi công ảnh ở chân trang nhân viên và chữ "Bản demo thực tập" ở trang đăng nhập.
- **Icon nhiều màu (FlatIcon):** thanh điều hướng HR, Admin, nhân viên mỗi mục một màu; thẻ chỉ số Tổng quan HR; trang Tài liệu; trang Tạo task bằng AI (thanh bước, đầu thẻ, ô giai đoạn).
- **Tổng quan HR:** 6 biểu đồ, khoảng cách thẻ 10px; số trung bình các lượt tạo task nằm trong phụ đề của thẻ (bỏ đầu mục riêng).
- **Ticket sự cố:** ô tìm kiếm (tên, email, tiêu đề, không phân biệt dấu) và ô chọn lọc trạng thái thay cho các nút; icon theo trạng thái; thẻ lấp đầy chiều cao; `requester_email` có trong danh sách ticket.
- **Tạo task bằng AI:** hết "Ngày 1/Ngày 2" mẫu (đã xóa trong DB dev); chưa có ngày nào thì tự mở biểu mẫu tạo ngày đầu tiên; khung "chưa chọn tài liệu" không còn nằm trên bộ chọn.
- **Tài liệu:** bảng vừa khít chiều ngang, chữ dài cắt bằng dấu … và xem đủ khi trỏ chuột; lọc theo ngày cập nhật (từ ngày, đến ngày); ô chọn danh mục thiết kế riêng; danh mục chỉ còn **Onboarding** và **Tài liệu khác** (migration dữ liệu `0008`: chuyển tài liệu sang hai nhóm, ẩn các nhóm cũ); hộp xem phiên bản rộng và cao hơn, hai nút "Tải file thành phiên bản mới" và "Tạo bản mới từ bản này" đưa lên đầu hộp.
- **Gỡ:** mục "Đầu mối và đường dẫn" khỏi thanh điều hướng, tab "Liên hệ và tài nguyên" khỏi hộp sửa task, mục "Đầu mối" khỏi điều hướng nhân viên.
- **Dữ liệu DB dev:** đã xóa toàn bộ tài liệu (kèm phiên bản, mục, chunk), ngày và lộ trình, việc nền; người dùng, phòng ban giữ nguyên. Có bản sao lưu trong thư mục tạm của phiên làm việc.
- **Kiểm chứng:** backend `pytest` 349 pass, `ruff`, `mypy` (181 file), `alembic check` sạch; frontend `vitest` 228 pass, `tsc`, `eslint` sạch.
