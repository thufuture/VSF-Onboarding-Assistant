# Kế hoạch: bộ đo, golden set có nhãn, giám khảo DeepSeek, và thử reranker cho chat Viga

Ngày viết: 10/10/2026. Trạng thái: **chỉ là kế hoạch, chưa code, chưa chạy phép đo mới.** Bổ sung cho `ke-hoach-toi-uu-chat-viga.md` (đã có luồng Viga, điểm yếu, nguồn tham khảo). Mọi số "đã đo" lấy từ `docs/value/benchmark-modal-llm-viga/` (06/10/2026); mọi số khác là giả thuyết cần đo, ghi rõ.

## 1. Hiện trạng chat Viga (nhận định từ code và số đã đo)

| Khía cạnh | Hiện trạng | Mức tin cậy |
|---|---|---|
| Độ chính xác | 75/80 đúng (93,8%) ở cấu hình đang chạy, trên 40 câu × 2 lượt; nhiễu 1–3 câu | Đã đo, nhưng bộ nhỏ, chỉ 2 tài liệu ngày 1, 1 persona (newhire2) |
| Độ trễ | Trung vị 5,95 giây, p95 10,67 giây; bước trả lời ~3,3 giây (46%) với ~7.500 token ngữ cảnh | Đã đo |
| Chi phí | ~0,003 USD mỗi câu | Đã đo |
| Truy hồi | Hybrid BM25 + vector, top 30 + RRF, gộp lên mục, cắt 3.000 token, **không ngưỡng, không rerank** | Đọc code; **chưa có số Hit@k hay MRR nào** |
| Trích dẫn | Kiểm cơ học nguyên văn; thử lại 1 lần nếu hỏng | Chưa biết tỉ lệ qua ngay lần đầu |
| Cá nhân hóa | Chỉ nhánh công cụ hành trình dùng tiến độ người dùng; nhánh tài liệu không biết người hỏi là ai | Đọc code |
| Lỗi biết rồi | Thời tiết bị trả INFO do luật "hôm nay"; câu nhiều ý mất ý khi tắt thinking; câu mơ hồ về địa điểm đổi kết quả giữa các lượt | Đã đo |
| Điều chưa biết | Truy hồi sai bao nhiêu phần trăm; bao nhiêu câu sai vì truy hồi và bao nhiêu vì mô hình; bao nhiêu câu NO_BASIS đúng/sai | **Cần golden set có nhãn mục** |

Kết luận tạm: số "93,8%" đo trên bộ nhỏ cho thấy chat khá ổn với tài liệu mẫu, nhưng **không đủ để đánh giá cải thiện** vì (1) quá ít câu và ít loại, (2) không tách được lỗi truy hồi với lỗi sinh, (3) không có câu cá nhân hóa, (4) chấm bằng so chuỗi con nên bỏ sót câu đúng ý nhưng khác chữ và chấm đúng cả câu thừa.

## 2. Cần thêm gì để benchmark được (chia hai tầng)

**Tầng 1 – chỉ trong script đo, không sửa sản phẩm (làm ngay):**
- Gọi trực tiếp `pipeline`/`answer_service`/`validator` trong process, ghi lại cho mỗi câu: câu con sau rewrite, các mục truy hồi (id, hạng BM25, hạng vector, điểm gộp), số token ngữ cảnh, kết quả validator, có thử lại không, thời gian từng bước (route, rewrite, embed, truy hồi, trả lời, kiểm).
- Chạy bước trả lời ở chế độ stream để tách thời gian tới token đầu, thời gian suy luận, thời gian viết.
- Nối `llm_calls` bằng `request_id` để lấy token vào/ra, token suy luận, token cache.
- DB tạm riêng nạp tài liệu `day1` và `core`, persona từ `users.json`.

**Tầng 2 – thay đổi nhỏ trong sản phẩm (làm sau, khi bạn duyệt):**
- Lưu `request_id` và `message_id` vào `chat_messages`/`llm_calls` để nối trace với tin nhắn thật.
- Ghi vết truy hồi (mục, điểm, thời gian) sau cờ, không lưu nội dung câu hỏi nếu chưa cho phép.
- Nút cho HR "thêm vào bộ kiểm thử" từ câu trả lời bị 👎 (đẩy câu vào hàng chờ gắn nhãn).
- Đưa tỉ lệ 👍 và tỉ lệ giải quyết lên trang phân tích.

## 3. Golden set có nhãn

**Quy mô đề xuất:** khoảng 150 câu, chia 100 câu phát triển và 50 câu **đóng băng** (không dùng để chỉnh phương án, chỉ để kiểm tra cuối).

**Cơ cấu (mỗi loại có ít nhất 8 câu):**

| Loại | Mục đích | Nhãn mong đợi |
|---|---|---|
| Hỏi một sự kiện | Truy hồi đúng mục, trích đúng | ANSWER + mục chuẩn |
| Nhiều ý | Không mất ý | ANSWER, danh sách ý bắt buộc |
| Viết tắt, sai chính tả, văn nói | Truy hồi bền với cách hỏi | ANSWER + mục chuẩn |
| Ngoại lệ, điều kiện | Nêu đúng điều kiện | ANSWER + câu điều kiện |
| Không có căn cứ | Không bịa | NO_BASIS |
| Ngoài phạm vi, thời tiết, tán gẫu | Định tuyến | OUT_OF_SCOPE/INFO |
| Thông tin cá nhân (lương, người hướng dẫn, chỗ ngồi) | Không bịa, gợi ý gửi HR | OUT_OF_SCOPE + gợi ý ticket |
| Hỏi tiếp theo (nhiều lượt) | Giải quyết đại từ, lịch sử | ANSWER theo ngữ cảnh |
| Chèn lệnh | Chống tiêm lệnh | Từ chối, không lộ prompt |
| Theo ngày hiệu lực (`as_of`) | Chọn đúng phiên bản | ANSWER đúng bản |
| **Cá nhân hóa** (cùng câu, khác persona/tiến độ) | Dùng đúng ngữ cảnh | Đáp án khác nhau theo trạng thái |

**Cấu trúc một mục nhãn:**
`id, loại, câu hỏi (các lượt), persona + trạng thái hành trình, as_of, nhãn_loại_phản_hồi, mục_chuẩn[ {tài_liệu, tiêu_đề_mục, trích_dẫn_nguyên_văn} ], ý_bắt_buộc[], điều_cấm[] (chuỗi/mẫu không được xuất hiện), cần_đề_nghị_ticket (có/không), độ_khó, người_gắn_nhãn, ngày`.

**Cách tạo (bán tự động, người duyệt):**
1. Với mỗi mục tài liệu mẫu, nhờ DeepSeek sinh 2–3 câu hỏi nháp kèm trích dẫn chuẩn và diễn đạt lại (viết tắt, sai chính tả); thêm tay các câu không có căn cứ, cá nhân, chèn lệnh.
2. Lấy thêm câu thật từ `golden_dev/test.jsonl` (242 câu, chưa ai chạy) và 👎/content gap trong dev.
3. **Người duyệt** (bạn hoặc HR) kiểm toàn bộ nhãn của 50 câu đóng băng và ít nhất 30% câu phát triển; mọi câu LLM và người bất đồng đều phải xem lại. Ước tính 3–4 giờ của một người.
4. Kiểm cơ học: mọi trích dẫn chuẩn phải nằm nguyên văn trong tài liệu (dùng `text_match.quote_matches`) để nhãn không sai chính tả.

## 4. Giám khảo DeepSeek (chấm lại)

**Nguyên tắc:** chấm bằng quy tắc trước, LLM chỉ chấm phần quy tắc không làm được.

| Lớp | Cách chấm | Ví dụ |
|---|---|---|
| Quy tắc cơ học | So loại phản hồi; trích dẫn nguyên văn (validator); ý bắt buộc theo chuỗi; điều cấm theo mẫu (email/số điện thoại/số tiền lạ, lộ prompt) | Đúng loại? Có bịa số tiền không? |
| Truy hồi | Mục chuẩn có nằm trong ngữ cảnh không (Hit@k, MRR) | Không cần LLM |
| Giám khảo LLM (DeepSeek) | Faithfulness (mỗi ý có được ngữ cảnh đỡ không), đầy đủ ý, đúng điều kiện, phù hợp ngữ cảnh người dùng, giọng điệu | Điểm 0/1/2 cho từng tiêu chí, JSON |

**Giảm thiên lệch (giám khảo cùng họ mô hình với Viga):**
- Giám khảo không biết phương án nào sinh ra câu trả lời; xáo thứ tự khi so cặp.
- Luôn kèm trích dẫn chuẩn và ngữ cảnh đã truy hồi, yêu cầu nêu lý do trước khi chấm, nhiệt độ thấp, tiêu chí viết rõ.
- **Hiệu chỉnh:** người chấm tay 40 câu, tính độ đồng thuận với giám khảo; nếu dưới ngưỡng thì sửa tiêu chí, không dùng điểm LLM làm kết luận cuối. Bất đồng giữa LLM và quy tắc cơ học được liệt kê để xem tay.
- Ghi rõ trong báo cáo: giám khảo là DeepSeek, cùng họ với mô hình trả lời, **chưa đối chiếu bằng mô hình khác**.

## 5. Bộ metric

| Nhóm | Metric | Nguồn |
|---|---|---|
| Truy hồi | Hit@5/10/20, MRR, số token ngữ cảnh, tỉ lệ mục chuẩn bị cắt khỏi ngân sách | Vết truy hồi |
| Sinh | Đúng/một phần/sai; đúng loại phản hồi; ý bắt buộc đủ; faithfulness; bịa thông tin cá nhân (mục tiêu 0) | Quy tắc + giám khảo |
| Trích dẫn | Qua validator lần đầu; phải thử lại; NO_BASIS do `validation_failed` | Pipeline |
| Định tuyến | Đúng nhánh (hành trình / tài liệu / ngoài phạm vi); đúng loại với câu thời tiết | Quy tắc |
| Cá nhân hóa | Độ nhạy theo người; dùng đúng ngữ cảnh | Quy tắc + giám khảo |
| Tốc độ | p50/p95 mỗi bước; thời gian tới token đầu; số lệnh LLM mỗi câu | Harness, `llm_calls` |
| Chi phí | USD mỗi câu | `llm_calls` |

Mỗi phương án chạy 2 lượt; chênh dưới 1–3 câu trên 40 coi là nhiễu.

## 6. Bỏ reranker vào thì sao

Hiện tại truy hồi dừng ở RRF rồi cắt theo 3.000 token mỗi câu con, **không chấm lại độ liên quan**. Reranker chấm lại các ứng viên (top 20–30) rồi chỉ giữ vài mục tốt nhất.

| Phương án | Cách làm | Kỳ vọng (giả thuyết, cần đo) | Chi phí và rủi ro |
|---|---|---|---|
| R0 | Như hiện tại | Đối chứng | |
| R1 | Chỉ thêm **ngưỡng điểm** + giới hạn top-k mục | Ngữ cảnh ngắn hơn, bước trả lời nhanh hơn; có thể mất mục chuẩn nếu ngưỡng cao | Rất rẻ; cần chọn ngưỡng bằng golden set |
| R2 | **Cross-encoder đa ngôn ngữ** (ví dụ họ bge-reranker-v2-m3) tự host trên máy embedding | Hit@k và MRR cao hơn; cắt ngữ cảnh mạnh mà vẫn đúng | Thêm một mô hình trên CPU (RAM, độ trễ chưa đo; cần xác nhận giấy phép và khả năng chạy trên máy 2 vCPU); thêm bước phải vận hành |
| R3 | **Rerank bằng DeepSeek** (tắt thinking) trên top 20 tiêu đề/đoạn đầu | Không thêm hạ tầng; có thể tăng độ chính xác | Thêm một lệnh LLM (~1 giây, ước tính), thêm chi phí, tăng nguy cơ nghẽn khi nhiều người hỏi (giới hạn 11 yêu cầu đồng thời) |

**Đánh đổi cần đo:** reranker tốn thêm thời gian ở bước truy hồi nhưng có thể **bù lại bằng prefill ngắn hơn** ở bước trả lời (giả thuyết chính: giảm ngữ cảnh từ ~7.500 xuống còn một phần). Kết quả cuối chỉ có nghĩa khi so **tổng thời gian một câu** và **độ chính xác trên golden set**, không phải một mình thời gian rerank. Nếu golden set cho thấy Hit@10 của R0 đã gần 100%, reranker chỉ có tác dụng giảm ngữ cảnh (R1 có thể đủ); nếu Hit@10 thấp, reranker mới thực sự đáng làm.

## 7. Thứ tự thực hiện (khi bạn duyệt)

1. **Dựng golden set bản nháp** (LLM sinh, quy tắc kiểm trích dẫn) và gửi bạn duyệt nhãn: đây là bước tốn công người nhất và quyết định chất lượng mọi kết luận sau.
2. **Dựng harness tầng 1** và chạy **V0 + R0** để có nhận định hiện trạng thật (Hit@k, MRR, loại lỗi: truy hồi hay sinh, độ trễ từng bước).
3. Hiệu chỉnh giám khảo DeepSeek với 40 câu chấm tay.
4. Thử lần lượt: giảm ngữ cảnh (R1) → rerank (R2/R3) → thinking thích ứng → ngữ cảnh người dùng và thẻ tiến độ (V1, V2) → stream.
5. Báo cáo: nhận định hiện trạng, bảng so sánh độ chính xác – tốc độ – chi phí theo từng phương án, đề xuất nâng cấp có thứ tự; kiểm lần cuối trên 50 câu đóng băng.

## 8. Chi phí, rủi ro, việc cần bạn quyết

- Tiền DeepSeek (ước tính, chưa đo): sinh nháp golden set khoảng vài chục xu USD; chạy một phương án trên 150 câu × 2 lượt khoảng 1 USD; giám khảo thêm khoảng bằng chi phí trả lời. Cả đợt vài đến vài chục USD tùy số phương án.
- **Người duyệt nhãn:** cần bạn hoặc HR dành khoảng 3–4 giờ. Không có bước này thì chỉ có "nhãn do LLM tự viết" và kết luận kém tin.
- Dữ liệu vẫn là tổng hợp; persona chỉ khác ở team và hành trình.
- Giám khảo và mô hình trả lời cùng họ DeepSeek: có thể chấm thiên vị; đã giảm bằng quy tắc cơ học và chấm tay hiệu chỉnh, nhưng không loại bỏ hoàn toàn.
- Reranker tự host cần xác nhận giấy phép và sức chạy trên máy hiện có trước khi bàn tiếp.

**Cần bạn quyết:** (1) ai duyệt nhãn golden set và khi nào; (2) đồng ý chi phí DeepSeek; (3) bắt đầu từ bước 1 (golden set) hay bước đo độ trễ nhanh trước?
