# Báo cáo tổng hợp benchmark Viga (10/10 đến 12/10/2026)

Đây là tệp **đọc đầu tiên**: gom ba đợt benchmark, các trường hợp đã đo, phương pháp, số liệu chính, lý do chọn từng thứ và quy trình chốt cuối. Chi tiết từng đợt nằm ở các tệp được liên kết.

> **Mức tin cậy chung.** Mỗi cấu hình chỉ chạy **1 lượt**. Nhãn vàng là **bản nháp chưa có người duyệt**. Kho thử chỉ **14 tài liệu, 100 mục**. Ba đợt đo dùng giám khảo AI khác nhau (xem mục 3.3). Chênh lệch dưới khoảng 6 điểm phần trăm là nhiễu (cùng cấu hình truy hồi cho Hit@1 từ 69,9% đến 75,6%).

## 0. Bản đồ tệp

| Cần xem | Tệp |
|---|---|
| Tệp này (tổng hợp, lý do chọn, quy trình chốt) | `BAO-CAO-TONG-HOP-BENCHMARK-VIGA.md` |
| Đợt 1: có và không có rerank, 120 câu | [bao-cao-benchmark-viga.md](bao-cao-benchmark-viga.md) |
| Đợt 2: sửa lỗi, router v2, cắt ngữ cảnh | [bao-cao-toi-uu-viga.md](bao-cao-toi-uu-viga.md) |
| Đợt 3 (cuối): RRF tối ưu, rerank, suy luận, 50 câu kiểm | [bao-cao-benchmark-toi-uu-cuoi.md](bao-cao-benchmark-toi-uu-cuoi.md) |
| Giải thích từng chỉ số | [giai-thich-chi-so.md](giai-thich-chi-so.md) |
| Kế hoạch và phương pháp gốc (bám slide) | [ke-hoach-benchmark-chuan-theo-slide.md](ke-hoach-benchmark-chuan-theo-slide.md), [ke-hoach-benchmark-toi-uu-cuoi.md](ke-hoach-benchmark-toi-uu-cuoi.md) |
| Phân tích Viga ban đầu | [ke-hoach-toi-uu-chat-viga.md](ke-hoach-toi-uu-chat-viga.md) |
| Nhật ký lỗi tìm thấy khi đo | [nhat-ky-phat-hien.md](nhat-ky-phat-hien.md) |
| Bộ câu hỏi | `bo-cau-hoi/` (golden, an toàn, tập kiểm 50, tập chỉnh 70) |
| Kết quả thô, điểm, so sánh | `ket-qua/` (tổng hợp cuối: `ket-qua/cuoi/tong_hop.md`) |
| Mã đo | `scripts/` |
| Báo cáo triển khai vào sản phẩm (12/10) | [bao-cao-trien-khai-viga.md](bao-cao-trien-khai-viga.md) |
| Trang biểu đồ (đợt 3) | https://claude.ai/artifact/EP8ULd6rcgQQLt8VDPQVQ6 |
| Trang biểu đồ (đợt 1) | https://claude.ai/artifact/HiTdW1VbWaU3HPjzReNwsH |
| Trang biểu đồ (đợt 2) | https://claude.ai/artifact/VpYXqWxSrtWKHAry94Q1aH |

## 1. Viga được đo là gì

Luồng một câu hỏi: lối tắt luật → router LLM → (công cụ hành trình tất định | hỏi tài liệu). Hỏi tài liệu gồm: viết lại và tách câu (≤ 5 câu con) → nhúng (BGE-M3 cục bộ) → BM25 + vector top 30 mỗi nhánh → RRF (k = 60) → gộp lên mục cha, ngân sách 3.000 token mỗi câu con → LLM trả lời có trích dẫn (suy luận bật) → kiểm trích dẫn nguyên văn.

Điểm yếu thấy trước khi đo: không có ngưỡng điểm hoặc giới hạn số mục (đưa ~68 mục, chỉ 3% đúng); `rerank.py` là hàm rỗng; ký tự đặc biệt làm truy vấn BM25 lỗi; bước trả lời bật suy luận là phần chậm nhất; câu ngoài phạm vi và chèn lệnh đều đi về xã giao.

## 2. Các trường hợp đã đo (đủ để tra nhanh)

### 2.1 Bộ câu hỏi
| Bộ | Số câu | Nội dung |
|---|---|---|
| **Golden** | 122 | tài liệu một sự kiện 52, kép 2 ý 17, kép 3 ý 8, không có căn cứ 8, công cụ hành trình 16, công cụ kép 6, thông tin cá nhân 5, ngoài phạm vi 5, chèn lệnh 3, xã giao 2; mỗi câu có mục đúng, trích dẫn chuẩn, ý bắt buộc, loại phản hồi và công cụ kỳ vọng |
| **An toàn và độ bền** | 46 | S1 chèn lệnh trực tiếp 12, S2 chèn lệnh gián tiếp 8, S3 jailbreak 3, S4 lộ bí mật và thông tin cá nhân 5, S5 thiên lệch (cặp) 6, S6 độ bền 9, S7 câu mơ hồ 3 |
| **Tập chỉnh** | 70 | chỉ để chọn tham số (RRF, rerank) |
| **Tập kiểm** | 50 | chỉ để so sánh cuối, chưa từng dùng để chọn tham số |

Nguồn: tài liệu thật đã ở trạng thái sẵn sàng trên DB dev, chụp vào DB riêng `vsf_bench` (không đụng DB dev hay production). Câu hỏi được sinh nháp bằng DeepSeek rồi bổ sung và rà bằng tay; nhãn chưa có người thứ hai duyệt.

### 2.2 Các cấu hình đã chạy
| Đợt | Nhãn | Cấu hình |
|---|---|---|
| 1 | R0 | Viga hiện tại |
| 1 | R1 | rerank bge-reranker-v2-m3 (fp32), 20 ứng viên giữ 5 |
| 2 | V_router | router v2 |
| 2 | V_k5, V_k3 | giữ 5 hoặc 3 mục (RRF mặc định) |
| 2 | V_k5_dedupe_cap | giữ 5 + khử trùng lặp + trần 2.500 token |
| 3 | A_on, A_off, A_adapt | RRF tối ưu × suy luận bật / tắt / thích ứng (router v2 **không** bật ở đợt 3) |
| 3 | B_on, B_off, B_adapt | + rerank int8, 8 ứng viên, 256 token, hạn 4 giây |
| 3 | C_cut5 | RRF tối ưu + cắt 5 mục, bật suy luận |
| 3 | B_full | rerank không giới hạn thời gian |
| 3 | C_off | RRF tối ưu + cắt 5 mục + tắt suy luận |

## 3. Phương pháp

### 3.1 Ba luồng đo riêng
A: định tuyến ý định; B: công cụ hành trình; C: tìm tài liệu và trả lời. Độ trễ cũng tách theo luồng thực, vì gộp chung làm P50 trông tốt giả (luật 0,02 giây, công cụ ~1 giây, tài liệu ~6 giây).

### 3.2 Chỉ số (giải thích đầy đủ ở [giai-thich-chi-so.md](giai-thich-chi-so.md))
Thứ hạng và phủ: Hit@1/3/5, MRR, Context Recall, Context Precision. Trả lời: Faithfulness, Đúng, Đủ ý, Liên quan, phủ ý bắt buộc, **North Star** (đúng ≥ 4 và Faithfulness ≥ 0,85). Vận hành: P50, P95, token, chi phí, tỉ lệ lỗi, đúng loại phản hồi. An toàn: an toàn cơ học, làm theo lệnh độc, thiên lệch.

### 3.3 Giám khảo
| Đợt | Giám khảo |
|---|---|
| 1 | DeepSeek + gpt-5-mini; đồng thuận Spearman 0,64, Cohen κ 0,41 (chưa đạt 0,7 và 0,6) |
| 2 | DeepSeek + gpt-5-mini |
| 3 | **Chỉ DeepSeek** (OpenAI bị vô hiệu hóa khóa; Gemini hết tiền; Groq giới hạn ~64 câu mỗi ngày; OpenRouter hết hạn mức giữa chừng; điểm Haiku đã chấm bị mất do lỗi quy trình của tôi) |

### 3.4 Thống kê
t-test cặp trên cùng câu, Wilcoxon, khoảng tin cậy 95% của chênh lệch, Cohen d. Chỉ coi có ý nghĩa khi p < 0,05.

## 4. Số liệu chính

### Đợt 1: rerank 20 → 5 so với hiện tại (120 câu, hai giám khảo)
| Chỉ số | R0 | R1 |
|---|---|---|
| Hit@1 | 53,3% | 82,4% |
| MRR | 0,646 | 0,878 |
| Context Precision | 2,4% | 22,1% |
| Context Recall | 98,7% | 95,6% |
| Faithfulness | 85,5% | 91,8% |
| North Star | 61,3% | 76,0% |
| Token vào mỗi câu | 15.652 | 5.104 |
| P50 luồng tài liệu | 5,75 giây | 38 giây |
| P95 luồng tài liệu | 10,3 giây | 115 giây |

Định tuyến (R0): ngoài phạm vi 0%, chèn lệnh 0%, chọn đúng công cụ 68,8%, đúng tham số ngày 50%, độ phủ công cụ câu kép 58,3%. Bộ an toàn: 0 câu làm theo lệnh độc.

### Đợt 2: sửa lỗi, router v2, cắt ngữ cảnh (120 câu)
| Thay đổi | Kết quả |
|---|---|
| Sửa BM25 ký tự đặc biệt | Tỉ lệ lỗi 1,3% → 0% |
| Router v2 | Ngoài phạm vi 0% → 100%, chèn lệnh 0% → 100%, chọn đúng công cụ 68,8% → 75%; độ phủ công cụ câu kép 58% → 33% (6 câu) |
| Giữ 5 mục (RRF mặc định) | Recall 98,7% → 76,9%, không nhanh hơn |
| Giữ 3 mục | Recall → 69,8% |

### Đợt 3: tập chỉnh (không LLM)
| Cách xếp hạng | Hit@1 | Hit@5 |
|---|---|---|
| chỉ BM25 | 37,1% | 57,5% |
| RRF mặc định (k=60, 1:1) | 45,6% | 73,8% |
| chỉ vector | 56,5% | 89,5% |
| **RRF k=10, BM25:vector = 0,1:1** | **55,4%** | **87,4%** |
| + rerank bge int8 (12 ứng viên, 256 token) | 68,7% | 92,2% |

Tốc độ rerank (mỗi câu hỏi con, 12 ứng viên): bge fp32 10,7 giây; **bge int8 4,4 giây**; mmarco-mMiniLM 1,8 giây (Hit@1 62,6%).

### Đợt 3: tập kiểm 50 câu (26 câu có đáp án, DeepSeek)
| Ô | Faithfulness | North Star | Hit@1 | P50 | P95 | USD/câu |
|---|---|---|---|---|---|---|
| A_on (RRF tối ưu, không cắt) | 85,1% | 65,4% | 75,6% | 7,72 s | 16,75 s | $0,0068 |
| A_off | 88,9% | 61,5% | 75,6% | 5,66 s | 7,43 s | $0,0060 |
| C_cut5 (cắt 5 mục) | **97,8%** | 80,8% | 75,6% | 5,92 s | 10,31 s | $0,0023 |
| B_full (rerank thật) | 94,9% | 76,9% | **91,7%** | 11,35 s | 22,08 s | $0,0025 |
| **C_off (cắt 5 mục, tắt suy luận)** | 90,7% | 69,2% | 69,9% | **3,85 s** | **5,84 s** | **$0,0020** |

Điểm có ý nghĩa thống kê (p < 0,05): cắt 5 mục tăng Faithfulness +12,6 điểm và giảm 2,3 giây; rerank thật tăng Hit@1 +16 điểm so với chỉ cắt nhưng **giảm phủ ý 8 điểm** và **chậm thêm 6,1 giây**; tắt suy luận giảm 2,8 giây. Bảng đầy đủ: [ket-qua/cuoi/tong_hop.md](ket-qua/cuoi/tong_hop.md).

## 5. Lý do chọn

| Quyết định | Lý do (kèm số đo) |
|---|---|
| Đo ba luồng riêng, tách độ trễ theo luồng | Gộp chung che lỗi định tuyến và làm P50 giả |
| Dùng bản chụp DB riêng `vsf_bench` | Không ảnh hưởng dev và production |
| Tách tập chỉnh 70 và tập kiểm 50 | Chọn tham số và kiểm trên cùng câu sẽ tự thổi phồng kết quả |
| RRF **k=10, BM25 : vector = 0,1 : 1**, không chọn "chỉ vector" | Hit@1 55,4% so với 56,5% (trong nhiễu); giữ nhánh từ khóa nhẹ cho mã và tên biểu mẫu chính xác |
| Cắt còn **5 mục** mỗi câu con | Với RRF tối ưu Recall giữ 100%; Faithfulness +12,6 điểm; nhanh hơn 2,3 giây; chi phí −64% |
| **Bật cắt cùng lúc với RRF tối ưu** | Cắt với RRF mặc định làm Recall tụt 98,7% → 77% (đợt 2) vì xếp hạng cũ chỉ đúng đầu ở ~50% câu |
| **Không dùng rerank** | Hit@1 tốt hơn nhưng câu trả lời không tốt hơn (Đúng 4,73 = 4,73, phủ ý −8 điểm), chậm thêm 6,1 giây; vượt ngân sách 10 giây (P95 22 giây) |
| Rerank (nếu dùng sau này): bge int8, 8 đến 12 ứng viên, 256 token | int8 nhanh gấp 2,4 lần và giữ độ chính xác; 12 ứng viên và 256 token không mất Hit@1; câu hỏi gốc không tốt hơn câu tách từ |
| Router v2 | Ngoài phạm vi và chèn lệnh 0% → 100% |
| Tắt suy luận là **tùy chọn**, không phải mặc định | Giảm 2 đến 5 giây (p < 0,001) nhưng Faithfulness có xu hướng giảm (97,8% → 90,7%, p = 0,07); chưa đủ bằng chứng chất lượng |
| Không dùng chế độ suy luận "thích ứng" | Không giảm P95 (16,7 giây) vì các câu chậm nhất đều là câu nhiều ý |
| Hạn rerank 4 giây (ô B) | Là phép thử ngân sách; 67 đến 88% lệnh bị cắt nên đã thêm ô B_full để đo rerank thật |

## 6. Quy trình chốt cuối

### 6.1 Cấu hình đề xuất triển khai
```
VIGA_ROUTER_V2=true
RETRIEVAL_PROFILE=optimized    (gói: RRF k=10, BM25:vector = 0,1:1, giữ 5 mục; đã có trong sản phẩm từ 12/10)
ANSWER_THINKING_MODE=always    (hoặc off nếu cần P95 dưới 6 giây, sau khi xác nhận chất lượng)
RERANK                          tắt
```
Luồng: lối tắt luật → router v2 → viết lại → nhúng → BM25 + vector, RRF k=10 trọng số 0,1 : 1 → cắt 5 mục → LLM trả lời có trích dẫn → kiểm trích dẫn.

### 6.2 Quy trình đánh giá một thay đổi (dùng lại cho mọi lần sau)
1. Dựng cấu hình sau cờ cấu hình (mặc định tắt).
2. Chọn tham số trên **tập chỉnh** bằng quét không LLM (`sweep_rrf.py`, `sweep_rerank.py`).
3. So sánh trên **tập kiểm** (`run_viga_benchmark.py --ids-file ...`), 1 lượt để sàng, **≥ 3 lượt** để kết luận.
4. Chấm bằng **hai giám khảo khác họ** (`score_benchmark.py`, `add_second_judge.py`), báo độ đồng thuận.
5. Tổng hợp và so sánh cặp (`summarize_final.py`), xuất dữ liệu biểu đồ (`export_dashboard_data.py`).
6. Đối chiếu **cổng chấp nhận**.

### 6.3 Cổng chấp nhận (so với cấu hình hiện tại)
| Chỉ số | Yêu cầu |
|---|---|
| Context Recall | không tụt quá 2 điểm |
| North Star, Faithfulness | không giảm (Faithfulness ≥ 0,85) |
| Đúng loại phản hồi, tỉ lệ lỗi | không tệ hơn |
| P95 luồng tài liệu | ≤ 10 giây |
| Bộ an toàn 46 câu | 0 câu làm theo lệnh độc |

### 6.4 Triển khai
1. Merge mọi thứ với cờ tắt (production không đổi).
2. Bật hồ sơ đề xuất trên dev, chạy benchmark 3 lượt, **nhãn đã được 2 người duyệt**.
3. Bật production cho một phần người dùng, so tỉ lệ 👍👎, "không có căn cứ", độ trễ P95 trong 1 đến 2 tuần.
4. Mở rộng; mỗi cờ tắt ngay bằng biến môi trường.

### 6.5 Việc còn thiếu trước khi chốt hoàn toàn
- ~~Thêm tham số RRF vào `hybrid_search.py`~~ (đã làm 12/10, xem báo cáo triển khai).
- Hai người duyệt nhãn; chạy ≥ 3 lượt.
- Một giám khảo thứ hai còn dùng được.
- Test tích hợp cho `_bm25_search` với DB thật.
- Đo trên kho lớn hơn và trên AWS 2 vCPU.

## 7. Hạn chế

Một lượt mỗi ô, 26 câu có đáp án trong tập kiểm; nhãn nháp; kho 100 mục; ba đợt dùng giám khảo khác nhau nên số của các đợt khác nhau không so thẳng được với nhau (chỉ so trong cùng đợt); ô B rerank hạn giờ chủ yếu phản ánh việc cắt ngữ cảnh; thời gian đo trên máy dev 6 CPU, không phải AWS; nhóm nhỏ (chèn lệnh, ngoài phạm vi) chỉ là chỉ báo; bộ an toàn không chạy lại cho đợt 3.

## 8. Nhánh và commit

| Nhánh | Nội dung |
|---|---|
| `feat/pdf-sang-word-va-ocr` | Mã và báo cáo đầy đủ (commit `375c8f2` cho đợt 3) |
| `feat/viga-context-optimization` | Bản sao đợt 1 và 2 (tách từ `origin/main`) |

Khóa API chỉ đọc lúc chạy từ tệp ngoài repo; không có khóa nào được lưu trong repo.
