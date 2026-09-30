# Báo cáo tiến độ Portal — HR và Quản trị hệ thống (cập nhật 30/09/2026)

> Nhánh `feat/portal-plan`. **Chưa commit, chưa push, chưa mở PR.**
> Bản dựng đối chiếu: [prototype-ui-flow-v15-shared-roadmap.html](../portal/prototype-ui-flow-v15-shared-roadmap.html).
> Kết luận ngắn: khu HR đã xong 5 trang có API thật, khu Quản trị hệ thống (Admin) đã xong toàn bộ 6 trang với API thật.
> Còn 3 mục chưa làm: Ticket sự cố, Phản hồi Viga, Đầu mối và đường dẫn.

## 1. Tình trạng từng trang

### Khu HR

| Trang | Đường dẫn | API | Trạng thái |
|---|---|---|---|
| Tổng quan | `/admin` | `GET /portal/dashboard` | Xong, 4 KPI số thật |
| Nhân viên | `/admin/employees` | `GET /portal/employees` | Xong, có phân trang 5 dòng và cột thao tác |
| Quản lý task | `/admin/tasks` | 6 endpoint (xem mục 2) | Xong, roadmap dạng sóng, menu "ngày" ở thanh bên |
| Tài liệu | `/admin/documents` | 5 endpoint | Xong, bảng 7 cột kiểu v14.2 |
| Tạo task bằng AI | `/admin/ai-tasks` | `POST /portal/ai/task-proposals` | Xong |
| Ticket sự cố | — | — | **Chưa làm** (bảng `tickets`, `ticket_messages` đã có, router chưa có) |
| Phản hồi Viga | — | — | **Chưa làm** (bảng `content_gaps` đã có, router chưa có) |
| Đầu mối và đường dẫn | — | — | **Chưa làm** (bảng `contact_channels`, `approved_links` đã có, router chưa có) |

### Khu Quản trị hệ thống (mới làm trong đợt này)

| Trang | Đường dẫn | API | Nội dung |
|---|---|---|---|
| Tổng quan | `/admin` (vai trò ADMIN) | `GET /admin/dashboard` | 4 KPI, biểu đồ nhân viên theo phòng ban, 5 hoạt động gần nhất |
| Người dùng | `/admin/users` | 5 endpoint | Tìm, lọc vai trò, thêm, sửa, đặt lại mật khẩu, khóa/mở khóa |
| Phòng ban | `/admin/teams` | 5 endpoint | Tạo, sửa, chi tiết kèm thành viên, lưu trữ/khôi phục, sao lộ trình mẫu |
| Thành viên | `/admin/members` | 3 endpoint | Gán người vào phòng ban, gỡ, lọc theo trạng thái truy cập |
| Lộ trình mẫu chung | `/admin/template` | `GET /admin/template-overview` | Bản mẫu chung và lộ trình của từng phòng ban |
| Nhật ký | `/admin/audit` | `GET /admin/audit-logs` | Đọc từ bảng `audit_logs` thật |

Thanh bên tự đổi theo vai trò: ADMIN thấy 6 mục trên, HR thấy menu HR như cũ.

## 2. API đã viết

### `/api/v1/portal/*` (HR) — bổ sung trong đợt này

| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/dashboard` | KPI Tổng quan HR, lọc theo team của người gọi |
| GET | `/employees` | Danh sách nhân viên kèm tiến độ, task hiện tại |
| GET | `/documents` | Danh sách tài liệu; đợt này thêm `owner_name` và `task_titles` |
| PATCH | `/documents/{id}` | Sửa tên và nhóm tài liệu |
| PATCH | `/documents/{id}/status` | Ẩn / kích hoạt lại (không xóa cứng) |
| GET | `/document-categories` | Nhóm tài liệu cho ô lọc và form |
| GET | `/stages` | Giai đoạn bản nháp để AI gắn task |
| GET | `/journey-templates/mine` | Cây lộ trình: giai đoạn → task → tiên quyết |
| POST | `/stages/{id}/tasks` | Thêm task thủ công, có `sort_order` và `depends_on` |
| PATCH | `/task-templates/{id}` | Sửa task, đổi giai đoạn, đổi thứ tự, đổi tiên quyết |
| DELETE | `/task-templates/{id}` | Xóa task |
| POST | `/journey-templates/{id}/publish` | Xuất bản, khóa sửa bản đã xuất bản |

### `/api/v1/admin/*` (chỉ vai trò ADMIN) — mới hoàn toàn

| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/dashboard` | KPI phòng ban, HR, nhân viên, số cần xử lý |
| GET | `/users` | Danh sách tài khoản kèm phòng ban đang thuộc |
| POST | `/users` | Tạo tài khoản, trả mật khẩu tạm đúng một lần |
| PATCH | `/users/{id}` | Sửa tên, email, vai trò (đổi vai trò thì thu hồi phiên cũ) |
| POST | `/users/{id}/reset-password` | Đặt lại mật khẩu, thu hồi mọi phiên |
| PATCH | `/users/{id}/status` | Khóa / mở khóa |
| GET, POST | `/teams` | Danh sách và tạo phòng ban |
| PATCH | `/teams/{id}` | Sửa tên, đổi HR phụ trách |
| PATCH | `/teams/{id}/status` | Lưu trữ / khôi phục |
| POST | `/teams/{id}/copy-template` | Sao lộ trình mẫu chung thành bản nháp riêng của phòng ban |
| GET, POST | `/memberships` | Danh sách và gán thành viên |
| DELETE | `/memberships/{team}/{user}` | Gỡ khỏi phòng ban |
| GET | `/template-overview` | Thông tin bản mẫu chung |
| GET | `/audit-logs` | Nhật ký thay đổi |

**Quy tắc nghiệp vụ đã cài:** không tự khóa hoặc tự hạ vai trò của chính mình; email trùng bị chặn không phân biệt hoa thường; chỉ tài khoản vai trò HR mới được đặt làm HR phụ trách; mã phòng ban là duy nhất; phòng ban đã có lộ trình thì không sao thêm lần nữa; tài khoản ADMIN không thuộc phòng ban nào; mọi thao tác ghi vào `audit_logs`.

**Sao lộ trình mẫu chung** chép đủ giai đoạn, task và quan hệ tiên quyết, sau đó ánh xạ lại id để tiên quyết trỏ vào task của bản sao, không trỏ ngược về bản gốc. Bản sao ở trạng thái `DRAFT` để HR của phòng ban sửa rồi tự xuất bản.

## 3. Sửa giao diện theo yêu cầu

| Yêu cầu | Đã làm |
|---|---|
| Mục "Tổng quan" luôn sáng dù đang ở trang khác | Sửa cách chọn mục đang mở: lấy mục khớp đường dẫn dài nhất, thay vì mọi `/admin/...` đều khớp `/admin` |
| Bỏ "Trợ lý hỏi đáp" khỏi menu HR | Đã bỏ khỏi menu; trang `/chat` vẫn còn nhưng HR không có đường vào từ thanh bên |
| Tên cột bảng không viết in hoa | Bỏ `text-transform: uppercase` ở cả 3 bảng (Tài liệu, Nhân viên, Admin), cỡ chữ tăng lên 12,5px |
| Chân phân trang nằm đáy thẻ, không sát dòng cuối | Thẻ chuyển sang `flex` dọc, vùng bảng có chiều cao tối thiểu bằng một trang đầy |
| Cột trạng thái bị xuống dòng | Thêm `white-space: nowrap` cho nhãn trạng thái |
| Bảng Tài liệu hiển thị rõ như v15 | Làm lại theo bản v14.2: icon file có màu theo nhóm, nhãn nhóm có icon riêng, cột "Xử lý nội dung" hai dòng, cột "Task sử dụng", cột "Cập nhật" kèm người phụ trách, 3 ô lọc dạng thả xuống có icon |
| Trang Nhân viên theo v15 | Thêm phân trang 5 dòng, dòng đếm ở chân bảng, cột thao tác "Xem task" và "Nhắn" |

**Lỗi đã sửa:** khóa `portalTasks.view` và `portalDocuments.view` bị dùng vừa làm nhóm vừa làm chuỗi, gây lỗi `INSUFFICIENT_PATH` và `MISSING_MESSAGE` trên trang Quản lý task và Tài liệu. Đã tách thành `viewTask` riêng.

## 4. Kiểm chứng đã chạy

| Việc | Kết quả |
|---|---|
| `ruff check` + `ruff format --check` | Sạch, 104 file |
| `mypy src` | Sạch, 104 file |
| `pytest tests` | 145 pass, 55 skip, **2 fail** |
| `pytest tests/integration/test_admin_api.py` | 3 pass (trên PostgreSQL thật) |
| `tsc --noEmit` | Sạch |
| `eslint src` | Sạch |
| `vitest run` | 149 pass, 13 file |
| Dựng lại Docker backend | Thành công, container khỏe |
| Gọi thật 6 endpoint `/admin/*` bằng cookie ADMIN | Trả đúng dữ liệu |
| Chụp màn hình có đăng nhập, 6 trang Admin + 2 trang HR | Khớp bố cục v15 |
| Chạy thử modal bằng trình duyệt thật | Tạo/sửa phòng ban, chi tiết + thành viên, lưu trữ, khôi phục, thêm/đặt lại/khóa người dùng, gỡ thành viên — tất cả đều có modal xác nhận trước khi gọi API |

**2 test hỏng** là `test_rejects_file_over_size_limit` và `test_rejects_text_shorter_than_minimum_length` trong `tests/test_ingest/test_parser.py`. Nguyên nhân là mã hóa `cp1252` của Windows không ghi được ký tự tiếng Việt khi pytest in thông báo lỗi, **không phải lỗi code**. Hai test này đã hỏng từ trước đợt này.

Test tích hợp Admin kiểm: HR bị chặn khỏi mọi endpoint admin; tạo tài khoản rồi đăng nhập được bằng mật khẩu tạm; sau khi khóa thì không đăng nhập được nữa; không tự khóa được chính mình; sao lộ trình mẫu chép đủ task và tiên quyết; phòng ban lưu trữ thì thành viên chuyển sang trạng thái truy cập đóng; nhật ký ghi đúng hành động.

## 5. Còn lại

| Việc | Cần gì |
|---|---|
| Ticket sự cố (HR) | Viết router cho `tickets` / `ticket_messages`, dựng UI |
| Phản hồi Viga (HR) | Viết router cho `content_gaps`, dựng UI |
| Đầu mối và đường dẫn (HR) | Viết router cho `contact_channels` / `approved_links`, dựng UI |
| Nút "Nhắn" ở trang Nhân viên | Chưa có API nhắn tin — nút đang để tắt |
| Nút "Xem task" ở trang Nhân viên | Hiện dẫn sang trang Quản lý task chung, chưa lọc theo từng người |
| Tab "Liên hệ" trong modal task | Phụ thuộc Đầu mối và đường dẫn |
| Mô tả ngắn cho tài liệu | Bảng `documents` chưa có cột mô tả; bảng hiện hiển thị `source_key` thay chỗ đó |
| Nhập người dùng từ CSV | v15 có nút này, chưa làm |

## 6. Ghi chú về phòng ban và Viga

Đã thống nhất: lộ trình onboarding hầu như giống nhau cho mọi người, nên dùng một lộ trình chung; phòng ban nào cần khác thì Admin sao bản mẫu rồi HR của phòng ban đó sửa bản sao (đã cài ở mục 2). Tài liệu để chung một kho, ai cần thì tải lên, Viga tìm trên toàn kho. **Không** gắn `team_id` vào bảng `documents` và **không** lọc tài liệu theo phòng ban khi Viga trả lời.

## 7. Cập nhật 30/09/2026 (buổi chiều): roadmap có màu và trang AI theo v15

| Việc | Chi tiết |
|---|---|
| Nhóm task thật | Thêm cột `task_templates.task_group` (Hồ sơ, Đào tạo, Thiết bị, Văn phòng, hoặc để trống) qua migration `0003`; HR chọn nhóm ở tab "Thông tin" của form task |
| Màu mốc trên roadmap | Mỗi nhóm một màu và icon như v15; task chưa phân nhóm dùng màu xám. Chú giải ở đáy luôn liệt kê đủ 4 nhóm, khớp đúng màu mốc (lần trước màu chưa có nghĩa và không có chú giải) |
| Đường cong roadmap | Dùng đúng công thức của v15, đủ 12 vị trí mốc; cờ Bắt đầu và huy hiệu Hoàn tất bám mốc đầu và cuối |
| Tạo task bằng AI | Bước hiện tại tô xanh, đường nối trải hết bề ngang; chọn sẵn giai đoạn đầu; ô giai đoạn có icon và màu riêng; bộ chọn tài liệu chuyển sang chọn nhiều nguồn (tìm kiếm, viền trái theo nhóm, huy hiệu "N đã chọn") |
| Dữ liệu mẫu | Sửa tên task và giai đoạn bị mất dấu tiếng Việt, gán nhóm cho 9 task mẫu |
| Kiểm chứng | 27 test tích hợp portal/admin pass (thêm test nhóm task: tạo, sửa, nhóm sai bị chặn 422); vitest 149 pass; tsc, eslint, ruff, mypy sạch |

**Còn lại thêm:** task do AI chấp nhận vào lộ trình chưa tự gán nhóm (đang để trống, HR chọn sau khi sửa task).
