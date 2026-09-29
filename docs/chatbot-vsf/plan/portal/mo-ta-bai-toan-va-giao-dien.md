# VSF Onboarding Portal: bài toán, nghiệp vụ, ba vai trò và giao diện

> Tài liệu mô tả để trao đổi với anh Trí và HR. Minh họa: [prototype-ui-flow-v11-ticket-su-co.html](prototype-ui-flow-v11-ticket-su-co.html) (dữ liệu mẫu, chạy độc lập bằng trình duyệt).
> Chưa có số đo thật. Mọi phần "giá trị so với baseline" đều là giả thuyết cần đo, không phải kết quả.

## 1. Bài toán

- **Ai:** nhân viên chính thức mới của khối KD&VH Vinmec (ban đầu là một khối, mở rộng thành nhiều phòng ban).
- **Hiện trạng (baseline):** nhận email onboard và tài liệu dài; nhờ mentor hoặc HR chỉ từng bước; dễ bỏ sót hạng mục (faceid, hợp đồng), làm sai thứ tự (điền form VinSOC khi chưa có phê duyệt T3), và hỏi lặp lại cùng câu hỏi.
- **Mục tiêu portal:** một nơi duy nhất cho lộ trình tuần đầu. Nhân viên biết hôm nay làm gì, làm gì trước, liên hệ ai, có mẫu email sẵn. Không phải chờ ai chỉ từng bước.
- **Chatbot Viga là phần hỗ trợ**, không phải trung tâm. Portal và checklist tạo ra phần lớn giá trị; Viga chỉ giúp ở chỗ checklist làm kém (rẽ nhánh, tra cứu, sự cố).

## 2. Nguyên tắc nghiệp vụ

1. **Task tự hoàn thành.** Nhân viên tự bấm "Tôi đã hoàn thành". Không có bước HR hay mentor duyệt hoàn thành (đã bỏ so với các bản trước).
2. **Thứ tự do hệ thống kiểm tra.** Task có tiên quyết thì bị khóa tới khi task trước xong và tới ngày của nó. Việc này do code kiểm tra, không do mô hình ngôn ngữ đoán.
3. **Gặp sự cố thì báo ticket, không tự mắc kẹt.** Trước tiên hỏi Viga; nếu chưa giải quyết được thì báo sự cố cho HR bằng ticket. Task được đánh dấu bị chặn cho tới khi HR xử lý xong.
4. **Nội dung do HR nhập và publish.** Sửa trên bản nháp; publish mới tạo phiên bản bất biến. Người đang chạy giữ bản cũ hoặc được migrate.
5. **Đường dẫn ngoài không bao giờ được đọc.** Task chỉ gắn mã; nhân viên thấy tên và mô tả HR viết, bấm để mở trang thật. Portal và Viga không đọc nội dung phía sau.
6. **AI chỉ đề xuất, người duyệt nội dung.** AI tạo bản nháp task từ tài liệu; HR xem, sửa, duyệt. AI không tự publish, không tự điền email, tên hay mã người thật.

## 3. Ba vai trò

| Vai trò | Là ai | Làm gì | Không làm gì |
|---|---|---|---|
| **Nhân viên mới** | Người mới vào khối | Xem roadmap nhiệm vụ theo ngày, làm và bấm hoàn thành, hỏi Viga, báo sự cố (ticket), theo dõi ticket, nhận thông báo | Sửa nội dung lộ trình; xem dữ liệu người khác |
| **HR** (làm luôn việc mentor) | HR phụ trách một hoặc nhiều phòng ban | Soạn nội dung (task, tài liệu, đầu mối, đường dẫn), tạo task bằng AI, publish; xem nhân viên phụ trách; xử lý ticket sự cố; xem phản hồi Viga để bổ sung tài liệu | Quản lý tài khoản hay phòng ban |
| **Admin** | Quản trị hệ thống | Tạo và lưu trữ phòng ban, gán HR và nhân viên vào phòng ban, quản lý tài khoản (tạo, đổi vai trò, đặt lại mật khẩu, khóa), xem thống kê và nhật ký | Soạn nội dung lộ trình (thuộc HR của phòng ban) |

Mô hình admin tham khảo Ralion: Người dùng, Phòng ban (như Project), Thành viên (như Membership, có trạng thái truy cập), Nhật ký. Không còn mục "Lộ trình mẫu chung" trong menu Admin ở bản hiện tại.

## 4. Luồng chính

### 4.1 Nhân viên làm task
1. Vào **Tổng quan**: thấy việc kế tiếp, tiến độ, biểu đồ tiến độ theo ngày, khối "Sự cố đã báo".
2. Vào **Nhiệm vụ**: chọn ngày ở thanh trên cùng (Ngày 1, Ngày 2, Ngày 3-5, Khi cần; mỗi ngày có icon và % hoàn thành). Roadmap là con đường uốn lượn ngang từ trái sang phải, mỗi nút là một task (Task 1, Task 2…) với màu theo trạng thái.
3. Mở task: đọc **hướng dẫn từng bước** (mỗi bước thu gọn, bấm mũi tên để mở), tab **Tài liệu và mẫu** (tài liệu đính kèm, mẫu email điền sẵn, đường dẫn tham chiếu, đầu mối), tab **Trao đổi**.
4. Bấm **Bắt đầu task**, làm xong bấm **Tôi đã hoàn thành**. Task phụ thuộc tự mở khóa.

Trạng thái task: Đang khóa, Sẵn sàng, Đang làm, Chờ bên ngoài (chờ email, chờ phản hồi), Đang kẹt (đã báo sự cố), Hoàn thành. Trễ hạn hiển thị đỏ khi task của ngày trước chưa xong.

### 4.2 Gặp sự cố
1. **Hỏi Viga** trong task hoặc nút "Hỏi Viga" ở đầu trang. Viga tra trong tài liệu và mục câu hỏi thường gặp, cách xử lý sự cố đã đăng, có trích nguồn.
2. Nếu không giải quyết được (hoặc bạn nhắn "vẫn lỗi"), Viga đề xuất nút **Báo sự cố cho HR**. Không có nút báo sự cố trực tiếp trong task hay trang Theo dõi (từ v12).
3. Bấm nút: mở form **Báo sự cố**:
   - Task gặp sự cố (đã chọn sẵn).
   - **Loại sự cố** trong danh sách: Thiết bị/laptop; Tài khoản/đăng nhập; Quyền truy cập; Hồ sơ/giấy tờ; Faceid/chấm công; Email/Teams; Hướng dẫn chưa rõ; Khác.
   - **Lời nhắn** mô tả (nếu báo từ Viga thì tự điền câu hỏi vừa hỏi).
   - **Đính kèm ảnh và video** (ảnh chụp màn hình, video quay lại lỗi).
4. Gửi: tạo ticket (mã TK-###), task chuyển sang **Đang kẹt**.
5. Mục **Theo dõi**: danh sách ticket của mình với trạng thái Mới, Đang xử lý, Đã xử lý; mở ticket để xem toàn bộ lời nhắn, ảnh, video, phản hồi của HR và trả lời thêm.

Nhân viên không còn phải tự theo dõi biểu mẫu hay chờ duyệt; mục Theo dõi chỉ là ticket sự cố.

### 4.3 HR xử lý ticket
1. Menu **Ticket sự cố** (có số ticket mới): bảng mã, nhân viên, task, loại sự cố, trạng thái, cập nhật.
2. Mở ticket: đọc lời nhắn và xem ảnh, video; **Nhận xử lý** (chuyển Đang xử lý), **trả lời** (kèm ảnh, video), **Đã giải quyết**.
3. Khi giải quyết: ticket sang Đã xử lý và task của nhân viên **được mở lại** (từ Đang kẹt về Đang làm).

### 4.4 HR soạn nội dung
- **Quản lý task:** chọn ngày, danh sách dạng roadmap (số thứ tự ở đầu dòng nhập được để đổi vị trí). Sửa task trong modal rộng có tab **Thông tin, Hướng dẫn, Tiên quyết, Liên hệ và tài nguyên** (và **Nguồn** nếu tạo từ AI). Thứ tự, ngày, nhóm, thời lượng, điều kiện áp dụng, các bước, tiên quyết, đầu mối, đường dẫn, mẫu email. Kiểm tra vòng tiên quyết khi lưu.
- **Đầu mối và đường dẫn:** khi chưa có sẵn thì thêm mới ngay trong task hoặc trong bước duyệt AI. Mục mới ở trạng thái "chưa duyệt", HR nhập giá trị thật và duyệt; mục chưa duyệt chặn publish.
- **Tài liệu:** tải lên, xem, sửa, gắn vào task, thay bản mới (có số phiên bản và lịch sử), xóa.
- **Mẫu task:** thư viện task chuẩn (nộp giấy tờ, nhận thiết bị, đào tạo, xin quyền…); chọn ngày rồi "Dùng mẫu" để thêm vào bản nháp.
- **Phiên bản:** kiểm tra trước publish (tiên quyết, đầu mối, đường dẫn, điều kiện hoàn thành), publish, giữ hoặc migrate người đang chạy.

### 4.5 Tạo task bằng AI từ tài liệu
Đường ống dùng chung với Viga:
1. **Định dạng lại** tài liệu onboard (docx) thành văn bản có cấu trúc.
2. **Ingest:** lưu tệp gốc và văn bản.
3. **Chunking:** tách theo tiêu đề và danh sách (100–300 từ), mỗi đoạn có mã (c1…), đường dẫn tiêu đề.
4. **AI sinh task:** đọc từng đoạn, đề xuất task có cấu trúc (tên, ngày, điều kiện hoàn thành, các bước, thời lượng, tiên quyết, đầu mối, đường dẫn, mẫu) kèm **mã đoạn nguồn** và **độ tin cậy**.
5. **HR duyệt:** xem từng đề xuất; bấm mã nguồn để cột bên phải cuộn và **tô sáng đúng đoạn** trong tài liệu; chấp nhận, sửa, bỏ; chọn hoặc thêm đầu mối và đường dẫn; hệ thống kiểm tra tiên quyết, thiếu đầu mối, thiếu điều kiện hoàn thành, thiếu nguồn.
6. Task đã duyệt vào **bản nháp** (nhãn Mới), giữ liên kết tới đoạn nguồn. Không tự publish.

Khi tài liệu đổi: tải phiên bản mới, hệ thống so đoạn cũ và mới, đề xuất cập nhật task bị ảnh hưởng hoặc task mới; HR áp dụng từng thay đổi vào bản nháp.

Tài liệu Ngày 1 đã viết lại có cấu trúc: [tai-lieu-ngay-1-viet-lai.md](tai-lieu-ngay-1-viet-lai.md), gồm hai đoạn bổ sung mẫu (câu hỏi thường gặp, xử lý sự cố) do soạn thêm để Viga trả lời; HR cần xác nhận.

### 4.6 Viga (hỏi đáp)
- **Đầu vào:** câu hỏi, hồ sơ nhân viên (địa điểm, loại máy, ngày hiện tại), tiến độ, nội dung đã đăng (task, hướng dẫn, tài liệu, câu hỏi thường gặp, xử lý sự cố, mẫu, đầu mối, mô tả đường dẫn).
- **Đầu ra:** loại phản hồi (bước kế tiếp, chưa đủ tiên quyết, kế hoạch ngày, thông tin, ngoài lộ trình), câu trả lời kèm nguồn, nút hành động (mở task, bắt đầu, sao chép mẫu, mở đường dẫn đã duyệt, **báo sự cố cho HR**).
- **Khi không có tài liệu:** chỉ nhân viên đến đầu mối của task, rồi HR phụ trách. Câu hỏi được ghi vào mục **Phản hồi Viga** của HR.
- **Đánh giá:** mỗi câu trả lời có 👍 và 👎; 👎 và câu không trả lời được hiện ở Phản hồi Viga để HR bổ sung tài liệu.
- **Viga không làm:** đổi trạng thái task, cấp quyền, đọc nội dung đường dẫn ngoài.

### 4.7 Admin
- **Tổng quan:** số phòng ban, nhân viên mới, tiến độ trung bình, số cần xử lý; biểu đồ nhân viên theo phòng ban, theo giai đoạn, câu hỏi Viga 7 ngày, task hay kẹt nhất, tài khoản theo vai trò; hoạt động gần đây.
- **Người dùng:** tạo, sửa vai trò, đặt lại mật khẩu, khóa hoặc mở khóa, nhập CSV.
- **Phòng ban:** tạo (tên, mã, HR phụ trách chính, tùy chọn sao chép lộ trình), lưu trữ và khôi phục, xem thành viên.
- **Thành viên:** gán người dùng vào phòng ban với vai trò HR phụ trách hoặc Nhân viên mới; trạng thái truy cập Hoạt động, Tạm dừng, Tài khoản khóa, Phòng ban lưu trữ.
- **Nhật ký:** ai làm gì, khi nào.

## 5. Giao diện (prototype v11)

| Vai trò | Menu |
|---|---|
| Nhân viên | Tổng quan · Nhiệm vụ · Theo dõi (ticket) · Thông báo |
| HR | Tổng quan · Nhân viên · Ticket sự cố · Phản hồi Viga · Quản lý task · Tài liệu · Tạo task bằng AI · Mẫu task · Đầu mối và đường dẫn · Phiên bản |
| Admin | Tổng quan · Người dùng · Phòng ban · Thành viên · Nhật ký |

Quy ước thiết kế: bo góc 5px, phẳng, màu thương hiệu #1090cb, navy #0c2d5b, font Be Vietnam Pro, bảng màu biểu đồ dịu (xanh lá, xanh dương, vàng, đỏ, xám). Header mỗi trang nằm trong một card. Footer cố định ở đáy màn hình. Modal có header và footer cố định, có icon, nút đóng luôn bấm được, chia mục bằng tab khi nhiều nội dung. Icon dùng bộ Lucide. Ảnh đại diện hoạt hình theo tên (bộ nam, bộ nữ). Bảng có phân trang.

Trạng thái task trên roadmap: xanh lá (hoàn thành), xanh dương (sẵn sàng, đang làm), vàng (đang chờ), xám (khóa), đỏ (trễ hạn hoặc đang kẹt).

## 6. Mô hình dữ liệu (rút gọn)

- **Journey mẫu và bản instance:** lộ trình theo phòng ban, có phiên bản; nhân viên chạy trên bản snapshot.
- **Task:** tên, ngày, nhóm, thứ tự, thời lượng, điều kiện hoàn thành, các bước, tiên quyết, đầu mối (mã), đường dẫn (mã), mẫu, điều kiện áp dụng, nguồn (mã đoạn tài liệu).
- **Tiến độ task theo người:** trạng thái (khóa, sẵn sàng, đang làm, chờ bên ngoài, kẹt, hoàn thành), thời điểm, ghi chú.
- **Ticket sự cố:** mã, nhân viên, task, loại sự cố, trạng thái (Mới, Đang xử lý, Đã xử lý), danh sách tin nhắn (người gửi, nội dung, thời điểm, tệp đính kèm ảnh hoặc video).
- **Tài liệu và đoạn (chunk):** tệp, phiên bản, đường dẫn tiêu đề, nội dung, mã đoạn.
- **Phản hồi Viga:** câu hỏi, loại (chưa trả lời được, đánh giá chưa ổn), số lần, trạng thái xử lý.
- **Người dùng, phòng ban, thành viên (vai trò trong phòng ban, trạng thái truy cập), nhật ký.**

## 7. Chỉ số cần đo (chưa có số)

- **Nhân viên:** thời gian hoàn tất checklist Ngày 1 và tuần 1; số bước làm sai thứ tự; số câu hỏi lặp gửi mentor hoặc HR; mức hài lòng.
- **Viga:** tỷ lệ trả lời có nguồn; tỷ lệ 👍; số câu chưa trả lời được; số ticket sinh ra từ Viga.
- **Ticket:** thời gian đến phản hồi đầu tiên, thời gian giải quyết, số ticket theo loại sự cố (chỉ ra chỗ tài liệu còn thiếu).
- **AI tạo task:** tỷ lệ HR chấp nhận không sửa; số mục sai lọt tới publish (mục tiêu 0); thời gian duyệt so với soạn tay.
- **HR:** thời gian cập nhật khi quy trình đổi.

Điều kiện dừng: nếu sau pilot Viga không giảm số câu hỏi gửi HR, hoặc tỷ lệ chấp nhận AI thấp và thời gian duyệt gần bằng soạn tay, bỏ phần đó và giữ checklist với soạn tay.

## 8. Rủi ro và điểm cần chốt

- **Dữ liệu ra ngoài:** có được gửi nội dung onboard tới mô hình ngôn ngữ bên ngoài không, hay phải chạy nội bộ? Ảnh và video đính kèm ticket lưu ở đâu, giữ bao lâu?
- **Quy mô HR:** một HR nhiều phòng ban thì thấy ticket của phòng ban nào (cần lọc theo phòng ban; prototype chưa lọc).
- **Cá nhân hóa:** điều kiện áp dụng (địa điểm, loại máy, vị trí) nào là có thật; prototype chỉ là nhãn hiển thị.
- **Chống lạm dụng ticket:** cần quy tắc thời gian phản hồi (SLA) và người thay thế khi HR vắng.
- **Không có bước duyệt hoàn thành:** chấp nhận rủi ro nhân viên tự bấm hoàn thành sai; giảm bằng điều kiện hoàn thành rõ ràng và HR theo dõi tiến độ.
- **Nội dung Ngày 2 trở đi là bản mẫu**, cần HR xác nhận.
- **Chưa chứng minh giá trị:** phần AI và Viga trong prototype là mô phỏng.

## 9. Lịch sử các bản prototype

| Bản | Nội dung chính |
|---|---|
| v1 | Bản đầu, dùng Viga và mentor |
| v2 | Gọn hơn; HR có AI tạo lộ trình (mô phỏng) |
| v3 | HR không AI, quản lý bằng bảng |
| v4–v5 | Viga cộng HR CRUD; HR làm luôn việc mentor; thêm Admin |
| v6 | Admin theo phòng ban (kiểu Ralion) |
| v7 | Roadmap nhiệm vụ, AI tạo task từ tài liệu có trích nguồn, Phản hồi Viga, Mẫu task |
| v8–v10 | Roadmap uốn lượn, nền sáng, cuối cùng là con đường ngang trái sang phải; footer cố định |
| **v11** | **Bỏ duyệt hoàn thành; sự cố báo bằng ticket (loại sự cố, lời nhắn, ảnh, video); HR xử lý ticket; Theo dõi = ticket** |
