# Golden set v0 (bản nháp, chờ người duyệt)

Sinh ngày 10/10/2026 từ các tài liệu **ACTIVE đang tìm kiếm được trong DB dev** (9 tài liệu, 99 mục; xuất ở `kho_muc_dev.json`). Bốn tài liệu đã ARCHIVED (Luật Công đoàn và các bản "Các trường hợp ngoại lệ ngày 1") **không** nằm trong kho vì Viga không tìm thấy chúng.

| Tệp | Nội dung |
|---|---|
| `golden_v0_nhap.jsonl` | 120 câu đầy đủ trường (mã mục thật `section_id`, trích dẫn chuẩn, nhãn route/công cụ, tập phát triển hay đóng băng) |
| `golden_v0_duyet.json` | **Bản dễ đọc để duyệt**: JSON thụt dòng, xếp theo nhóm, mỗi câu có khối `duyệt` cho 2 người (sinh bằng `../scripts/export_review_json.py`) |
| `golden_v0_duyet.csv` | Bản để mở bằng Excel và duyệt (UTF-8, có cột quyết định cho **2 người**) |
| `kho_muc_dev.json` | Các mục tài liệu làm kho đo (id mục, nội dung) |
| `../scripts/generate_golden_draft.py` | Script sinh (hạt giống cố định, chạy lại cho cùng bố cục) |

## Cơ cấu (120 câu)

| Nhóm | Số câu | Đơn / kép |
|---|---|---|
| Tài liệu: một sự kiện | 50 | đơn |
| Tài liệu: câu kép 2 ý / 3 ý | 17 / 8 | kép |
| Tài liệu: không có căn cứ | 8 | đơn |
| Hành trình: công cụ (persona newhire3) | 16 / 6 | đơn / kép |
| Ngoài phạm vi, cá nhân, chèn lệnh, xã giao | 5 / 5 / 3 / 2 | đơn |

Tổng: 89 đơn, 31 kép. Tập phát triển 83 câu, tập đóng băng 37 câu (chia theo nhóm, hạt giống cố định). Ngoài phạm vi + cá nhân + chèn lệnh = 13 câu (11%), đạt yêu cầu "đối kháng ≥ 10%" của slide.

## Đã kiểm tự động

- Mọi "trích dẫn chuẩn" và "ý bắt buộc" của câu tài liệu nằm **nguyên văn** trong mục tương ứng (dùng đúng hàm so khớp `text_match.quote_matches` của Viga): 0 trường hợp lệch.
- Tài liệu **trùng** nội dung (tài liệu "Ngoại lệ laptop" xuất hiện hai lần) chỉ dùng một bản làm nguồn; mã mục của bản kia ghi ở `tương_đương_section_id` để khi chấm truy hồi không bị tính sai.
- Tài liệu "bản cũ, đã thay thế" **không** làm nguồn câu hỏi nhưng vẫn nằm trong kho như nhiễu mâu thuẫn.

## Người duyệt cần kiểm gì (từng dòng trong CSV)

1. **Câu hỏi tự nhiên và rõ nghĩa chưa?** (nhân viên mới có hỏi vậy không?)
2. **Đáp án chuẩn đúng với tài liệu không và đủ ý không?** Đối chiếu cột "trích dẫn chuẩn".
3. **Cột "mục gần nhất" (câu không có căn cứ):** câu thật sự **không** trả lời được từ tài liệu? Nếu trả lời được thì sửa nhãn hoặc bỏ.
4. **Câu hành trình (công cụ):** công cụ kỳ vọng đúng chưa? Câu kép nhiều công cụ: kỳ vọng nên trả lời đủ các ý hay chấp nhận một công cụ?
5. **Ca đã thấy:** `gd_001` có đáp án chuẩn là "tài liệu chưa có quy định" (tài liệu nói rõ chưa có quy định): quyết định nhãn là `ANSWER` (nêu rằng chưa có quy định) hay `NO_BASIS`.
6. Quyết định **giữ / sửa / bỏ**; nếu sửa thì ghi nội dung sửa ở cột bên cạnh.

Slide yêu cầu **ít nhất 2 người** duyệt mỗi đáp án và Cohen's κ ≥ 0,6 giữa hai người; nếu chỉ có một người thì ghi rõ trong báo cáo là chưa đạt chuẩn này.

## Hạn chế đã biết

- Câu hỏi sinh từ các mục có sẵn nên **thiên về mục "ngoại lệ"** (nhiều nhất từ hồ sơ/hợp đồng 31 lượt) và rất ít từ "Hỏi đáp bổ sung" (1); nên thêm câu thật từ nhân viên/HR nếu có.
- Kho dev chỉ 99 mục, nên truy hồi dễ; **khó phân biệt rerank có tốt hơn hay không** (xem `ke-hoach-benchmark-chuan-theo-slide.md`, mục 8 và 11).
- Đáp án chuẩn do DeepSeek viết nháp; chỉ được tin sau khi người duyệt.
- Chưa có câu hỏi nhiều lượt (theo yêu cầu: chỉ đơn và kép).
