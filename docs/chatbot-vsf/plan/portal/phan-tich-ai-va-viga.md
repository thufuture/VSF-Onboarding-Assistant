# Phân tích: áp dụng AI vào đâu, và Viga còn cần không

> Bản nháp để trao đổi với anh Trí. Chưa có số đo thật; các chỉ tiêu ghi "cần đo" sẽ chốt sau pilot.
> Minh họa: [prototype-ui-flow-v2-clean-ai.html](prototype-ui-flow-v2-clean-ai.html) (trang HR "Tạo bằng AI" và giao diện nhân viên đã gọn).
> Landing + Login (mô phỏng theo vsf-onboarding-assistant.vercel.app/vi và /vi/login, đổi nội dung cho Portal): mở [prototype-ui-flow-v15-shared-roadmap.html](prototype-ui-flow-v15-shared-roadmap.html) là vào thẳng trang chủ; bấm "Đăng nhập" hoặc mở `#gate=login` để vào trực tiếp màn đăng nhập.
> Bản v15 (roadmap "Tạo task bằng AI" dùng chung thiết kế với "Quản lý task": cùng khoảng cách card 158px, cùng node, cùng đường cong, không còn card bị cắt cạnh; card có 5 nút thao tác — chấp nhận, xem nguồn, sửa, nhân bản, xóa — chấp nhận và xóa đều có modal xác nhận): [prototype-ui-flow-v15-shared-roadmap.html](prototype-ui-flow-v15-shared-roadmap.html); đặc tả tổng thể: [dac-ta-tong-the-portal-onboarding-v14.md](dac-ta-tong-the-portal-onboarding-v14.md).
> Bản v12 (chỉ Viga đề xuất báo sự cố, không có nút báo trực tiếp): [prototype-ui-flow-v12-viga-bao-su-co.html](prototype-ui-flow-v12-viga-bao-su-co.html).
> Bản v11 (không duyệt, báo sự cố bằng ticket): [prototype-ui-flow-v11-ticket-su-co.html](prototype-ui-flow-v11-ticket-su-co.html); mô tả đầy đủ: [mo-ta-bai-toan-va-giao-dien.md](mo-ta-bai-toan-va-giao-dien.md).
> Bản v10 (roadmap ngang, con đường uốn lượn trái sang phải): [prototype-ui-flow-v10-roadmap-ngang.html](prototype-ui-flow-v10-roadmap-ngang.html).
> Bản v9 (roadmap nền sáng, chip ngày có tiến độ): [prototype-ui-flow-v9-roadmap-sang.html](prototype-ui-flow-v9-roadmap-sang.html).
> Bản v8 (roadmap uốn lượn, footer cố định, trang Theo dõi): [prototype-ui-flow-v8-roadmap.html](prototype-ui-flow-v8-roadmap.html).
> Bản v7 (roadmap, AI tạo task từ tài liệu): [prototype-ui-flow-v7-ai-ingest.html](prototype-ui-flow-v7-ai-ingest.html); tài liệu nguồn viết lại: [tai-lieu-ngay-1-viet-lai.md](tai-lieu-ngay-1-viet-lai.md).
> Bản Admin theo phòng ban (kiểu Ralion): [prototype-ui-flow-v6-hr-admin-phong-ban.html](prototype-ui-flow-v6-hr-admin-phong-ban.html).
> Bản 3 vai trò (Nhân viên, HR làm luôn việc mentor, Admin): [prototype-ui-flow-v5-hr-admin.html](prototype-ui-flow-v5-hr-admin.html).
> Bản Viga + HR quản lý (không AI soạn): [prototype-ui-flow-v4-viga-hr-crud.html](prototype-ui-flow-v4-viga-hr-crud.html); nội dung Viga: [viga-chatbot-muc-dich-du-lieu.md](viga-chatbot-muc-dich-du-lieu.md).
> Bản không dùng AI: [prototype-ui-flow-v3-no-ai.html](prototype-ui-flow-v3-no-ai.html) (HR quản lý task, tài liệu, liên hệ và link, phiên bản bằng bảng thêm, sửa, xóa; không Viga, không AI). Nên dùng bản này cho pilot; AI chỉ thêm khi có nhiều phòng ban.

## 1. Hai câu hỏi

1. Có nên dùng AI để **HR phòng ban dựng lộ trình onboarding** (kiểu Ralion: AI dựng "bản nháp", người duyệt) không, và có đáng so với làm tay không?
2. Đã có checklist rồi thì **còn cần chat Viga** không, và Viga để làm gì?

## 2. AI soạn lộ trình cho HR

**Vấn đề thật:** tài liệu onboard của phòng ban là văn bản rời (email, Word). Chuyển thành lộ trình có cấu trúc (task, tiên quyết, điều kiện hoàn thành, đầu mối, mẫu) là việc tốn công, dễ thiếu sót, và phải làm lại cho mỗi phòng ban. Đây đúng là bài toán "văn bản không cấu trúc → dữ liệu có cấu trúc" mà mô hình ngôn ngữ làm tốt.

**Có phù hợp không:** phù hợp có điều kiện.

| Điều kiện | Nhận định |
|---|---|
| Nhiều phòng ban hoặc nội dung đổi thường xuyên | AI có lợi rõ (bản nháp thay vì soạn từ đầu) |
| Chỉ một phòng ban, một tài liệu, ít đổi | Soạn tay có thể đã đủ nhanh; giá trị AI thấp |
| Tài liệu nguồn thiếu chi tiết | AI không tự bịa được phần thiếu; nó chỉ nên hỏi lại HR |

Kết luận: đây là tính năng **giúp scale**, hợp với định hướng anh Trí ("chatbot để tiện scale sau này"). Không nên coi là điều kiện để chạy pilot Ngày 1.

**Giá trị so với baseline (chưa đo, cần đo):**

| Chỉ số | Baseline (làm tay) | Có AI hỗ trợ | Cách đo |
|---|---|---|---|
| Thời gian dựng lộ trình từ tài liệu sẵn có | HR tự đọc, tách, gán tiên quyết | AI dựng nháp, HR review | Phút mỗi lộ trình, so 2–3 lần làm tay gần nhất |
| Độ đầy đủ mỗi task | Dễ thiếu điều kiện hoàn thành, tiên quyết | Kiểm tra tự động, AI hỏi lại chỗ thiếu | % task đủ trường bắt buộc khi publish |
| Chất lượng bản nháp AI | - | HR chấp nhận, sửa hoặc bỏ | Tỷ lệ chấp nhận không sửa; số mục sai HR bắt được |
| Mở rộng phòng ban | Soạn lại từ đầu | Dùng lại quy trình | Số phòng ban onboard mỗi quý; thời gian mỗi phòng ban |
| Rủi ro | Chậm, ít bịa | Có thể bịa | Số mục sai lọt tới publish (mục tiêu 0) |

**Rào chắn để giữ chất lượng:**
- AI chỉ tạo **bản nháp**; không tự publish, không đổi lộ trình đang chạy.
- Mỗi đề xuất kèm **trích nguồn** (đoạn nào trong tài liệu) và **độ tin cậy** (cao, trung bình, thấp); mục không có nguồn bị gắn cờ.
- AI **không điền email, URL, tên hay mã người thật**; chỉ dùng mã tham chiếu. Giá trị thật do HR nhập và duyệt.
- AI **hỏi lại** những chỗ tài liệu thiếu (ví dụ thời hạn ký hợp đồng) thay vì đoán.
- Kiểm tra tự động trước khi tạo nháp: phụ thuộc thiếu hoặc vòng, mã đầu mối và link chưa có, mục không có nguồn.
- Dữ liệu tài liệu gửi tới mô hình cần được anh Trí xác nhận cho phép (rủi ro về nơi xử lý dữ liệu).

## 3. Còn cần Viga không?

**Nếu chỉ có checklist và trang hướng dẫn:** phần lớn việc tuyến tính (faceid, tủ gửi đồ, ký hợp đồng) đã đủ. Viga không thêm giá trị ở đó, và nếu đặt nổi bật sẽ làm giao diện rối.

**Viga chỉ đáng có ở ba việc mà checklist làm kém:**

| Việc | Vì sao checklist chưa đủ |
|---|---|
| Định tuyến khi không biết bắt đầu từ đâu, hoặc tình huống rẽ nhánh (đổi Ubuntu, VPN, USB) | Người dùng không biết mình thuộc nhánh nào; Viga chọn đúng luồng và kiểm tra tiên quyết bằng code |
| Tra cứu điều nằm ngoài checklist (nội quy, quy định) | Cần tìm trong tài liệu HR đã đăng và trích nguồn (RAG) |
| Ghi lại câu hỏi chưa trả lời được | Trở thành danh sách chỗ HR cần bổ sung nội dung, nối vào bước soạn lộ trình |

**Viga không làm:** đổi trạng thái task, duyệt hoàn thành, cấp quyền, đọc nội dung link ngoài.

**Vị trí trong giao diện:** một nút "Hỏi Viga" ở header và một nút ngữ cảnh "Hỏi Viga về task này"; không lặp ở nhiều nơi.

**Tiêu chí giữ hoặc bỏ sau pilot:** nếu Viga ít được dùng hoặc không giảm số câu hỏi gửi mentor, thu gọn về đúng ba việc trên; nếu vẫn thấp thì bỏ, chỉ giữ checklist.

## 4. Đề xuất

1. Pilot Ngày 1 trước với checklist và trang hướng dẫn (đã đủ giá trị cốt lõi).
2. Thêm Viga cho hai chuỗi có rẽ nhánh (ngoại lệ Ubuntu/VPN, laptop và ITHD) và tra cứu tài liệu.
3. Thêm AI soạn lộ trình khi bắt đầu onboard phòng ban thứ hai, hoặc khi HR bắt đầu tự cập nhật nội dung thường xuyên.
4. Đo baseline trước: thời gian soạn tay, số câu hỏi gửi mentor trong tuần đầu.

## 5. Cần chốt với anh Trí
- Có cho phép gửi tài liệu onboard tới mô hình ngôn ngữ bên ngoài không, hay phải chạy trong hạ tầng nội bộ?
- Ai là người duyệt bản nháp AI (HR hay mentor), và mức độ tin cậy nào thì được chấp nhận nhanh?
- Chỉ tiêu thành công cho từng chỉ số ở mục 2.

## 6. Ba mục của HR: làm gì, ai dùng, input và output

| Mục | Làm gì | Ai dùng, khi nào | Input | Output |
|---|---|---|---|---|
| Tạo bằng AI | AI đọc tài liệu và đề xuất bản nháp lộ trình; HR duyệt từng mục | HR khi lập lộ trình cho phòng ban mới, hoặc khi tài liệu nguồn đổi lớn | Tài liệu nguồn (email, docx, pdf), phòng ban, đối tượng, ghi chú | Bản nháp: task, ngày, tiên quyết, cách xác nhận, mã đầu mối/link/mẫu, trích nguồn, độ tin cậy, câu hỏi cho HR |
| Lộ trình mẫu | Nơi HR xem, chỉnh, kiểm tra và publish lộ trình thành phiên bản | HR mỗi lần cập nhật; mentor chỉ xem | Bản nháp (từ AI hoặc soạn tay) | Phiên bản bất biến; người đang chạy giữ bản cũ hoặc được migrate |
| Liên hệ và link | Danh bạ mã tham chiếu: HR nhập giá trị thật của đầu mối, viết mô tả link, rồi duyệt | HR khi có mã mới | Mã tham chiếu, giá trị thật, mô tả link | Chỉ mục đã duyệt hiện cho nhân viên và Viga; mục chưa duyệt chặn publish |

Thứ tự làm: Tạo bằng AI → Liên hệ và link → Lộ trình mẫu (kiểm tra và publish) → nhân viên thấy trên portal.

## 7. Nguồn tài liệu: tải lên, xem, tách đoạn

1. **Tải lên:** docx, pdf, md, txt. Bản thật lưu tệp gốc để HR đối chiếu.
2. **Chuyển sang văn bản:** giữ tiêu đề, danh sách, bảng (dùng lại bộ chuyển đổi của pipeline nạp tài liệu đã có trong repo).
3. **Tách thành đoạn (chunk):** theo tiêu đề và gạch đầu dòng, giữ danh sách trong cùng một đoạn, khoảng 100–300 từ. Mỗi đoạn lưu: tệp, đường dẫn tiêu đề, trang, nội dung, mã đoạn.
4. **AI đọc từng đoạn:** đề xuất task kèm mã đoạn nguồn và độ tin cậy.
5. **Kiểm tra:** phụ thuộc, thiếu điều kiện hoàn thành, thiếu nguồn, mã chưa có; HR duyệt rồi mới tạo bản nháp.

HR xem được tài liệu và các đoạn (mục lục, đường dẫn tiêu đề, trang, task nào dùng đoạn đó) ngay trong trang Tạo bằng AI.

**Mỗi task AI đề xuất gồm:** tên, ngày, điều kiện hoàn thành, các bước, thời lượng ước tính (AI ước lượng, không có trong tài liệu), tiên quyết, cách xác nhận, đầu mối (mã), link (mã), mẫu văn bản, nguồn (mã đoạn), độ tin cậy. Chỉ đầu mối và link là mã; giá trị thật do HR nhập.

## 8. Giá trị so với baseline: nhận định thẳng

- **Chưa chứng minh được.** Phần AI trong prototype là mô phỏng; chưa có số baseline; chưa có lần chạy thật.
- **Lộ trình mẫu và Liên hệ và link không phải AI** và là hạ tầng bắt buộc: quản lý phiên bản, kiểm tra trước publish, nguồn duy nhất cho đầu mối và link đã duyệt. Giá trị so với việc chép đầu mối vào email và Word là ít sai sót và dễ cập nhật, nhưng với một phòng ban thì mức cải thiện khiêm tốn.
- **Tạo bằng AI** là phần có nhiều giả định nhất. Giá trị chỉ rõ khi có từ hai phòng ban trở lên hoặc nội dung đổi thường xuyên.
- **Điều kiện dừng đề xuất:** nếu sau khi đo, tỷ lệ HR chấp nhận không sửa thấp hoặc thời gian review gần bằng soạn tay, bỏ phần AI và giữ soạn tay trên Lộ trình mẫu.
- **Phần tạo nhiều giá trị nhất cho nhân viên mới** vẫn là checklist và trang hướng dẫn; phần HR là hạ tầng để nội dung đó luôn đúng và mở rộng được.
