# Kế hoạch: benchmark bản tối ưu (RRF tối ưu, có và không rerank, suy luận bật/tắt/thích ứng)

Ngày: 11/10/2026. Nối tiếp [bao-cao-toi-uu-viga.md](bao-cao-toi-uu-viga.md). Giải thích từng chỉ số: [giai-thich-chi-so.md](giai-thich-chi-so.md).

## 1. Mục đích

Trả lời ba câu hỏi bằng số liệu:
1. **Chỉnh cách trộn BM25 và vector (RRF) có cải thiện thứ hạng không**, và có đủ để khỏi cần rerank không?
2. **Rerank đã tối ưu có đáng đánh đổi về tốc độ không** so với RRF đã tối ưu?
3. **Suy luận ở bước trả lời** (bật luôn, tắt luôn, thích ứng theo độ phức tạp câu hỏi) ảnh hưởng chất lượng, tốc độ và chi phí thế nào?

Kết quả quyết định hướng tiếp theo của Viga (không phải để kết luận cuối cùng, vì nhãn còn là bản nháp và chỉ chạy một lượt).

## 2. Thiết kế thí nghiệm

### 2.1 Tách dữ liệu 50 / 70
- **70 câu "chỉnh"**: chỉ dùng để chọn tham số (RRF, rerank). 
- **50 câu "kiểm"**: chưa từng dùng để chọn tham số, dùng để so sánh cuối cùng.
- Chia theo tầng (nhóm câu hỏi, độ khó, kiểu diễn đạt) và hạt giống cố định, nên cả hai tập bao quát cùng các tình huống.
- Lý do: chọn tham số và kiểm tra trên cùng câu sẽ thổi phồng kết quả.

Cơ cấu 50 câu kiểm: tài liệu một sự kiện 14, kép 2 ý 7, kép 3 ý 5, không có căn cứ 4, công cụ đơn 6, công cụ kép 4, thông tin cá nhân 3, ngoài phạm vi 3, chèn lệnh 2, xã giao 2.

### 2.2 Giai đoạn chỉnh tham số (trên 70 câu, chỉ truy hồi, **không gọi LLM**)
Đáp án chuẩn đã ghi sẵn mục tài liệu đúng, nên chấm thứ hạng không cần mô hình đọc.

- **Quét RRF:** `k` ∈ {10, 30, 60, 100} × hệ số nhánh BM25 : vector ∈ {0,5; 1; 2}, thêm hai mốc đối chứng BM25 riêng và vector riêng. Chọn cấu hình có Hit@1 và MRR tốt nhất mà Recall không tụt.
- **Quét rerank:** trên cấu hình RRF tốt nhất, thử (a) câu hỏi đưa cho reranker: câu đã tách từ (hiện tại) hay câu gốc; (b) số ứng viên 20 hay 12; (c) độ dài tối đa mỗi cặp 512 hay 256 token. Đo Hit@1, Recall, thời gian chấm một câu.
- Cổng chấp nhận cho mọi phương án tăng tốc: Hit@1 và Recall không tụt quá 2 điểm so với 20 ứng viên, 512 token.

### 2.3 Giai đoạn so sánh cuối (trên 50 câu, chạy Viga đầy đủ)
Ma trận 2 × 3, mỗi ô một lượt:

| | Suy luận bật luôn | Suy luận tắt luôn | Suy luận thích ứng |
|---|---|---|---|
| **RRF tối ưu** | A-bật | A-tắt | A-thích-ứng |
| **RRF tối ưu + rerank tối ưu** | B-bật | B-tắt | B-thích-ứng |

Mọi ô dùng bản sửa BM25 (router v2 không bật ở các ô này, xem báo cáo cuối). Cắt ngữ cảnh không dùng (đã chứng minh làm hỏng truy hồi khi không có thứ hạng tốt).

**Quy tắc "thích ứng":** suy luận bật khi câu hỏi được tách thành nhiều hơn một câu con; tắt khi chỉ có một câu con. Lý do: đo trước đây cho thấy tắt suy luận làm câu nhiều ý mất ý, còn câu một ý trả lời tốt mà nhanh hơn 20 đến 30%.

Điểm khác với phiên bản trước: để rerank tốn thời gian không lặp lại ba lần, điểm rerank được lưu lại theo (câu hỏi, đoạn) và dùng lại giữa ba ô B.

## 3. Các chỉ số và vì sao đo chúng

| Nhóm | Chỉ số | Mục đích trong thí nghiệm này |
|---|---|---|
| Thứ hạng | Hit@1, Hit@3, Hit@5, MRR | Đo trực tiếp chất lượng xếp hạng, thứ cần cải thiện khi chỉnh RRF và rerank |
| Phủ | Context Recall | Bảo đảm mục đúng không bị bỏ rơi khi cắt ứng viên hoặc rút ngắn |
| Gọn | Context Precision, số mục và token đưa vào | Đo mức "rác" đưa cho mô hình, liên quan chi phí và thời gian |
| Trả lời | Faithfulness, Đúng, Đủ ý, phủ ý bắt buộc, Liên quan | Xem thứ hạng tốt hơn có thành câu trả lời tốt hơn không |
| Chỉ số chính | North Star (đúng và có căn cứ) | Một con số quyết định "bản nào tốt hơn" |
| Phản hồi | Đúng loại phản hồi, tỉ lệ lỗi | Không được tệ đi |
| Tốc độ | P50, P95 theo luồng và theo bước | Đo đánh đổi của rerank và suy luận |
| Chi phí | Token vào/ra, USD mỗi câu | Đo hiệu quả kinh tế |
| Độ tin cậy | κ và Spearman giữa hai giám khảo, khoảng tin cậy, p-value cặp | Cho biết chênh lệch nào đáng tin |

Phân tích tách riêng **câu một ý** và **câu nhiều ý**, vì suy luận ảnh hưởng hai nhóm này khác nhau.

## 4. Các bước thực hiện và tệp tạo ra

| Bước | Việc | Tệp |
|---|---|---|
| 1 | Tách 50/70 theo tầng | `scripts/make_subsets.py` → `bo-cau-hoi/tap_kiem_50.json`, `bo-cau-hoi/tap_chinh_70.json` |
| 2 | Quét RRF (không LLM) | `scripts/sweep_rrf.py` → `ket-qua/quet-tham-so/rrf.json`, `rrf.md` |
| 3 | Quét rerank | `scripts/sweep_rerank.py` → `ket-qua/quet-tham-so/rerank.json`, `rerank.md` |
| 4 | Cờ chế độ suy luận trong sản phẩm (`ANSWER_THINKING_MODE`) + test | `backend/src/config.py`, `backend/src/services/viga/answer_service.py` |
| 5 | Mở rộng harness: trọng số RRF, câu gốc cho reranker, độ dài, bộ nhớ đệm điểm rerank | `scripts/run_viga_benchmark.py` |
| 6 | Chạy ma trận 6 ô trên 50 câu, chấm hai giám khảo | `ket-qua/F_*` |
| 7 | Tổng hợp, so sánh cặp | `scripts/summarize_final.py` → `ket-qua/cuoi/*.json`, `.md` |
| 8 | Báo cáo, giao diện biểu đồ | `bao-cao-benchmark-toi-uu-cuoi.md`, trang Artifact |

## 5. Rủi ro và hạn chế
- 50 câu, một lượt mỗi ô: chỉ phát hiện chênh lệch lớn. Nhóm nhỏ (ví dụ 2 câu chèn lệnh) chỉ là chỉ báo.
- Nhãn bản nháp chưa duyệt; hai giám khảo đồng thuận κ 0,41.
- Quét tham số dùng **câu gốc** (không qua bước viết lại bằng LLM) nên với câu kép chỉ gần đúng so với pipeline thật. Kết quả cuối ở bước 6 mới là pipeline đầy đủ.
- Kho chỉ 100 mục: kết quả có thể khác khi kho lớn.
- Tốc độ rerank đo trên máy dev, không phải AWS.
- Chỉnh tham số trên cùng một kho 100 mục có thể không chuyển sang kho lớn hơn.
- Nếu một tham số tốt lên nhờ RRF/rerank chỉ trong harness, muốn dùng thật phải đưa vào sản phẩm sau cờ (việc sau).

## 6. Quy ước an toàn
- Không đụng DB dev hay production (chạy trên bản chụp `vsf_bench`).
- Khóa OpenAI chỉ đọc lúc chạy từ `.env` của dự án P-040, không lưu vào repo.
- Chỉ gửi nội dung tổng hợp của benchmark cho giám khảo.
- Mọi cờ sản phẩm mặc định tắt; thay đổi chỉ có hiệu lực khi đặt biến môi trường.
