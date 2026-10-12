# PDF sang Word giữ bố cục và OCR cho PDF scan

Ngày 09/10/2026. Cả hai tính năng **tắt mặc định** (`PDF_TO_WORD_ENABLED`, `OCR_ENABLED`), không có migration.

## 1. PDF gốc sang Word để sửa (pdf2docx)

**Vấn đề:** bộ chuyển PDF sang Word của ONLYOFFICE cho ra 1.700 khung chữ trôi nổi (không sửa như Word được), còn dựng lại từ Markdown thì mất bố cục.
**Cách làm:** dùng `pdf2docx` (giấy phép MIT) phân tích bố cục thành đoạn văn và bảng thật, rồi bỏ các ngắt mục trung gian để văn bản chảy liền.

Đo thật trên `PUB_R03` (25 trang): chuyển mất 4,8 giây; 414 đoạn văn; trình soạn thảo xếp thành 27 trang (gốc 25); fonts, căn đều hai bên, đậm nghiêng giữ nguyên. Hạn chế: tiêu đề và số trang lặp ở đầu mỗi trang gốc thành dòng nằm giữa văn bản; không tiêu đề kiểu "Heading".

**Giữ Markdown đã chunk, biết sửa ở đâu** (`markdown_patch.py`):
- `M`: Markdown đọc từ PDF gốc (đã chunk và embedding). `B0`: Markdown đọc từ bản Word ngay sau khi chuyển. `B1`: Markdown đọc từ bản Word sau khi HR sửa. B0 và B1 dùng chung một bộ đọc nên khác biệt giữa chúng chính là phần HR sửa.
- So B0 với B1 theo từng từ. Mỗi chỗ sửa được neo vào M bằng hai chuỗi 5 từ giống hệt và duy nhất ở hai bên; chỉ đoạn giữa hai mỏ neo được thay bằng đoạn tương ứng của B1. Phần còn lại của M giữ nguyên từng ký tự.
- Không neo được (văn bản lặp, M và B0 quá lệch) thì dùng nguyên B1 như trước.

Đo thật: M và B0 giống nhau 99,84% theo từ. Sửa 3 chỗ: chỉ 3 trên 1.335 dòng của M đổi (dùng nguyên B1 thì 1.029 dòng đổi), mất 0,8 giây.

**Pháp lý (cần quyết định):** `pdf2docx` là MIT nhưng phụ thuộc **PyMuPDF (AGPL-3.0 hoặc giấy phép thương mại của Artifex)**. Bật tính năng trong ứng dụng mạng có thể buộc cung cấp mã nguồn cho người dùng (cả người dùng nội bộ). Chưa xin ý kiến pháp lý; mình không đưa ra kết luận.

## 2. OCR cho PDF scan (Tesseract qua OCRmyPDF)

Không dùng mô hình Hugging Face hay Modal. Tesseract 5.5 + gói `vie`, chạy CPU ngay trong backend.

| Phép đo (5 trang PUB_R03 giả scan: 200 dpi, nghiêng nhẹ, JPEG 55) | Kết quả |
|---|---|
| Sai ký tự (CER) | 1,0 đến 1,1% (bỏ dấu 0,47%) |
| Sai từ (WER) | 3,0 đến 3,1% |
| Số liệu sai/mất | 3 trên 69 |
| Thời gian trong ảnh Docker, 2 luồng | 22 giây cho 5 trang (khoảng 4,4 giây mỗi trang) |

Luồng: tải PDF có quá ít chữ lên (OCR bật) thì lưu file, tạo bản nháp `PROCESSING` và việc nền `INGEST_VERSION`; OCR xong, đọc thành Markdown, bản nháp thành `DRAFT`, file gốc là PDF có lớp chữ. Hỏng thì bản nháp về `DRAFT` kèm lý do để xóa được. Giao diện báo "đang OCR" và nhắc **soát lại chữ** (nhất là số liệu, ngày tháng, số hiệu) khi bản nháp đến từ OCR.

**Chưa đo:** scan thật (`PUB_R05`, 39 trang, không có đáp án), ảnh chụp bằng điện thoại, bảng phức tạp. Số liệu sai 4,3% hơi vượt ngưỡng kế hoạch (1/30): kết quả OCR luôn cần người soát.
**Dùng `--force-ocr`:** Ghostscript 10.0 của Debian bookworm bị OCRmyPDF từ chối với `--skip-text` (lỗi làm hỏng PDF có sẵn chữ), nên mọi trang đều được nhận dạng lại.

## 3. Bật tính năng

Ảnh backend tăng từ khoảng 0,8 GB lên 1,4 GB (Tesseract, Ghostscript, OpenCV, PyMuPDF): kiểm tra ổ đĩa `vsf-aws` trước khi deploy.

```
PDF_TO_WORD_ENABLED=true      # cần quyết định pháp lý ở mục 1
OCR_ENABLED=true              # OCR_LANGUAGES=vie+eng, OCR_MAX_PAGES=60, OCR_JOBS=1, OCR_TIMEOUT_SECONDS=1800
```

OCR chạy `nice -n 15` và 1 luồng, nhưng vẫn dùng CPU chung với embedding trên `vsf-aws` (2 vCPU); bản scan dài sẽ làm API chậm hơn trong lúc chạy.
