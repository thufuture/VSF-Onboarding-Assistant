# VSF Onboarding Assistant

Trợ lý onboarding cho nhân sự mới: trả lời **từ tài liệu đã được duyệt, có trích dẫn nguồn**, chỉ đúng quy trình, đúng đầu mối và biểu mẫu; khi thiếu căn cứ thì nói thẳng là chưa có thay vì đoán.

> **Trạng thái:** đang ở Phase 0 → 1a (dựng khung). **Bản demo thực tập, chưa phải sản phẩm chính thức.** Chưa có mã ứng dụng; hiện repo chứa tài liệu thiết kế, kế hoạch và bộ dữ liệu test.

## Tài liệu

Toàn bộ nằm trong [docs/chatbot-vsf/](docs/chatbot-vsf/). Đọc theo thứ tự:

| Tài liệu | Vai trò |
|---|---|
| [PRD chuẩn](docs/chatbot-vsf/vsf-onboarding-assistant-prd.md) | Yêu cầu, chỉ số mục tiêu, tiêu chí hoàn thành |
| [Thiết kế hệ thống](docs/chatbot-vsf/vsf-onboarding-assistant-system-design.md) | Kiến trúc, pipeline, API, hợp đồng route, frontend |
| [Thiết kế cơ sở dữ liệu](docs/chatbot-vsf/vsf-onboarding-assistant-database-design.md) | Bảng, ràng buộc, migration |
| [Triển khai và CI](docs/chatbot-vsf/vsf-onboarding-assistant-deployment-ci.md) | VPS, Compose, Caddy, GitHub Actions |
| [Kế hoạch](docs/chatbot-vsf/plan/README.md) | Phase 0–12, timebox 4 tuần, bắt buộc/stretch |
| [Bộ dữ liệu test](docs/chatbot-vsf/data/README.md) | 45 tệp PDF/DOCX giả lập, registry, 242 câu vàng |

**Chuẩn và lưu trữ.** Chỉ các tài liệu ở bảng trên là chuẩn. Hai tệp trong [docs/chatbot-vsf/archive/](docs/chatbot-vsf/archive/) (`prd-v2.md`, `prd.docx`) chỉ để tra cứu lịch sử, **không dùng làm yêu cầu**. Khi mâu thuẫn, PRD chuẩn thắng.

## Dữ liệu là giả lập

Mọi tài liệu `SYN_*` và `PUBSUM_*` trong bộ seed là **dữ liệu giả lập** (nhãn `SYNTHETIC` ở chân trang), dùng để kiểm chứng kỹ thuật. Chúng **không** phải chính sách hay quy trình thật của VSF và không chứng minh bot đúng với quy trình thật.

## Kiểm tra bộ dữ liệu

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r docs\chatbot-vsf\data\tools\requirements.txt
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python docs\chatbot-vsf\data\tools\validate_seed.py
```

- Thư mục `data/documents/real_public/` (PDF luật công khai) **không được commit**; validator coi nó là tùy chọn.
- **Chỉ chạy `generate_seed.py` trên máy có `real_public/`.** Trên máy thiếu nó, script bỏ các dòng `real_public` khỏi manifest và làm manifest bị đổi.

## Cấu hình

Sao chép `.env.example` thành `.env` và điền giá trị. **Không bao giờ commit `.env`** hay khóa API vào repo. Mật khẩu `ChangeMe!123` trong dữ liệu seed chỉ là mật khẩu dev.

## Đóng góp

Mỗi phase là một hoặc vài PR nhỏ; dùng [mẫu PR](.github/pull_request_template.md). Không sửa migration đã áp dụng. Bảo vệ nhánh `main`: *(chưa cấu hình; cập nhật sau khi kiểm tính năng của gói GitHub — nếu gói không hỗ trợ thì giữ quy ước "không commit thẳng `main`" bằng tay)*.
