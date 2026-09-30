# Báo cáo tiến độ Portal — Nhân viên mới, HR và Quản trị hệ thống (cập nhật 30/09/2026)

> Nhánh `feat/portal-plan`. Đã commit cục bộ, **chưa push, chưa mở PR**.
> Đối chiếu giao diện: [prototype-ui-flow-v15-shared-roadmap.html](../portal/prototype-ui-flow-v15-shared-roadmap.html).
> Chi tiết ingest tài liệu và tạo task bằng AI: [ingest-tai-lieu-va-tao-task-bang-ai.md](ingest-tai-lieu-va-tao-task-bang-ai.md).

**Kết luận ngắn:** khu HR có 5 trang, khu Quản trị hệ thống (Admin) có 6 trang, khu nhân viên mới `/me` có 7 trang.
**Mọi trang đều chạy với API thật; chỉ ngăn "Hỏi Viga" là bản dựng giao diện** (suy ra câu trả lời từ lộ trình thật,
chưa gọi `POST /chat/ask` — mục 3).
Luồng "tải tài liệu, AI đề xuất task, HR duyệt, xuất bản, nhân viên làm, Viga trả lời có nguồn" chạy được từ đầu đến cuối.
Còn 3 mục HR chưa làm (Ticket sự cố, Phản hồi Viga, Đầu mối và đường dẫn) và **2 lỗi thật đã xác minh nhưng chưa sửa**
(mục 4).

## 1. Đã làm

### 1.1 Khu HR (5 trang)

| Trang | Đường dẫn | Nội dung chính | API |
|---|---|---|---|
| Tổng quan | `/admin` | Lời chào, 4 KPI số thật | `GET /portal/dashboard` |
| Nhân viên | `/admin/employees` | Bảng tiến độ, task hiện tại, trạng thái, phân trang 5 dòng | `GET /portal/employees` |
| Quản lý task | `/admin/tasks` | Roadmap ngang có nút Bắt đầu và Kết thúc, thanh bên là lộ trình dọc theo ngày, thống kê (tổng, nháp, đã xuất bản, cần bổ sung) gộp vào tiêu đề ngày kèm icon, thêm/sửa/nhân bản/xóa task, thứ tự, tiên quyết (chống vòng), nhóm task có màu, xuất bản. Đã bỏ hàng thẻ thống kê và ô tìm kiếm task | 6 endpoint (mục 2) |
| Tài liệu | `/admin/documents` | Bảng 7 cột, 3 ô lọc nhiều màu, thêm, sửa, xem dạng trang giấy có mục lục đứng yên, xem file gốc, ngừng sử dụng và kích hoạt lại | 5 endpoint |
| Tạo task bằng AI | `/admin/ai-tasks` | Chọn nhiều tài liệu, chọn giai đoạn đích, xem đề xuất kèm nguồn, chấp nhận từng task | 2 endpoint |

### 1.2 Khu nhân viên mới (7 trang, vai trò USER, đường dẫn `/me`)

Thay cho trang roadmap cũ ở `/chat` (đã xóa). Khung riêng: **thanh tiêu đề ngang trải hết bề ngang** — logo bên trái,
bốn mục chức năng ở giữa, bên phải là nút "Hỏi Viga", chuông thông báo (bấm ra thẻ 4 thông báo mới nhất, có nút đánh dấu
đã đọc và lối sang trang Thông báo) và avatar mở thẻ tài khoản gồm Hồ sơ, sáng/tối, ngôn ngữ và Đăng xuất.
Thứ tự mục đúng `NAV.employee` của prototype v15. Mỗi trang có banner ảnh kèm ảnh đại diện của người đang đăng nhập.

| Trang | Đường dẫn | Nội dung chính | API |
|---|---|---|---|
| Tổng quan | `/me` | Lời chào đủ họ tên kèm ảnh đại diện, thẻ tiến độ trên banner, 4 KPI, **biểu đồ tròn** theo trạng thái việc, danh sách việc làm được ngay, việc vừa xong, lối tắt | `GET /portal/me/journey` |
| Nhiệm vụ | `/me/tasks` | Cây ngày dọc bên trái; bên phải xem theo **lộ trình** (dùng chung roadmap với HR) hoặc **danh sách** | `GET /portal/me/journey` |
| Chi tiết việc | `/me/tasks/{id}` | Cột trái là các việc trong ngày xếp dọc như lộ trình nhỏ (màu, icon và số thứ tự theo nhóm việc); giữa là "Vì sao phải làm", "Các bước thực hiện", "Điều kiện hoàn thành" tách từ nội dung HR soạn; phải là chặng trạng thái, nút tự xác nhận hoàn thành, nút hỏi Viga, việc tiên quyết và việc sẽ mở sau | `GET /portal/me/journey`, `POST /portal/me/tasks/{id}/complete` |
| Theo dõi | `/me/progress` | 4 KPI, tiến độ từng ngày, cột theo nhóm việc, hoạt động gần đây | `GET /portal/me/journey` |
| Tài liệu | `/me/documents` | Thẻ tài liệu theo nhóm màu, tìm theo tên, lọc theo nhóm, đọc ngay trong trang | `GET /portal/me/documents`, `GET /chat/documents/{version_id}` |
| Thông báo | `/me/notifications` | Lọc tất cả/chưa đọc, đánh dấu đã đọc, bấm vào là mở đúng việc | Suy ra từ lộ trình (chưa có API riêng) |
| Hỏi Viga | ngăn bên phải mọi trang | Cột 372px như view `chat` của v15: avatar Viga, nhãn loại câu trả lời, việc đang chặn, nút mở đúng việc, hộp "Viga làm được gì, không làm gì" | **Chưa nối API** — suy ra từ lộ trình thật |
| Hồ sơ | `/me/profile` | Thông tin tài khoản, tiến độ, đổi tên hiển thị, đổi mật khẩu | `GET` và `PATCH /portal/me/profile`, `POST /portal/me/password` |

Chuyển hướng theo vai trò (đã thử thật bằng HTTP): chưa đăng nhập vào `/me` → `/login?next=`; HR hoặc Admin vào `/me` →
`/admin`; nhân viên vào `/admin` hoặc `/chat` → `/me`; nhân viên gọi API của HR hoặc Admin → 403.

### 1.3 Khu Quản trị hệ thống (6 trang, chỉ vai trò ADMIN)

| Trang | Đường dẫn | Nội dung chính |
|---|---|---|
| Tổng quan | `/admin` (ADMIN) | 4 KPI, biểu đồ nhân viên theo phòng ban, hoạt động gần đây |
| Người dùng | `/admin/users` | Tìm, lọc vai trò, thêm (mật khẩu tạm hiện một lần), sửa, đặt lại mật khẩu, khóa/mở khóa |
| Phòng ban | `/admin/teams` | Tạo, sửa, chi tiết kèm thành viên, lưu trữ/khôi phục, sao lộ trình mẫu chung |
| Thành viên | `/admin/members` | Gán và gỡ người khỏi phòng ban, lọc theo trạng thái truy cập |
| Lộ trình mẫu | `/admin/template` | Bản mẫu chung và lộ trình của từng phòng ban |
| Nhật ký | `/admin/audit` | Đọc từ `audit_logs` thật |

### 1.4 Backend

| Nhóm | Nội dung |
|---|---|
| Portal (HR) | dashboard, employees, documents (danh sách, sửa, ẩn/kích hoạt), document-categories, stages, journey-templates/mine, thêm/sửa/xóa task, xuất bản, upload tài liệu, xem file gốc, đề xuất và chấp nhận task AI |
| Admin | 14 endpoint: dashboard, users (tạo, sửa, đặt lại mật khẩu, khóa), teams (tạo, sửa, lưu trữ, sao lộ trình), memberships, template-overview, audit-logs |
| Cơ sở dữ liệu | Migration `0002` (portal core) và `0003` (`task_templates.task_group`); enum `TaskGroup` |
| Quy tắc nghiệp vụ | Không tự khóa hay tự hạ vai trò; email không trùng; chỉ tài khoản HR làm HR phụ trách; mã phòng ban duy nhất; phòng ban đã có lộ trình thì không sao thêm lần nữa; lộ trình đã xuất bản bị khóa sửa; tiên quyết chỉ AND và chống vòng |
| Nhân viên | Lộ trình tạo khi mở `GET /portal/me/journey`, task có tiên quyết bị khóa, tự xác nhận hoàn thành thì mở khóa task phụ thuộc. Lộ trình trả thêm ngày (`stage_id`, `stage_sort_order`), nhóm task và **danh sách tiên quyết kèm trạng thái** để giao diện nói rõ "cần xong việc nào trước" |
| Nhân viên: hồ sơ | `GET` và `PATCH /portal/me/profile` (tiến độ, phòng ban, ngày bắt đầu), `POST /portal/me/password` — đổi mật khẩu thì thu hồi mọi phiên cũ, riêng thiết bị đang dùng được cấp cookie mới nên không bị đăng xuất |
| Nhân viên: tài liệu | `GET /portal/me/documents` chỉ trả tài liệu đang hiệu lực (`ACTIVE`) và có phiên bản `ACTIVE`; nội dung đọc qua `/chat/documents/{version_id}` sẵn có |

### 1.5 Giao diện dùng chung

| Việc | Chi tiết |
|---|---|
| Modal xác nhận | Mọi hành động có tác dụng phụ (xóa, nhân bản, ngừng sử dụng, kích hoạt lại, khóa, gỡ, xuất bản) đều qua modal xác nhận |
| Thanh bên | Theo vai trò (HR, Admin, nhân viên); nút thu/mở nằm sau dòng vai trò, thu còn 68px chỉ icon, nhớ lựa chọn |
| Bảng màu | Nền xám lạnh, thẻ `#f7f9fc` trên nền `#e9edf3`, chữ dịu, ba mức đậm nhạt (400, 500, 600), không chữ in hoa, bo góc 5px, khoảng cách thẻ 5px |
| Icon | Bộ icon phẳng hai tông tự vẽ (`components/flat-icons/FlatIcon.tsx`) cho menu, thanh trên, nút roadmap; thêm hai tông `red` và `violet` cho mốc Bắt đầu và Kết thúc |
| Roadmap dùng chung | `components/roadmap/JourneyRoad.tsx` — HR và nhân viên dùng chung một bộ phận: đường cong mềm, nút tròn có icon nhóm, thẻ có dải màu, mốc Bắt đầu (đỏ) và Kết thúc (tím) khác hẳn 4 màu nhóm việc. Bản của nhân viên tô xanh lá đoạn đường đã đi, nút đã xong có dấu tích, việc bị khóa xám kèm ổ khóa |
| Hiệu ứng | Nút, thẻ, dòng bảng đều có hiệu ứng khi trỏ chuột (0,15 giây). Khu nhân viên: vệt chạy ở đỉnh trang khi đổi trang, nội dung trôi lên, ảnh bìa ba tấm đổi chậm, sóng nước chạy ở đáy ảnh, đường roadmap "chạy" từ trái sang. Mọi hiệu ứng tắt khi máy đặt `prefers-reduced-motion` |
| Logo | Một thành phần dùng chung `components/brand/VsfMark.tsx`: ô vuông bo góc chia chéo xanh dương và đỏ, chữ "V" trắng. Dùng ở trang chủ, trang đăng nhập, khung HR/Admin và khung nhân viên nên mọi nơi giống hệt nhau |
| Avatar Viga | `components/avatar/VigaAvatar.tsx` — nhân viên hỗ trợ đeo tai nghe, cổng thẳng từ `vigaAvatar()` của v15 |
| Ngôn ngữ | Toàn bộ chữ qua `next-intl`, có `vi` và `en` |

### 1.6 Kiểm chứng đã chạy

| Việc | Kết quả |
|---|---|
| `ruff check`, `ruff format --check`, `mypy src` | Sạch |
| Test tích hợp portal và admin (6 file, PostgreSQL thật) | 30 pass (thêm 3 test cho `/me`: tiên quyết, hồ sơ và đổi mật khẩu, tài liệu) |
| `tsc --noEmit`, `eslint src` | Sạch |
| `vitest run` | 168 pass, 16 file (thêm 19 test cho khu nhân viên: mô hình lộ trình, máy trả lời Viga, khung và trang Nhiệm vụ) |
| `next build` | Thành công, sinh đúng 6 route `/[locale]/me/*` |
| Gọi thật API bằng cookie ADMIN, HR và nhân viên; chụp màn hình có đăng nhập; bấm thử modal, ngăn Viga, đổi cách xem | Đúng dữ liệu thật của `newhire1` (4 việc Ngày 1, 1 việc bị khóa đúng tiên quyết) |
| Chụp màn hình khu nhân viên | 6 trang, giao diện tối, khổ điện thoại, ngăn Viga, chi tiết việc — đều đúng bố cục |

## 2. API đã viết

### `/api/v1/portal/*` (HR)

| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/dashboard` | KPI Tổng quan theo phòng ban của người gọi |
| GET | `/employees` | Nhân viên kèm tiến độ và task hiện tại |
| GET, POST | `/documents` | Danh sách tài liệu (kèm task đang dùng, người phụ trách) và tải lên |
| PATCH | `/documents/{id}`, `/documents/{id}/status` | Sửa tên và nhóm; ngừng sử dụng hoặc kích hoạt lại |
| GET | `/documents/{version_id}/original` | Xem hoặc tải file gốc |
| GET | `/document-categories`, `/stages`, `/journey-templates/mine` | Danh mục, giai đoạn nháp, cây lộ trình |
| POST | `/journey-templates`, `/journey-templates/{id}/stages`, `/journey-templates/{id}/publish` | Tạo lộ trình, giai đoạn, xuất bản |
| POST, PATCH, DELETE | `/stages/{id}/tasks`, `/task-templates/{id}` | Thêm, sửa, xóa task (thứ tự, tiên quyết, nhóm) |
| POST | `/ai/task-proposals`, `/stages/{id}/tasks/from-proposal` | AI đề xuất; chấp nhận đề xuất |
| GET, POST | `/me/journey`, `/me/tasks/{id}/complete` | Lộ trình (kèm ngày, nhóm, tiên quyết) và hoàn thành task của nhân viên |
| GET, PATCH | `/me/profile` | Hồ sơ và tiến độ của chính mình; đổi tên hiển thị |
| POST | `/me/password` | Đổi mật khẩu của chính mình (thu hồi phiên cũ, giữ phiên thiết bị đang dùng) |
| GET | `/me/documents` | Thư viện tài liệu cho nhân viên (chỉ tài liệu đang hiệu lực) |

### `/api/v1/admin/*` (chỉ ADMIN)

`GET /dashboard`, `GET|POST /users`, `PATCH /users/{id}`, `POST /users/{id}/reset-password`, `PATCH /users/{id}/status`,
`GET|POST /teams`, `PATCH /teams/{id}`, `PATCH /teams/{id}/status`, `POST /teams/{id}/copy-template`,
`GET|POST /memberships`, `DELETE /memberships/{team}/{user}`, `GET /template-overview`, `GET /audit-logs`.

## 3. Chưa làm

| Việc | Ghi chú |
|---|---|
| Ticket sự cố (HR) | Bảng `tickets`, `ticket_messages` đã có; chưa có router và giao diện |
| Phản hồi Viga (HR) | Bảng `content_gaps` đã có; chưa có router và giao diện |
| Đầu mối và đường dẫn (HR) | Bảng `contact_channels`, `approved_links` đã có; chưa có router và giao diện; tab "Liên hệ" trong form task phụ thuộc mục này |
| Nút "Nhắn" ở trang Nhân viên | Đang tắt, chưa có API nhắn tin |
| Nút "Xem task" ở trang Nhân viên | Mới dẫn sang Quản lý task chung, chưa lọc theo từng người |
| Tạo task bằng AI: hoàn thiện | Chưa lưu `done_criteria`, `estimated_minutes`, `warnings`; chưa tự gán nhóm task; chưa đề xuất tiên quyết; chưa có "Chấp nhận tất cả" và xem trước roadmap |
| Nhập người dùng từ CSV (Admin) | v15 có nút này, chưa làm |
| Mô tả ngắn cho tài liệu | Bảng `documents` chưa có cột mô tả; bảng hiện hiển thị `source_key` |
| **Hỏi Viga (nhân viên)** | Đây là **chỗ duy nhất trong portal chưa dùng API thật**. Câu trả lời suy ra từ chính lộ trình thật của người đang đăng nhập (bước kế tiếp, việc bị khóa vì việc nào, kế hoạch ngày) chứ không gọi `POST /chat/ask`; không khớp thì nói thẳng "chưa có trong lộ trình". Trên ngăn trò chuyện có ghi rõ điều này. Khi nối API thật chỉ cần thay hàm `askViga` trong `vigaMock.ts`, giữ nguyên kiểu dữ liệu |
| **Thông báo (nhân viên)** | Chưa có bảng và API thông báo. Danh sách hiện được suy ra từ lộ trình thật (việc vừa mở khóa, việc đã xong, nhắc việc của ngày, lời chào); trạng thái "đã đọc" lưu ở trình duyệt của từng người (`localStorage`), không gửi lên máy chủ và không đồng bộ giữa máy |
| Trang cá nhân của nhân viên | Chưa có ảnh đại diện tự tải lên (đang dùng ảnh vẽ sẵn theo tên), chưa có đổi email, chưa có lịch sử đăng nhập |
| Giao diện | Icon nét mảnh còn ở ô KPI của Tài liệu, Tổng quan HR, Nhân viên và các trang Admin; các trang này chưa được thiết kế lại theo phong cách mới như Quản lý task và khu nhân viên |
| Ingest | OCR file scan, xử lý ảnh nhúng, hàng đợi và tiến độ, rerank |
| Dữ liệu thật | 10 task ngày 1 từ tài liệu thật (kế hoạch P4B) chưa nạp; dữ liệu trong DB dev là dữ liệu mẫu |

## 4. Lỗi đã xác minh, chưa sửa

| # | Lỗi | Bằng chứng | Ảnh hưởng |
|---|---|---|---|
| 1 | **Tải phiên bản mới của cùng tài liệu thất bại.** Phiên bản cũ không được đóng (`effective_to` trống, không chuyển `ARCHIVED`), DB cấm hai bản `ACTIVE` chồng ngày | Chèn thử bản mới trong transaction rồi rollback: `ex_document_versions_active_no_overlap` | Nút "Tải phiên bản mới" ở trang Tài liệu sẽ lỗi |
| 2 | **Tài liệu đã "ngừng sử dụng" vẫn được Viga tìm thấy.** Nút chỉ đổi `documents.status`, truy vấn tìm kiếm chỉ lọc theo trạng thái phiên bản | Đọc `hybrid_search.py` và `set_document_status` | Thông báo trong modal đúng với danh sách chọn của AI nhưng không đúng với Viga |

Hai lỗi này ảnh hưởng luồng tài liệu; nên sửa trước khi demo cho mentor.

## 5. Rủi ro và lưu ý khác

| Mục | Nội dung |
|---|---|
| Docker khi dựng lại | Container `migrate` có lần không tự thoát nên `docker compose up` bị treo; migration đã áp dụng xong, phải khởi động backend tay. Cần kiểm tra trước khi chạy lại trên máy khác |
| Test không phải lỗi code | 2 test `test_parser` hỏng do mã hóa `cp1252` của Windows khi in tiếng Việt (đã hỏng từ trước); 6 test tích hợp cũ (`test_core_schema`, `test_ingest_service`) va chạm với dữ liệu danh mục đã có sẵn trong DB dev |
| Dữ liệu mẫu | DB dev có lộ trình "Onboarding Day 1" đã xuất bản và một bản nháp do tôi tạo khi test; đã sửa lại tiếng Việt có dấu và gán nhóm task. Nên xóa hoặc thay bằng dữ liệu thật trước khi demo |
| Khóa bí mật | `backend/.env` chứa khóa LLM, embedding, Cloudinary, Langfuse thật; đã được `.gitignore`, không có trong commit. Không dán vào tài liệu hay tin nhắn |
| Prompt AI | Gửi toàn bộ section của tài liệu, chưa có ngân sách token; tài liệu rất dài có thể vượt ngữ cảnh |
| Ảnh bìa khu nhân viên | Dùng lại 3 ảnh tòa nhà của trang chủ (Wikimedia Commons, CC BY 3.0 và CC BY-SA 4.0). Chỉ là ảnh minh họa, đã ghi công ở chân trang và trong `public/images/landing/CREDITS.md`; **không** ngụ ý VSF làm việc tại tòa nhà đó |
| Tài liệu cho nhân viên | Trang Tài liệu của nhân viên không cho tải file gốc (endpoint file gốc chỉ mở cho HR và Admin), chỉ đọc bản Markdown đã nạp |

## 6. Lịch sử commit trên nhánh (từ mới nhất)

| Commit | Nội dung |
|---|---|
| `9b60597` | Giao diện HR/Admin kiểu doanh nghiệp, hiệu ứng trỏ chuột, cây ngày dọc, mốc Bắt đầu và Kết thúc, tài liệu báo cáo |
| `c62c6f9` | Thẻ ngày ở thanh bên gọn một nửa, giãn cờ Bắt đầu và Kết thúc |
| `6935900` | Nút thu/mở thanh bên chuyển xuống dòng vai trò |
| `f948432` | Nút thu/mở thanh bên, khoảng cách 5px, icon trong thẻ task, cây ngày dạng thẻ |
| `3d39f03` | Thu gọn khoảng cách, làm dịu nền thẻ, logo hai màu, màu nhóm task đậm hơn |
| `7f12feb` | Chuẩn hóa giao diện kiểu doanh nghiệp, roadmap có nút Bắt đầu và Kết thúc |
| `32c1437` | Làm lại giao diện HR (roadmap, tài liệu, thanh bên) |
| `0f81bd0` | Toàn bộ portal HR và Admin với API thật |

Toàn bộ khu nhân viên mới (`/me`), API `/portal/me/*` và các test kèm theo **chưa commit** tại thời điểm viết báo cáo này.

## 7. Ghi chú về phòng ban và Viga

Đã thống nhất: lộ trình onboarding gần như giống nhau cho mọi người nên dùng một lộ trình chung; phòng ban nào cần khác
thì Admin sao bản mẫu rồi HR của phòng ban đó sửa bản sao. Tài liệu để chung một kho, ai cần thì tải lên, Viga tìm trên
toàn kho. **Không** gắn `team_id` vào `documents` và **không** lọc tài liệu theo phòng ban khi Viga trả lời.
