# Báo cáo benchmark cuối: RRF tối ưu, rerank, cắt ngữ cảnh và suy luận ở bước trả lời

Ngày chạy: 11/10/2026. Nhánh: `feat/pdf-sang-word-va-ocr` (mã) và `feat/viga-context-optimization` (bản sao nhánh Viga). Nối tiếp [bao-cao-benchmark-viga.md](bao-cao-benchmark-viga.md) và [bao-cao-toi-uu-viga.md](bao-cao-toi-uu-viga.md). Kế hoạch: [ke-hoach-benchmark-toi-uu-cuoi.md](ke-hoach-benchmark-toi-uu-cuoi.md). Giải thích từng chỉ số: [giai-thich-chi-so.md](giai-thich-chi-so.md). Trang biểu đồ: xem mục 9.

> **Đọc trước.** (1) Mỗi cấu hình chạy **1 lượt** trên 50 câu. Cùng một cấu hình truy hồi nhưng chạy ở các ô khác nhau cho Hit@1 từ 69,9% đến 75,6%, do bước viết lại câu hỏi bằng LLM không cố định, nên **chênh lệch dưới khoảng 6 điểm là nhiễu**. (2) Điểm chất lượng do **một giám khảo AI (DeepSeek)** chấm. Giám khảo thứ hai không chấm được (mục 7). (3) Nhãn vàng vẫn là bản nháp chưa có người duyệt.

## 1. Kết luận và đề xuất

| Câu hỏi | Trả lời dựa trên số đo |
|---|---|
| Chỉnh trọng số RRF có ích không? | **Có.** Trên tập chỉnh, Hit@1 tăng từ 45,6% (mặc định) lên 55,4% (k=10, BM25 nhẹ 0,1 so với vector 1). Chỉ dùng vector còn cao hơn (56,5%): nhánh BM25 yếu (37%) nên kéo kết quả trộn xuống |
| Cắt còn 5 mục có an toàn không? | **Có, nếu đi cùng RRF tối ưu.** Recall giữ 100%, Faithfulness 85,1% → 97,8% (p = 0,02), nhanh hơn 2,3 giây (p < 0,001), chi phí giảm 64%. (Với RRF mặc định thì cắt làm Recall tụt 98,7% → 77%, kết quả báo cáo trước) |
| Rerank có đáng không? | **Chưa, ở quy mô kho này.** Rerank đầy đủ nâng Hit@1 +16 điểm (p = 0,02) nhưng câu trả lời **không tốt hơn** (Đúng không đổi, phủ ý −8 điểm, p = 0,03) và **chậm thêm 6,1 giây** (P50 11,4 giây, P95 22 giây) |
| Tắt suy luận ở bước trả lời thì sao? | Nhanh hơn 2,3 đến 4,6 giây (p < 0,001); chất lượng không tụt có ý nghĩa nhưng Faithfulness có xu hướng thấp hơn (97,8% → 90,7%, p = 0,07). Chế độ "thích ứng" **không giúp** P95 |
| Đạt tối đa 10 giây không? | **Có, với RRF tối ưu + cắt 5 mục** (P50 5,9 giây, P95 10,3 giây khi bật suy luận; **P50 3,9 giây, P95 5,8 giây khi tắt suy luận**). Cấu hình có rerank không đạt (P95 12 đến 22 giây) |

**Đề xuất triển khai (theo thứ tự):**
1. Đưa tham số RRF (`k`, hệ số hai nhánh) vào sản phẩm sau cờ (hiện mới có trong harness, xem mục 8).
2. Bật `RETRIEVAL_MAX_SECTIONS=5` **cùng lúc** với RRF tối ưu, không bật riêng.
3. Cân nhắc `ANSWER_THINKING_MODE=off`: nhanh nhất, rẻ nhất, nhưng cần xem lại chất lượng trên nhãn đã duyệt và nhiều lượt trước khi bật cho mọi câu. Một lựa chọn trung gian là bật suy luận (P95 10,3 giây, chất lượng cao nhất trong các ô đo).
4. **Chưa** dùng rerank. Xét lại khi kho tài liệu lớn hơn hoặc có GPU.

## 2. Thiết kế

- Tập **chỉnh** 70 câu (chọn tham số) và tập **kiểm** 50 câu (so sánh cuối), tách theo tầng nhóm câu hỏi, độ khó, kiểu diễn đạt, hạt giống cố định ([make_subsets.py](scripts/make_subsets.py), [tap_kiem_50.json](bo-cau-hoi/tap_kiem_50.json), [tap_chinh_70.json](bo-cau-hoi/tap_chinh_70.json)). Hai câu NO_BASIS cũ gd_076, gd_079 được đổi nhãn sang "trả lời một phần" (kho có FAQ nhắc tới HR Portal), thêm gd_121 và gd_122 (đã kiểm kho không có thú cưng, hỗ trợ mua nhà).
- Mọi ô dùng bản sửa BM25, chạy trên bản chụp `vsf_bench` (không đụng DB dev/production). **Không ô nào bật router v2** (đã kiểm: câu ngoài phạm vi vẫn đi về xã giao); tác động của router v2 được đo riêng ở đợt 2 và chỉ ảnh hưởng luồng định tuyến, không ảnh hưởng truy hồi và trả lời tài liệu. Sai sót này đã được sửa ở bản ngày 12/10.
- **Ma trận 2 × 3** (RRF tối ưu: A; RRF tối ưu + rerank: B) × (suy luận bật luôn / tắt luôn / thích ứng), cộng ba ô đối chứng: **C_cut5** (chỉ cắt 5 mục), **B_full** (rerank không giới hạn thời gian), **C_off** (cắt 5 mục + tắt suy luận).
- "RRF tối ưu" = `k = 10`, hệ số BM25 : vector = 0,1 : 1. Rerank (ô B): `bge-reranker-v2-m3` int8, 8 ứng viên, 256 token, giữ 5 mục.

## 3. Quét tham số (tập chỉnh, không gọi LLM)

### 3.1 RRF (49 câu tài liệu có đáp án)

| Cấu hình | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@10 |
|---|---|---|---|---|---|
| chỉ BM25 | 37,1% | 53,4% | 57,5% | 0,478 | 69,7% |
| chỉ vector | 56,5% | 79,9% | 89,5% | 0,694 | 92,9% |
| RRF mặc định (k=60, 1:1) | 45,6% | 65,0% | 73,8% | 0,582 | 80,3% |
| **RRF k=10, BM25:vector = 0,1:1 (chọn)** | **55,4%** | **79,9%** | **87,4%** | **0,688** | **92,2%** |

Chi tiết 22 cấu hình: [quet-tham-so/rrf.md](ket-qua/quet-tham-so/rrf.md). Chọn cấu hình giữ nhánh BM25 nhẹ thay vì "chỉ vector" vì chênh lệch nhỏ (nằm trong nhiễu) và nhánh từ khóa còn giúp với mã, tên biểu mẫu chính xác.

### 3.2 Rerank (12 ứng viên, 256 token, 49 câu)

| Cấu hình | Hit@1 | Hit@5 | MRR | giây/cặp | giây/câu hỏi con |
|---|---|---|---|---|---|
| chỉ RRF | 55,4% | 87,4% | 0,686 | | |
| bge-reranker-v2-m3 fp32 (câu gốc) | 68,7% | 92,2% | 0,783 | 0,89 | 10,7 |
| **bge-reranker-v2-m3 int8** (câu gốc) | **68,7%** | **92,2%** | **0,787** | **0,37** | **4,4** |
| bge int8 (câu tách từ) | 70,7% | 92,2% | 0,798 | 0,37 | 4,4 |
| mmarco-mMiniLM-v2 (câu gốc) | 62,6% | 87,1% | 0,725 | 0,15 | 1,8 |

Phát hiện: câu hỏi gốc **không** tốt hơn câu tách từ (nghi vấn ban đầu sai); 12 ứng viên và 256 token giữ nguyên độ chính xác so với 20 ứng viên và 512 token; lượng tử hóa int8 giữ độ chính xác và nhanh gấp 2,4 lần; mô hình nhỏ nhanh nhất nhưng kém hơn rõ. Chi tiết: [quet-tham-so/rerank.md](ket-qua/quet-tham-so/rerank.md), `rerank_int8.md`, `rerank_minilm.md`.

## 4. Kết quả ma trận trên tập kiểm 50 câu

Chỉ tính câu tài liệu có đáp án (n = 26: 14 câu một ý, 12 câu nhiều ý). A = RRF tối ưu, B = + rerank (hạn 4 giây), C_cut5 = chỉ cắt 5 mục, B_full = rerank không hạn giờ, C_off = cắt 5 mục + tắt suy luận. Hậu tố `on / off / adapt` = suy luận bật / tắt / thích ứng.

| Chỉ số | A_on | A_off | A_adapt | B_on | B_off | B_adapt | C_cut5 | B_full | C_off |
|---|---|---|---|---|---|---|---|---|---|
| Context Recall | 96,2% | 100,0% | 96,2% | 98,7% | 96,2% | 94,9% | 100,0% | 100,0% | 100,0% |
| Context Precision | 3,2% | 3,3% | 3,2% | 22,9% | 22,7% | 21,9% | 21,1% | 24,7% | 20,6% |
| Hit@1 | 75,6% | 75,6% | 75,6% | 77,6% | 78,2% | 72,4% | 75,6% | 91,7% | 69,9% |
| Hit@3 | 91,0% | 94,9% | 92,3% | 98,7% | 96,2% | 94,9% | 94,9% | 100,0% | 96,2% |
| MRR | 0,835 | 0,856 | 0,839 | 0,875 | 0,863 | 0,821 | 0,850 | 0,956 | 0,820 |
| Phủ ý bắt buộc | 68,4% | 74,1% | 71,4% | 68,1% | 65,5% | 64,7% | 76,9% | 68,6% | 72,5% |
| Faithfulness | 85,1% | 88,9% | 85,2% | 93,6% | 90,4% | 92,6% | 97,8% | 94,9% | 90,7% |
| Đúng (1–5) | 4,54 | 4,46 | 4,42 | 4,81 | 4,46 | 4,58 | 4,73 | 4,73 | 4,62 |
| Đủ ý (1–5) | 4,08 | 4,08 | 4,08 | 4,42 | 3,85 | 4,04 | 4,27 | 4,27 | 4,08 |
| Liên quan (1–5) | 4,54 | 4,54 | 4,54 | 4,65 | 4,46 | 4,50 | 4,65 | 4,65 | 4,62 |
| **North Star** | 65,4% | 61,5% | 57,7% | 80,8% | 69,2% | 84,6% | 80,8% | 76,9% | 69,2% |
| Đúng loại phản hồi | 92,3% | 96,2% | 92,3% | 92,3% | 92,3% | 88,5% | 92,3% | 92,3% | 92,3% |
| Mục vào LLM | 68,0 | 72,3 | 68,9 | 9,2 | 8,5 | 8,1 | 8,8 | 9,2 | 8,7 |
| Token vào | 18.321 | 19.201 | 18.471 | 5.257 | 5.030 | 5.020 | 5.217 | 5.331 | 5.212 |

Tỉ lệ lỗi 0% ở mọi ô.

### Độ trễ luồng tài liệu (giây) và chi phí

| Ô | P50 | P95 | Trung bình | P50 câu một ý | P50 câu nhiều ý | USD/câu |
|---|---|---|---|---|---|---|
| A_on | 7,72 | 16,75 | 8,65 | 6,13 | 8,85 | $0,0068 |
| A_off | 5,66 | 7,43 | 5,79 | 5,35 | 5,93 | $0,0060 |
| A_adapt | 7,18 | 16,71 | 8,74 | 4,87 | 8,82 | $0,0072 |
| B_on | 10,68 | 15,53 | 11,22 | 9,74 | 12,10 | $0,0024 |
| B_off | 9,62 | 12,07 | 9,67 | 9,17 | 10,81 | $0,0020 |
| B_adapt | 9,92 | 13,04 | 9,99 | 9,48 | 10,57 | $0,0022 |
| **C_cut5** | 5,92 | 10,31 | 6,18 | 5,22 | 6,45 | $0,0023 |
| B_full | 11,35 | 22,08 | 12,27 | 10,97 | 12,71 | $0,0025 |
| **C_off** | **3,85** | **5,84** | **4,00** | **3,67** | **4,07** | **$0,0020** |

Số mục vào LLM giảm từ ~68 xuống ~9 và chi phí giảm khoảng 65%, ở mọi ô có cắt.

## 5. So sánh cặp (khoảng tin cậy và p-value từ t-test cặp)

| So sánh | Chỉ số | Δ | 95% CI | p |
|---|---|---|---|---|
| A_on → C_cut5 (cắt 5 mục) | Faithfulness | +0,126 | [+0,020; +0,232] | **0,021** |
| | Thời gian (giây) | −2,30 | [−3,55; −1,04] | **0,0008** |
| | North Star | +0,154 | [−0,094; +0,401] | 0,21 |
| | Đúng (1–5) | +0,19 | [−0,19; +0,57] | 0,31 |
| C_cut5 → B_full (rerank thật) | Hit@1 | +0,160 | [+0,025; +0,296] | **0,022** |
| | Phủ ý bắt buộc | −0,083 | [−0,159; −0,006] | **0,035** |
| | Đúng (1–5) | 0,00 | [−0,32; +0,32] | 1,00 |
| | North Star | −0,038 | [−0,252; +0,175] | 0,71 |
| | Thời gian (giây) | +6,10 | [+4,42; +7,78] | **< 0,0001** |
| A_on → A_off (tắt suy luận) | Thời gian (giây) | −2,76 | [−4,23; −1,28] | **0,0007** |
| | North Star | −0,038 | [−0,218; +0,141] | 0,66 |
| A_on → C_off | Thời gian (giây) | −4,61 | [−6,00; −3,23] | **< 0,0001** |
| | North Star | +0,038 | [−0,203; +0,280] | 0,75 |
| C_cut5 → C_off | Faithfulness | −0,071 | [−0,148; +0,007] | 0,072 |
| | North Star | −0,115 | [−0,324; +0,093] | 0,26 |

Toàn bộ cặp: [ket-qua/cuoi/tong_hop.md](ket-qua/cuoi/tong_hop.md). Với n ≈ 26 câu mỗi ô, các chênh lệch North Star lớn (+15 điểm) vẫn **chưa đạt ý nghĩa thống kê**; chỉ các kết quả in đậm đạt p < 0,05.

## 6. Phân tích

1. **Cắt ngữ cảnh là thay đổi hiệu quả nhất.** Hybrid cũ đưa ~68 mục (khoảng 18 nghìn token) cho LLM mà chỉ 3% là mục đúng. Cắt còn 5 mục mỗi câu hỏi con (khi RRF đã tối ưu) giữ Recall 100%, tăng bám tài liệu, giảm 2,3 giây và 64% chi phí. Tác dụng này đến từ việc bỏ nhiễu, không cần mô hình thứ hạng mạnh hơn.
2. **Rerank giải đúng vấn đề thứ hạng nhưng không phải vấn đề của câu trả lời.** Hit@1 lên 91,7% (rất đáng kể về thứ hạng), nhưng khi đã giữ đúng 5 mục, LLM tìm được thông tin từ đó dù mục đúng không đứng đầu. Vì vậy chất lượng trả lời không tăng, còn thời gian tăng gấp đôi. Với kho 100 mục và top-5, thứ hạng trong 5 mục ít quan trọng.
3. **Suy luận.** Là phần chậm nhất của luồng tài liệu. Tắt nó giảm 2 đến 5 giây và rút P95 xuống dưới 6 giây. Chất lượng có xu hướng tụt nhẹ ở Faithfulness (chưa đạt ý nghĩa thống kê, mẫu nhỏ). Chế độ "thích ứng" chỉ bật suy luận cho câu nhiều ý, nên các câu chậm nhất vẫn chậm: P95 không đổi (16,7 giây).
4. **Nhiễu của phép đo.** Cùng cấu hình truy hồi (A_on, A_off, A_adapt, C_cut5 cho Hit@1 75,6%; C_off cho 69,9%) mà số khác nhau, vì bước viết lại tách câu hỏi con bằng LLM cho kết quả hơi khác mỗi lần. Đây là lý do cần ≥3 lượt.

## 7. Lỗi và hạn chế phải biết

- **Các ô B (rerank hạn 4 giây) không phải rerank thật.** 67 đến 88% lệnh rerank bị hạn giờ cắt và rơi về thứ tự RRF, vì các câu hỏi con chạy song song tranh CPU và lệnh bị hủy vẫn chiếm máy chủ. Cải thiện của B nên đọc là "RRF tối ưu cộng cắt còn 5 mục". Rerank thật được đo ở ô **B_full**.
- **Chỉ một giám khảo (DeepSeek).** Giám khảo thứ hai (OpenAI) bị vô hiệu hóa khóa; Gemini hết tiền trả trước; Groq chỉ cho khoảng 64 câu mỗi ngày; OpenRouter (Claude Haiku) hết khoản tặng giữa chừng. **Điểm Haiku đã chấm (khoảng 150 câu) bị mất** do tôi xóa trước khi chấm lại cho nhất quán rồi hết tiền (lỗi quy trình của tôi), nên không tính được độ đồng thuận hai giám khảo cho ma trận cuối. Điểm giám khảo chỉ là chỉ báo, đặc biệt vì giám khảo cùng họ với mô hình trả lời.
- 1 lượt mỗi ô, n ≈ 26 câu có đáp án mỗi ô; nhãn vàng chưa duyệt; kho chỉ 100 mục (tiêu đề tài liệu trong kho thử đều là bản tổng hợp).
- Tốc độ rerank đo trên máy dev (6 CPU), không phải AWS 2 vCPU.
- Hai nhãn gd_076, gd_079 đổi giữa chừng; các số của bộ benchmark cũ (R0, R1) không chạy lại.
- Nhóm nhỏ (ví dụ chèn lệnh 2 câu, ngoài phạm vi 3 câu) chỉ là chỉ báo. Bộ an toàn không chạy lại cho các ô mới.

## 8. Những gì đã và chưa có trong sản phẩm

| Việc | Trạng thái |
|---|---|
| Sửa BM25 ký tự đặc biệt | Có trong mã (không cờ) |
| Router v2 (`VIGA_ROUTER_V2`) | Có, mặc định tắt |
| Cắt ngữ cảnh (`RETRIEVAL_MAX_SECTIONS`, `RETRIEVAL_DEDUPE_SECTIONS`, `RETRIEVAL_TOTAL_TOKEN_CAP`) | Có, mặc định tắt |
| Chế độ suy luận (`ANSWER_THINKING_MODE`: always / off / adaptive) | Có, mặc định `always` |
| **RRF tối ưu (k, hệ số nhánh)** | **Chưa có trong sản phẩm**, chỉ ở harness (`run_viga_benchmark.py --rrf-k --w-bm25 --w-vector`). Cần thêm cờ cấu hình vào `hybrid_search.py` |
| Rerank | Chưa có (`rerank.py` vẫn là hàm rỗng); chỉ có dịch vụ thử `rerank_server.py` |

Khi triển khai: bật RRF tối ưu và cắt 5 mục **cùng lúc**; không bật cắt với RRF mặc định (Recall tụt 98,7% → 77%).

## 9. Tệp và đường dẫn

| Nội dung | Đường dẫn |
|---|---|
| Kế hoạch | [ke-hoach-benchmark-toi-uu-cuoi.md](ke-hoach-benchmark-toi-uu-cuoi.md) |
| Giải thích chỉ số | [giai-thich-chi-so.md](giai-thich-chi-so.md) |
| Tập kiểm 50, tập chỉnh 70 | [bo-cau-hoi/tap_kiem_50.json](bo-cau-hoi/tap_kiem_50.json), [bo-cau-hoi/tap_chinh_70.json](bo-cau-hoi/tap_chinh_70.json) |
| Kết quả quét RRF, rerank | [ket-qua/quet-tham-so/](ket-qua/quet-tham-so/) |
| Kết quả từng ô (thô và điểm) | `ket-qua/F_A_on/`, `F_A_off/`, `F_A_adapt/`, `F_B_on/`, `F_B_off/`, `F_B_adapt/`, `F_C_cut5/`, `F_B_full_on/`, `F_C_cut5_off/` |
| Tổng hợp và so sánh cặp | [ket-qua/cuoi/tong_hop.md](ket-qua/cuoi/tong_hop.md), `tong_hop.json`, `dashboard_data.json` |
| Mã đo | [scripts/make_subsets.py](scripts/make_subsets.py), [sweep_rrf.py](scripts/sweep_rrf.py), [sweep_rerank.py](scripts/sweep_rerank.py), [run_viga_benchmark.py](scripts/run_viga_benchmark.py), [run_final_matrix.sh](scripts/run_final_matrix.sh), [run_ablation.sh](scripts/run_ablation.sh), [run_best_cell.sh](scripts/run_best_cell.sh), [summarize_final.py](scripts/summarize_final.py), [export_dashboard_data.py](scripts/export_dashboard_data.py) |
| Mã sản phẩm đổi | `backend/src/config.py`, `services/retrieval/hybrid_search.py`, `services/viga/{router,pipeline,answer_service,context_limit,service}.py` |
| Trang biểu đồ | Trang Artifact do Claude tạo cho báo cáo này (liên kết ở tin nhắn bàn giao) |

## 10. Tái tạo

```
python docs/value/optimize-chatviga/scripts/make_subsets.py
PYTHONPATH=backend python docs/value/optimize-chatviga/scripts/sweep_rrf.py
PYTHONPATH=backend python docs/value/optimize-chatviga/scripts/sweep_rerank.py     # cần run_reranker.sh start
TOP=8 LEN=256 TIMEOUT=4 bash docs/value/optimize-chatviga/scripts/run_final_matrix.sh
bash docs/value/optimize-chatviga/scripts/run_ablation.sh
bash docs/value/optimize-chatviga/scripts/run_best_cell.sh
python docs/value/optimize-chatviga/scripts/summarize_final.py                      # cần numpy, scipy
python docs/value/optimize-chatviga/scripts/export_dashboard_data.py
```

Khóa API chỉ đọc lúc chạy từ tệp ngoài repo; không có khóa nào được lưu trong repo.
