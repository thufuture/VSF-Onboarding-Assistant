# P0A — Chốt domain/schema (chi tiết)

> Thuộc [ke-hoach-trien-khai-portal.md §5](../ke-hoach-trien-khai-portal.md) (P0A), gom các câu hỏi "chặn domain/schema" ở §7 và nguyên tắc retention ở §8 thành quyết định cụ thể, đủ để bắt đầu viết migration ở P1. Mentor đang bận golive, đã cho phép tự nghiên cứu và quyết — tài liệu này **tự chốt theo nguyên tắc MVP an toàn nhất** (ưu tiên phương án dễ đảo ngược), đánh dấu rõ chỗ nào nên xác nhận lại với mentor/HR sau khi rảnh.
> Không làm ở đây: duyệt nội dung task Ngày 1 thật, đầu mối/link thật — đó là **P0B**.

## 1. Mục tiêu và đầu ra

**Mục tiêu:** có đủ quyết định về state machine, enum, quan hệ dữ liệu và nguyên tắc xóa/lưu để viết migration P1 mà không phải sửa lại giữa chừng.

**Đầu ra:**
1. Bảng quyết định ở mục 3 — mỗi dòng có câu trả lời cụ thể (không còn "cần hỏi mentor").
2. Danh sách enum/field chốt ở mục 4 — dùng thẳng làm cột trong migration P1.
3. Nguyên tắc retention ở mục 5 — áp dụng khi thiết kế foreign key (`ON DELETE ...`) ở P1.

## 2. Cách quyết định khi không có mentor

Với mỗi câu hỏi, phân loại:
- **Đã có sẵn** trong tài liệu cũ ([ke-hoach-portal-onboarding.md](../../portal/ke-hoach-portal-onboarding.md), [dac-ta-tong-the-portal-onboarding-v14.md](../../portal/dac-ta-tong-the-portal-onboarding-v14.md)) → dùng nguyên, không tự đoán mới.
- **Chưa có, nhưng đảo ngược được rẻ** (đổi enum, đổi default) → tự chốt theo MVP, ghi chú "có thể đổi sau".
- **Chưa có và khó đảo ngược** (ảnh hưởng cấu trúc bảng chính, hoặc liên quan tới người thật/dữ liệu nhân sự) → tự chốt phương án an toàn nhất nhưng **gắn cờ xác nhận lại với mentor** trước khi đưa dữ liệu thật lên.

## 3. Bảng quyết định

| # | Câu hỏi | Trạng thái | Quyết định | Lý do / nguồn |
|---|---|---|---|---|
| D1 | Task hoàn thành theo cơ chế nào? | **Đã đổi quyết định** | ~~HR duyệt (`HR_APPROVAL`)~~ → **bỏ hẳn**. Chỉ còn 1 cách: **nhân viên tự bấm "Hoàn thành"** khi đọc xong hướng dẫn và tự thấy đã làm. Không có bước duyệt, không có minh chứng nộp lên hệ thống. **Hoàn thành là 1 hành động duy nhất cho cả task**: dù hướng dẫn hiển thị nhiều bước (1, 2, 3...), không có nút "done" riêng cho từng bước con — nhân viên đọc/làm hết rồi bấm "Hoàn thành" 1 lần cho toàn bộ task. (Khác với D8: D8 là điều kiện tiên quyết **giữa các task khác nhau** với nhau, không phải giữa các bước trong cùng 1 task — 2 khái niệm không liên quan). Backend chỉ kiểm tra prerequisite (task tiên quyết phải `DONE`) trước khi cho bấm hoàn thành | Đơn giản hóa MVP theo yêu cầu — xem [ke-hoach-trien-khai-portal.md §3](../ke-hoach-trien-khai-portal.md) |
| D2 | Journey đang chạy có nhận cập nhật khi template publish version mới, hay giữ snapshot? | Đã có sẵn | **Snapshot mặc định** — publish version mới **không** tự đổi journey đang chạy; HR **chủ động chọn** cho từng journey: giữ nguyên hoặc migrate (chỉ áp dụng task chưa bắt đầu, task `DONE` giữ nguyên) | [ke-hoach-portal-onboarding.md §4.1](../../portal/ke-hoach-portal-onboarding.md#41-tách-template-và-instance) |
| D3 | Kẹt/không hiểu task thì xử lý sao? | **Đã đổi quyết định** | ~~Nộp minh chứng (`EVIDENCE_REQUIRED`)~~ → **bỏ hẳn bảng `task_evidence`**. Thay bằng: nhân viên hỏi Viga trong ngữ cảnh task; nếu Viga không đủ căn cứ trả lời, Viga đề nghị tạo ticket (có xác nhận của nhân viên) — HR xử lý qua ticket, không qua "duyệt minh chứng" | Đơn giản hóa MVP; khớp §1.1 (vai trò Viga) ở ke-hoach-trien-khai-portal.md |
| D4 | Task khác nhau theo địa điểm/loại máy thì xử lý sao? | **Đã đổi quyết định** | ~~Lọc bằng `applies_when` ở schema~~ → **bỏ hẳn**. Thông tin khác nhau theo địa điểm/loại máy (vd: tầng nào, tòa nào) là **dữ liệu tĩnh giống nhau cho mọi người ở cùng nơi đó**, không phải điều kiện cần lọc theo từng nhân viên — viết thẳng vào **nội dung hướng dẫn task** dạng rẽ nhánh bằng chữ: "Nếu bạn làm ở HCM: tầng 14, Vincom Đồng Khởi. Nếu ở HN: tầng 21, Technopark Gia Lâm." Task vẫn hiện cho mọi nhân viên như nhau, không có task nào bị ẩn/`NOT_APPLICABLE` vì lý do này | Đơn giản hóa MVP theo yêu cầu — không cần cơ chế lọc cho thông tin vốn tĩnh |
| D5 | Ticket gán người hay team? | Đã có sẵn | Vào **hàng đợi chung của team**, HR "Nhận xử lý" mới gán `assigned_hr_id` | Mục 3, ke-hoach-trien-khai-portal.md |
| D6 | Khi ticket đóng, task tự thoát `BLOCKED` hay HR quyết định? | Cần chốt (dễ đảo ngược) | **HR chủ động đổi trạng thái task**, hệ thống không tự suy luận. Lý do: đóng ticket không đồng nghĩa vấn đề gốc đã hết (vd: ticket đóng vì "đã hướng dẫn xong" nhưng nhân viên chưa thực sự thao tác xong) — tự động hóa dễ sai. Ticket có field `resolution_note`; UI gợi ý HR đổi trạng thái task liên quan nhưng không tự làm | Nguyên tắc "workflow do backend kiểm soát, không suy luận hộ" (v14 §5.3) |
| D7 | ~~1 EmployeeTask thuộc nhiều điều kiện applies_when cùng lúc thì xử lý sao?~~ | Không còn áp dụng | Câu hỏi này chỉ có ý nghĩa khi còn cơ chế lọc theo điều kiện (D4) — D4 đã bỏ, nên D7 **không còn cần quyết định** | Hệ quả của D4 |
| D8 | `task_dependencies` (prerequisite) có cho phép OR không (hoàn tất 1-trong-N task trước là đủ), hay chỉ AND? | Cần chốt (khó đảo ngược — ảnh hưởng thuật toán tính `READY`) | **Chỉ AND** ở MVP: task chỉ `READY` khi **toàn bộ** task tiên quyết `DONE`. Không có OR. Nếu sau này cần OR, thêm bảng `task_dependency_groups` chứ không sửa bảng gốc | Khớp ví dụ Ngày 1 hiện có (chuỗi phụ thuộc đơn giản, không có nhánh OR) — [ke-hoach-portal-onboarding.md §6](../../portal/ke-hoach-portal-onboarding.md#6-ví-dụ-dữ-liệu-ngày-1-đầu-vào-seed-cần-hr-duyệt) |
| D9 | `content_gaps` (Viga/HR phản hồi thiếu nguồn) có gắn với `team_id` không? | Cần chốt (dễ đảo ngược) | Có — `content_gaps.team_id` bắt buộc, để HR chỉ thấy gap của phòng ban mình, đúng nguyên tắc scope theo team đã chốt | Nhất quán với mục 3, ke-hoach-trien-khai-portal.md |
| D10 | `journey_templates`/`task_templates` có `team_id = NULL` cho nội dung dùng chung không? | Đã có sẵn | Có — mục 3 đã chốt: dữ liệu dùng chung để `team_id = NULL`, chỉ ADMIN sửa được | Mục 3, ke-hoach-trien-khai-portal.md |

## 4. Enum & field chốt cho migration P1

Tổng hợp lại để copy thẳng khi viết migration (không lặp lại toàn bộ mô hình §15 v14, chỉ liệt kê phần có quyết định mới hoặc dễ quên):

```
-- role + team: ĐÃ CÓ SẴN trong code (users.role = USER|HR|ADMIN, bảng teams/team_members)
-- không thêm cột/bảng mới — xem P1/P1.md mục 0 để biết chi tiết đã kiểm tra code thật

-- KHÔNG còn completion_type / bảng task_evidence (D1, D3) — mọi task chỉ tự-hoàn-thành

-- trạng thái EmployeeTask (bỏ WAITING_APPROVAL vì không còn ai duyệt — D1;
--  bỏ NOT_APPLICABLE vì không còn cơ chế lọc theo điều kiện — D4)
employee_tasks.status ENUM(
  'LOCKED','READY','IN_PROGRESS',
  'WAITING_EXTERNAL','BLOCKED','DONE','SKIPPED'
)
employee_tasks.team_id FK teams.id NOT NULL
employee_tasks.completed_at TIMESTAMP NULLABLE  -- set khi nhân viên tự bấm "Hoàn thành"

-- KHÔNG còn task_templates.applies_when (D4, D7) — nội dung khác biệt theo
-- địa điểm/loại máy viết trực tiếp trong hướng dẫn task (Markdown), không lọc ở schema

-- prerequisite (D8) — chỉ AND, không cần bảng group ở MVP
task_dependencies(task_template_id, depends_on_task_template_id)

-- ticket (đã chốt ở mục 3 file chính)
tickets.team_id FK teams.id NOT NULL
tickets.assigned_hr_id FK users.id NULLABLE
tickets.resolution_note TEXT NULLABLE  -- (D6)

-- content_gaps (D9)
content_gaps.team_id FK teams.id NOT NULL

-- scope dùng chung (D10)
journey_templates.team_id FK teams.id NULLABLE  -- NULL = dùng chung, chỉ ADMIN sửa
task_templates.team_id FK teams.id NULLABLE
documents.team_id FK teams.id NULLABLE
contact_channels.team_id FK teams.id NULLABLE
approved_links.team_id FK teams.id NULLABLE
```

## 5. Nguyên tắc retention (áp dụng khi viết `ON DELETE` ở P1)

Copy từ [ke-hoach-trien-khai-portal.md §8](../ke-hoach-trien-khai-portal.md#8-retention-và-xóa-dữ-liệu--chốt-nguyên-tắc-từ-p0a-không-lùi-hết-về-sau), chốt cụ thể thành hành vi FK:

| Đối tượng | Hành vi khi bị xóa/ngừng dùng | FK gợi ý |
|---|---|---|
| `employee_tasks`, `employee_journeys` | Soft delete (cột `deleted_at`), không xóa cứng — giữ lịch sử onboarding | Không dùng `ON DELETE CASCADE` |
| `tickets`, `ticket_messages` | Soft delete, giữ để audit xử lý sự cố | Không dùng `ON DELETE CASCADE` |
| `journey_templates`/`task_templates` **đã publish** | Bất biến — không sửa/xóa, chỉ tạo version mới | Không có thao tác xóa; publish tạo row mới |
| `journey_templates`/`task_templates` **draft chưa publish** | Hard delete được | `ON DELETE CASCADE` xuống `task_dependencies` của riêng draft đó |
| `documents` | Không xóa file gốc nếu còn `task_source_mappings` trỏ tới (delete-guard, đã có ở P4A) — nếu buộc phải ngừng dùng, đổi trạng thái `RETIRED` thay vì xóa | `ON DELETE RESTRICT` khi còn tham chiếu |
| `audit_logs` | Không bao giờ xóa (bất biến), kể cả khi user liên quan bị xóa | `ON DELETE SET NULL` cho `actor_id` (giữ log, mất liên kết user) |
| `users` (nhân viên nghỉ việc) | Soft delete (`deactivated_at`), ẩn khỏi UI danh sách — **không xóa cứng** vì sẽ vỡ `employee_journeys`/`tickets`/`audit_logs` liên quan | Không dùng `ON DELETE CASCADE` trên `users` |

## 6. Definition of Done — P0A xong khi nào

- [ ] Toàn bộ 10 dòng ở bảng mục 3 có quyết định cụ thể (không còn ô "cần hỏi mentor").
- [ ] Danh sách enum/field ở mục 4 đã review — khớp với §15 v14 và §4–5 ke-hoach-portal-onboarding.md, không mâu thuẫn.
- [ ] Bảng retention ở mục 5 đã áp dụng được thành `ON DELETE ...` cụ thể cho từng FK chính.
- [ ] Đã đánh dấu rõ (trong tài liệu này hoặc ghi chú riêng) những quyết định **khó đảo ngược** (D8) để nếu mentor phản hồi khác thì biết chỗ nào phải sửa migration thay vì chỉ đổi config.

## 7. Bàn giao cho P0B / P1

- **P0B** (chốt dữ liệu seed thật) chạy song song, không phụ thuộc P0A xong hết — nhưng cần D8 ở đây để biết seed Ngày 1 phải khai báo dependency thế nào, và cần viết hướng dẫn task theo đúng kiểu rẽ nhánh bằng chữ đã chốt ở D4 (vd: khai rõ theo địa điểm ngay trong nội dung, không tách task riêng).
- **P1** (migration) dùng thẳng mục 4 làm cột schema; dùng mục 5 làm chính sách xóa; không cần quay lại hỏi domain nữa trừ khi mentor phản hồi khác với quyết định đã chốt ở đây.
