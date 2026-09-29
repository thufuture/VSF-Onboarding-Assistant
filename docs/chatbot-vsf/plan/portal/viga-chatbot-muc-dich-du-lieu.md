# Viga (chatbot): mục đích, dữ liệu vào ra, khác gì checklist

> Bản nháp để trao đổi với anh Trí. Chưa có số đo thật. Minh họa: [prototype-ui-flow-v4-viga-hr-crud.html](prototype-ui-flow-v4-viga-hr-crud.html).

## 1. Chốt hướng
- **HR không cần AI sinh lộ trình/tài liệu.** Một phòng ban, nội dung ít đổi: HR nhập tay trên trang quản lý task và tài liệu là đủ; giá trị AI ở đây thấp và chưa đo được.
- **Tập trung chatbot ở phía người dùng.** Viga đọc **nội dung HR đã nhập và đã đăng** (task, tài liệu, mẫu, đầu mối), rồi trả lời theo **hồ sơ từng nhân viên**.
- HR nhập tay hết thì chat làm gì? Chat **không tạo nội dung**; chat **tìm, chọn và ghép** nội dung đã có cho đúng người, đúng lúc.

## 2. Checklist làm được gì, chat làm được gì thêm

| Nhu cầu | Checklist | Viga |
|---|---|---|
| Việc tuần tự, rõ ràng (faceid, tủ gửi đồ) | Đủ | Không thêm giá trị |
| "Mình đang ở đâu, bước nào tiếp?" | Có (Việc kế tiếp) | Trả lời bằng lời, hỏi tự nhiên |
| Tình huống rẽ nhánh (đổi Ubuntu, VPN, USB) | Phải đọc cả hướng dẫn để biết nhánh nào | Hỏi vài câu, chọn đúng chuỗi bước, kiểm tra bước tiên quyết |
| Hỏi điều nằm ngoài checklist (nội quy, quy định) | Không có | Tìm trong tài liệu đã đăng, trích nguồn |
| Cần mẫu email điền sẵn | Nút "Sao chép" trong task | Cùng kết quả; tiện khi đang hỏi |
| Điều chỉnh theo từng người | Checklist chỉ ẩn/hiện task theo điều kiện | Diễn giải theo hồ sơ (địa điểm, loại máy, ngày hiện tại) |
| Phát hiện chỗ tài liệu thiếu | Không | Ghi lại câu hỏi không trả lời được cho HR |

Kết luận thẳng: phần lớn giá trị cho nhân viên mới nằm ở checklist và trang hướng dẫn. Viga chỉ đáng giữ cho **ba việc**: rẽ nhánh, tra cứu ngoài checklist, ghi lại chỗ thiếu tài liệu. Nếu pilot cho thấy ít người dùng hoặc mentor vẫn nhận số câu hỏi như cũ, thu gọn hoặc bỏ.

## 3. Dữ liệu vào, dữ liệu ra

**Input mỗi lượt hỏi**
- Câu hỏi của nhân viên.
- Hồ sơ: mã, địa điểm làm việc, loại máy (Windows/Ubuntu), ngày onboarding hiện tại.
- Tiến độ: trạng thái từng task của người đó.
- Nội dung đã đăng: task, hướng dẫn, tài liệu, mẫu email, đầu mối, mô tả đường dẫn (phiên bản đang áp dụng cho người đó).

**Output**
- `response_type`: PREREQUISITE_REQUIRED, NEXT_STEP, DAY_PLAN, INFO, NOT_IN_JOURNEY.
- Câu trả lời ngắn kèm nguồn (task hoặc tài liệu nào).
- `suggested_actions`: mở task, bắt đầu task, mở ngày, sao chép mẫu, mở đường dẫn đã duyệt.

**Viga không làm:** đổi trạng thái task, duyệt hoàn thành, cấp quyền, đọc nội dung phía sau đường dẫn ngoài. Bước tiên quyết do code kiểm tra, không do mô hình ngôn ngữ đoán.

## 4. Cá nhân hóa: mỗi người onboarding hơi khác nhau
- Mỗi task có trường **Áp dụng cho** (mọi nhân viên / chỉ Vincom Đồng Khởi / chỉ khi cần yêu cầu ngoại lệ). Trong prototype trường này là nhãn hiển thị; bản thật tính từ hồ sơ để đặt trạng thái "Không áp dụng".
- Ví dụ: faceid chấm công chỉ hiện cho người ở Đồng Khởi; chuỗi Ubuntu/VPN chỉ mở khi người đó yêu cầu.
- Viga dùng cùng hồ sơ để trả lời: cùng câu "Em cần làm gì hôm nay?" nhưng mỗi người ra danh sách khác.
- Cần chốt với HR: những điều kiện nào là có thật (địa điểm, loại máy, vị trí, ngày vào).

## 5. Phiên bản nội dung
- HR sửa trên **bản nháp**; **publish** mới tạo phiên bản bất biến.
- Người đang chạy giữ bản cũ hoặc được migrate (HR chọn khi publish).
- Tài liệu có số phiên bản riêng (v1.0, v1.1…) và lịch sử thay đổi; Viga chỉ trích tài liệu đã đăng, không trích bản nháp.
- Câu Viga trả lời phải nêu rõ nguồn và phiên bản để mentor truy lại được.

## 6. Phần vai trò khác được xem gì
- **(v5 gộp vào HR)** Việc mentor do HR làm: xem tất cả task và tài liệu; bấm "Xem task" ở bảng nhân viên, hàng chờ duyệt hoặc bảng tất cả task để đọc nội dung task nhân viên đang kẹt (hướng dẫn, sự cố hay gặp, tài liệu). Có bình luận hai chiều theo task.
- **HR:** quản lý task, tài liệu, đầu mối và đường dẫn, phiên bản; xem nội dung task như nhân viên; thấy danh sách câu hỏi Viga chưa trả lời được.
- **Đầu mối và đường dẫn:** task chỉ gắn **mã**. Nhân viên thấy tên và mô tả HR viết ("Dùng để", "Khi nào", "Cần chuẩn bị") rồi bấm mở trang thật. Portal và Viga không đọc nội dung trang đó. Có bảng nào dùng ở task nào và cần duyệt trước khi hiện.

## 7. Giá trị so với baseline: nhận định thẳng
- Chưa có số baseline; phần Viga trong prototype là mô phỏng (câu trả lời soạn sẵn).
- Cần đo trước pilot: số câu hỏi lặp lại gửi mentor/HR trong tuần đầu, thời gian đến khi xong checklist Ngày 1, số bước làm sai thứ tự.
- Cần đo với Viga: tỷ lệ chọn đúng task/bước tiếp theo trên bộ câu hỏi mẫu, tỷ lệ trả lời có nguồn, số câu hỏi không trả lời được.
- Điều kiện dừng: nếu Viga không giảm số câu hỏi gửi mentor sau pilot, bỏ Viga và giữ checklist.

## 8. Cần chốt với anh Trí
- Nội dung onboard có được gửi tới mô hình ngôn ngữ bên ngoài không, hay phải chạy nội bộ?
- Các điều kiện cá nhân hóa nào là có thật (địa điểm, loại máy, vị trí)?
- Mentor xem nội dung task và tài liệu ở mức nào (chỉ đọc, hay được sửa ghi chú)?
- Chỉ tiêu thành công cho các chỉ số ở mục 7.

## 9. Agent AI dùng chung một đường ống cho HR và Viga (v7)
- **Nạp tài liệu:** định dạng lại (docx sang văn bản có cấu trúc) → ingest (lưu tệp gốc và văn bản) → chunking theo tiêu đề và danh sách → mỗi đoạn có mã, đường dẫn tiêu đề.
- **HR (tạo task):** AI đọc các đoạn và đề xuất task có cấu trúc (tên, ngày, cách xác nhận, tiên quyết, điều kiện hoàn thành, các bước, đầu mối, đường dẫn, mẫu), **mỗi task trích mã đoạn nguồn**; bấm mã để tới đúng đoạn trong tài liệu. HR xem, sửa, xóa, chọn hoặc thêm đầu mối và đường dẫn rồi duyệt. AI không tự publish.
- **Khi tài liệu đổi:** tải bản mới, hệ thống so đoạn cũ và mới, đề xuất cập nhật task bị ảnh hưởng hoặc task mới; HR áp dụng từng thay đổi vào bản nháp.
- **Viga (hỏi đáp):** cùng các đoạn đã đăng, truy hồi đoạn liên quan và trích nguồn. Câu hỏi thường gặp và cách xử lý sự cố được viết vào tài liệu (đoạn bổ sung mẫu) để Viga trả lời.
- **Không có tài liệu:** Viga chỉ đến **đầu mối của task**, rồi HR phụ trách; câu hỏi được ghi vào mục Phản hồi Viga.
- **Đánh giá:** nhân viên bấm 👍 hoặc 👎 ở mỗi câu trả lời; câu 👎 và câu không trả lời được hiện ở menu Phản hồi Viga của HR.
- **Đường dẫn ngoài:** không bao giờ đọc nội dung; chỉ dùng mô tả HR viết.
- **Chưa chứng minh:** phần AI trong prototype là mô phỏng (đề xuất soạn sẵn). Cần đo tỷ lệ HR chấp nhận không sửa và thời gian duyệt so với soạn tay trước khi kết luận có lợi.
