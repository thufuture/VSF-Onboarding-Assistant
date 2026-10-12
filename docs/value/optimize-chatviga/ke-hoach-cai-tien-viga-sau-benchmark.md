# Kế hoạch cải tiến Viga sau benchmark (11/10/2026)

Căn cứ: [bao-cao-benchmark-viga.md](bao-cao-benchmark-viga.md). Kế hoạch chỉ ghi việc cần làm, **chưa code**. Mỗi giai đoạn là một PR riêng, mọi thay đổi hành vi nằm sau cờ cấu hình mặc định tắt, để merge không ảnh hưởng production.

## Nguyên tắc

- Sửa lỗi chắc chắn trước, thử nghiệm sau. Mỗi thay đổi phải đo lại bằng đúng bộ benchmark này.
- Chỉ kết luận khi chạy ≥3 lượt và nhãn đã có người duyệt (giai đoạn 0).
- Guardrail của slide: P95 ≤ 5 giây, chi phí ≤ $0,05/câu, faithfulness ≥ 0,85. Không thay đổi nào được làm tụt ba chỉ số này.

## Giai đoạn 0: làm cho phép đo đáng tin (trước mọi thứ khác)

| Việc | Tiêu chí xong |
|---|---|
| 2 người duyệt nhãn vàng (golden 120 câu + an toàn 46 câu) từ file JSON đã có | Mọi nhãn có trạng thái đã duyệt; câu bất đồng được thống nhất |
| Chấm lại với nhãn đã duyệt, so với người trên mẫu ~30 câu | Spearman ≥ 0,7 và κ ≥ 0,6 giữa giám khảo và người |
| Chạy mỗi cấu hình ≥3 lượt | Báo cáo trung bình ± độ lệch chuẩn, không chỉ một lần |
| Quyết định `INFO` có tính là "từ chối đạt" cho câu ngoài phạm vi/chèn lệnh hay không | Ghi vào README bộ câu hỏi |

Chi phí ước tính: vài đô-la LLM giám khảo; phần lớn là công người duyệt.

## Giai đoạn 1: sửa lỗi chắc chắn (PR 1)

1. **Ký tự đặc biệt trong BM25** (`backend/src/services/ingest/lexical.py`, nơi dựng truy vấn trong `retrieval/hybrid_search.py`): thoát hoặc bọc từng từ; thêm test với `[ ] { } ( ) " : * ? ~ ^ + - \` và các câu thật như `gd_068`. Lỗi hiện bị nuốt thành `assistantUnavailable`: ghi log cảnh báo có tên loại lỗi.
2. **Định tuyến ngoài phạm vi và chèn lệnh**: thêm ví dụ `OUT_OF_SCOPE` và chèn lệnh vào prompt router; sửa luật regex "hôm nay … làm gì" đang bắt câu thời tiết (#110).
3. **Chọn công cụ và tham số ngày**: xem lại mô tả công cụ trong prompt router; đặc biệt `get_day_plan` (đúng tham số ngày chỉ 50%).

Đo lại: luồng A và B, tỉ lệ lỗi, an toàn. Mục tiêu: out_of_scope và injection ≥ 80% đúng nhãn; chọn công cụ ≥ 85%; tỉ lệ lỗi 0% trên bộ ký tự đặc biệt. Không đổi hành vi nào khác.

## Giai đoạn 2: giảm ngữ cảnh không cần rerank (PR 2, sau cờ)

Vấn đề: 57 mục đưa vào LLM, chỉ 2,4% đúng; token vào 15,7k/câu.
- Thử trên harness (không đụng sản phẩm): (a) cắt top-k nhỏ sau RRF, (b) ngưỡng điểm, (c) kết hợp, với k ∈ {5, 8, 10}. Mỗi biến thể 1 lượt trước, chọn 1–2 biến thể tốt nhất rồi chạy 3 lượt.
- Tiêu chí chọn: North Star không giảm so với R0, Recall ≥ 95%, token vào giảm ≥ 40%, độ trễ không tăng.
- Nếu đạt: đưa vào sản phẩm sau cờ `RETRIEVAL_CONTEXT_CAP` (tên tạm), mặc định tắt.

Câu hỏi cần trả lời: lợi ích của R1 đến từ "ít ngữ cảnh hơn" hay từ "xếp đúng thứ tự"? Nếu cắt top-k đã đủ, không cần reranker.

## Giai đoạn 3: rerank (chỉ khi giai đoạn 2 không đủ)

Cổng vào: sau giai đoạn 2 vẫn còn khoảng cách chất lượng đáng kể so với R1 (ví dụ Hit@1, North Star).
1. **Kiểm tra giấy phép** mô hình `bge-reranker-v2-m3` cho dùng thương mại.
2. **Giải bài toán tốc độ** trên harness, mỗi phương án đo chất lượng và P50/P95: giảm ứng viên 20 → 10; mô hình nhỏ hơn hoặc lượng tử hóa (ONNX/int8); GPU nếu có ngân sách. Mục tiêu: rerank ≤ 1 giây/câu.
3. **Tích hợp**: điền stub `rerank.py`, nối trong `search_to_sections`, cờ `RERANK_ENABLED` mặc định tắt, có timeout và tự rơi về thứ tự RRF nếu reranker lỗi hoặc chậm.
4. **Triển khai**: dev trước, đo, rồi mới production. Chạy reranker như dịch vụ riêng (không chung CPU với backend); chốt kích thước máy dựa trên số đo, không phỏng đoán.

Chưa có bằng chứng rằng chuyển lên AWS 2 vCPU làm rerank nhanh hơn (đo vi mô ~23 giây/20 cặp).

## Giai đoạn 4: độ trễ luồng tài liệu

P95 hiện 10,3 giây (R0). Đo trước, sửa sau:
- Tách thời gian đọc ngữ cảnh và suy nghĩ ở bước trả lời (chạy stream trong harness).
- Thử: tắt suy luận cho câu một ý, bật cho câu nhiều ý; gộp route + rewrite; embed song song với router; prompt caching của DeepSeek.
- Chỉ nhận thay đổi nếu chất lượng không giảm ngoài nhiễu.

## Giai đoạn 5: câu kép nhiều công cụ

Độ phủ công cụ ở câu kép 58,3%. Cho phép router trả nhiều công cụ trong một câu; đo lại luồng B. Làm sau giai đoạn 1 vì phụ thuộc prompt router mới.

## Giai đoạn 6: cá nhân hóa (kế hoạch ban đầu)

Chưa có số liệu nào trong lần đo này ủng hộ làm trước các giai đoạn trên. Khi các giai đoạn 1–3 xong, dùng đúng khung benchmark này (thêm bộ câu hỏi nhiều persona) để thử V1/V2 trong `ke-hoach-toi-uu-chat-viga.md`.

## Thứ tự và phụ thuộc

```
0 (nhãn, nhiều lượt) ─┬─> 1 (sửa lỗi) ──> 5 (câu kép)
                      ├─> 2 (cắt ngữ cảnh) ──> 3 (rerank, nếu cần)
                      └─> 4 (độ trễ)
                                  └──────────> 6 (cá nhân hóa)
```

Giai đoạn 1 có thể bắt đầu ngay, không cần chờ giai đoạn 0 (sửa lỗi rõ ràng, test tự kiểm). Giai đoạn 2 và 3 nên chờ nhãn đã duyệt để số đo đáng tin.

## Rủi ro cần theo dõi

- Sửa router có thể làm tụt route khác (document 96,4%): luôn chạy lại toàn bộ luồng A.
- Cắt ngữ cảnh có thể mất ý ở câu kép (phủ ý hiện 75%): theo dõi riêng nhóm câu kép 3 ý.
- Kho thử 100 mục nhỏ hơn thật: sau khi chọn phương án, kiểm tra lại trên kho lớn hơn trước khi bật ở production.
- PyMuPDF (AGPL) và giấy phép reranker là hai điểm pháp lý còn mở, cần quyết định riêng.
- Mọi cờ mặc định tắt; merge không đổi hành vi production cho đến khi bạn chủ động bật.

## Việc cần bạn quyết định

1. Có đồng ý bắt đầu giai đoạn 1 ngay (PR nhỏ) không?
2. Ai duyệt nhãn (cần 2 người) và khi nào?
3. Có ngân sách GPU hoặc sẵn sàng thử mô hình rerank nhỏ hơn không, hay dừng ở giai đoạn 2?
