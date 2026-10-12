# Báo cáo benchmark Viga: có và không có rerank (`bge-reranker-v2-m3`)

Ngày chạy: 10/10/2026. Số liệu thô: `ket-qua/summary.json`, `ket-qua/tables.md`. Bộ câu hỏi: `bo-cau-hoi/`. Mã đo: `scripts/`.

> **Đọc trước:** mỗi cấu hình chỉ chạy **1 lần** (theo yêu cầu), nhãn vàng là **bản nháp chưa có người duyệt**, tài liệu thử chỉ 100 mục. Kết quả dùng để **định hướng**, chưa đủ để kết luận cuối. Mục 9 liệt kê đủ hạn chế.

## 1. Tóm tắt

| Câu hỏi | Trả lời |
|---|---|
| Rerank có cải thiện chất lượng truy hồi không? | **Có, rõ rệt.** Hit@1 53,3% → 82,4%; MRR 0,646 → 0,878; Context Precision 2,4% → 22,1% (đều p < 0,001). Context Recall giảm nhẹ 98,7% → 95,6% (không có ý nghĩa thống kê, p = 0,11). |
| Có cải thiện câu trả lời không? | **Faithfulness tăng** 85,5% → 91,8% (p = 0,03); "đúng và có căn cứ" 61,3% → 76,0% (p = 0,015). Điểm "đúng", "đủ ý", "liên quan" **không đổi** (chênh nằm trong nhiễu). |
| Rẻ hơn không? | **Có.** Token vào mỗi câu 15,7k → 5,1k; chi phí LLM mỗi câu ~$0,0057 → ~$0,0023 (luồng tài liệu), nhờ ngữ cảnh từ ~4.800 xuống ~470 token. |
| Nhanh hơn không? | **Không, chậm hơn rất nhiều** trên máy thử: reranker CPU mất ~94 giây mỗi câu tài liệu (P50 luồng tài liệu 5,75 s → 38 s). Chưa dùng được cho người dùng thật nếu không có GPU hoặc mô hình nhẹ hơn. |
| Viga hiện tại có lỗi nào đáng sửa ngay, không liên quan rerank? | Có: ký tự đặc biệt làm BM25 lỗi (F1), câu ngoài phạm vi/chèn lệnh đều đi về xã giao, chọn sai công cụ hành trình. |
| An toàn? | Bộ 46 câu an toàn: **0 câu làm theo lệnh độc**, cả hai cấu hình. Điểm yếu là *phân loại* (xem mục 6), không phải rò rỉ. |

## 2. Phương pháp (bám slide day13/14/18)

- **Ba luồng đo riêng** để không trộn lẫn: A = định tuyến ý định; B = công cụ hành trình; C = tìm kiếm tài liệu + trả lời. Độ trễ cũng tách theo luồng thực (gộp chung cho P50 thấp giả).
- **Golden set** ~120 câu (đơn và kép) lấy từ tài liệu thật đã ở trạng thái sẵn sàng trên DB dev (chụp vào DB riêng `vsf_bench`, **không đụng dev/prod**), nhãn gồm mục đúng, trích dẫn chuẩn, ý bắt buộc, loại phản hồi, công cụ kỳ vọng.
- **Chỉ số truy hồi:** Context Recall/Precision, Hit@1/3/5, MRR. **Sinh:** Faithfulness, Answer Relevancy, đúng, đủ ý, mạch lạc (thang 1–5, rubric + suy luận, nhiệt độ 0), North Star = đúng **và** có căn cứ.
- **Hai giám khảo khác họ:** DeepSeek và `gpt-5-mini` (OpenAI). Chỉ gửi nội dung tổng hợp của benchmark. Điểm lấy trung bình hai giám khảo.
- **So sánh:** t-test cặp, Wilcoxon, khoảng tin cậy 95% của chênh lệch, Cohen d.
- **Cấu hình:** R0 = Viga hiện tại (hybrid RRF, ngân sách 3.000 token). R1 = lấy 20 ứng viên → rerank → giữ 5 trong ngân sách. Cùng mô hình, cùng prompt, cùng DB.
- **Bộ an toàn** 46 câu: chèn lệnh trực tiếp/gián tiếp (cài trong tài liệu), jailbreak, lộ bí mật/thông tin cá nhân, thiên lệch (cặp), độ bền (biến thể), câu mơ hồ. Chấm cơ học (có làm theo lệnh/lộ chuỗi canary không) + giám khảo.

## 3. Luồng C: tìm kiếm tài liệu (câu có đáp án)

| Chỉ số | R0 | R1 (rerank 20→5) | Δ | 95% CI | p (t cặp) |
|---|---|---|---|---|---|
| Context Recall | 98,7% | 95,6% | −3,1 đ%| [−6,9; +0,7] | 0,109 |
| Context Precision | 2,4% | 22,1% | +19,7 đ% | [+17,1; +22,3] | <0,001 |
| Hit@1 | 53,3% | 82,4% | +29,1 đ% | [+15,9; +42,4] | <0,001 |
| Hit@3 | 71,1% | 94,2% | +23,1 đ% | [+12,9; +33,3] | <0,001 |
| Hit@5 | 75,6% | 95,6% | +20,0 đ% | [+10,8; +29,2] | <0,001 |
| MRR | 0,646 | 0,878 | +0,232 | [+0,134; +0,329] | <0,001 |
| Phủ ý bắt buộc | 75,3% | 73,3% | −2,0 đ% | [−10,0; +5,9] | 0,613 |
| Faithfulness | 85,5% | 91,8% | +6,4 đ% | [+0,6; +12,1] | 0,030 |
| Đúng (1–5) | 4,507 | 4,473 | −0,03 | [−0,24; +0,18] | 0,754 |
| Đủ ý (1–5) | 4,113 | 4,027 | −0,09 | [−0,37; +0,20] | 0,543 |
| Liên quan (1–5) | 4,740 | 4,567 | −0,17 | [−0,37; +0,02] | 0,075 |
| **North Star (đúng + có căn cứ)** | 61,3% | 76,0% | +14,7 đ% | [+2,9; +26,4] | 0,015 |
| Số mục đưa vào LLM | 56,8 | 7,6 | −49,2 | | <0,001 |
| Token ngữ cảnh | 4.829 | 473 | −4.356 | | <0,001 |
| Chi phí LLM/câu | $0,0060 | $0,0020 | −$0,0033 | | <0,001 |

**Diễn giải.** Hybrid hiện tại *tìm đủ* (Recall 98,7%) nhưng *xếp kém và trộn nhiều rác*: đưa ~57 mục vào LLM, chỉ 2,4% là mục đúng. Rerank sắp mục đúng lên đầu (Hit@1 +29 điểm) và cắt ngữ cảnh 10 lần, nên câu trả lời bám tài liệu hơn và rẻ hơn. Theo thứ tự chẩn đoán trong slide (recall → precision → faithfulness → relevancy), điểm nghẽn của Viga hiện tại nằm ở **precision**, không phải recall. Đổi lại Recall và độ phủ ý giảm nhẹ (không có ý nghĩa thống kê, nhưng cần theo dõi: giữ 5 mục có thể bỏ sót ý thứ hai ở câu kép; câu kép 3 ý đúng loại 87,5% → 75%).

## 4. Độ trễ và chi phí theo luồng thực

| Cấu hình | Luồng | n | P50 (s) | P95 (s) | Chi phí/câu |
|---|---|---|---|---|---|
| R0 | tài liệu | 85 | 5,75 | 10,26 | $0,00567 |
| R0 | công cụ hành trình | 17 | 1,05 | 1,32 | $0,00072 |
| R0 | xã giao | 11 | 1,16 | 1,25 | $0,00081 |
| R0 | chặn thông tin cá nhân (luật) | 6 | 0,02 | 0,04 | 0 |
| R1 | tài liệu | 82 | 38,04 | 115,00 | $0,00230 |
| R1 | công cụ hành trình | 17 | 1,09 | 1,38 | $0,00072 |

Thời gian từng bước, luồng tài liệu (trung bình, giây):

| Bước | R0 | R1 |
|---|---|---|
| router | 1,19 | 1,20 |
| rewrite | 1,14 | 1,07 |
| embed | 0,68 | 0,66 |
| truy hồi | 0,18 | 94,31 (trong đó rerank 93,99) |
| trả lời | 3,22 | 2,70 |

Chỉ tiêu bảo vệ (guardrail) trong slide: P95 ≤ 5 s, chi phí ≤ $0,05, faithfulness ≥ 0,85. Chi phí đạt cả hai cấu hình. **P95 không đạt ở cả hai** (R0 10,3 s do bước trả lời bật suy luận; R1 115 s do rerank CPU). Faithfulness R0 85,5% vừa chạm ngưỡng, R1 91,8%.

**Về tốc độ rerank (quan trọng):** số trên là máy dev chạy mô hình 568M tham số fp32 trên CPU, trong Docker 6 CPU. Đo vi mô với 2 CPU (giống cấu hình AWS hiện tại) ~23 giây cho 20 cặp, tức là **đẩy lên AWS 2 vCPU sẽ không nhanh hơn**, và chưa có bằng chứng nào cho thấy chạy trên AWS giúp. Chỉ khi có GPU, hoặc giảm còn ~10 ứng viên, hoặc dùng mô hình nhỏ/lượng tử hóa (cần đo lại chất lượng), rerank mới đạt ngưỡng 5 giây.

## 5. Luồng A (định tuyến) và B (công cụ)

Định tuyến (kỳ vọng → đúng, hai cấu hình giống hệt vì router không phụ thuộc rerank):

| Nhóm | n | Đúng |
|---|---|---|
| document | 83 | 96,4% (R0) / 92,8% (R1, nhiễu của LLM) |
| tool | 22 | 77,3% |
| personal | 5 | 80,0% |
| smalltalk | 2 | 100% |
| **out_of_scope** | 5 | **0%** (cả 5 → xã giao) |
| **injection** | 3 | **0%** (cả 3 → xã giao) |

Công cụ hành trình: chọn đúng công cụ (câu đơn) **68,8%**; đúng tham số ngày `get_day_plan` **50%**; độ phủ công cụ ở câu kép **58,3%** (router chỉ chọn một công cụ mỗi câu, đúng thiết kế nhưng thiếu ý ở câu kép).

## 6. Bộ an toàn và độ bền (46 câu)

| Bộ | n | An toàn cơ học (R0 / R1) | Làm theo lệnh độc (giám khảo) |
|---|---|---|---|
| S1 chèn lệnh trực tiếp | 12 | 100% / 100% | 0% |
| S2 chèn lệnh gián tiếp (trong tài liệu) | 8 | 100% / 100% | 0% |
| S3 jailbreak, nội dung có hại | 3 | 100% / 100% | 0% |
| S4 lộ bí mật, thông tin cá nhân | 5 | 100% / 100% | 0% |
| S5 thiên lệch (3 cặp) | 6 | 100% / 100% | 0% |
| S6 độ bền (biến thể câu hỏi) | 9 | 100% / 100% | 0% |
| S7 câu mơ hồ | 3 | 100% / 100% | 0% |

Không có câu nào làm theo lệnh độc hay lộ canary. Thiên lệch: cùng loại phản hồi 100% giữa hai vế của cặp; độ giống từ trung bình 0,88. **Lưu ý:** "an toàn" ở đây nghĩa là *không làm theo lệnh*; nhiều câu chèn lệnh/ngoài phạm vi được xếp `INFO` (xã giao) thay vì `OUT_OF_SCOPE`. Cần người duyệt quyết `INFO` có tính là từ chối đạt không (hiện được chấp nhận trong bộ an toàn). Chỉ 3 câu S3 và 3 cặp S5 nên **mẫu rất nhỏ** ở hai bộ này.

## 7. Phân tích lỗi (rút gọn, theo 5 Whys)

1. **Ký tự đặc biệt làm BM25 lỗi (lỗi thật của sản phẩm, F1).** Người dùng thấy "trợ lý không khả dụng" (`gd_068`, câu kép 3 ý, câu con có `[...]` trích nhãn tài liệu). *Vì sao?* ParadeDB từ chối chuỗi truy vấn. → `to_lexical_text` không thoát cú pháp truy vấn. → Chưa có test ký tự đặc biệt. → Lỗi bị nuốt thành `ERROR assistantUnavailable`, không phải 500, nên không thấy trong log. Tỉ lệ lỗi 1,3% (2/150 câu) ở cả hai cấu hình. **Đề xuất:** thoát/bọc từng từ, thêm test, cảnh báo log.
2. **Ngoài phạm vi và chèn lệnh đều đi về xã giao (0/8).** Router chưa có nhãn `OUT_OF_SCOPE` rõ trong prompt ví dụ; câu thời tiết "hôm nay" còn bị luật regex "hôm nay … làm gì" bắt (#110). Hệ quả: không làm theo lệnh nhưng trả lời xã giao thay vì từ chối có hướng dẫn.
3. **Chọn sai công cụ / thiếu tham số ngày (68,8% / 50%).** Phần lớn nhầm sang trả lời bằng tài liệu (5/22), và câu kép chỉ gọi một công cụ (F3, `gd_100`).
4. **Lỗi môi trường đo, không phải lỗi Viga (F1b).** Ban đầu ~8% câu lỗi `unrecognized node type` do chỉ mục BM25 của bản khôi phục bị hỏng; `REINDEX` sửa hết (0/510 lần trên DB dev thật). Các câu lỗi đã chạy lại cùng cấu hình; bản lần đầu giữ ở `lượt_1_lần_đầu.jsonl` (R0 an toàn 3 câu, R1 4 câu thử lại thành công). Số liệu trong báo cáo là **sau khi thử lại**.

## 8. Đề xuất

| Ưu tiên | Việc | Lý do / bằng chứng |
|---|---|---|
| 1 | Sửa thoát ký tự đặc biệt cho BM25 + test | Lỗi thật, rẻ, không phụ thuộc rerank |
| 2 | Thêm nhãn `OUT_OF_SCOPE`, ví dụ chèn lệnh vào router; sửa luật "hôm nay" | 0/8 đúng |
| 3 | Giảm ngữ cảnh đưa vào LLM (ngưỡng điểm hoặc cắt top-k) **không cần rerank** | Precision 2,4%, 57 mục vào LLM; token và chi phí giảm lớn. Nên đo riêng "cắt top-k mà không rerank" để tách hiệu ứng |
| 4 | Rerank sau cờ cấu hình, mặc định tắt (`search_to_sections`/`rerank.py`), PR riêng | Chất lượng tốt hơn rõ rệt, nhưng **tốc độ chưa dùng được** trên CPU; cần GPU hoặc mô hình nhẹ, và **kiểm tra giấy phép** mô hình trước khi dùng thương mại |
| 5 | Cho phép nhiều công cụ trong một câu kép | Độ phủ 58,3% |
| 6 | Duyệt nhãn bởi 2 người, chạy ≥3 lượt | Điều kiện để kết luận chính thức |

Nên **không bật** rerank ở production cho đến khi mục 4 giải quyết tốc độ. Việc merge các thay đổi trong báo cáo này không đổi hành vi sản phẩm (chưa sửa code sản phẩm nào).

## 9. Hạn chế (trung thực)

- **Mỗi cấu hình chỉ 1 lần chạy**: không ước lượng được độ biến thiên của LLM. Slide khuyến nghị ≥3 lượt; các p-value dựa trên biến thiên giữa các câu, không giữa các lượt.
- **Nhãn là bản nháp chưa có người duyệt.** Đồng thuận hai giám khảo trên điểm "Đúng": Spearman 0,64, Cohen κ nhị phân 0,41, đồng thuận thô 86%, lệch ≥2 điểm 7,3% (n = 150). Cả hai chưa đạt ngưỡng calibration của slide (Spearman ≥ 0,7, κ ≥ 0,6), và chưa có nhãn người để hiệu chỉnh. Điểm giám khảo là chỉ báo, không phải sự thật.
- **Kho tài liệu nhỏ** (100 mục/100 chunk, tổng hợp từ dữ liệu dev), nên Recall cao hơn môi trường thật; phép so rerank trên kho lớn có thể khác.
- **Câu hỏi sinh từ chính tài liệu** có thể thiên về từ khóa trùng; câu kép/hành trình tổng hợp.
- Nhóm thiểu số: injection (3), out_of_scope (5), S3 (3), S5 (3 cặp), S7 (3) quá nhỏ để suy ra tỉ lệ.
- Độ trễ rerank đo trên một máy dev, một cấu hình (20→5); chưa quét tham số (số ứng viên, số giữ) và chưa thử GPU/mô hình lượng tử.
- Giám khảo DeepSeek cùng họ với mô hình trả lời của Viga (rủi ro thiên vị tự ưu ái); đã giảm bằng giám khảo thứ hai khác họ nhưng không loại bỏ.
- Chi phí chỉ tính LLM trả lời/route/rewrite; chưa gồm hạ tầng reranker và embedder.

## 10. Tái tạo

Từ gốc repo, với DB `vsf_bench`, embedder `127.0.0.1:8080`, reranker `scripts/run_reranker.sh start`:

```
PYTHONPATH=backend python docs/value/optimize-chatviga/scripts/run_viga_benchmark.py --label R0_full
PYTHONPATH=backend python docs/value/optimize-chatviga/scripts/run_viga_benchmark.py --label R1_full --rerank
python docs/value/optimize-chatviga/scripts/score_benchmark.py --label R0_full --judge
python docs/value/optimize-chatviga/scripts/compare_configs.py --base R0_full --test R1_full
```

Khóa API giám khảo chỉ đọc lúc chạy, không lưu trong repo.
