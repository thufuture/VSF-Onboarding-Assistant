# Kế hoạch triển khai VSF Onboarding Assistant

> Trạng thái: **bản nháp v4**. **Phase 0 đã thực hiện phần kỹ thuật** ([báo cáo](phase-0/bao-cao-phase-0.md)); đang chờ duyệt kế hoạch [Phase 1](phase-1/phase-1.md).
> Phạm vi: **1 người, timebox 4 tuần** (20,5 ngày công gồm 1,1 ngày stretch), **có bản demo trên máy chủ thật**. Đây là timebox mục tiêu, không phải cam kết production; khoảng dao động thực tế 4–6 tuần. Repo đích: https://github.com/thufuture/VSF-Onboarding-Assistant (private, đang trống).

## Tài liệu trong thư mục này

| Tài liệu | Nội dung |
|---|---|
| [master-plan.md](master-plan.md) | Phase 0–12: mục tiêu, việc, đầu ra, cổng hoàn thành, phụ thuộc, rủi ro; bắt buộc/stretch; quyết định kỹ thuật và hạ tầng; đối chiếu nhận xét Codex |
| [landing-page-plan.md](landing-page-plan.md) | Phase 10 [stretch]: landing tiếng Việt tối giản (0,5 ngày) theo bố cục VLearn, một ảnh minh họa có giấy phép |
| [frontend-login-reuse.md](frontend-login-reuse.md) | Phase 4: tái sử dụng giao diện đăng nhập của Ralion (giữ / đổi / bỏ), việc R1–R4, cổng kiểm |
| [phase-0/phase-0.md](phase-0/phase-0.md) | Phase 0 chi tiết: hiện trạng đã kiểm, 5 điểm dừng để duyệt, 15 bước, mã dự kiến, thư mentor nháp, cổng hoàn thành, rủi ro |
| [phase-0/bao-cao-phase-0.md](phase-0/bao-cao-phase-0.md) | **Báo cáo Phase 0**: đã hoàn thành gì, kết quả kiểm, còn lại gì |
| [phase-1/phase-1.md](phase-1/phase-1.md) | Phase 1 chi tiết (1a khung cục bộ + CI, 1b khung triển khai): hiện trạng đã kiểm, quyết định, từng bước, cổng, rủi ro, mã dự kiến |
| [phase-4/phase-4.md](phase-4/phase-4.md), [phase-4/bao-cao-phase-4.md](phase-4/bao-cao-phase-4.md) | Phase 4: kế hoạch và **báo cáo** đăng nhập, đăng xuất, trang cho nhân sự mới (4-A đến 4-C đã xong, chưa push) |
| [huong-dan-thiet-lap-may-chu.md](huong-dan-thiet-lap-may-chu.md) | Phase 0: hướng dẫn từng bước cài công cụ, tạo khóa SSH, thuê VPS, DuckDNS, thử HTTPS, cấu hình GitHub |
| [phu-luc-may-chu-va-chi-phi.md](phu-luc-may-chu-va-chi-phi.md) | So sánh máy chủ/PaaS, tên miền, CI, bảng "đủ hay không", chi phí (nguồn chính thức) |

## Tài liệu nền

**Chuẩn (dùng làm yêu cầu và thiết kế)**

| Tài liệu | Vai trò |
|---|---|
| [PRD chuẩn](../vsf-onboarding-assistant-prd.md) | Yêu cầu, chỉ số mục tiêu, tiêu chí hoàn thành |
| [Thiết kế hệ thống](../vsf-onboarding-assistant-system-design.md) | Kiến trúc, pipeline, API, hợp đồng route (mục 9.1), frontend, lộ trình M0–M6 |
| [Thiết kế cơ sở dữ liệu](../vsf-onboarding-assistant-database-design.md) | Bảng, ràng buộc INV1–INV23, migration `0001_core`–`0004_tickets` |
| [Triển khai và CI](../vsf-onboarding-assistant-deployment-ci.md) | Phase 1b (D0–D2) và Phase 11a/11b; phần còn lại làm sau MVP |
| [Bộ dữ liệu test](../data/README.md) | 45 file PDF/DOCX giả lập, registry, 242 câu golden |

**Lưu trữ (chỉ tra cứu lịch sử, không dùng làm yêu cầu):** `vsf-onboarding-assistant-prd-v2.md` và `vsf-onboarding-assistant-prd.docx`. Ở repo mới hai tệp này nằm trong `docs/chatbot-vsf/archive/`. Khi mâu thuẫn, PRD chuẩn thắng.

## Tổng quan phase (tuần tự)

| Phase | Tên | Ngày công | Loại |
|---|---|---:|---|
| 0 | Repo, tài liệu chuẩn/lưu trữ, xin dữ liệu thật, chuẩn bị VPS | 0,5 | Bắt buộc |
| 1a | Khung cục bộ (Compose, CI, `/api/v1/health`) | 1 | Bắt buộc |
| 1b | Khung triển khai (HTTPS trên máy chủ thật; giới hạn cứng 1 ngày) | 1 | Bắt buộc, có đường lui |
| 2 | Lát cắt dọc: 1 tài liệu → trả lời có nguồn; `0001_core` đầy đủ | 3 | Bắt buộc |
| 3 | Dữ liệu: rà tay, đóng băng golden test | 1 | Bắt buộc |
| 4 | Xác thực và trang `/vi/login` (tái dùng Ralion) | 1,5 | Bắt buộc |
| 5 | Ingest hoàn chỉnh | 2,5 | Bắt buộc |
| 6 | Registry, tìm kiếm quy trình, harness đánh giá | 2,5 | Bắt buộc |
| 7 | Lõi chat 6 loại phản hồi và ticket | 3 | Bắt buộc |
| 8 | Giao diện tối thiểu | 1,5 | Bắt buộc |
| 9 | Đánh giá và báo cáo | 1 | Bắt buộc |
| 11a | Deploy thủ công bản cuối + cấu hình an toàn | 0,5 | Bắt buộc |
| 12a | Demo nghiệm thu, bảng đối chiếu PRD mục 11 | 0,4 | Bắt buộc |
| 10 | Landing tiếng Việt, tối giản | 0,5 | Stretch |
| 11b | Tự động deploy, rollback tự động, diễn tập khôi phục | 0,5 | Stretch |
| 12b | Pilot nhỏ | 0,1 | Stretch |
| | **Bắt buộc 19,4 · Stretch 1,1 · Tổng** | **20,5** | |

Ước lượng chưa hiệu chỉnh; đo lại sau Phase 2. Nếu tự động deploy, landing hoặc pilot là bắt buộc, coi mốc là 5–6 tuần. Thứ tự cắt khi trễ ở [master-plan.md](master-plan.md) mục 3.

## Quyết định đã chốt (chi tiết ở master-plan mục 5)

- **Hạ tầng:** máy chủ chính Oracle Cloud Always Free (ARM, thử nghiệm, có thể bị thu hồi khi nhàn rỗi), dự phòng Hetzner Cloud CX23 (thuê 1 tháng rồi xóa), tên miền DuckDNS, GitHub Actions + GHCR, chỉ dữ liệu giả lập trên VPS.
- **Provider:** LLM **DeepSeek** (`deepseek-flash`, JSON output), embedding **BGE-M3 trên Modal**; khóa lấy từ Ralion, **chỉ dùng cục bộ** (khóa riêng có hạn mức trước khi lên VPS); embedding và LLM giả trong test/CI.
- **Migration:** `0001_core` viết đầy đủ ở Phase 2, `0002_registry` ở Phase 6, `0003_chat` + `0004_tickets` ở Phase 7; không có bảng `sessions`.
- **Route:** `/` → `/vi`; `/vi/login`, `/vi/chat`; toàn bộ API ở `/api/v1/*`; `/api/v1/health` công khai, `/api/v1/ready*` chỉ nội bộ.
- **Link đã duyệt** có `code` và `version_no`; quy trình tham chiếu bằng `link_codes`.

## Thay đổi qua các bản

- **v2 (Codex vòng 1):** cắt phạm vi thay vì kéo dài lịch; tuần tự; landing về cuối; chỉ tiếng Việt; thêm lát cắt dọc và phase dữ liệu; tài liệu chuẩn/lưu trữ.
- **v3:** đưa triển khai vào 4 tuần (bù bằng landing, giao diện, bỏ B2).
- **v4 (Codex vòng 2):** sửa migration/`sessions`, cardinality, versioning link, provider, gate `PUB_R05`, hợp đồng route và Caddy, phụ thuộc Phase 12, timebox bắt buộc/stretch; tách phụ lục hạ tầng; chỉ dùng nguồn chính thức; sửa lời khuyên sai về Quick Tunnel (không hỗ trợ SSE). Chi tiết ở master-plan mục 9.

## Ba điều cần nhớ

1. Bộ dữ liệu hiện tại là **giả lập**: kiểm chứng kỹ thuật, không chứng minh bot đúng với quy trình VSF thật.
2. Các con số chất lượng trong PRD là **mục tiêu**; chỉ báo cáo số đã đo trên golden test.
3. Landing chỉ mượn **bố cục** của VLearn; ảnh phải có giấy phép và chú thích "minh họa"; không dùng logo Vin/VSF khi chưa được đồng ý.

## Khi duyệt xong

Việc đầu tiên là Phase 0: tạo thư mục repo mới, chép **có chọn lọc** tài liệu (bản cũ vào `archive/`), gửi mentor danh sách xin dữ liệu thật, chuẩn bị VPS, rồi mới đẩy lên GitHub. Bước đẩy lên GitHub cần xác nhận riêng.
