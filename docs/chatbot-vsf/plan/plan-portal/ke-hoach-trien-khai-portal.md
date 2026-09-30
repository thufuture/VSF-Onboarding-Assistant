# VSF Onboarding Portal — Kế hoạch kiến trúc, design, vai trò và phase triển khai

> Trạng thái: bản nháp v1, tổng hợp để anh xem trước khi bắt tay code. Mentor (anh Trí) đang bận golive, đã cho phép tự nghiên cứu và triển khai tiếp.
> Dựa trên: [dac-ta-tong-the-portal-onboarding-v14.md](../portal/dac-ta-tong-the-portal-onboarding-v14.md) (đặc tả tổng thể, đã duyệt về mặt thiết kế), [ke-hoach-portal-onboarding.md](../portal/ke-hoach-portal-onboarding.md) (mô hình dữ liệu và luồng nghiệp vụ chi tiết, bản nháp v3), [phan-tich-ai-va-viga.md](../portal/phan-tich-ai-va-viga.md) (phạm vi AI/Viga), và prototype UI đã build xong: [prototype-ui-flow-v15-shared-roadmap.html](../portal/prototype-ui-flow-v15-shared-roadmap.html) (đã gửi mentor xem, link Artifact: https://claude.ai/artifact/FEYH8GCDUcDW7mo2FxfaK6). Tài liệu này **không lặp lại chi tiết** ở các file trên — chỉ xếp thứ tự làm và chỉ ra file nào là nguồn cho phần nào.
> Hạ tầng và pipeline RAG/ingest/auth **tái dùng từ dự án chatbot** đã chạy thật (xem [master-plan.md](../master-plan.md), [huong-dan-thiet-lap-may-chu.md](../huong-dan-thiet-lap-may-chu.md)) — Portal không dựng lại từ đầu, chỉ thêm domain mới (roadmap/task/ticket) lên trên nền đó.

## 1. Portal khác gì với chatbot đã có

Chatbot hiện tại là **hỏi-đáp tự do có trích dẫn** (RAG). Portal là **workflow có trạng thái**: mỗi nhân viên có một lộ trình (journey) gồm các task theo thứ tự, có điều kiện tiên quyết, có trạng thái do backend kiểm soát — không phải hội thoại tự do. Viga trong Portal đổi vai trò từ "trả lời câu hỏi" sang **"trợ lý dẫn đường theo tiến độ từng người"** (mục 8, [ke-hoach-portal-onboarding.md](../portal/ke-hoach-portal-onboarding.md)): biết task nào đang mở, gợi ý bước tiếp theo, và chỉ tạo ticket khi được xác nhận — không tự suy luận trạng thái từ link ngoài.

Vì vậy Portal cần **domain mới** (journey/task/ticket) cộng **tái dùng** domain đã có (auth, document ingest, RAG retrieval, LLM adapter).

### 1.1 Task làm gì, Viga làm gì — ranh giới rõ, không để LLM làm việc UI/backend đã biết chắc

**Nguyên tắc:** một task tốt phải đủ để **đa số nhân viên tự hoàn thành mà không cần hỏi Viga**. Việc gì backend/UI đã biết chắc chắn (trạng thái, prerequisite, việc tiếp theo) thì **hiển thị trực tiếp trên UI**, không gọi LLM cho việc đó — vừa nhanh hơn, vừa không có rủi ro bịa. Cụ thể:

| Việc | Ai làm mặc định | Vì sao |
|---|---|---|
| "Việc tiếp theo là gì" | **UI chủ động hiển thị**, tính thẳng từ state machine | Backend đã biết chắc task nào mở/khóa; nếu phải hỏi Viga mới biết việc tiếp theo nghĩa là UI chưa làm tốt |
| "Vì sao task này bị khóa" | **UI chủ động hiển thị**, kiểu "Đang khóa. Hãy hoàn tất 'Nhận laptop và tài khoản' trước." | Đây là dữ liệu backend đã có (prerequisite), không cần suy luận ngôn ngữ tự nhiên |
| Nội dung task (làm gì, ở đâu, chuẩn bị gì, các bước, đầu mối, link) | **Task/hướng dẫn tĩnh**, HR viết một lần | Cố định, giống nhau cho mọi người, không cần cá nhân hóa |

Nếu người dùng **vẫn chủ động hỏi Viga** "Tiếp theo tôi làm gì?" hay "Sao task này bị khóa?", Viga **vẫn phải trả lời** — chỉ khác cách trả lời: Viga gọi cùng API/state machine mà UI dùng để lấy kết quả xác định, rồi diễn đạt lại bằng ngôn ngữ tự nhiên; **không tự suy luận trạng thái từ ngữ cảnh hội thoại**. Nói cách khác: UI và Viga dùng chung một nguồn sự thật (backend), khác nhau ở kênh hiển thị.

**Giá trị thật của Viga** — chỉ ở chỗ nội dung tĩnh không đủ:
- Câu hỏi tự do, không khớp chính xác tên/nội dung task.
- Thông tin nằm rải rác ở nhiều tài liệu, cần tổng hợp.
- Ngoại lệ không có trong hướng dẫn chuẩn (địa điểm khác, loại máy khác...).
- Không biết câu hỏi thuộc task nào — Viga phải map câu hỏi sang đúng ngữ cảnh.
- Cần **kết hợp trạng thái cá nhân thật (từ backend) với nội dung tài liệu** để trả lời đúng tình huống của riêng người đó.
- Nguồn không đủ → nói "chưa có căn cứ" thay vì đoán, rồi gợi ý tạo ticket — **chỉ tạo sau khi người dùng xác nhận**.
- Ghi nhận câu hỏi lặp lại nhiều lần để HR biết tài liệu/task nào đang thiếu, cần bổ sung.

**Ví dụ đối chiếu:**
- Task ghi: *"Đến ITHD tầng 12, nhận laptop, đăng nhập Outlook và Teams, sau đó nhập mã bàn giao để hoàn tất."* → không cần Viga để lặp lại nội dung này, UI hiển thị thẳng.
- Nhân viên hỏi: *"Tôi nhận laptop rồi nhưng Teams báo chưa có quyền, tôi có thể làm task faceid trước không?"* → đây mới là việc của Viga: (1) lấy trạng thái task thật từ backend, (2) kiểm tra prerequisite bằng code, (3) tìm hướng dẫn xử lý lỗi Teams trong tài liệu, (4) trả lời kèm citation, (5) nếu tài liệu không có hướng dẫn phù hợp thì nói rõ và đề nghị tạo ticket, (6) chỉ tạo ticket sau khi nhân viên xác nhận.

Tóm lại: **task = luồng chuẩn, phải tự đủ cho đa số**; **Viga = lớp hỗ trợ cho phần còn lại** (câu hỏi tự do, ngoại lệ, đa nguồn, cá nhân hóa theo trạng thái thật) — không phải một kênh thay thế cho việc UI hiển thị trạng thái.

## 2. Kiến trúc mục tiêu

Sơ đồ đầy đủ ở [dac-ta-tong-the-portal-onboarding-v14.md §16](../portal/dac-ta-tong-the-portal-onboarding-v14.md#16-kiến-trúc-hệ-thống-mục-tiêu). Tóm tắt quyết định:

| Lớp | Quyết định | Lý do |
|---|---|---|
| Frontend | Next.js/React, 1 app 3 vai trò (route theo role như chatbot hiện tại: `/vi/portal/employee`, `/vi/portal/hr`, `/vi/portal/admin`) | Tái dùng `VsfBrand`, tokens, layout, i18n đã có ở frontend chatbot |
| Backend | Thêm module vào **cùng FastAPI modular monolith** của chatbot, không tách service riêng ở giai đoạn này | Tránh vận hành 2 backend, 2 lần deploy, 2 lần auth cho 1 người dùng |
| Auth | Tái dùng cookie HMAC + `users`/`roles` đã có; thêm `role_bindings` cho EMPLOYEE/HR/ADMIN | Không làm lại xác thực |
| Dữ liệu workflow | PostgreSQL, bảng mới theo [dac-ta-tong-the-portal-onboarding-v14.md §15](../portal/dac-ta-tong-the-portal-onboarding-v14.md#15-mô-hình-dữ-liệu-khái-niệm) và mô hình template/instance ở [ke-hoach-portal-onboarding.md §4](../portal/ke-hoach-portal-onboarding.md#4-mô-hình-dữ-liệu) | Tách JourneyTemplate (HR soạn, có version) khỏi EmployeeJourney (snapshot theo người), publish không phá vỡ lộ trình đang chạy |
| Retrieval cho AI-đề-xuất-task và Viga | Tái dùng pipeline ingest/BM25/pgvector đã có ở chatbot; task chỉ lưu `task_source_mappings` trỏ về document/section/chunk có sẵn, không nạp lại | Không xây lại RAG, chỉ thêm bảng liên kết |
| Ticket | Bảng mới `tickets`, `ticket_events`, `ticket_messages` trong cùng DB | Đơn giản, không cần ITSM ngoài ở MVP (đúng phạm vi "Không" của [ke-hoach-portal-onboarding.md §1](../portal/ke-hoach-portal-onboarding.md#1-bối-cảnh-và-mục-tiêu)) |
| Hạ tầng | Cùng AWS EC2 + Caddy + Vercel đã triển khai cho chatbot | Không cần máy chủ mới cho MVP |

## 3. Vai trò và quyền

Chốt **3 vai trò hệ thống, không hơn**: EMPLOYEE, HR, ADMIN. **MENTOR, CONTENT_OWNER, TASK_OWNER không phải role trong hệ thống** — bỏ hoàn toàn khỏi mô hình dữ liệu và code (không tạo bảng/enum riêng cho các tên này), để tránh developer đọc [ke-hoach-portal-onboarding.md §2](../portal/ke-hoach-portal-onboarding.md#2-vai-trò) rồi hiểu nhầm còn tồn tại persona thứ tư. Những việc mà tài liệu đó mô tả cho "mentor" (theo dõi tiến độ người phụ trách, nhắc, duyệt) là **trách nhiệm nghiệp vụ của HR**, không phải role. Gọi thống nhất: "HR phụ trách nhân viên", "HR duyệt task", "HR xử lý ticket", "HR quản lý tài liệu" — luôn là HR làm, không phải một actor khác. Ma trận quyền chi tiết ở [dac-ta-tong-the-portal-onboarding-v14.md §18](../portal/dac-ta-tong-the-portal-onboarding-v14.md#18-ma-trận-quyền-rút-gọn):

| Vai trò | Việc chính | Không được làm |
|---|---|---|
| **EMPLOYEE** | Xem lộ trình, đọc hướng dẫn task rồi **tự bấm "Hoàn thành"** khi xong, báo kẹt/hỏi Viga khi không hiểu | Tự đổi trạng thái task ngoài rule (task tiên quyết chưa xong thì không bấm hoàn thành được); xem lộ trình người khác |
| **HR** | Soạn/publish JourneyTemplate, quản lý tài liệu, duyệt đầu mối/link, dùng AI đề xuất task, xử lý ticket theo team, xem tiến độ nhân viên | Tự publish task chưa qua bước AI-đề-xuất → HR-duyệt nếu dùng nguồn AI |
| **ADMIN** | Quản lý user, team, role, audit log | Không mặc định sửa nội dung nghiệp vụ (roadmap/task) |

**Bỏ hẳn khái niệm `completion_type` nhiều loại** (đã có ở [ke-hoach-portal-onboarding.md §5.1](../portal/ke-hoach-portal-onboarding.md#51-ba-loại-xác-nhận-hoàn-thành): `SELF_CONFIRM`/`EVIDENCE_REQUIRED`/`OWNER_APPROVAL`) — **quyết định mới: mọi task chỉ có một cách hoàn thành duy nhất là nhân viên tự bấm "Hoàn thành"** khi đọc xong hướng dẫn và tự thấy đã làm. Không có minh chứng, không có HR duyệt task. Lý do đổi: đơn giản hóa MVP, đúng hướng "task portal + kiểm tra AI/chatbot" hơn là quy trình phê duyệt nội bộ phức tạp. Khi nhân viên kẹt hoặc không hiểu, họ hỏi Viga; nếu Viga không đủ căn cứ, Viga đề nghị tạo ticket (có xác nhận) — HR chỉ xử lý qua ticket, không còn bước "duyệt task" riêng.

**"Không phải role" khác với "không cần scope"**: HR vẫn là một role duy nhất, nhưng cần biết HR nào phụ trách nhân viên nào. Chốt cardinality rõ ràng:

- 1 phòng ban (team) → **nhiều** HR, **nhiều** EMPLOYEE.
- 1 HR → thuộc đúng **1** phòng ban. 1 EMPLOYEE → thuộc đúng **1** phòng ban.
- Các HR cùng phòng ban có **quyền ngang nhau** trên dữ liệu của phòng ban đó: xem nhân viên/tiến độ, xử lý ticket, quản lý roadmap/task/tài liệu/đầu mối/link, xem phản hồi Viga.

**Mô hình dữ liệu:** vì ràng buộc là 1 user – đúng 1 team (không phải nhiều-nhiều), dùng cột FK trực tiếp thay vì bảng join:

> **Đã kiểm tra code thật (backend/src/model/), cập nhật lại:** `users.role` hiện có sẵn 3 giá trị `USER`/`HR`/`ADMIN` (Portal "EMPLOYEE" = giá trị `USER` trong DB, không thêm role mới). `teams`/`team_members` **đã tồn tại sẵn** (migration `0001_core.py`), dạng many-to-many, đang dùng cho `auth_service.department_name()`. **Không thêm cột `primary_team_id`** — Portal tái dùng thẳng `team_members`, scope kiểm bằng `EXISTS (SELECT 1 FROM team_members WHERE team_id=? AND user_id=?)`. Chi tiết kỹ thuật ở [P1/P1.md](P1/P1.md).

```
users: id, role (USER|HR|ADMIN) -- đã có sẵn
teams: id, code, name -- đã có sẵn
team_members: team_id, user_id -- đã có sẵn, dùng làm nguồn scope, không tạo bảng/cột mới
```

**Quy tắc quyền:** HR truy cập được đối tượng khi tồn tại dòng `team_members` khớp `(team_id, hr.user_id)`. Mọi bảng nghiệp vụ cần scope đều lưu `team_id`: `journey_templates`, `employee_journeys`, `employee_tasks`, `documents`, `tickets`, `contact_channels`, `approved_links`, `content_gaps`. Dữ liệu dùng chung toàn công ty có thể để `team_id = NULL`, nhưng chỉ ADMIN hoặc quyền riêng mới được sửa.

**Ticket — cơ chế "Nhận xử lý" để tránh trùng:** `tickets.assigned_hr_id` (nullable). Ticket mới vào hàng đợi chung của phòng ban, mọi HR trong team đều thấy; 1 HR bấm "Nhận xử lý" → hệ thống set `assigned_hr_id`; HR khác vẫn xem được nhưng không cùng cập nhật nếu chưa được chuyển giao; khi HR nghỉ, HR khác "Nhận lại" hoặc Admin chuyển người xử lý.

**Task: không còn bước HR duyệt.** Nhân viên tự bấm "Hoàn thành" (xem mục 3 bảng vai trò) — không có `approved_by_hr_id`/`approved_at` trên `employee_tasks` vì không còn ai duyệt task. Nếu sau này thực tế phát sinh nhu cầu cần HR xác nhận lại một số task nhạy cảm, thêm lại field này chứ không thiết kế sẵn ở MVP.

Không cần bảng assignment riêng (`hr_employee_assignments`, `ticket_assignments`, `document_hr_owners`) — scope theo `team_id` + cột audit `assigned_hr_id` (ticket) là đủ cho MVP; chỉ thêm bảng riêng khi thực tế phát sinh nhu cầu gán đích danh phức tạp hơn.

Nguyên tắc bất biến giữ nguyên như chatbot: **workflow do code kiểm soát, AI chỉ đề xuất — không tự publish, không tự duyệt task nhạy cảm** ([dac-ta-tong-the-portal-onboarding-v14.md §5.3](../portal/dac-ta-tong-the-portal-onboarding-v14.md#53-quy-tắc-bất-biến)).

## 4. Design (prototype v15 là baseline — chưa phải "đã chốt")

Prototype v15 đã thống nhất **cấu trúc/kiến trúc thông tin**, không cần thiết kế lại từ đầu, nhưng **chưa được kiểm chứng bằng dữ liệu và điều kiện thật**. Không đổi kiến trúc thông tin lớn nếu chưa có lý do, nhưng phải polish và test lại khi có backend thật:

- Đã thống nhất, giữ nguyên: token màu/font/bo góc đồng bộ chatbot (navy `#0c2d5b`, cyan `#1090cb`, Be Vietnam Pro — [dac-ta-tong-the-portal-onboarding-v14.md §19](../portal/dac-ta-tong-the-portal-onboarding-v14.md#19-thiết-kế-giao-diện-chung)); landing + login; roadmap dùng chung component giữa "Quản lý task" và "Tạo task bằng AI"; card AI-đề-xuất 5 hành động có modal xác nhận.
- **Chưa được kiểm chứng, phải làm khi nối API thật (P3 trở đi):** dữ liệu thật thay vì mock; tên task dài; roadmap 20–30 task (prototype mới test với ít task); màn hình laptop nhỏ; người dùng thật (nhân viên/HR) chứ không phải chỉ nội bộ; loading/empty/error state thật (§20 v14) — hiện chỉ có UI, chưa có trạng thái lỗi thật từ API; keyboard navigation và accessibility (§19 v14 yêu cầu WCAG AA, chưa audit); responsive dưới 1000px với dữ liệu thật; quyền/trạng thái lấy từ backend thật thay vì state giả lập trong file.

## 5. Phase triển khai (đề xuất)

Khung tương tự cách chia phase của chatbot ([master-plan.md](../master-plan.md)): mỗi phase là PR nhỏ, có cổng hoàn thành rõ, làm tuần tự.

**Chốt thứ tự: AI đề xuất task làm trước Viga.** Lý do: (1) AI đề xuất task giúp HR dựng roadmap nhanh hơn ngay từ đầu, có giá trị demo và vận hành sớm; (2) luồng AI-đề-xuất → HR duyệt → publish là workflow khép kín, không phụ thuộc Viga; (3) Viga cần dữ liệu vận hành thật (câu hỏi lặp, task đã publish) để có ngữ cảnh trả lời tốt, nên làm sau khi đã có roadmap thật (kể cả roadmap do AI hỗ trợ tạo) sẽ có nhiều ngữ cảnh hơn để test. Điều kiện đi kèm: retrieval của chatbot cần đủ ổn định trước khi bật AI đề xuất task (xem rủi ro ở mục 6).

| Phase | Tên | Việc chính | Đầu ra / cổng hoàn thành | Phụ thuộc |
|---|---|---|---|---|
| **P0A** | Chốt domain/schema | Trả lời các câu hỏi **chặn schema** ở mục 7 (snapshot hay live-update, `NOT_APPLICABLE` theo điều kiện nào, ticket gán người hay team, ai đổi `BLOCKED`...) và nguyên tắc retention ở mục 8 | Đủ quyết định để thiết kế migration, không cần chờ duyệt nội dung task thật | Không |
| **P0B** | Chốt dữ liệu seed thật | Xác nhận với mentor/HR: danh sách task Ngày 1 thật (mục 6, [ke-hoach-portal-onboarding.md](../portal/ke-hoach-portal-onboarding.md#6-ví-dụ-dữ-liệu-ngày-1-đầu-vào-seed-cần-hr-duyệt)), mã đầu mối/link nào đã duyệt | Bảng dữ liệu seed được HR xác nhận (không còn "ứng viên") | Không, chạy song song P0A; chỉ **P3/P4C và pilot** cần P0B xong, P1 không cần chờ |
| **P1** | Data model + migration + **RBAC/scope nền tảng** | Tạo bảng theo §15 v14 + §4 ke-hoach: `journey_templates/stages/task_templates/task_dependencies`, `employee_journeys/tasks/events/evidence`, `contact_channels`, `approved_links`, `tickets/*`; **đồng thời** dựng RBAC 3 role, bảng team/phòng ban, gán role, cột/bảng assignment (`hr_assignee_id` hoặc `hr_employee_assignments` — mục 3), kiểm quyền server-side ở tầng dùng chung (không để dành tới P8, vì P3/P4 sẽ phải sửa lại API nếu thiếu) | Migration chạy được, `alembic check` xanh; seed giả lập nạp được; 1 API mẫu chặn được truy cập sai role/sai scope | P0A |
| **P2** | API + state machine nhân viên | Implement state machine EmployeeTask (§5.2 ke-hoach), API `GET /me/journey`, `POST /me/tasks/{id}/start\|complete`, kiểm tiên quyết server-side | Test unit state machine + prerequisite; Postman/API test theo §17 v14 | P1 |
| **P3** | Giao diện Nhân viên: roadmap + task detail | Nối UI roadmap và chi tiết task đã có trong prototype v15 vào API thật (không gồm ticket — xem P5), bỏ dữ liệu giả; UI tự hiển thị "việc tiếp theo"/"lý do khóa" từ state machine thật (§1.1) | Nhân viên demo đăng nhập → xem roadmap → hoàn thành 1 task thật, task phụ thuộc tự mở khóa | P2 |
| **P4A** | HR: quản lý tài liệu | API + UI upload nhiều file, theo dõi trạng thái ingest từng file, xem Markdown liên tục kèm mục lục heading, tải file gốc, thay thế tài liệu, đánh dấu task nào đang dùng tài liệu, chặn xóa nếu còn task phụ thuộc. **Tái sử dụng component và API xem tài liệu hiện có của chatbot** (đọc nội dung, highlight citation) làm nền; cần kiểm tra thực tế component đó trước khi giả định dùng được thẳng, rồi **mở rộng thêm** mục lục heading, section focus rõ trong khung Portal, usage-mapping, delete-guard, review-gate — các phần mở rộng này là mới cho Portal | HR upload 1 tài liệu, thấy trạng thái ingest, xem được nội dung, không xóa được nếu đang có task dùng | P1 |
| **P4B** | HR: quản lý roadmap/task thủ công | API + UI tạo/sửa/nhân bản JourneyTemplate/TaskTemplate (chưa AI), gắn prerequisite, `applies_when` (mọi task đều tự-hoàn-thành, không còn `completion_type`) | HR tạo tay được 1 template đầy đủ task | P4A, P2 |
| **P4C** | Đầu mối, link, validation, publish | Quản lý `contact_channels`/`approved_links` (DRAFT→APPROVED theo §4.3 ke-hoach); validation khi publish (chặn dependency vòng, thiếu prerequisite, liên hệ/link chưa duyệt — §4.1 ke-hoach); publish tạo version bất biến | HR publish 1 template hợp lệ, nhân viên demo thấy đúng lộ trình; publish bị chặn nếu còn liên hệ DRAFT | P4B |
| **P5** | Ticket end-to-end (thủ công) | API + UI tạo ticket **thủ công từ task** (chưa có Viga ở phase này), theo dõi "Ticket của tôi" (nhân viên), xử lý ticket theo team (HR) | Nhân viên tạo ticket từ 1 task → HR xử lý và đóng, có audit | P3, P4C |
| **P6** | AI đề xuất task | Nối `task_source_mappings` với retrieval đã có; API `POST /ai/task-proposals`; UI đã có sẵn trong v15 (chấp nhận/sửa/nhân bản/xóa có xác nhận). **Cổng đúng luồng:** AI đề xuất có citation → HR xem nguồn → HR chấp nhận/sửa/bỏ → tạo **task DRAFT** trong màn "Quản lý task" (P4B) → qua validation (P4C) → HR publish → nhân viên **mới thấy sau publish**, không thấy thẳng từ đề xuất AI | HR chọn 1 tài liệu → AI ra đề xuất → HR duyệt tạo draft → publish → nhân viên demo thấy task đó | P4B, P4C, retrieval của chatbot ổn định (nên có số liệu Recall@5 trước khi bật) |
| **P7** | Viga theo ngữ cảnh task | Tích hợp Viga vào context task (`task_id`, ngày/giai đoạn, trạng thái thật) theo §8 ke-hoach; phạm vi đúng như §1.1 (UI vẫn tự hiển thị "việc tiếp theo"/"lý do khóa"; nếu người dùng hỏi Viga thì Viga lấy cùng kết quả từ backend rồi diễn đạt lại, không tự suy luận); Viga không tự suy trạng thái từ link ngoài (§4.5); **bổ sung luồng Viga chuẩn bị ticket draft và yêu cầu người dùng xác nhận trước khi gửi** (nối vào ticket API đã có ở P5); ghi log câu hỏi không trả lời được để HR xem | Hỏi Viga trong 1 task với câu hỏi tự do/ngoại lệ → trả lời đúng theo tiến độ cá nhân, gợi ý ticket khi cần (có xác nhận), không bịa | P3, P5 |
| **P8** | Admin UI | Chỉ còn phần **giao diện** quản lý user/team/role/audit — RBAC/scope backend đã làm ở P1 | Admin tạo được user, gán role, xem audit log qua UI | P1 |
| **P9** | Pilot 1 đơn vị | Rollout theo §24 v14: pilot employee roadmap + ticket + AI-đề-xuất-task + Viga ở 1 đơn vị, đo B0/B1/B2; **Admin UI (P8) không chặn pilot** — chỉ cần thiết khi có nhiều user hơn quản lý được bằng seed/CLI | Số liệu thật đầu tiên, danh sách gap để sửa | P0B, P3, P4A, P4B, P4C, P5, P6, P7 |

**Thứ tự ưu tiên nếu thiếu thời gian:** P0A→P1→P3 là lõi bắt buộc (nhân viên dùng được, có RBAC từ đầu); P4A→P4C→P5 để HR vận hành không cần thao tác thủ công qua DB; P6 (AI đề xuất task) làm trước P7 (Viga) theo thứ tự đã chốt; P8 (Admin UI) có thể lùi sau P9 nếu cần pilot sớm.

## 6. Rủi ro cần theo dõi

- **Trùng backend với chatbot**: thêm module vào modular monolith có thể làm phình codebase — theo dõi ranh giới module (`journey/`, `ticket/` tách thư mục riêng trong cùng service) để dễ tách ra sau nếu cần.
- **Dữ liệu thật chưa có**: P0 chưa xong thì P1 chỉ chạy trên seed giả lập — không đưa dữ liệu HR thật lên demo cho tới khi được duyệt (giữ nguyên nguyên tắc ở [master-plan.md §5](../master-plan.md#5-quyết-định-kỹ-thuật-và-hạ-tầng-đã-chốt)).
- **AI đề xuất task (P6)** phụ thuộc chất lượng retrieval hiện tại của chatbot — nếu Recall@5 chưa đo, nên đo trước hoặc song song khi làm P6, tham khảo [bao-cao-mentor-vsf-onboarding-v5.docx](../../bao-cao-mentor-vsf-onboarding-v5.docx) mục 2.3 ưu tiên 3.
- **Quản lý tài liệu (P4A) không chỉ là "nối lại ingest đã có"**: cần thêm usage-mapping (task nào đang dùng tài liệu nào), delete-guard, và review-gate trước khi tài liệu được Viga/AI dùng — đây là phần mới cho Portal, không có sẵn ở chatbot.

## 7. Câu hỏi với mentor — chia theo mức độ chặn (không gộp chung một danh sách "không chặn")

Danh sách gốc ở [dac-ta-tong-the-portal-onboarding-v14.md §25](../portal/dac-ta-tong-the-portal-onboarding-v14.md#25-điểm-cần-xác-nhận-trước-production). Một số câu hỏi **thực sự chặn** thiết kế state machine/schema, không thể để "hỏi sau":

**Chặn domain/schema — nên có câu trả lời (dù tạm) trước P0A/P1, vì đổi sau sẽ phải sửa migration/state machine:**
- Journey đang chạy (EmployeeJourney) có nhận cập nhật khi template publish version mới không, hay giữ snapshot cố định?
- Task có được đánh dấu `NOT_APPLICABLE` theo điều kiện nào (địa điểm, loại máy)?
- Ticket được gán cho HR cụ thể hay cho cả nhóm/team?
- Khi ticket đóng, task tự thoát `BLOCKED` hay phải HR chủ động đổi trạng thái?

(Đã bỏ câu hỏi về HR duyệt task và minh chứng — quyết định mới: mọi task chỉ có 1 cách hoàn thành là nhân viên tự bấm "Hoàn thành", không có `HR_APPROVAL`/`EVIDENCE_REQUIRED` — xem mục 3.)
- Nguyên tắc retention/soft-delete (xem mục 8) — ảnh hưởng schema ngay từ đầu, không thể để hoàn toàn sau.

**Cần trước pilot (P9), không chặn code trước đó:**
- Bộ phận/đơn vị nào pilot đầu tiên; có tài liệu Ngày 1 thật chưa (= P0B).
- Identity provider và dữ liệu nhân sự nguồn (nếu SSO thật).

**Có thể quyết định sau, không ảnh hưởng kiến trúc:**
- Số ngày retention chính xác, legal hold cụ thể.
- Cấu hình tích hợp/notification channel cụ thể.

Có thể bắt đầu code skeleton (P1) song song, nhưng **không khóa migration production hoặc làm đầy đủ P2–P5** trước khi nhóm câu hỏi "chặn domain/schema" có câu trả lời.

## 8. Retention và xóa dữ liệu — chốt nguyên tắc từ P0A, không lùi hết về "sau"

Số ngày retention chính xác có thể quyết định sau, nhưng **nguyên tắc** phải chốt trước P1 vì ảnh hưởng trực tiếp foreign key và schema:
- Đối tượng nào chỉ cho **soft delete** (vd: `employee_tasks`, `tickets` — cần giữ lịch sử onboarding) và đối tượng nào cho **hard delete** (vd: draft chưa publish).
- Đối tượng nào **bất biến** sau khi publish (JourneyTemplate version, giống nguyên tắc "publish tạo version bất biến" đã có).
- Xóa `document` có xóa luôn file gốc trên object storage không, hay chỉ đánh dấu ngừng dùng (vì task cũ có thể vẫn trỏ tới version đó).
- Audit log có bao giờ bị xóa không (khuyến nghị: không, giữ bất biến như audit của chatbot — §21 v14).
- Xóa `user` (nhân viên nghỉ việc) thì `employee_journeys`/`employee_tasks`/`tickets` liên quan xử lý ra sao (soft-delete + ẩn khỏi UI, không xóa cứng).

## 9. Observability và vận hành — gắn vào từng phase, không tách phase riêng

Không cần một phase riêng, nhưng phải làm kèm khi build các phase tương ứng, nếu không P9 (pilot) sẽ không có cách debug khi lỗi:
- **P1**: rate limit theo user/role (tái dùng cơ chế đã có ở chatbot cho Viga — §4.2 v5.docx: 100 câu/5 phút/người); feature flag cho AI task generation (P6) và Viga (P7) để tắt nhanh nếu có sự cố.
- **P4A**: metrics/log cho ingest job Portal (trạng thái, lỗi, thời gian) — tái dùng dashboard/telemetry đã có ở chatbot nếu được; retry/dead-letter cho job ingest lỗi.
- **P6/P7**: correlation ID xuyên suốt UI → API → retrieval → LLM → ticket (để trace 1 câu hỏi Viga hoặc 1 lần AI đề xuất từ đầu tới cuối); log latency/token/chi phí LLM giống cơ chế Langfuse đã dùng ở chatbot (§21 v14).
- **Trước P9 (pilot)**: có backup/restore cho các bảng Portal mới; có quy trình rollback/forward-fix migration nếu P1 phát hiện lỗi schema sau khi đã có dữ liệu thật.
