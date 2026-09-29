# Kế hoạch: Portal Onboarding VSF (checklist + lộ trình + trợ lý dẫn đường)

> Trạng thái: bản nháp v3, để thống nhất scope với anh Đinh Minh Trí. Chưa dùng làm đặc tả code cho đến khi các câu hỏi ở mục 14 được chốt và PRD được cập nhật (mục 13).
> Quy ước: "ứng viên" hoặc "cần xác nhận" là thông tin chưa được chủ sở hữu duyệt, không được hiển thị cho nhân viên cho đến khi HR/content owner publish.

## 1. Bối cảnh và mục tiêu

Theo trao đổi với anh Trí (24/09): anh Huy muốn có chatbot, nhưng chatbot là hướng "để tiện scale sau này"; **phần portal thì hợp lý nên cứ build**. Anh Trí yêu cầu thống nhất scope trước: user là ai/phòng ban nào, lộ trình gồm gì, dữ liệu hiển thị ra sao, chat khi scale thì input/output/data thế nào.

**Mục tiêu:** nhân viên chính thức mới của khối KD & VH Vinmec tự biết hôm nay/tuần này phải làm gì, theo thứ tự nào, hỏi ai, mà không phải chờ mentor chỉ từng bước.

**Chatbot** tên **Viga** (Vin Intelligent Guidance Assistant) là **trợ lý dẫn đường** chạy trên tiến độ từng người, không phải hỏi đáp tài liệu tự do (mục 8). Portal quyết định lộ trình; chatbot giảm công sức hiểu quy trình và đưa người dùng tới hành động hợp lệ kế tiếp.

**Phạm vi MVP:**
- Có: nhân viên chính thức khối KD&VH Vinmec; nội dung Ngày 1–Tuần 1 (các stage sau chỉ là chỗ dành sẵn trong mô hình); checklist có xác nhận hoàn thành; chatbot dẫn đường cho hai chuỗi giá trị cao (mục 8.4); mentor xem tiến độ; HR/content owner biên tập và publish nội dung; nhắc việc **trong portal**.
- Không: thực tập sinh và cộng tác viên, các khối khác, SSO thật, gửi nhắc qua email/Teams, tích hợp ITSM/HRIS, **đọc/tải/nhúng nội dung từ link ngoài** (mục 4.5), **mở rộng corpus RAG** (giữ nguyên năng lực RAG hiện có).

## 2. Vai trò

| Vai trò | Là ai | Quyền chính |
|---|---|---|
| EMPLOYEE (persona chính) | CBNV chính thức mới của khối, đã biết chỗ ngồi và mentor | Xem lộ trình, làm task, nộp minh chứng, báo kẹt, hỏi chatbot |
| MENTOR | Người kèm nhân viên | Xem tiến độ và task kẹt của người phụ trách; nhắc trong portal; duyệt task loại OWNER_APPROVAL nếu được gán |
| CONTENT_OWNER (HR/phòng ban) | Chủ sở hữu nội dung nghiệp vụ | Soạn, duyệt, publish JourneyTemplate; nhập và duyệt liên hệ/link tham chiếu |
| ADMIN | Quản trị kỹ thuật | Quản lý tài khoản và vai trò, cấu hình hệ thống; không tự sửa nội dung nghiệp vụ |

Intern chỉ vận hành demo khi được cấp quyền tạm thời và có thời hạn; đó không phải một vai trò của hệ thống.

Vì sao chỉ nhân viên chính thức: tài liệu Ngày 1 viết cho CBNV mới (đào tạo hội nhập bắt buộc, ký hợp đồng lao động, lý lịch tư pháp, giấy khám sức khỏe, faceid). Thực tập sinh có thể không đi đúng các bước này. Template theo **loại nhân sự** nên thêm loại mới chỉ cần thêm lộ trình.

## 3. Vấn đề và baseline

**Hiện tại:** email onboard + tài liệu dài + mentor chỉ từng bước. Hệ quả: chờ mentor, bỏ sót hạng mục, làm sai thứ tự (ví dụ điền form VinSOC trước khi có phê duyệt T3), hỏi lặp lại.

**Giá trị portal:** một nơi duy nhất cho lộ trình; thứ tự phụ thuộc được hệ thống kiểm tra; đầu mối và mẫu email có sẵn; mentor thấy trạng thái mà không phải hỏi lại.

## 4. Mô hình dữ liệu

### 4.1 Tách template và instance

| Lớp | Thực thể | Ghi chú |
|---|---|---|
| Template (do CONTENT_OWNER soạn) | JourneyTemplate → TemplateStage → TaskTemplate | Có version. Publish tạo version bất biến |
| Instance (theo từng người) | EmployeeJourney → EmployeeTask | Tạo bằng **snapshot** từ một version template khi nhân viên bắt đầu |

Quy tắc:
- Publish version mới **không** thay đổi EmployeeJourney đang chạy.
- CONTENT_OWNER chủ động chọn cho từng journey: giữ nguyên, hoặc migrate (chỉ áp dụng cho task chưa bắt đầu; task đã DONE giữ nguyên).
- Khi publish, hệ thống chặn: dependency vòng tròn, task tiên quyết không tồn tại, liên hệ/link tham chiếu chưa được duyệt, task không có điều kiện hoàn thành.

### 4.2 TaskTemplate
- Tiêu đề, mô tả, lý do phải làm, lỗi hay gặp, ước lượng thời gian, hạn tương đối (ví dụ "trong ngày 1").
- `completion_type` (mục 5.1) và cấu hình minh chứng nếu có.
- `prerequisites`: danh sách task tiên quyết.
- `applies_when`: điều kiện áp dụng (địa điểm làm việc, loại máy Windows/Ubuntu).
- `contact_code`, `link_code` (tham chiếu, mục 4.3), `template_codes` (mẫu văn bản có biến: họ tên, mã NV).
- `required`: bắt buộc hay không.

### 4.3 Liên hệ và link theo mã tham chiếu
Task không chứa email, tên, tầng hay URL trực tiếp. Task chỉ chứa mã; giá trị nằm trong bảng do CONTENT_OWNER quản lý và duyệt:

| Mã | Ý nghĩa | Giá trị ứng viên (chưa xác minh) |
|---|---|---|
| `ITHD_SUPPORT` | Hộp thư hỗ trợ ITHD | support@vinsmartfuture.tech (có trong tài liệu intern cung cấp) |
| `ITHD_QUICK_ACCESS` | Trang xem nhu cầu có Quick access không | URL helpdesk trong tài liệu, cần xác nhận |
| `VINSOC_SECURITY_FORM` | Form yêu cầu ANBM VinSOC | link trong tài liệu, cần xác nhận |
| `VINMEC_T3_APPROVER` | Người phê duyệt T3 của khối | anh Dương Anh Nghi, cần xác nhận |
| `TRAINING_CONTACT` | Đầu mối đào tạo hội nhập | Phòng ĐT&PTVH, cần xác nhận |
| `LOCKER_REQUESTER` | Người xử lý yêu cầu tủ gửi đồ của khối | mã trong tài liệu, cần xác nhận |
| `ITHD_TICKET_OWNER` | Người tạo ticket ITHD của khối | mã trong tài liệu, cần xác nhận |

Mã nhân sự thật (như trong tài liệu gốc) chỉ được nhập vào bảng này sau khi HR xác nhận. Mỗi bản ghi có trạng thái DRAFT → APPROVED; chỉ APPROVED mới hiển thị.

### 4.4 EmployeeTask và hồ sơ
- Hồ sơ: loại nhân sự, khối, địa điểm, loại máy, mentor, ngày bắt đầu.
- EmployeeTask: trạng thái (mục 5.2), minh chứng, ghi chú, người duyệt, thời điểm từng chuyển trạng thái (audit log).

### 4.5 Nguyên tắc về link: chỉ tham chiếu, không đọc nội dung
Portal và chatbot **không** truy cập, tải, trích xuất, nhúng (iframe) hay tóm tắt nội dung phía sau bất kỳ link nào (helpdesk, form VinSOC, VinGro, Teams, email...). Link chỉ là một tham chiếu kèm **mô tả do content owner viết**: "link này dùng để làm gì, khi nào dùng, cần chuẩn bị gì".
- Mỗi link có: `link_code`, tiêu đề, mô tả mục đích, khi nào dùng, việc cần chuẩn bị, trạng thái DRAFT/APPROVED. Link mở ở tab mới.
- Chatbot chỉ biết mô tả trong bảng; nó không biết form có những trường nào, ticket đang ở trạng thái gì, hay trang đó hiện gì.
- Hệ quả cho hoàn thành: vì portal không nhìn thấy kết quả trong hệ thống ngoài, việc làm ở hệ thống ngoài phải được xác nhận bằng **minh chứng do người dùng nhập** (ví dụ mã ticket, ảnh chụp) hoặc **owner duyệt**, không tự suy ra từ link.
- Chatbot không được nói những điều chỉ có thể biết bằng cách mở link ("form của bạn đã được duyệt"); khi thiếu thông tin thì hướng dẫn người dùng tự kiểm tra ở đó.

## 5. Hoàn thành và trạng thái

### 5.1 Ba loại xác nhận hoàn thành
| Loại | Cách hoàn thành | Ví dụ |
|---|---|---|
| `SELF_CONFIRM` | Người dùng tự xác nhận | Đọc nội quy, chọn ảnh đại diện |
| `EVIDENCE_REQUIRED` | Phải nhập kết quả hoặc gửi minh chứng | Nhập mã ticket đã tạo; ảnh chụp đã đăng nhập Outlook/Teams |
| `OWNER_APPROVAL` | HR/task owner/mentor duyệt | Đào tạo hội nhập đạt ≥ 80%, ký hợp đồng, nộp đủ hồ sơ |

Nguyên tắc: **AI chỉ sơ kiểm minh chứng (gợi ý đủ/thiếu); rule hoặc owner mới chốt.** Task nhạy cảm (hồ sơ nhân sự, hợp đồng, quyền truy cập) không bao giờ do AI tự duyệt.

### 5.2 State machine của EmployeeTask
| Trạng thái | Ý nghĩa |
|---|---|
| `NOT_APPLICABLE` | Không áp dụng cho người này (khác địa điểm/loại máy) |
| `LOCKED` | Chưa đủ tiên quyết |
| `READY` | Đủ tiên quyết, chưa bắt đầu |
| `IN_PROGRESS` | Đang làm |
| `WAITING_EXTERNAL` | Đã gửi đi và chờ bên ngoài phản hồi (email T3, phản hồi VinSOC) |
| `WAITING_APPROVAL` | Đã nộp minh chứng, chờ owner duyệt |
| `BLOCKED` | Kẹt, có lý do và người cần hỗ trợ |
| `DONE` | Hoàn thành hợp lệ theo `completion_type` |
| `SKIPPED` | Bỏ qua có lý do (chỉ khi `required = false` hoặc owner cho phép) |

Chuyển trạng thái hợp lệ (rút gọn):
`LOCKED → READY` (khi mọi tiên quyết `DONE`) → `IN_PROGRESS` → `WAITING_EXTERNAL` hoặc `WAITING_APPROVAL` → `DONE`; `BLOCKED` vào/ra từ `IN_PROGRESS`, `WAITING_*`. Mọi chuyển trạng thái do **backend** kiểm tra; frontend không tự đổi status.

## 6. Ví dụ dữ liệu Ngày 1 (đầu vào seed, cần HR duyệt)

| # | Task | Loại | Đầu mối (mã) | Tiên quyết / ghi chú |
|---|---|---|---|---|
| 1 | Nộp hồ sơ: CV, lý lịch tư pháp (hoặc giấy hẹn), giấy khám sức khỏe, xác nhận nơi cư trú (VNeID mức 2 được), CCCD photo, chứng chỉ chuyên môn bắt buộc | OWNER_APPROVAL | Phòng tuyển dụng | |
| 2 | Check-in địa điểm làm việc | SELF_CONFIRM | theo nơi onboard | |
| 3 | Đào tạo hội nhập. Xong khi: điểm danh đầu giờ + khảo sát sau khóa + test cuối khóa ≥ 80% | OWNER_APPROVAL | `TRAINING_CONTACT` | Bắt buộc |
| 4 | Ký hợp đồng lao động theo email hướng dẫn cuối ngày | OWNER_APPROVAL | HR | Ký trong thời hạn quy định |
| 5 | Đăng ký faceid chấm công (tầng 14) và faceid ra vào tòa nhà | EVIDENCE_REQUIRED | Phòng nhân sự | Chỉ khi làm ở Vincom Đồng Khởi; faceid tòa nhà chờ email |
| 6 | Nhận laptop tầng 12; đăng nhập được Outlook và Teams | EVIDENCE_REQUIRED | ITHD + HR | **Cổng chặn**: task 7, 8, 9 cần task này |
| 7 | Ảnh đại diện, chữ ký, slide | SELF_CONFIRM | email onboard | Cần task 6 |
| 8 | Xem Quick access, viết ticket ITHD theo mẫu khi cần | EVIDENCE_REQUIRED (mã ticket) | `ITHD_SUPPORT` | Cần task 6 |
| 9 | Yêu cầu tủ gửi đồ | SELF_CONFIRM | `LOCKER_REQUESTER` | |

## 7. Luồng nghiệp vụ

- **F1. Đăng nhập và vào lộ trình:** đăng nhập → landing theo vai trò → "Hôm nay / Tuần này", % hoàn thành, task kế tiếp. Đổi mật khẩu lần đầu là **việc phải làm thêm** (hiện project chưa có API/UI đổi mật khẩu); nếu chưa kịp thì dùng mật khẩu do admin cấp cho demo.
- **F2. Làm task:** mở task → đọc hướng dẫn, đầu mối, mẫu → thực hiện → nộp theo `completion_type` → backend kiểm tra → mở khóa task phụ thuộc.
- **F3. Ticket ITHD:** xem Quick access trước; nếu cần thì dùng mẫu email gửi `ITHD_SUPPORT`, tiêu đề `ITHD [Địa điểm] + [yêu cầu]`, nội dung theo mẫu, biến họ tên tự điền.
- **F4. Yêu cầu ngoại lệ** (đổi Ubuntu, webmail, VPN, USB/Internet, Firewall, PAM, ZTNA, WAF, Cloud/Wiz):
  1. Xin phê duyệt T3 (`VINMEC_T3_APPROVER`) bằng email `Xin phê duyệt [nội dung] - [họ tên] - [mã NV]` → `WAITING_EXTERNAL`.
  2. Điền form `VINSOC_SECURITY_FORM`, đính email phê duyệt đủ luồng Thẩm định/Phê duyệt theo CNPQ. Máy đã có Ubuntu sẵn có thể duyệt qua Teams kèm ảnh chụp → `WAITING_EXTERNAL`.
  3. Chờ email phản hồi VinSOC.
  4. Tạo ticket ITHD (`ITHD_TICKET_OWNER`) và thực hiện tại phòng ITHD tầng 14.
- **F5. Mentor:** xem danh sách người phụ trách, task `BLOCKED`/`WAITING_*` quá lâu; nhắc **trong portal** (không email/Teams); duyệt task OWNER_APPROVAL được gán.
- **F6. Content owner:** soạn template, duyệt liên hệ/link, publish version, chọn migrate hay giữ nguyên journey đang chạy.
- **F7. Báo cáo:** tiến độ theo người/khối, bước hay kẹt (nguồn cho metric).
- **F8. Chat dẫn đường:** mục 8.

## 8. Viga: trợ lý dẫn đường (chatbot)

Tên trợ lý: **Viga** (Vin Intelligent Guidance Assistant).

### 8.1 Phân vai code và LLM
| Việc | Ai làm |
|---|---|
| Kiểm tra tiên quyết, thứ tự, điều kiện hoàn thành, quyền | **Code** (backend) |
| Ánh xạ câu hỏi sang task/flow | LLM |
| Diễn đạt, điền mẫu | LLM + template |
| Hỏi đáp tài liệu dài (nội quy) | RAG hiện có, không mở rộng corpus trong MVP |
| Đọc nội dung sau link ngoài | **Không ai làm** (mục 4.5); chỉ dùng mô tả link do owner viết |

### 8.2 Luồng xử lý một câu hỏi
1. User hỏi (ví dụ "Em muốn đổi máy sang Ubuntu").
2. LLM ánh xạ sang task/flow (ở đây F4).
3. Code lấy tiên quyết và đối chiếu tiến độ user.
4. Thiếu tiên quyết → trả `PREREQUISITE_REQUIRED` kèm task cần làm trước.
5. Đủ tiên quyết → hướng dẫn bước kế tiếp kèm mẫu và đầu mối đã duyệt.
6. Không khớp task nào → nói chưa có trong lộ trình và chỉ đầu mối chung đã duyệt; không đoán.

### 8.3 Contract phản hồi
```json
{
  "response_type": "PREREQUISITE_REQUIRED",
  "message": "Bạn cần nhận laptop và đăng nhập Outlook/Teams trước.",
  "current_task_id": 25,
  "blocking_tasks": [{ "task_id": 18, "title": "Nhận laptop", "status": "READY" }],
  "suggested_actions": [
    { "type": "OPEN_TASK", "task_id": 18, "label": "Mở task Nhận laptop" }
  ],
  "sources": []
}
```
- `response_type`: `PREREQUISITE_REQUIRED`, `NEXT_STEP`, `INFO`, `NOT_IN_JOURNEY`.
- Action tối thiểu: `OPEN_TASK`, `START_TASK`, `SUBMIT_EVIDENCE`, `COPY_TEMPLATE`, `REPORT_BLOCKER`, `OPEN_APPROVED_LINK`.
- Khi user bấm action, **backend kiểm tra lại quyền và trạng thái**; frontend không tự đổi status.
- Chỉ trả liên hệ/link có trạng thái APPROVED.

### 8.4 Chatbot đáng làm ở đâu
Xếp theo (tần suất hỏi × chi phí sai × độ dài chuỗi):
1. **Cao nhất:** luồng ngoại lệ F4 (chuỗi 4 bước, dễ sai thứ tự).
2. **Cao:** chuỗi laptop → Outlook/Teams → ticket ITHD.
3. **Trung bình:** nhắc hạn ký hợp đồng và đào tạo hội nhập (nhắc bằng rule trong portal, không cần LLM).
4. **Thấp:** faceid, tủ gửi đồ, ảnh đại diện; checklist là đủ.

MVP chỉ đầu tư chatbot vào hai chuỗi đầu.

## 9. Thiết kế checklist

1. Mặc định chỉ hiện 1–3 việc kế tiếp; danh sách đầy đủ ở trang riêng.
2. Xếp theo đường găng: việc nghẽn nhiều thứ phía sau lên trước (nhận laptop, đăng nhập Outlook/Teams).
3. Bắt đầu sớm việc có thời gian chờ (`WAITING_EXTERNAL`). Thời gian chờ thực tế của phê duyệt và VinSOC cần HR xác nhận.
4. Ẩn việc `NOT_APPLICABLE` theo địa điểm và loại máy.
5. Mỗi task có đủ: vì sao phải làm, khi nào coi là xong, đầu mối, mẫu copy, lỗi hay gặp.
6. Nhắc trong portal: hạn ký hợp đồng, đào tạo hội nhập chưa đạt, task chờ quá lâu.
7. Cho phép báo kẹt kèm lý do để mentor thấy.

## 10. Metric

North-star: **tỷ lệ task hoàn thành đúng thứ tự và đúng điều kiện mà không cần hỏi trực tiếp mentor/HR.**

| Nhóm | Metric |
|---|---|
| Tốc độ | Thời gian hoàn tất checklist Ngày 1 và Tuần 1 |
| Phụ thuộc mentor | Số lần hỏi mentor/HR trong tuần đầu; thời gian mentor phải hỗ trợ |
| Chất lượng | Số task bị bỏ sót hoặc làm sai thứ tự; số lần bị trả lại ticket/form |
| Đúng hạn | Tỷ lệ task bắt buộc hoàn thành đúng hạn |
| Trải nghiệm | Hài lòng (1–5); "biết tuần này cần làm gì" (có/không) |
| Chatbot | Tỷ lệ chọn đúng prerequisite/next task trên bộ câu hỏi mẫu; số lần chặn được làm sai thứ tự |
| Vận hành | Thời gian content owner cập nhật một thay đổi quy trình |

Chỉ tiêu số (target) **chưa đặt**; chốt với anh Trí sau khi có baseline. Đề xuất cách đo:
- Baseline: phỏng vấn 3–5 nhân viên mới gần đây.
- Usability/task test: 5–10 người (có thể dùng người mô phỏng nếu thiếu nhân viên mới).
- 2–3 người dùng thật chỉ gọi là **mini-pilot định tính**, không dùng để tuyên bố tác động.

Ràng buộc cứng (không phải target đo lường, là điều kiện chấp nhận):
- 0 task nhạy cảm do AI tự duyệt.
- 0 liên hệ/link chưa APPROVED được hiển thị.
- 0 lần portal hoặc AI tải, nhúng hay suy diễn nội dung phía sau link ngoài; chatbot chỉ dùng mô tả link do owner viết.
- Mọi chuyển trạng thái đều do backend kiểm tra và ghi audit log.

Lưu ý: "đào tạo đạt ≥ 80%" là điều kiện nghiệp vụ của nhân viên, không phải metric đánh giá portal.

## 11. Tái sử dụng cái đã có

- Hạ tầng đang chạy: AWS + Vercel, CI/CD, auth (scrypt + cookie phiên), i18n vi/en, landing/login (`frontend/src/features/`).
- Backend: FastAPI + Postgres + Alembic (thêm migration cho template/instance/tiến độ), CLI `create_user`.
- Chat/RAG hiện có (hybrid search, guardrail, validator trích dẫn): giữ; dùng cho hỏi đáp tài liệu dài.
- Ralion (`D:\Intern-VSF\P-040`) làm tham khảo: `features/member-onboarding` (Checklist, TaskDetail, Journey, Blockers), `features/admin-console`, UI primitives `Pm*`, `features/auth/routing.ts` (đổi mật khẩu, chuyển trang theo vai trò). Không copy file `.env`.

## 12. Phase (chatbot đi sớm bằng vertical slice)

| Phase | Nội dung | Kết quả |
|---|---|---|
| 0 | Chốt scope với anh Trí (mục 14); cập nhật PRD (mục 13); HR xác nhận nội dung và liên hệ | Scope được duyệt. **Không code trước bước này** |
| 1 | Wireframe và luồng UI cho nhân viên, mentor, content owner | Anh Trí duyệt |
| 2 | **Vertical slice**: đăng nhập → task Nhận laptop → task Outlook/Teams bị `LOCKED` → hỏi chatbot về Ubuntu → phát hiện thiếu tiên quyết → mở đúng task → hoàn thành hợp lệ → task kế tiếp mở khóa | Chứng minh sớm giá trị "giảm phụ thuộc mentor" |
| 3 | Mở rộng nhân viên: đủ Ngày 1–Tuần 1, đủ loại xác nhận và state machine | Nhân viên dùng được toàn bộ |
| 4 | Content owner: template, version, snapshot, kiểm tra dependency vòng, duyệt liên hệ/link | HR tự soạn và publish |
| 5 | Mentor view, nhắc trong portal, báo cáo | Có số đo |
| 6 | Chatbot chuỗi F4 đầy đủ và bộ câu hỏi mẫu | Kiểm tra tiên quyết ổn định |
| 7 | Đo baseline so với portal; mini-pilot; demo nghiệm thu | Báo cáo giá trị |

## 13. Thay đổi so với PRD hiện hành

PRD chuẩn `docs/chatbot-vsf/vsf-onboarding-assistant-prd.md` (dòng 15, 80, 211) xếp checklist cá nhân, nhắc việc và theo dõi tiến độ vào giai đoạn sau, ngoài MVP. Kế hoạch này đảo ngược điều đó theo chỉ đạo của anh Trí và anh Huy.

Cần làm trước khi code:
- Cập nhật PRD: đưa portal + checklist vào MVP, chuyển hỏi đáp tài liệu tự do xuống giai đoạn sau.
- Cập nhật thiết kế DB (hiện có 10 thực thể và invariant INV1–INV23) để bổ sung template/instance/tiến độ.
- Ghi lại quyết định bằng một ADR ngắn để tránh hai nguồn yêu cầu mâu thuẫn.

## 14. Câu hỏi cần chốt với anh Trí

1. Phạm vi user: chỉ khối KD&VH Vinmec hay nhiều khối?
2. MVP chỉ nhân viên chính thức? Thực tập sinh và cộng tác viên đi cùng checklist hay lộ trình riêng sau?
3. Mỗi tháng khối có bao nhiêu nhân viên chính thức mới (để biết đo metric có đủ mẫu không)?
4. Lộ trình dài bao lâu (Ngày 1, tuần 1, hay 30/60/90 ngày)? Có tài liệu sau Ngày 1 không?
5. Ai là content owner (HR hay mentor) và ai duyệt liên hệ/link?
6. Task nào cần xác nhận bởi owner (`OWNER_APPROVAL`) và ai là người duyệt?
7. Có cần mentor/quản lý xem tiến độ không, và xem đến mức nào?
8. Có cần SSO/Outlook thật hay tài khoản riêng đủ cho demo?
9. Chỉ tiêu thành công anh Huy kỳ vọng là gì?
10. Nội dung có nhạy cảm cần đặt portal trong mạng nội bộ không (hiện chạy trên AWS/Vercel ngoài)?
11. Chat khi scale: input, output, dữ liệu mong muốn là gì? (đề xuất ở mục 8)

## 15. Rủi ro

- Nội dung và liên hệ lỗi thời nhanh; giảm bằng mã tham chiếu, trạng thái duyệt và version.
- Dữ liệu nội bộ (đầu mối, quy trình bảo mật) đặt trên hạ tầng ngoài; cần anh Trí xác nhận được phép.
- HR xác nhận nội dung chậm sẽ chặn tiến độ; cần chốt người và thời hạn ở phase 0.
- Chưa có baseline thật nên chưa chứng minh được cải thiện; chỉ tuyên bố tác động khi đo đủ mẫu.
- Vì không đọc được nội dung link, portal không tự biết việc ở hệ thống ngoài đã xong chưa; phụ thuộc vào minh chứng người dùng nhập hoặc owner duyệt, nên có thể chậm hoặc bị khai sai.
- Chatbot sai thứ tự làm mất niềm tin; vì vậy tiên quyết do code kiểm tra, AI không chốt hoàn thành.
- Chi phí AWS chạy 24/7 khoảng $75–80/tháng, credit dự kiến hết khoảng giữa tháng 11/2026 (theo báo cáo hạ tầng); cần chốt kế hoạch giảm chi phí.

## 16. Kiểm chứng

- Anh Trí duyệt scope và wireframe trước khi build.
- Backend (pytest): state machine, mở khóa tiên quyết, chặn dependency vòng khi publish, snapshot không bị đổi khi publish version mới, quyền theo vai trò.
- Frontend (Vitest) và e2e: đăng nhập → làm task → task kế tiếp mở khóa; chatbot trả `PREREQUISITE_REQUIRED` khi thiếu tiên quyết và action `OPEN_TASK` mở đúng task.
- Bộ câu hỏi mẫu cho chuỗi Ubuntu và chuỗi laptop/ITHD, gồm cả ca thiếu tiên quyết và ca không khớp task.
- Kiểm tra: không hiển thị liên hệ/link chưa APPROVED; không task nhạy cảm nào được AI tự duyệt.

## 17. Prototype giao diện

[prototype-ui-flow.html](prototype-ui-flow.html): một file HTML độc lập, mở trực tiếp bằng trình duyệt, dữ liệu giả lập, không kết nối hệ thống.

**Icon và avatar:** icon dùng bộ Lucide (ISC), nhúng sẵn nên chạy được khi không có mạng. Mọi tiêu đề trang, tiêu đề thẻ và tiêu đề mục đều có icon nền dịu. Link có icon theo loại (trang hỗ trợ, biểu mẫu bảo mật, tài liệu nội bộ). Người dùng (nhân viên, mentor, HR, thành viên) có avatar hoạt hình cùng phong cách với Viga, gồm 6 kiểu nam và 6 kiểu nữ; bản mẫu chọn theo chữ cái đầu của tên, sản phẩm thật cho người dùng tự chọn. Phòng ban dùng icon tòa nhà thay vì avatar người.

**Bố cục:** mỗi trang có chân trang; bảng có hàng đầu và hàng chân khác màu; ba dashboard có banner chào kèm avatar.

**Phong cách:** phẳng, viền mảnh, mọi thẻ/nút/ô nhập bo 5px, màu dịu (một màu xanh thương hiệu, trạng thái dùng sắc độ của cùng một màu). Màu biểu đồ đã chạy kiểm tra bằng validate_palette (ordinal xanh 3 bậc sáng/tối, categorical 3 slot). Biểu đồ vẽ bằng SVG thuần, có tooltip, chú giải, và nút "Xem bảng". Các bảng có icon đầu dòng (tài liệu, thành viên, task, link) và phân trang.

**Nhân viên**
- Tổng quan (dashboard): 4 chỉ số (một số lớn duy nhất là tiến độ tuần đầu), 3 biểu đồ (trạng thái việc theo ngày, khối lượng giờ theo ngày, số việc theo cách xác nhận), việc ưu tiên kế tiếp, hoạt động gần đây, đầu mối nhanh.
- Nhiệm vụ: cây ở thanh bên và tab trang chính đều theo **ngày** (Ngày 1, Ngày 2, Ngày 3–5, Khi cần) nên khớp nhau. Mỗi ngày có mục tiêu, tiến độ, danh sách "Làm ngay" đánh số theo thứ tự nên làm, "Đang chờ", "Chưa mở khóa", "Đã xong", "Việc tồn từ ngày trước". Có nút giả lập hôm nay là Ngày 1/2/3–5. Nội dung Ngày 2 trở đi là bản mẫu (gắn nhãn "Mẫu").
- Trang task: dải tóm tắt 5 ô (ở đâu, khi nào, ai hỗ trợ, thời lượng, kết quả), hướng dẫn từng bước dạng stepper, checklist chuẩn bị, xử lý sự cố, câu hỏi thường gặp, tài liệu, đầu mối, mô tả link, mẫu email. Cột phải: trạng thái (tiến trình dọc) và hành động, "Sau task này", lịch sử.
- Tài liệu có hai loại: **Đính kèm task** (gắn với một việc, cũng hiện ở trang task đó) và **Đọc thêm** (tài liệu tham khảo, không thuộc task nào). Bảng có tìm kiếm, lọc theo loại và nhóm, icon, phân trang.
- Trang task có mục **Trao đổi với mentor**: bình luận hai chiều theo từng task.
- Viga có avatar nhân vật hoạt hình phong cách văn phòng (áo vest navy, tai nghe xanh thương hiệu) và nút "Hỏi Viga" ở header. Sau khi đã hỏi, gợi ý câu hỏi được ẩn (còn link "Gợi ý câu hỏi"). Màn hình giải thích nêu Viga hỏi được gì, không làm gì, input, xử lý, output kèm ví dụ thật.
- Thông báo.

**Mentor:** tổng quan (4 chỉ số, biểu đồ tiến độ từng nhân viên, biểu đồ nhân viên theo ngày, danh sách cần chú ý, trao đổi gần đây), danh sách nhân viên (tìm kiếm, lọc, phân trang, nút "Nhắn" để nhắc việc hoặc bình luận), hàng chờ duyệt, và trang **Trao đổi** để trả lời bình luận của nhân viên theo từng task.

**HR / content owner:** tổng quan (4 chỉ số, biểu đồ số task theo ngày và cách xác nhận, thời gian hoàn thành trung bình (dữ liệu mẫu), lịch sử phiên bản), lộ trình mẫu (kiểm tra trước publish, bảng task), liên hệ và link.

Nội dung hướng dẫn, dữ liệu nhân viên khác, số liệu biểu đồ HR và tài liệu là bản minh họa; tên, đầu mối, link và ngày chỉ là mẫu. HR cần thay bằng nội dung chính thức trước khi dùng thật.
