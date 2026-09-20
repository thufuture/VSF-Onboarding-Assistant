# VSF Onboarding Assistant — Mục lục tài liệu

Thư mục này chứa đặc tả của hệ thống mới (chatbot onboarding VSF). **Đọc theo thứ tự dưới đây.** Nếu hai tài liệu mâu thuẫn: PRD chuẩn thắng về phạm vi và hành vi sản phẩm; system design và DB design thắng về kỹ thuật.

## Tài liệu chuẩn (đang hiệu lực)

| Thứ tự | Tệp | Nội dung |
|---|---|---|
| 1 | `vsf-onboarding-assistant-prd.md` | **PRD chuẩn**: bài toán, phạm vi MVP, 6 loại phản hồi, quy trình/link/đầu mối/form, ticket tối thiểu, chỉ số |
| 2 | `vsf-onboarding-assistant-system-design.md` | Kiến trúc hệ thống, pipeline ingest và chat, quyền riêng tư, API, frontend và design system, lộ trình build |
| 3 | `vsf-onboarding-assistant-database-design.md` | Schema chi tiết (class diagram, kiểu dữ liệu, ràng buộc, chỉ mục, migration) |
| 4 | `vsf-onboarding-assistant-deployment-ci.md` | Triển khai, CI/CD, sao lưu, giám sát (khung ở Phase 1b, hoàn thiện ở Phase 11; xem `plan/`) |
| 5 | `plan/README.md` | **Kế hoạch triển khai**: Phase 0–12, timebox 4 tuần, bắt buộc/stretch, quyết định kỹ thuật và hạ tầng đã chốt |

## Tài liệu lưu trữ (không dùng làm đặc tả)

Nằm trong `archive/`, chỉ để tra cứu lịch sử. **Không dùng làm yêu cầu.**

| Tệp | Trạng thái |
|---|---|
| `archive/vsf-onboarding-assistant-prd-v2.md` | Đã thay thế bởi PRD chuẩn (ghi rõ ở đầu tệp) |
| `archive/vsf-onboarding-assistant-prd.docx` | Bản DOCX sinh từ PRD giai đoạn đầu (trước khi viết lại), đã lỗi thời; sinh lại từ PRD chuẩn nếu cần bản Word |

## Dữ liệu test

`data/` chứa bộ tài liệu PDF/DOCX, registry, câu hỏi vàng và công cụ sinh/kiểm tra (xem `data/README.md`). Sinh lại bằng `python data/tools/generate_seed.py`, kiểm bằng `python data/tools/validate_seed.py`. Dữ liệu ở lại trong `docs/chatbot-vsf/data/` (CLI nạp seed ở Phase 5 đọc đường dẫn này). `data/documents/real_public/` là tùy chọn và không được commit; chỉ chạy `generate_seed.py` trên máy có nó.

## Quy ước

- Ví dụ về Vinmec, Ubuntu, VinSOC, địa điểm, đầu mối và biểu mẫu là **giả định để mô phỏng**, chưa phải thông tin VSF đã xác nhận (theo PRD chuẩn).
- Dữ liệu thử nghiệm giai đoạn đầu lấy từ lab DAY18 (chính sách giả lập); chỉ đủ để kiểm tra kỹ thuật, không chứng minh bot xử lý đúng quy trình VSF thật.
