# PRD — VSF Onboarding Assistant

> Bản định hướng MVP. Ví dụ về Vinmec, Ubuntu, VinSOC, địa điểm, đầu mối và biểu mẫu bên dưới là **giả định để mô phỏng**, không phải thông tin/chính sách VSF đã được xác nhận. Chỉ đưa vào chatbot sau khi có tài liệu và owner phê duyệt.

## 0. Tóm tắt

VSF Onboarding Assistant là chatbot AI giúp người mới biết **cần làm gì, theo quy trình nào và liên hệ ai** trong quá trình onboarding. Lộ trình và các bước chung được áp dụng thống nhất; bot dùng tài liệu đã duyệt để giải thích quy trình, không tự đoán thông tin cá nhân hoặc thực hiện thay bộ phận phụ trách.

MVP tập trung vào ba năng lực:

- **Hỏi đáp có nguồn:** trả lời về lộ trình chung, chính sách, hướng dẫn ngày đầu và đầu mối hỗ trợ.
- **Điều hướng đúng bước:** với việc cần xác minh hoặc xử lý bởi người thật, bot đưa quy trình, kênh liên hệ, biểu mẫu và bước tiếp theo thay vì bịa câu trả lời.
- **Chuyển yêu cầu có chọn lọc:** chỉ đề nghị tạo ticket khi đúng quy trình và thực sự cần người xử lý; câu hỏi ngoài miền sản phẩm thì từ chối ngắn gọn, không tạo ticket.

MVP thu thập và xác minh dữ liệu từ **một bộ phận pilot** nhưng mô hình nội dung có thể mở rộng sang các bộ phận khác. Checklist tự động, nhắc việc và theo dõi tiến độ cá nhân để giai đoạn sau.

## 1. Bài toán

### 1.1 Vấn đề 1 — Biết quy trình chung nhưng khó tìm đúng bước tiếp theo

Người mới thường không biết tài liệu ở đâu, bản nào còn hiệu lực, việc nào tự thực hiện được và việc nào phải qua HR, IT hoặc đầu mối khác. Một câu hỏi thực tế thường cần cả **thông tin** lẫn **hướng hành động**.

> **Người mới:** “Ngày mai đi làm tôi đến đâu, cần làm gì trước?”  
> **Khó khăn:** Thông tin nằm rải rác trong thư nhận việc, hướng dẫn tiếp nhận và danh bạ đầu mối. Nếu thiếu lịch cá nhân, bot không thể tự xác định một địa chỉ/giờ cụ thể.

### 1.2 Vấn đề 2 — Câu hỏi cá nhân hoặc tác vụ hỗ trợ không có đáp án trong tài liệu chung

Tài liệu chung có thể mô tả **cách tìm chỗ ngồi, mentor hoặc cách yêu cầu cài máy**, nhưng không nhất thiết chứa vị trí, tên mentor hay trạng thái xử lý của từng người. Nếu trả lời trực tiếp bằng suy đoán, bot dễ hướng dẫn sai; nếu chỉ nói “không biết”, người dùng vẫn không biết phải làm gì.

> **Người mới:** “Mai tôi ngồi chỗ nào?”  
> **Bot sai:** “Bạn ngồi bàn A12.”  
> **Bot đúng:** “Tôi không có sơ đồ phân chỗ cá nhân. Bạn kiểm tra thư tiếp nhận/lịch ngày đầu; nếu chưa có, liên hệ đầu mối tiếp nhận theo hướng dẫn này. Khi tới nơi, báo tên và bộ phận tại quầy tiếp nhận.”

### 1.3 Phát biểu bài toán

> Làm thế nào để người mới nhận được câu trả lời đáng tin cậy về onboarding chung và luôn biết **bước tiếp theo hợp lệ**, kể cả khi bot không có dữ liệu cá nhân hoặc không được phép thực hiện tác vụ thay con người?

Hệ thống phải phân biệt rõ: **trả lời từ tài liệu**, **hướng dẫn theo quy trình**, **chuyển người phụ trách**, và **từ chối câu hỏi không liên quan**.

## 2. Đối tượng và mô hình nội dung

### 2.1 Đối tượng sử dụng

- **Người mới:** hỏi về ngày đầu, quy trình, chính sách, thiết bị/tài khoản và đầu mối hỗ trợ.
- **HR/Content owner:** duyệt tài liệu, duy trì quy trình và biểu mẫu.
- **Bộ phận xử lý:** tiếp nhận ticket hoặc yêu cầu được chuyển đến đúng hàng đợi.

Không chia ba lộ trình riêng cho thực tập sinh, thử việc và chính thức trong MVP. Nếu một chính sách thật sự có điều kiện áp dụng khác nhau, bot nêu điều kiện từ tài liệu đã duyệt hoặc hỏi thêm thông tin cần thiết; không tự suy ra quyền lợi cá nhân.

### 2.2 Tài liệu dùng chung, hướng dẫn theo ngữ cảnh

Tài liệu onboarding được quản lý trong một kho chung. Có hai dạng nội dung:

1. **Quy trình/chính sách chung:** mọi người cùng tra cứu một nguồn và cùng các bước cơ bản.
2. **Hướng dẫn có điều kiện:** một bước chung nhưng chi tiết phụ thuộc địa điểm, bộ phận hoặc loại yêu cầu; bot chỉ chọn nhánh khi điều kiện được người dùng cung cấp hoặc có trong hồ sơ đáng tin cậy.

Ví dụ giả định: tài liệu IT đã duyệt ghi “nhân sự thuộc đơn vị X dùng Ubuntu”. Khi người dùng cho biết mình thuộc đơn vị X, bot có thể trả lời **thiết bị dự kiến dùng Ubuntu** và trích nguồn. Nhưng câu “cài Ubuntu thế nào?” phải theo quy trình cấp phát/cấu hình thiết bị nếu tài liệu quy định IT thực hiện; bot không tự đưa các bước cài đặt ngoài hướng dẫn được duyệt.

**MVP không xây ACL/phân quyền tài liệu theo từng bộ phận.** Nội dung được đưa vào kho chat phải được owner xác nhận là có thể hiển thị cho toàn bộ người dùng pilot. Tài liệu hạn chế, bí mật hoặc chứa dữ liệu cá nhân không được nhập vào kho này. Bộ phận là **ngữ cảnh chọn hướng dẫn**, không phải khóa cấp quyền.

## 3. Phạm vi MVP

### Trong phạm vi

- Chat nhiều lượt bằng tiếng Việt, hiểu câu hỏi viết tắt/không dấu phổ biến.
- Tra cứu lộ trình onboarding chung, chính sách liên quan, hướng dẫn ngày đầu và danh bạ đầu mối đã duyệt.
- Chọn nhánh hướng dẫn theo thông tin đáng tin cậy hoặc hỏi lại khi thiếu ngữ cảnh.
- Trả lời có nguồn, phiên bản và ngày hiệu lực khi tài liệu cung cấp.
- Hướng dẫn người dùng tự tìm thông tin cá nhân qua kênh chính thức.
- Hiển thị link, biểu mẫu, danh sách thông tin cần chuẩn bị và bước tiếp theo khi quy trình yêu cầu.
- Tạo ticket tối thiểu **chỉ khi quy trình đã duyệt quy định cần ticket**, sau khi người dùng xác nhận nội dung.
- Giao diện quản lý tài liệu, đầu mối, liên kết, biểu mẫu và phiên bản ở mức tối thiểu.

### Ngoài phạm vi

- Tự đọc HRIS, sơ đồ chỗ ngồi, phân công mentor hoặc trạng thái hồ sơ cá nhân.
- Tự cài hệ điều hành/phần mềm, cấp tài khoản, phê duyệt hoặc thay đổi dữ liệu nhân sự.
- Tự mở liên kết chưa được xác minh hoặc khẳng định liên kết “an toàn” khi chưa có bằng chứng kiểm duyệt.
- ACL tài liệu chi tiết theo từng bộ phận/người dùng.
- Checklist cá nhân, nhắc việc, theo dõi tiến độ và portal quản lý tiến độ.
- Mở rộng đầy đủ cho mọi bộ phận trước khi pilot đạt tiêu chí nghiệm thu.

## 4. Hợp đồng phản hồi của chatbot

| Loại phản hồi | Khi nào dùng | Bot phải cung cấp |
|---|---|---|
| `ANSWER` | Có nguồn đủ căn cứ cho câu hỏi chung. | Câu trả lời ngắn, điều kiện áp dụng, trích dẫn và hiệu lực. |
| `GUIDE_PROCESS` | Cần thực hiện một quy trình nhưng bot không thực hiện thay. | Các bước được duyệt, đầu mối/kênh, link/form chính thức và bước tiếp theo. |
| `ASK_CLARIFICATION` | Thiếu địa điểm/bộ phận/loại thiết bị để chọn nhánh. | Một câu hỏi làm rõ cần thiết; không đoán. |
| `OFFER_TICKET` | Quy trình yêu cầu người phụ trách xử lý qua ticket. | Lý do, hàng đợi nhận, bản nháp form và yêu cầu xác nhận. |
| `NO_BASIS` | Thiếu hoặc mâu thuẫn tài liệu. | Nói rõ chưa xác minh được; chỉ kênh xác minh phù hợp nếu đã có nguồn. |
| `OUT_OF_SCOPE` | Câu hỏi không liên quan onboarding/chính sách/hỗ trợ nội bộ. | Từ chối ngắn; không hỏi tạo ticket. |

Không phải mọi câu không trả lời được đều tạo ticket. Nếu tài liệu chỉ hướng dẫn gọi hotline hoặc liên hệ đầu mối thì bot đưa kênh đó; không tự tạo ticket. Nếu không có quy trình chuyển tiếp đáng tin cậy, bot nói rõ chưa biết kênh chính xác và đề nghị kiểm tra với HR, không bịa email hoặc link.

## 5. Kịch bản hội thoại mẫu

### 5.1 Thiết bị: trả lời điều kiện, sau đó điều hướng quy trình

> **Giả định để demo:** tài liệu IT được duyệt xác nhận đơn vị Vinmec dùng Ubuntu; quy trình cài máy yêu cầu liên hệ IT qua ticket; bộ phận VinSOC kiểm tra và công bố liên kết cài đặt. Tên đơn vị, hệ điều hành và quy trình thực tế cần VSF xác nhận.

**Người mới:** Tôi thuộc Vinmec, máy công ty dùng hệ điều hành gì?  
**Bot:** Theo hướng dẫn thiết bị đang áp dụng cho đơn vị này, máy được cấu hình Ubuntu. *Nguồn: Hướng dẫn cấp phát thiết bị, mục …, phiên bản …, hiệu lực …* Nếu thiết bị của bạn khác hướng dẫn, hãy xác nhận với IT trước khi thay đổi.

**Người mới:** Vậy cài Ubuntu sao?  
**Bot:** Quy trình hiện hành yêu cầu IT cấu hình máy, nên bạn không nên tự cài. Bước tiếp theo: (1) mở form yêu cầu cấu hình thiết bị tại **[link đã được owner duyệt]**; (2) điền mã nhân viên, bộ phận, mã thiết bị và mô tả nhu cầu; (3) gửi vào hàng đợi IT; (4) chờ hướng dẫn và chỉ dùng link/tệp cài đặt được công bố qua kênh VinSOC/IT đã xác minh. Tôi có thể chuẩn bị nội dung ticket cho bạn. Bạn muốn xem bản nháp không?

**Người mới:** Có.  
**Bot:** Bản nháp gồm: “Yêu cầu cấu hình Ubuntu cho thiết bị [mã thiết bị]; bộ phận [đơn vị]; liên hệ [kênh được phép].” Bạn kiểm tra và xác nhận gửi. Tôi chưa gửi khi bạn chưa xác nhận.

### 5.2 Chỗ ngồi: không đoán vị trí, chỉ cách tìm

**Người mới:** Ngày mai tôi ngồi ở đâu?  
**Bot:** Tôi không có dữ liệu phân chỗ cá nhân nên không thể nói chính xác số bàn. Bạn hãy kiểm tra thư tiếp nhận/lịch ngày đầu; nếu chưa có thông tin, liên hệ đầu mối tiếp nhận được ghi trong **[hướng dẫn ngày đầu đã duyệt]**. Khi đến nơi, báo tên và bộ phận tại quầy tiếp nhận để được dẫn tới vị trí. Nếu hướng dẫn chính thức có form yêu cầu hỗ trợ chỗ ngồi, tôi sẽ cung cấp form đó.

### 5.3 Mentor: hướng dẫn tra cứu, không bịa tên

**Người mới:** Mentor của tôi là ai?  
**Bot:** Tôi chưa có danh sách phân công mentor cá nhân. Bạn kiểm tra thư giới thiệu đội/nhóm hoặc kênh phân công đã nêu trong hướng dẫn onboarding. Nếu chưa được phân công, liên hệ đầu mối bộ phận theo **[danh bạ đã duyệt]**. Nếu quy trình yêu cầu mở ticket để xác nhận mentor, tôi có thể chuẩn bị form; nếu chỉ cần hỏi đầu mối thì không tạo ticket.

### 5.4 Ngoài phạm vi: từ chối, không tạo ticket

**Người mới:** Dự báo thời tiết cuối tuần?  
**Bot:** Tôi chỉ hỗ trợ thông tin onboarding và quy trình nội bộ liên quan. Câu hỏi này không thuộc phạm vi hỗ trợ.

## 6. Quy tắc tài liệu và liên kết

Mỗi tài liệu tối thiểu có: `title`, `owner`, `version`, `status`, `effective_from`, `effective_to`, `topic`, `conditions`, `approved_links`. Mỗi quy trình có thêm: `trigger`, `steps`, `responsible_team`, `contact_channel`, `ticket_required`, `form_fields`, `next_step`.

```text
Thu thập → Owner xác nhận nội dung/điều kiện/đầu mối/link
→ Kiểm tra bản mới và bảo mật → Duyệt → ACTIVE
→ Theo dõi thay đổi → ARCHIVED hoặc phiên bản mới
```

- Chỉ tài liệu `ACTIVE` và còn hiệu lực được dùng để trả lời.
- Link chỉ hiển thị nếu thuộc danh mục đã được owner xác nhận; nếu quy trình yêu cầu VinSOC quét/duyệt, phải có trạng thái duyệt trước khi công bố.
- Không suy diễn rằng một link an toàn chỉ vì nó xuất hiện trong cuộc chat hoặc tài liệu chưa duyệt.
- Trích dẫn lấy từ tài liệu hệ thống, không để LLM tự tạo tên nguồn, ngày hiệu lực hoặc đường dẫn.

## 7. Yêu cầu chức năng

| ID | Yêu cầu |
|---|---|
| FR-01 | Bot tra cứu tài liệu onboarding chung và trả lời có trích dẫn. |
| FR-02 | Bot hỏi làm rõ khi thiếu điều kiện để chọn nhánh quy trình. |
| FR-03 | Bot không tự khẳng định chỗ ngồi, mentor, hồ sơ, hợp đồng hoặc thiết bị cá nhân nếu không có nguồn hợp lệ. |
| FR-04 | Với việc cần xử lý, bot chỉ đúng bộ phận, kênh, form và bước tiếp theo từ quy trình đã duyệt. |
| FR-05 | Ticket chỉ được đề nghị khi `ticket_required=true` hoặc có quy trình chuyển tiếp được phê duyệt. |
| FR-06 | Bot hiển thị bản nháp và chỉ gửi ticket sau khi người dùng xác nhận. |
| FR-07 | Câu không liên quan được từ chối ngắn, không đề nghị ticket. |
| FR-08 | HR/Owner cập nhật được tài liệu, đầu mối, link, form và phiên bản mà không sửa code. |
| FR-09 | Bot chỉ dùng link đã duyệt và không hướng dẫn thao tác IT trái quy trình. |

## 8. Dữ liệu cần chuẩn bị

1. Lộ trình và quy trình onboarding chung do VSF xác nhận.
2. Hướng dẫn ngày đầu, hồ sơ, chính sách và danh bạ đầu mối.
3. Danh sách tình huống cần HR/IT/VinSOC hoặc bộ phận khác xử lý.
4. Mẫu form/ticket thật: trường bắt buộc, hàng đợi nhận, trạng thái và phản hồi tiếp theo.
5. Danh mục link chính thức cùng owner, trạng thái kiểm tra và ngày xác nhận.
6. Các điều kiện rẽ nhánh thật theo bộ phận/địa điểm/thiết bị nếu có.
7. 80–120 câu hỏi thực tế, gồm câu trả lời được, cần điều hướng, cần hỏi rõ, cần ticket, thiếu căn cứ và ngoài phạm vi.

Không lấy ví dụ trong PRD làm dữ liệu vận hành nếu chưa được owner xác nhận. Với pilot, ưu tiên một bộ phận và một số quy trình hỗ trợ phổ biến trước; sau đó mới tăng độ phủ.

## 9. Timeline MVP — 4 tuần

| Giai đoạn | Việc chính | Kết quả |
|---|---|---|
| Chuẩn bị, 2–3 ngày | Chọn bộ phận pilot, owner; thu quy trình, form, link, câu hỏi thật. | Corpus và luồng hỗ trợ mẫu đã được xác nhận. |
| Tuần 1 | Xây chat, nhập tài liệu, tìm nguồn, câu trả lời có trích dẫn. | Trả lời câu hỏi chung và biết nói thiếu căn cứ. |
| Tuần 2 | Mô hình hóa quy trình, điều kiện rẽ nhánh và hỏi làm rõ. | Bot điều hướng đúng bước, không đoán dữ liệu cá nhân. |
| Tuần 3 | Form/ticket có xác nhận, quản lý link và phiên bản. | Kịch bản IT/HR chạy end-to-end với dữ liệu pilot. |
| Tuần 4 | Benchmark, kiểm thử link/ticket, pilot người dùng, sửa lỗi. | Báo cáo chất lượng và demo nghiệm thu. |

## 10. Baseline, benchmark và metric

| Baseline | Mô tả |
|---|---|
| B0 | Người dùng tự tìm trong tài liệu/kênh chat. |
| B1 | Tìm kiếm từ khóa trong tài liệu. |
| B2 | RAG chỉ trả lời nội dung, không điều hướng quy trình. |
| Proposed | RAG có nguồn + định tuyến quy trình + form/ticket có kiểm soát. |

| Chỉ số | Mục tiêu MVP |
|---|---:|
| Recall@5 trên câu có tài liệu | ≥ 85% |
| Câu trả lời có căn cứ và trích dẫn đúng | ≥ 90% |
| Chọn đúng loại phản hồi (`ANSWER`/`GUIDE_PROCESS`/...) | ≥ 95% |
| Chọn đúng đầu mối/form/ticket theo tài liệu | ≥ 95% |
| Tự bịa thông tin cá nhân, đầu mối hoặc link | 0 case trong bộ test |
| Ticket được gửi khi chưa xác nhận | 0 case |
| Đề nghị ticket cho câu ngoài phạm vi | 0 case |
| Link chưa duyệt được đưa cho người dùng | 0 case |
| Câu trả lời được người dùng pilot đánh giá hữu ích | ≥ 80% |

Đây là **mục tiêu**, chưa phải kết quả đã đo. Bộ đánh giá phải gồm cả câu hỏi nhiều lượt như “dùng hệ điều hành gì?” → “cài sao?”, và các câu dễ khiến bot đoán tên mentor/chỗ ngồi.

## 11. Tiêu chí hoàn thành MVP

1. Người mới hỏi được về lộ trình chung và nhận câu trả lời có nguồn.
2. Bot phân biệt được câu có đáp án, câu cần hướng dẫn quy trình, câu cần hỏi rõ, câu cần ticket và câu ngoài phạm vi.
3. Bot không khẳng định thông tin cá nhân khi không có nguồn; luôn đưa bước tiếp theo hữu ích nếu quy trình đã duyệt có hướng dẫn.
4. Ticket/form được định tuyến đúng và chỉ gửi sau khi người dùng xác nhận.
5. Link và tài liệu trả cho người dùng đều đã được owner duyệt, còn hiệu lực.
6. Pilot đạt ngưỡng chất lượng đã đặt và không có lỗi an toàn trong bộ kiểm thử.

## 12. Hướng mở rộng

Sau khi chất lượng chatbot và luồng hỗ trợ được chứng minh: mở rộng bộ phận, tăng số quy trình, tích hợp HRIS/ITSM nếu được cấp quyền, checklist cá nhân, nhắc việc và theo dõi tiến độ onboarding.
