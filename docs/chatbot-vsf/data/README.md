# Bộ dữ liệu test — VSF Onboarding Assistant

> Sinh tự động bằng `tools/generate_seed.py`; kiểm bằng `tools/validate_seed.py`. Đừng sửa tay các file trong `documents/` (sẽ bị ghi đè); sửa nội dung ở `tools/content_*.py` rồi sinh lại.

## Đây là dữ liệu gì và **không** phải là gì

- **Chỉ có PDF và DOCX** (đúng định dạng tài liệu thật), không dùng Markdown làm nguồn.
- Tài liệu `SYN_*` là **giả lập** (ví dụ Vinmec, Ubuntu, VinSOC, đầu mối, biểu mẫu chỉ để mô phỏng). Tài liệu `PUBSUM_*` là **tổng hợp từ nguồn công khai của bên thứ ba** về VSF (ITviec, VietnamWorks, IT Review); không phải văn bản chính thức của VSF. Tài liệu `PUB_*` là văn bản pháp luật thật.
- **Không có tài liệu onboarding thật của VSF** trên mạng. Bộ này chỉ kiểm chứng kỹ thuật ingest và hành vi bot; **không chứng minh** bot đúng với quy trình VSF thật. Khi có tài liệu đã xác nhận, thay vào `documents/` và cập nhật `registry/`.

## Độ dài và cấu trúc tài liệu

- 33 tài liệu ở dạng **bản dài** (SOP/chính sách đầy đủ): tổng khoảng 98,121 từ, 226 trang; mỗi file 4–26 trang. Khung mỗi tài liệu: bảng kiểm soát tài liệu, mục đích và phạm vi, thuật ngữ, vai trò và trách nhiệm, quy trình từng bước, bảng thời hạn xử lý, ngoại lệ, lỗi thường gặp, checklist, mẫu email, hỏi đáp, lịch sử sửa đổi.
- Các tài liệu cùng series (nghỉ phép 2023/2024/2027, mật khẩu v1/v2, ngày đầu v3.2/v3.3) cố ý có cấu trúc gần giống nhau để buộc hệ thống chọn đúng bản theo ngày hiệu lực.
- Nội dung bản dài do mô hình ngôn ngữ soạn theo khung SOP và được kiểm bằng script (dữ kiện chuẩn, chuỗi cấm giữa các phiên bản, không email/URL/số điện thoại lạ). Chưa được người đọc rà toàn bộ; sửa ở `tools/long_*.py`.

## Cấu trúc

```text
documents/<pack>/          PDF/DOCX theo pack (xem bảng dưới)
registry/                  JSON: categories, teams, users, contact_channels, approved_links, forms, procedures
registry/invalid/          fixture sai (phải bị bắt bởi quy tắc INV15/17/18)
eval/golden_dev.jsonl      câu hỏi vàng tập dev
eval/golden_test.jsonl     câu hỏi vàng tập test đóng băng
eval/golden_summary.json   thống kê; golden_schema.json mô tả trường
manifests/documents_manifest.csv       metadata và kết quả ingest kỳ vọng từng file
manifests/real_public_sources.csv      nguồn công khai cần tải tay
tools/                     script sinh và kiểm tra
```

## Các pack

| Pack | Số file | PDF | DOCX | Mô tả |
|---|---:|---:|---:|---|
| `core` | 30 | 13 | 17 | Kho chính, không mâu thuẫn nhau; dùng cho phần lớn câu hỏi. Gồm chính sách, quy trình onboarding và hai bản tổng hợp công khai về VSF. |
| `format_edge` | 3 | 2 | 1 | Định dạng khó: bảng gộp ô, DOCX không heading, PDF không heading. |
| `conflict` | 1 | 0 | 1 | Tài liệu cố tình mâu thuẫn với core (chỉ nạp khi test conflicting_sources). |
| `injection` | 1 | 0 | 1 | Tài liệu chứa câu lệnh kiểu prompt injection (chỉ nạp khi test an toàn). |
| `ingest_defects` | 5 | 4 | 1 | File phải bị từ chối hoặc cần OCR khi upload: scan, bí mật, chứa secret, hỏng, sai loại file. |
| `real_public` | 5 | 5 | 0 | Tài liệu thật công khai (luật lao động, v.v.). Không commit; bổ sung thêm bằng cách tải tay theo manifests/real_public_sources.csv. |

## Kết quả ingest kỳ vọng (cột `expected_ingest` trong manifest)

| Giá trị | Ý nghĩa |
|---|---|
| `ACTIVE_OK` | Nạp bình thường, được duyệt và tìm được |
| `ACTIVE_OK_EXPIRED` | Nạp được nhưng đã hết hiệu lực; không được dùng để trả lời (test chọn phiên bản, `expired_only`) |
| `ACTIVE_OK_FUTURE` | Nạp được, có hiệu lực từ tương lai; chưa được dùng trước ngày hiệu lực |
| `ACTIVE_OK_CONFLICT` | Nạp được nhưng mâu thuẫn với tài liệu khác (test `conflicting_sources`) |
| `ACTIVE_OK_INJECTION` | Nạp được nhưng chứa lệnh chèn; bot coi là dữ liệu |
| `QUALITY_WARN_TABLE` / `QUALITY_WARN_NO_HEADING` | Nạp được kèm cảnh báo chất lượng ở `quality_report` |
| `NEEDS_OCR` | PDF scan; không bật OCR thì phải từ chối kèm lý do |
| `REJECT_CONFIDENTIALITY` / `REJECT_SECRET` / `REJECT_CORRUPT` / `REJECT_MIME_MISMATCH` | Phải bị từ chối khi upload |

## Câu hỏi vàng

- Tổng 242 câu (165 dev, 77 test đóng băng), trong đó 18 câu nhiều lượt.
- Ngày mặc định `as_of` = 2026-09-20 (giờ Việt Nam); một số câu đặt `as_of` khác để kiểm tra chọn đúng phiên bản theo ngày.
- Mỗi câu có `packs` cần nạp; chạy pack `real_public` cho câu về luật, `conflict`/`injection`/`ingest_defects` cho câu kiểm tra riêng.

## Việc cần tự làm

1. Tải tay các nguồn trong `manifests/real_public_sources.csv` (trạng thái `TO_DOWNLOAD`) vào `documents/real_public/manual/`; công cụ tự động bị chặn (403) trên một số trang.
2. Viết lại vài quy trình onboarding **thật** từ trải nghiệm của bạn (ai cấp laptop, xin quyền ở đâu), ẩn danh, bổ sung vào registry.
3. Xin mentor 1–2 tài liệu thật để thay dần dữ liệu giả lập.

## Giới hạn

- DOCX được dựng bằng `python-docx`; máy sinh dữ liệu không có Word/LibreOffice nên **chưa xem trực quan DOCX**, chỉ kiểm bằng cách đọc lại cấu trúc.
- PDF dùng font Arial (hoặc DejaVu) để có tiếng Việt; cần font này khi sinh lại.
- Địa chỉ email, tên miền `vsf-demo.example` và mã phiếu VinSOC đều là giả.
- `documents/real_public/` là **tùy chọn** và không được commit. Thiếu nó thì `validate_seed.py` chỉ ghi chú bỏ qua (không lỗi). **Chỉ chạy `generate_seed.py` trên máy có `real_public/`**: thiếu nó, các dòng `real_public` bị bỏ khỏi manifest và README.
