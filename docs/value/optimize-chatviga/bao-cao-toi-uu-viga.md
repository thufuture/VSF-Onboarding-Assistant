# Báo cáo tối ưu Viga: sửa lỗi, router v2 và giảm ngữ cảnh

Nhánh: `feat/viga-context-optimization`. Ngày chạy: 11/10/2026. Đây là phần tiếp của [bao-cao-benchmark-viga.md](bao-cao-benchmark-viga.md) (so sánh có và không có rerank). Giải thích từng chỉ số: [giai-thich-chi-so.md](giai-thich-chi-so.md). Số liệu thô: `ket-qua/so-sanh/`.

> **Đọc trước:** mỗi cấu hình chỉ chạy **1 lượt** trên cùng bộ ~120 câu golden (nhãn bản nháp, chưa có người duyệt), kho thử 100 mục. Chênh lệch nhỏ (vài điểm %) chưa đáng tin. Mọi thay đổi trong báo cáo nằm **sau cờ cấu hình mặc định tắt**: merge không đổi hành vi production.

## 1. Tóm tắt

| Thay đổi | Kết quả | Kết luận |
|---|---|---|
| **A1. Sửa lỗi BM25 với ký tự đặc biệt** | Tỉ lệ lỗi 1,3% → 0% ở cả 4 biến thể (đều chứa bản sửa); thử riêng 3 câu có `[ ] " ( ) :` đều trả kết quả | **Nên merge**, không cần cờ, không đổi kết quả câu đang chạy tốt |
| **A2/A3. Router v2** (`VIGA_ROUTER_V2`) | Ngoài phạm vi 0% → 100%, chèn lệnh 0% → 100%, thông tin cá nhân 80% → 100%, chọn đúng công cụ 68,8% → 75%. Chỉ số tài liệu không đổi. An toàn vẫn 100%. **Nhưng** độ phủ công cụ ở câu kép 58% → 33% (6 câu) | **Nên bật**, kèm theo dõi câu kép; cần xem lại (xem 3.2) |
| **B. Cắt ngữ cảnh bằng top-k, ngưỡng, khử trùng lặp, trần token** | Token vào giảm ~65–70%, chi phí LLM mỗi câu giảm ~50%. **Nhưng** Context Recall tụt 98,7% → 70–77%, phủ ý 75% → 58–63%, điểm "đúng" 4,51 → 4,03–4,17. **Tốc độ không cải thiện.** | **Không bật.** Cắt không dùng rerank làm mất mục đúng |
| **Phát hiện chính** | Bước trả lời tốn 3,2–3,8 giây dù ngữ cảnh giảm 70%: thời gian nằm ở **suy luận ẩn** (~450–560 token), không ở đọc ngữ cảnh | Muốn nhanh hơn phải điều khiển suy luận (C2), không phải cắt ngữ cảnh |

## 2. Cấu hình đã đo

| Nhãn | Cờ | Mô tả |
|---|---|---|
| R0 | không | Viga hiện tại (từ báo cáo trước) |
| V_router | `VIGA_ROUTER_V2=1` | Router tách xã giao / ngoài phạm vi / chèn lệnh, làm rõ `get_day_plan` |
| V_k5 | `RETRIEVAL_MAX_SECTIONS=5` | Giữ tối đa 5 mục mỗi câu hỏi con |
| V_k3 | `RETRIEVAL_MAX_SECTIONS=3` | Giữ tối đa 3 mục |
| V_k5_dedupe_cap | `MAX_SECTIONS=5`, `DEDUPE_SECTIONS=1`, `TOTAL_TOKEN_CAP=2500` | Thêm khử trùng lặp giữa câu con và trần 2.500 token cho cả lượt |

Mọi biến thể đều chạy trên mã đã có bản sửa BM25. Bộ an toàn 46 câu chỉ chạy lại cho V_router (các biến thể B bị loại ở golden nên không tốn thêm).

## 3. Kết quả

### 3.1 Sửa lỗi BM25 (A1)

Cách làm: thử truy vấn gốc trước; chỉ khi ParadeDB báo `could not parse query string` mới bỏ ký tự cú pháp và thử lại, trong SAVEPOINT để không hỏng giao dịch. Nhờ đó câu đang chạy tốt không đổi kết quả. Kiểm tra thủ công trên DB bench: câu thường trả 30 kết quả như cũ; câu `[ trong tài liệu ngày 1 ] , [ bổ sung ... ]` và câu `hợp đồng "quá hạn" (ký) : sao?` trả 30 và 25 kết quả thay vì lỗi, và phiên vẫn dùng tiếp được. Trên golden: tỉ lệ lỗi 1,3% (2/150 câu) → 0% ở cả 4 biến thể. Có 2 test đơn vị mới cho hàm làm sạch ký tự (cộng 5 test cho `limit_context` và 2 test cho router v2). Việc còn thiếu: test tích hợp với DB thật (chưa viết, xem mục 6).

### 3.2 Router v2 (A2/A3)

| Nhóm câu | n | R0 đúng | V_router đúng |
|---|---|---|---|
| tài liệu | 83 | 96,4% | 96,4% |
| công cụ hành trình | 22 | 77,3% | 72,7% |
| thông tin cá nhân | 5 | 80,0% | 100% |
| xã giao | 2 | 100% | 100% |
| **ngoài phạm vi** | 5 | **0%** | **100%** |
| **chèn lệnh** | 3 | **0%** | **100%** |

Luồng B: chọn đúng công cụ (câu đơn) 68,8% → 75,0%; đúng tham số ngày vẫn 50%; **độ phủ công cụ ở câu kép 58,3% → 33,3%**. Chỉ số trả lời tài liệu giữ nguyên (Recall 98,7%, Hit@1 54,7%, North Star 62,7%, loại phản hồi đúng 92% → 93,3%). Bộ an toàn 46 câu: an toàn cơ học vẫn 100% ở mọi bộ.

Điều cần lưu ý:
- Nhóm câu kép chỉ có 6 câu, 1 lượt: thay đổi 58% → 33% là 1 đến 2 câu, có thể là nhiễu, nhưng cùng chiều với việc công cụ hành trình giảm nhẹ (77% → 73%). Trước khi bật cần chạy lại nhiều lượt và xem 6 câu đó.
- Chi phí mỗi câu tăng nhẹ do prompt router dài hơn (tổng $0,0046 so với $0,0042 tính cả mọi luồng; phần chênh nằm trong nhiễu của lượt chạy).
- Tham số ngày vẫn 50%: lời nhắc thêm vào chưa sửa được. Cần xem các câu sai cụ thể để chỉnh.

### 3.3 Cắt ngữ cảnh (B): đo được gì

| Chỉ số (câu có đáp án) | R0 | V_k5 | V_k3 | V_k5_dedupe_cap |
|---|---|---|---|---|
| Context Recall | 98,7% | **76,9%** | **69,8%** | **76,0%** |
| Context Precision | 2,4% | 15,9% | 23,6% | 15,6% |
| Hit@1 | 53,3% | 54,7% | 52,9% | 54,4% |
| Phủ ý bắt buộc | 75,3% | 60,3% | 58,2% | 63,2% |
| Faithfulness | 85,5% | 92,4% | 90,1% | 91,5% |
| Đúng (1–5) | 4,51 | 4,17 | 4,03 | 4,15 |
| North Star (đúng + có căn cứ) | 61,3% | 62,7% | 58,7% | 58,7% |
| Đúng loại phản hồi | 92,0% | 88,0% | 85,3% | 86,7% |
| Mục đưa vào LLM | 56,8 | 7,9 | 4,5 | 7,5 |
| Token vào (cả câu) | 15.652 | 5.610 | 4.663 | 5.305 |
| Chi phí LLM/câu (mọi luồng) | $0,0042 | $0,0020 | $0,0019 | $0,0020 |
| P50 luồng tài liệu (giây) | 5,75 | 5,66 | 5,72 | 5,57 |
| P95 luồng tài liệu (giây) | 10,26 | 12,11 | 16,11 | 11,86 |
| Bước trả lời (giây, tb) | 3,22 | 3,03 | 3,62 | 3,37 |

**Vì sao thất bại.** Hit@1 của thứ hạng hiện tại chỉ 53%: gần một nửa số câu, mục đúng không đứng đầu. Cắt xuống 5 hay 3 mục là cắt theo thứ hạng đó, nên mất mục đúng (Recall −22 đến −29 điểm). Faithfulness tăng (92%) vì ít ngữ cảnh thì ít cơ hội bịa, nhưng câu trả lời **ít đúng hơn** (điểm "đúng" tụt 0,34 đến 0,48, p < 0,01) và thiếu ý. North Star không cải thiện vì đúng giảm bù faithfulness tăng. Ngược lại rerank (báo cáo trước) cải thiện Hit@1 lên 82% nên cắt xuống 5 mục vẫn giữ Recall 95,6%. **Cắt chỉ an toàn khi thứ hạng tốt.**

**Vì sao không nhanh hơn.** Ngữ cảnh giảm từ 15,8k xuống 4,8k token (−70%) nhưng bước trả lời vẫn 3,0–3,6 giây (R0: 3,2–3,5). Số token suy luận ẩn ở bước trả lời giữ nguyên ~450 đến 560 mỗi câu. Kết luận: **thời gian trả lời do suy luận quyết định, không do độ dài ngữ cảnh**. Phần tiết kiệm thật là chi phí (giảm ~50%), không phải tốc độ. P95 còn tệ hơn (tới 16 giây ở k=3), có thể do thử lại khi trích dẫn không hợp lệ vì mất mục đúng; chưa xác minh.

## 4. Việc nên làm tiếp (theo số liệu)

| Ưu tiên | Việc | Căn cứ |
|---|---|---|
| 1 | Merge A1 (sửa BM25) | Lỗi thật, không đổi hành vi câu bình thường |
| 2 | Bật router v2 sau khi xem lại 6 câu kép và các câu sai tham số ngày | +100 điểm ở ngoài phạm vi và chèn lệnh, không ảnh hưởng tài liệu |
| 3 | **Thử điều khiển suy luận ở bước trả lời** (tắt cho câu một ý, bật cho câu nhiều ý), có cờ | Đây là nơi thời gian thật sự nằm; trước đây đo cho thấy nhanh hơn 20–30% |
| 4 | Giữ cờ cắt ngữ cảnh ở trạng thái tắt; chỉ xét lại khi có thứ hạng tốt hơn (rerank nhẹ hoặc cải thiện thuật toán xếp hạng) | Đo ở 3.3 |
| 5 | Nâng chất lượng thứ hạng trước (Hit@1 53%): ví dụ điều chỉnh trọng số BM25 và vector, thêm ngữ cảnh tài liệu vào đoạn trước khi nhúng | Nút thắt thật là thứ hạng |
| 6 | Duyệt nhãn, chạy ≥3 lượt trước khi kết luận chính thức | Chưa đủ tin cậy |

## 5. Giải thích các chỉ số

Xem [giai-thich-chi-so.md](giai-thich-chi-so.md): Context Recall/Precision, Hit@k, MRR, Faithfulness, Answer Relevancy, North Star, P50/P95, p-value, κ…

## 6. Hạn chế

- **Một lượt mỗi cấu hình**, nhãn vàng nháp, kho 100 mục (như báo cáo trước). Hai giám khảo đồng thuận κ 0,41 (chưa đạt 0,6).
- Nhóm nhỏ: câu kép công cụ 6 câu, ngoài phạm vi 5, chèn lệnh 3. Số 100% ở nhóm nhỏ không phải bằng chứng mạnh.
- Bộ an toàn chỉ chạy lại cho router v2, chưa chạy cho các biến thể B.
- Chưa có test tích hợp cho `_bm25_search` với DB thật (chỉ test hàm làm sạch và kiểm tay trên DB bench).
- Chưa đo C2 (tắt suy luận theo số câu con), C3 (bộ nhớ đệm prompt), C4 (stream): chưa code.
- Nguyên nhân P95 tăng khi cắt ngữ cảnh mới là suy đoán.
- Chi phí so sánh giữa các lượt có nhiễu giá và nhiễu mô hình.

## 7. Cờ cấu hình (đều mặc định tắt)

| Biến môi trường | Tác dụng |
|---|---|
| `VIGA_ROUTER_V2=1` | Router v2 |
| `RETRIEVAL_MAX_SECTIONS=N` | Giữ N mục mỗi câu con (0 = tắt) |
| `RETRIEVAL_MIN_SCORE_RATIO=r` | Bỏ mục có điểm < r × điểm mục đầu (chưa đo riêng) |
| `RETRIEVAL_TOTAL_TOKEN_CAP=N` | Trần token ngữ cảnh cho cả lượt |
| `RETRIEVAL_DEDUPE_SECTIONS=1` | Không đưa lại mục đã có ở câu con trước |

Rollback: bỏ biến môi trường hoặc đặt về giá trị mặc định. A1 không có cờ (không đổi kết quả câu đang chạy tốt).
