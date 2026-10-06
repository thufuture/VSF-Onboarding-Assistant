# Bộ file Word thử nghiệm cho ngày 1

> **Chỉ để thử.** Các mục gắn nhãn `[BỔ SUNG THỬ NGHIỆM]` là quy định **do người soạn dữ liệu thử đặt ra**, không phải quy định của công ty; HR
> phải xác nhận trước khi dùng thật. Nhãn `[TRONG TÀI LIỆU NGÀY 1]` là nội dung lấy từ `Huong_dan_ngay_1_onboarding.docx`; nhãn `[CHƯA CÓ QUY ĐỊNH]` là
> chỗ cố ý để trống để kiểm tra Viga có nói thẳng "chưa có căn cứ" thay vì đoán không. Các file `~$...docx` là tệp khóa tạm của Word, không phải dữ liệu.

| File | Dùng để thử | Kết quả mong đợi khi tải lên |
|---|---|---|
| `Huong_dan_ngay_1_onboarding.docx` | Bản gốc, **không sửa** | Tài liệu nguồn của các file bên dưới. Không có heading nên bị suy tiêu đề từ các dòng viết HOA (3 mục, chất lượng trung bình) |
| `Huong_dan_ngay_1_onboarding_co_header.docx` | Cùng nội dung bản gốc, chỉ đổi định dạng sang Heading 1 đến 3 | Chất lượng cấu trúc **tốt**, 18 mục |
| `Huong_dan_ngay_1_onboarding_khong_header.docx` | Cùng nội dung, **không có heading nào** (chỉ chữ liền nhau) | Cảnh báo "suy ra tiêu đề" (các dòng viết HOA thành tiêu đề), 7 mục |
| `Cac_truong_hop_ngoai_le_ngay_1_v1.docx` | Câu hỏi ngoại lệ: không có VNeID, chỉ có CMND, chưa có lý lịch tư pháp, làm lại bài test... Bản 1 **chưa có quy định** cho nhiều ca | Viga trả "chưa có căn cứ" ở các ca để trống |
| `Cac_truong_hop_ngoai_le_ngay_1_v2.docx` | Bản cập nhật của v1: bổ sung quy định cho ca CMND và làm lại bài test | Dùng để thử **phiên bản mới đóng bản cũ**, rồi hỏi lại "thay VNeID bằng CMND được không?" thấy đổi câu trả lời |
| `Ngoai_le_ho_so_hop_dong_ngay_1.docx` | Ngoại lệ về hồ sơ và hợp đồng lao động | Có heading, 14 mục |
| `Ngoai_le_laptop_tai_khoan_ngay_1.docx` | Ngoại lệ về laptop và tài khoản | Có heading, 16 mục |
| `Ngoai_le_ticket_ubuntu_vpn_vinsoc.docx` | Ngoại lệ yêu cầu IT: Ubuntu, VPN, bảo mật | Có heading, 17 mục |
| `Quy_trinh_su_co_ngay_1_khong_cau_truc.docx` | **Không dùng Heading**: chỉ tiêu đề giả in đậm hoặc đánh số | Cảnh báo "suy ra tiêu đề" (chất lượng trung bình) |
| `Dau_moi_va_kenh_ho_tro_ngay_1.docx` | Nội dung dạng **bảng** (đầu mối, kênh hỗ trợ) | Bảng được đọc thành Markdown, 4 mục |
| `Huong_dan_ho_so_ban_cu_da_thay_the.docx` | Quy định **cố ý mâu thuẫn** với hướng dẫn mới (bản cũ đã thay thế) | Dùng để thử đặt bản cũ thành đã thay thế và kiểm Viga không dùng nó |

Cách thử nhanh: đăng nhập HR, vào **Tài liệu** → **Thêm tài liệu**, chọn một file và bấm "Tải lên"; thanh phần trăm hiện khi kích hoạt. Muốn thử phiên bản: tải `v1`,
sau đó dùng nút "Tải phiên bản mới" của tài liệu đó để tải `v2` (tạo bản nháp), xem lại rồi **Kích hoạt**; hoặc đặt lại `v1` bằng "Đặt làm bản áp dụng".

**Chưa có file nào ở mức "kém cấu trúc" (POOR)** nên bước LLM chia mục chưa được kích hoạt bởi bộ này (bước đó chỉ chạy khi luật không tìm được tiêu đề nào và tài liệu từ 400 từ trở lên; đã có test tự động). Muốn thử, tải một file toàn chữ liền, dài hơn 400 từ, không có dòng tiêu đề nào.
