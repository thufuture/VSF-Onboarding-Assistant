# PRD v2 — VSF Onboarding Assistant

> **ĐÃ THAY THẾ — chỉ giữ làm tham khảo lịch sử.** Bản chuẩn hiện hành là `vsf-onboarding-assistant-prd.md` (6 loại phản hồi, ticket nội bộ tối thiểu thuộc MVP, quy trình/link/đầu mối/form có cấu trúc). Không dùng tài liệu này làm nguồn đặc tả.

> Bản cập nhật sau khi mentor (Đinh Minh Trí) góp ý: bỏ mô hình phân quyền theo bộ phận/nhóm nhân sự, vì tài liệu onboarding về cơ bản là công khai nội bộ và dùng chung cho tất cả mọi người. Bản v1 (`vsf-onboarding-assistant-prd.md`) giữ nguyên làm tham khảo lịch sử thiết kế.

## 0. Tóm tắt

VSF Onboarding Assistant là chatbot AI hỗ trợ nhân sự mới tra cứu quy trình onboarding và các chính sách liên quan, dựa trên **một kho tài liệu chung, công khai nội bộ, dùng như nhau cho tất cả mọi người** — không phân quyền theo bộ phận hay nhóm nhân sự.

MVP tập trung làm **chatbot hỏi đáp chuẩn**:

- Trả lời có trích dẫn từ tài liệu còn hiệu lực.
- Với câu hỏi trông có vẻ cần thông tin cá nhân (vị trí ngồi, mentor là ai, cách xin cấp phần mềm...) nhưng thực ra có quy trình chung để tự tìm/tự thực hiện — bot hướng dẫn đúng quy trình đó, không bịa ra câu trả lời cá nhân.
- Từ chối khi câu hỏi ngoài phạm vi hoặc không đủ căn cứ.

Checklist, nhắc việc và theo dõi tiến độ cá nhân là giai đoạn tiếp theo, chỉ thực hiện sau khi chất lượng hỏi đáp của chatbot được chứng minh.

## 1. Bài toán

### 1.1 Thông tin phân tán và khó kiểm chứng

Tài liệu onboarding/chính sách nằm rải rác trong email, PDF, Word, biểu mẫu, Drive hoặc kho nội bộ. Nhân sự mới khó biết cần đọc tài liệu nào, file nào đang có hiệu lực. Hệ quả là người mới phải hỏi HR/đồng nghiệp, mất thời gian chờ, có thể làm theo hướng dẫn cũ; HR cũng phải trả lời lặp lại các câu hỏi có thể tra cứu từ tài liệu.

### 1.2 Câu hỏi trông như cần dữ liệu cá nhân nhưng thực ra có quy trình chung

Nhiều câu hỏi của người mới nghe qua tưởng cần dữ liệu cá nhân (vị trí ngồi, mentor là ai, làm sao xin cấp phần mềm) nhưng thực chất công ty đã có quy trình chung để tự tìm ra câu trả lời đó. Nếu bot không phân biệt được, sẽ xảy ra 1 trong 2 lỗi:

- **Bịa câu trả lời cá nhân** — ví dụ tự đoán vị trí ngồi hoặc tên mentor dù không có căn cứ.
- **Từ chối luôn cả những câu có thể hướng dẫn được** — làm giảm giá trị chatbot, vì phần lớn câu hỏi "trông cá nhân" thực ra đều có quy trình chung để trả lời.

### 1.3 Ba loại câu hỏi thực tế

**Loại 1 — trả lời trực tiếp được (nội dung giống nhau cho tất cả):**

> **Người dùng:** Bộ phận Vinmec thì cài hệ điều hành gì?
> **Bot:** Theo hướng dẫn cài đặt máy đang có hiệu lực, bộ phận Vinmec dùng Ubuntu.
> *Nguồn: Hướng dẫn cài đặt máy, mục …, phiên bản đang có hiệu lực.*

**Loại 2 — trông như cá nhân, nhưng có quy trình chung để tự tìm/tự thực hiện:**

> **Người dùng:** Ngày mai tôi ngồi vị trí nào?
> **Bot:** Tôi không có thông tin vị trí ngồi cụ thể của bạn. Theo hướng dẫn ngày đầu, bạn liên hệ lễ tân tại sảnh chính hoặc kiểm tra email xác nhận chỗ ngồi được gửi trước ngày làm việc đầu tiên.
> *Nguồn: Hướng dẫn ngày đầu, mục …, phiên bản đang có hiệu lực.*

> **Người dùng:** Mentor của tôi là ai?
> **Bot:** Tôi không có thông tin phân công mentor cụ thể. Theo quy trình onboarding, bạn có thể xem trong email chào mừng hoặc hỏi quản lý trực tiếp để biết mentor được phân công.
> *Nguồn: Quy trình onboarding, mục …, phiên bản đang có hiệu lực.*

> **Người dùng:** Tôi cần cài phần mềm X thì làm sao?
> **Bot:** Bạn cần tạo yêu cầu gửi bộ phận VinSOC để được quét và duyệt link cài đặt trước khi dùng. Tôi có thể chuẩn bị sẵn mẫu yêu cầu — bạn xác nhận nội dung rồi tôi gửi giúp.
> *Nguồn: Quy trình cấp phần mềm, mục …, phiên bản đang có hiệu lực.*
>
> **Người dùng:** Có, gửi giúp tôi.
> **Bot:** Yêu cầu đã được tạo, mã `IT-XXXX`, gửi tới bộ phận VinSOC.

**Loại 3 — ngoài phạm vi, từ chối thẳng:**

> **Người dùng:** Viết code giúp tôi.
> **Bot:** Câu hỏi này ngoài phạm vi hỗ trợ của tôi (chỉ hỗ trợ onboarding và chính sách nội bộ VSF).

## 2. Mục tiêu và đối tượng

### 2.1 Mục tiêu MVP

- Giúp người mới tự tra cứu câu hỏi onboarding phổ biến, kể cả câu hỏi trông có vẻ cá nhân.
- Giảm câu hỏi lặp lại gửi tới HR/IT.
- Mọi câu trả lời nghiệp vụ có nguồn kiểm chứng.
- Không bịa thông tin cá nhân; có quy trình tạo ticket rõ ràng khi cần hành động thật.

### 2.2 Đối tượng sử dụng

Tất cả nhân sự mới tại VSF — **không phân biệt bộ phận hay loại hợp đồng ở giai đoạn MVP**, vì tài liệu và quy trình onboarding được coi là dùng chung.

| Đối tượng | Nhu cầu chính |
|---|---|
| Nhân sự mới (mọi bộ phận, mọi loại hợp đồng) | Ngày đầu, chính sách chung, quy trình xin hỗ trợ/cấp phát khi cần. |
| HR/IT/content owner | Quản lý tài liệu và tiếp nhận ticket được tạo từ chatbot. |

## 3. Mô hình tài liệu

- **Một kho tài liệu chung duy nhất**, công khai nội bộ, không chia theo bộ phận hay nhóm nhân sự.
- Tài liệu vẫn cần quản lý **phiên bản và hiệu lực** (bản cũ hết hạn không được dùng để trả lời) — đây là vấn đề "đúng bản mới nhất", tách biệt hoàn toàn với việc "ai được xem", nên vẫn giữ nguyên yêu cầu này từ bản v1.
- Nội dung tài liệu chia theo **2 dạng dùng để định tuyến câu trả lời** (không phải để phân quyền):
  - **Nội dung trả lời trực tiếp** — chính sách, quy định, văn hoá công ty, hướng dẫn kỹ thuật chung.
  - **Nội dung mô tả quy trình tự tra cứu/thực hiện** — hướng dẫn cách tìm ra thông tin mang tính cá nhân (tìm chỗ ngồi, tìm mentor, xin cấp phần mềm...), bao gồm cả mẫu ticket/form nếu quy trình đó cần tạo yêu cầu.

## 4. Phạm vi MVP

### Trong phạm vi

- Chat nhiều lượt bằng tiếng Việt, trên một kho tài liệu chung duy nhất.
- Quản lý tài liệu, metadata, phiên bản và hiệu lực (không có trường phân quyền theo bộ phận/nhóm nhân sự).
- 3 loại phản hồi: trả lời trực tiếp có trích dẫn / hướng dẫn quy trình tự tra cứu-thực hiện / từ chối ngoài phạm vi.
- Tạo ticket tối thiểu khi quy trình cần một hành động thật (ví dụ xin cấp phần mềm), sau khi người dùng xác nhận nội dung.

### Ngoài phạm vi MVP

- Phân quyền tài liệu theo bộ phận/nhóm nhân sự (`visibility`/`applicability`).
- Checklist, nhắc việc và theo dõi tiến độ cá nhân — xem mục 14.
- Portal tiến độ cho HR/manager.
- Tích hợp HRIS, SSO, chấm công hoặc bảng lương.
- Tự động duyệt hồ sơ, cấp quyền hoặc sửa dữ liệu nhân sự.
- Tích hợp Teams, Slack, Zalo hoặc email notification.

## 5. Luồng và yêu cầu chức năng

```text
Nhận câu hỏi → Phân loại (trả lời trực tiếp | hướng dẫn quy trình | ngoài phạm vi)
→ Tìm bằng chứng trong kho tài liệu chung → Sinh và kiểm tra
→ Trả lời | Hướng dẫn quy trình (có thể kèm tạo ticket) | Từ chối
```

Ba loại phản hồi: `ANSWER` (bao gồm cả trả lời trực tiếp và hướng dẫn quy trình — cả hai đều là nội dung có trích dẫn, khác nhau ở việc có kèm bước tạo ticket hay không), `ESCALATION` (khi quy trình cần tạo yêu cầu thật), `REFUSAL_OUT_OF_SCOPE`.

| ID | Yêu cầu |
|---|---|
| FR-01 | Bot phân loại câu hỏi thuộc 1 trong 3 loại (mục 1.3) trước khi trả lời; không tự suy đoán thông tin cá nhân. |
| FR-02 | HR/content owner quản lý tài liệu mà không sửa mã nguồn. |
| FR-03 | Tài liệu có phiên bản và ngày hiệu lực; chỉ bản đang hiệu lực được dùng để trả lời. |
| FR-04 | Câu trả lời nghiệp vụ có tên nguồn, mục/trang, phiên bản và hiệu lực nếu có. |
| FR-05 | Thiếu căn cứ hoặc nguồn mâu thuẫn thì từ chối, không bịa nội dung. |
| FR-06 | Với câu hỏi loại 2 (mục 1.3), bot trả lời bằng quy trình tự tra cứu/thực hiện, không bịa kết quả cá nhân. |
| FR-07 | Khi quy trình cần tạo yêu cầu thật (ví dụ xin cấp phần mềm), bot soạn nội dung yêu cầu, chỉ gửi sau khi người dùng xác nhận. |
| FR-08 | Thay đổi tài liệu có audit log. |

## 6. Quy tắc tài liệu

Metadata tối thiểu: `title`, `category`, `version`, `status`, `effective_from`, `effective_to`, `owner`, `response_type` (`direct` | `procedure`).

```text
Upload → Kiểm tra → PENDING_REVIEW → Owner duyệt → ACTIVE → ARCHIVED/version mới
```

- Không sửa đè phiên bản đã kích hoạt; khi version mới ACTIVE thì version cũ tự động chuyển ARCHIVED (đúng 1 bản ACTIVE tại một thời điểm cho mỗi tài liệu).
- Chỉ tài liệu `ACTIVE` và còn hiệu lực được dùng.
- Trích dẫn được dựng từ nguồn đã truy xuất, không lấy từ nội dung LLM tự tạo.

## 7. Khi nào tạo ticket

| Trường hợp | Ví dụ | Xử lý |
|---|---|---|
| Ngoài miền sản phẩm | "Viết code giúp tôi." | Từ chối, không tạo ticket. |
| Thiếu tài liệu | "Tháng đầu có được làm ở nhà không?" | Nói thiếu căn cứ; đề nghị gửi HR/content owner bổ sung. |
| Quy trình cần hành động thật | "Tôi cần cài phần mềm X." | Soạn nội dung yêu cầu, hiển thị bản nháp, chỉ gửi sau khi xác nhận. |
| Khiếu nại/nhạy cảm | "Tôi muốn phản ánh vấn đề." | Tạo yêu cầu riêng tư cho HR được phân quyền. |
| Nguồn mâu thuẫn | Hai tài liệu active hướng dẫn khác nhau. | Không tự chọn; chuyển content owner. |

## 8. Kịch bản demo hoàn chỉnh

**Minh:** Bộ phận Vinmec thì cài hệ điều hành gì?
**Bot:** Theo hướng dẫn cài đặt máy đang có hiệu lực, bộ phận Vinmec dùng Ubuntu.
*Nguồn: Hướng dẫn cài đặt máy, mục 2, phiên bản đang có hiệu lực.*

**Minh:** Vậy tôi cài phần mềm giám sát nội bộ sao cho đúng quy trình?
**Bot:** Bạn cần gửi yêu cầu tới bộ phận VinSOC để link cài đặt được quét và duyệt trước khi dùng. Tôi soạn sẵn nội dung yêu cầu, bạn xác nhận gửi chứ?

**Minh:** Có.
**Bot:** Yêu cầu đã được tạo, mã `IT-0042`, gửi tới bộ phận VinSOC.

**Minh:** Ngày mai tôi ngồi vị trí nào?
**Bot:** Tôi không có thông tin vị trí ngồi cụ thể của bạn. Theo hướng dẫn ngày đầu, bạn liên hệ lễ tân tại sảnh chính hoặc kiểm tra email xác nhận chỗ ngồi.
*Nguồn: Hướng dẫn ngày đầu, mục 4, phiên bản đang có hiệu lực.*

## 9. Dữ liệu cần chuẩn bị

1. Tài liệu onboarding chung còn hiệu lực (giới thiệu công ty, văn hoá, nội quy, phúc lợi).
2. Tài liệu mô tả các quy trình tự tra cứu/thực hiện thường gặp nhất (tìm chỗ ngồi, tìm mentor, xin cấp phần mềm/thiết bị, các đầu mối liên hệ hỗ trợ chung).
3. Danh sách HR/IT/content owner tiếp nhận ticket.
4. 60–100 câu hỏi đánh giá có câu trả lời, nguồn và loại phản hồi chuẩn (bao phủ cả 3 loại ở mục 1.3).
5. 5–10 người dùng pilot và ít nhất một content owner nghiệm thu.

```text
Kiểm kê → Loại trùng/bản cũ → Xác nhận owner và hiệu lực
→ Gắn metadata/phiên bản → Che dữ liệu nhạy cảm → Duyệt → Nhập hệ thống
```

## 10. Kế hoạch MVP — 4 tuần

### Chuẩn bị (2–3 ngày)

Thu 10–20 tài liệu chung + quy trình tự tra cứu phổ biến; 20–30 câu hỏi thật cho cả 3 loại.

### Tuần 1 — Chat có nguồn

Làm sạch dữ liệu; xây nhập liệu, tìm kiếm và giao diện chat; trả lời có trích dẫn và từ chối khi thiếu nguồn.

### Tuần 2 — Phân loại đúng 3 nhóm câu hỏi

Phân loại câu hỏi trực tiếp / quy trình / ngoài phạm vi; quản lý phiên bản và hiệu lực; xây 40–60 câu đánh giá.

### Tuần 3 — Ticket và quản trị tối thiểu

Cho HR/content owner quản lý tài liệu; hoàn thiện luồng tạo ticket (soạn nội dung, xác nhận, gửi); mở rộng lên 60–100 câu đánh giá.

### Tuần 4 — Đánh giá và pilot

Khóa dữ liệu; đo baseline; kiểm thử prompt injection và câu hỏi ngoài phạm vi; pilot 5–10 người và sửa lỗi.

## 11. Baseline, benchmark và chỉ số

| Mã | Phương án |
|---|---|
| B0 | Người dùng tự tìm trong thư mục. |
| B1 | Tìm kiếm từ khóa. |
| B2 | Vector RAG chưa phân loại 3 nhóm câu hỏi. |
| Proposed | Hybrid RAG có phân loại câu hỏi, evidence gate và trích dẫn. |

| Chỉ số | Mục tiêu |
|---|---:|
| Recall@5 | ≥ 85% |
| Faithfulness | ≥ 90% |
| Citation đúng tài liệu | ≥ 95% |
| Route accuracy (đúng 1 trong 3 loại) | ≥ 95% |
| Trả lời không có căn cứ | 0 case |
| Bịa thông tin cá nhân (vị trí, mentor...) | 0 case |
| Dùng tài liệu hết hiệu lực | 0 case |
| False refusal rate | ≤ 10% |
| P90 latency | ≤ 10 giây |
| Đánh giá hữu ích trong pilot | ≥ 80% |

Các số trên là mục tiêu cần kiểm chứng, chưa phải kết quả đã đạt.

## 12. Rủi ro chính

| Rủi ro | Ví dụ | Kiểm soát |
|---|---|---|
| Tài liệu trùng/thiếu owner | "final" và "final-new". | Kiểm kê và duyệt trước khi nhập. |
| Thiếu tài liệu mô tả quy trình cá nhân | Chưa ai viết "cách tìm mentor" thành văn bản. | Ưu tiên thu thập nhóm này ngay từ tuần chuẩn bị — đây là phần dễ thiếu nhất vì trước giờ chỉ truyền miệng. |
| Nhầm loại 1 và loại 2 | Bot trả lời thẳng vị trí ngồi dù không có căn cứ. | Route accuracy là chỉ số bắt buộc đo riêng, không gộp chung với các lỗi khác. |
| Parse sai PDF/DOCX | Bảng mất tên cột. | Quality gate và review trước kích hoạt. |
| Tiếng Việt nội bộ | "nv thu viec nop hs gi". | Chuẩn hóa, alias và hybrid search. |
| AI thêm thông tin | Nguồn không có nhưng bot tự tạo. | Chỉ sinh từ bằng chứng và kiểm tra đầu ra. |

Khó nhất không phải giao diện chat mà là **thu thập đủ tài liệu mô tả quy trình cá nhân (vốn trước giờ chỉ truyền miệng) và chứng minh bot phân loại đúng 3 nhóm câu hỏi**.

## 13. Tiêu chí hoàn thành MVP

1. Mọi câu trả lời nghiệp vụ có trích dẫn kiểm chứng được.
2. Phân loại đúng câu hỏi trả lời trực tiếp / hướng dẫn quy trình / ngoài phạm vi.
3. Không bịa thông tin cá nhân (vị trí, mentor, trạng thái hồ sơ...).
4. Quy trình cần hành động thật luôn tạo ticket sau khi người dùng xác nhận, không tự gửi.
5. HR/content owner quản lý tài liệu và phiên bản mà không sửa mã nguồn.
6. Đạt ngưỡng chỉ số ở mục 11 trên bộ kiểm thử.

## 14. Hướng mở rộng

Sau khi chatbot đạt tiêu chí MVP:

- **Checklist dùng chung 1 template** cho tất cả (không cần nhiều bản theo bộ phận, vì lộ trình onboarding được coi là giống nhau) — chỉ **tiến độ** (task nào đã làm/chưa) là lưu riêng theo từng người, vì đây là trạng thái cá nhân chứ không phải nội dung tài liệu cần phân quyền.
- Câu hỏi "Hôm nay tôi cần làm gì?", nhắc việc, theo dõi blocker.
- Portal HR/manager xem tiến độ tổng hợp.
- Tích hợp HRIS và kênh thông báo — lúc đó mới cần xét lại việc có cần phân quyền tài liệu theo bộ phận hay không, nếu phạm vi mở rộng ra nhiều công ty con/bộ phận có nội dung thực sự khác biệt.
