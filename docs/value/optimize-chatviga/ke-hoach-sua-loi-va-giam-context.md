# Kế hoạch: sửa lỗi + giảm ngữ cảnh để Viga trả lời nhanh mà vẫn đúng (chưa dùng rerank)

Ngày: 11/10/2026. **Chỉ là kế hoạch, chưa code.** Căn cứ số liệu: [bao-cao-benchmark-viga.md](bao-cao-benchmark-viga.md). Rerank tạm gác (chậm trên CPU, còn vướng giấy phép); xem [ke-hoach-cai-tien-viga-sau-benchmark.md](ke-hoach-cai-tien-viga-sau-benchmark.md) cho bức tranh đầy đủ.

## 1. Vấn đề đo được (luồng tài liệu, cấu hình hiện tại)

| Số đo | Giá trị | Ý nghĩa |
|---|---|---|
| Số mục đưa vào LLM mỗi câu | ~57 | Gấp nhiều lần cần thiết |
| Context Precision | 2,4% | Chỉ ~1/40 mục đưa vào là mục đúng |
| Context Recall | 98,7% | Tìm *đủ*, nên có chỗ cắt bớt |
| Token ngữ cảnh / token vào cả câu | ~4.800 / ~15.700 | Bước trả lời phải đọc rất nhiều |
| Bước trả lời | 3,2 giây (~46% tổng thời gian), suy luận đang bật | Phần chậm nhất |
| P50 / P95 luồng tài liệu | 5,75 / 10,26 giây | P95 vượt ngưỡng 5 giây của slide |
| Chi phí LLM mỗi câu | ~$0,0057 | Đạt (ngưỡng $0,05) |

Vì sao ~57 mục (đọc từ code): `search_to_sections` (`retrieval/hybrid_search.py`) lấy top 30 BM25 + 30 vector, gộp RRF lên mục cha, rồi chỉ dừng khi **vượt 3.000 token**, không có ngưỡng điểm hay giới hạn số mục. Việc này chạy **riêng cho mỗi câu hỏi con** (`pipeline.py`, `_run_document_qa`, tối đa 5 câu con) và `build_user_prompt` ghép ngữ cảnh của từng câu con vào prompt, nên câu kép nhân ngữ cảnh lên và cùng một mục có thể xuất hiện nhiều lần (cần xác nhận khi làm, xem bước 2.2).

## 2. Các thay đổi đề xuất (từ chắc chắn đến cần thử)

Mọi thay đổi hành vi nằm sau cờ cấu hình, **mặc định tắt**; merge không đổi production cho đến khi bạn bật.

### Nhóm A: sửa lỗi chắc chắn (không đổi chất lượng, chỉ bớt lỗi)

| # | Việc | Nơi sửa | Kiểm chứng |
|---|---|---|---|
| A1 | Thoát/bọc từng từ trong truy vấn BM25; ghi log cảnh báo kèm loại lỗi thay vì nuốt thành `assistantUnavailable` | `ingest/lexical.py` (`to_lexical_text`), nơi dựng truy vấn trong `retrieval/hybrid_search.py` | Test đơn vị với `[ ] { } ( ) " : * ? ~ ^ + - \`; chạy lại `gd_068`; tỉ lệ lỗi 1,3% → 0% |
| A2 | Thêm ví dụ `OUT_OF_SCOPE` và câu chèn lệnh vào prompt router; sửa luật "hôm nay … làm gì" bắt nhầm câu thời tiết (#110) | `viga/router.py` (prompt), luật shortcut | Luồng A: out_of_scope và injection từ 0% lên ≥ 80% đúng nhãn; document/tool/smalltalk không tụt |
| A3 | Làm rõ mô tả `get_day_plan` (tham số ngày) và ranh giới công cụ với tài liệu | `viga/router.py` (mô tả công cụ) | Luồng B: chọn đúng công cụ 68,8% → ≥ 85%; đúng ngày 50% → ≥ 80% |

A2 và A3 cùng là sửa prompt router nên gộp một lần đo.

### Nhóm B: giảm ngữ cảnh đưa vào LLM (giảm token, giảm thời gian trả lời)

| # | Việc | Ghi chú |
|---|---|---|
| B1 | **Giới hạn số mục mỗi câu hỏi con** sau RRF (thử top 3, 5, 8) thay vì chỉ cắt theo 3.000 token | Rẻ nhất, thay đổi nhỏ trong `search_to_sections` |
| B2 | **Ngưỡng điểm tương đối**: bỏ mục có điểm RRF < x% điểm mục đầu | Giúp câu có ít mục liên quan không bị độn thêm |
| B3 | **Khử trùng lặp giữa các câu con**: mục nào đã có ở câu con trước thì chỉ ghi một lần | Câu kép đỡ phình prompt; cần kiểm tra trước trong `prompt_builder.build_user_prompt` xem trùng thật bao nhiêu |
| B4 | **Cắt tổng token ngữ cảnh** của cả prompt (không chỉ mỗi câu con), ví dụ 2.000 token | Chặn trần cho câu kép nhiều ý |
| B5 | Giữ nguyên thứ tự đưa mục vào prompt theo điểm, mục tốt nhất đứng đầu | Tránh mô hình bỏ sót vì mục đúng nằm giữa |

Rủi ro chính: cắt quá tay làm mất ý ở câu kép (độ phủ ý hiện 75,3%) hoặc mất mục đúng (Recall 98,7%). Vì vậy **không chọn cấu hình bằng cảm tính**, mà quét tham số bằng harness (mục 3).

### Nhóm C: làm bước trả lời nhanh hơn (sau khi nhóm B đã giảm ngữ cảnh)

| # | Việc | Ghi chú |
|---|---|---|
| C1 | Tách thời gian "đọc ngữ cảnh" và "suy nghĩ" bằng stream trong harness (hiện `first_token_ms` và `reasoning_ms` trống vì Viga không stream) | Chỉ đo, chưa đổi sản phẩm. Quyết định C2 dựa vào đây |
| C2 | Tắt suy luận (thinking) cho câu **một ý** và vẫn bật cho câu nhiều ý | Đã đo trước đó: tắt hết nhanh hơn 20 đến 30% nhưng câu nhiều ý mất ý, nên phải tách theo số câu con |
| C3 | Đặt phần cố định (system prompt, quy tắc) ở đầu prompt để tận dụng bộ nhớ đệm của DeepSeek | Có sẵn cột `cached_input_tokens` trong `llm_calls` để kiểm tra có ăn không |
| C4 | Stream câu trả lời ra giao diện (người dùng thấy chữ đầu sớm) | Thay đổi lớn hơn (kể cả validator trích dẫn cần toàn câu), để sau cùng, có thể tách PR riêng |

## 3. Cách đo (tái dùng harness có sẵn, không đụng DB dev/prod)

1. **Giai đoạn 0 (làm trước):** hai người duyệt nhãn vàng, chạy mỗi cấu hình ≥ 3 lượt, để chênh lệch nhỏ (vài điểm phần trăm) có ý nghĩa. Hiện chỉ 1 lượt, nhãn là bản nháp.
2. **Quét tham số B** trên harness bằng cách bọc `search_to_sections` (cùng cách R1 đã làm, nhưng không gọi reranker): k ∈ {3, 5, 8} × ngưỡng ∈ {tắt, 50%, 70%} × khử trùng lặp {tắt, bật}. Mỗi tổ hợp chạy 1 lượt để sàng; chọn 1 đến 2 tổ hợp tốt nhất chạy 3 lượt. Chạy trên **tập tài liệu**, tách riêng câu đơn và câu kép.
3. **Đo C1/C2** trên cấu hình B đã chọn.
4. Báo cáo cùng định dạng: bảng so với R0 hiện tại, p-value, độ trễ theo bước và theo luồng, chi phí.

## 4. Tiêu chí chấp nhận (cấu hình nào cũng phải đạt cùng lúc)

| Chỉ số | Yêu cầu so với R0 hiện tại |
|---|---|
| Context Recall | không tụt quá 2 điểm phần trăm (hiện 98,7%) |
| Phủ ý bắt buộc | không tụt quá 2 điểm (hiện 75,3%), nhất là câu kép 3 ý |
| North Star (đúng + có căn cứ) | không giảm (hiện 61,3%) |
| Faithfulness | ≥ 0,85, không giảm |
| Đúng loại phản hồi, tỉ lệ lỗi | không tệ hơn |
| Token vào mỗi câu | giảm ≥ 40% |
| P50 và P95 luồng tài liệu | giảm; mục tiêu P95 tiến về ≤ 5 giây (chấp nhận chưa chạm nếu bước nghĩ vẫn chiếm phần lớn) |
| Bộ an toàn (46 câu) | vẫn 0 câu làm theo lệnh độc |

Tập nhãn đang là bản nháp nên chỉ chốt khi nhãn đã được duyệt.

## 5. Thứ tự làm và PR

| PR | Nội dung | Phụ thuộc |
|---|---|---|
| 0 | Duyệt nhãn; chạy lại R0 ≥ 3 lượt (đường cơ sở) | không |
| 1 | A1 (BM25 ký tự đặc biệt) + test | không, làm được ngay |
| 2 | A2 + A3 (prompt router, luật) | PR 1 không bắt buộc; đo lại luồng A và B |
| 3 | B1 đến B5 sau cờ `RETRIEVAL_CONTEXT_CAP` (tên tạm), mặc định tắt | kết quả quét tham số ở harness |
| 4 | C2/C3 (thinking theo số câu con, prompt caching) sau cờ | PR 3 và số đo C1 |
| 5 | C4 stream (nếu còn cần) | PR 4 |

Mỗi PR mô tả cách bật/tắt cờ và cách rollback (tắt cờ là về hành vi cũ). Bạn là người merge và bật cờ.

## 6. Rủi ro và điều chưa biết

- **Nhãn và số lượt chưa đủ** để chốt chênh lệch nhỏ; bước 0 là điều kiện của mọi kết luận.
- **Kho thử chỉ 100 mục**: kết quả cắt k trên kho lớn hơn có thể khác; cần kiểm tra lại khi tài liệu tăng.
- **Cắt ngữ cảnh có thể làm mất ý** ở câu kép; theo dõi riêng nhóm này, và dừng nếu phủ ý tụt.
- Suy luận ở bước trả lời giúp câu nhiều ý; không tắt hàng loạt.
- Sửa prompt router có thể làm tụt route khác (document hiện 96,4%); luôn chạy lại toàn bộ luồng A.
- Ước lượng thời gian tiết kiệm được **chưa có**: các con số đo hiện tại chưa tách đọc ngữ cảnh và suy nghĩ (C1 trả lời việc này). Kỳ vọng giảm token ~40% là mục tiêu, không phải kết quả đã đo.

## 7. Cần bạn quyết

1. Đồng ý thứ tự PR trên không? (đề xuất: PR 1 và PR 2 trước, B sau khi quét tham số).
2. Ai duyệt nhãn vàng (cần 2 người) và khi nào?
3. Khi cho phép code, bắt đầu từ PR 1 (BM25) nhé?
