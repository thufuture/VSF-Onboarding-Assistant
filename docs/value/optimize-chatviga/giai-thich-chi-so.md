# Giải thích các chỉ số trong báo cáo benchmark Viga

Dành cho người đọc báo cáo không chuyên về AI. Mỗi chỉ số có: nó đo cái gì, cách tính, đọc thế nào, và giới hạn.

## 1. Cách đo chung

- **Golden set**: bộ ~120 câu hỏi có nhãn đáp án chuẩn, lấy từ tài liệu thật trên DB dev. Mỗi câu ghi: mục tài liệu đúng, trích dẫn chuẩn, ý bắt buộc phải có, loại phản hồi kỳ vọng (trả lời / không có căn cứ / ngoài phạm vi), công cụ kỳ vọng.
- **Ba luồng đo riêng**, vì gộp lại sẽ che lỗi:
  - **A, định tuyến**: Viga có hiểu đúng người dùng muốn gì (hỏi tài liệu, hỏi việc trong lộ trình, xã giao, ngoài phạm vi) hay không.
  - **B, công cụ hành trình**: nếu là câu về lộ trình, có chọn đúng công cụ và đúng tham số không.
  - **C, tìm tài liệu và trả lời**: có tìm đúng đoạn tài liệu và trả lời đúng, có căn cứ không.
- **Giám khảo AI** (LLM-as-judge): hai mô hình khác họ (DeepSeek và gpt-5-mini) chấm điểm câu trả lời theo thang có hướng dẫn, nhiệt độ 0, kèm lý do. Điểm lấy trung bình hai giám khảo.
- **Một lượt chạy** mỗi cấu hình: mỗi câu hỏi chỉ hỏi Viga một lần. Số liệu có nhiễu ngẫu nhiên của mô hình; vì vậy chênh lệch nhỏ chưa đáng tin.

## 2. Chỉ số tìm kiếm tài liệu (luồng C, "truy hồi")

Đây là bước Viga chọn các đoạn tài liệu để đưa cho mô hình đọc. Sai ở đây thì phía sau không cứu được.

| Chỉ số | Ý nghĩa dễ hiểu | Cách tính | Đọc thế nào |
|---|---|---|---|
| **Context Recall** (độ phủ ngữ cảnh) | Đoạn tài liệu đúng có nằm trong số đoạn đưa cho mô hình không | Tỉ lệ các đoạn chuẩn của câu hỏi có mặt trong ngữ cảnh | Càng cao càng tốt. 98% nghĩa là gần như luôn tìm *đủ*. |
| **Context Precision** (độ chính xác ngữ cảnh) | Trong các đoạn đưa vào, bao nhiêu đoạn thật sự cần | Số đoạn đúng chia tổng số đoạn đưa vào | Thấp = đưa nhiều rác. Hiện ~2%: cứ 40 đoạn mới có 1 đoạn đúng. Rác làm mô hình đọc lâu, tốn tiền, dễ nhiễu. |
| **Hit@k** (k = 1, 3, 5) | Đoạn đúng có nằm trong k vị trí đầu của danh sách xếp hạng không | Tỉ lệ câu có đoạn đúng trong top k | Hit@1 = xếp hạng nhất đã đúng. Cho biết chất lượng *thứ tự*. |
| **MRR** (Mean Reciprocal Rank) | Đoạn đúng đứng thứ mấy, trung bình | Trung bình của 1 chia vị trí đoạn đúng đầu tiên (1, 1/2, 1/3...) | Từ 0 đến 1, gần 1 là đoạn đúng thường đứng đầu. |

Ghi nhớ: Recall cho biết *tìm có đủ không*, Precision và Hit/MRR cho biết *có gọn và xếp đúng không*. Viga hiện tìm đủ nhưng lẫn nhiều rác.

## 3. Chỉ số chất lượng câu trả lời (luồng C, "sinh")

| Chỉ số | Ý nghĩa | Cách tính |
|---|---|---|
| **Faithfulness** (trung thực với tài liệu) | Câu trả lời có bám tài liệu, không bịa không | Giám khảo tách câu trả lời thành các ý, kiểm từng ý có trong đoạn tài liệu đã đưa không; tỉ lệ ý có căn cứ |
| **Answer Relevancy** (liên quan) | Có trả lời đúng điều được hỏi không, không lạc đề | Giám khảo chấm 1 đến 5 |
| **Đúng (1 đến 5)** | So với đáp án chuẩn có đúng không | Giám khảo chấm so với đáp án tham chiếu |
| **Đủ ý (1 đến 5)** | Có đủ các ý cần có không | Giám khảo chấm; kèm **Phủ ý bắt buộc**: tỉ lệ cụm bắt buộc (ví dụ "Phòng nhân sự") xuất hiện trong câu trả lời, tính bằng máy, không qua giám khảo |
| **Mạch lạc (1 đến 5)** | Văn có dễ đọc, rõ ràng không | Giám khảo chấm |
| **North Star: đúng và có căn cứ** | Chỉ số chính: vừa đúng vừa bám tài liệu | Tỉ lệ câu đạt đồng thời "đúng" và "có căn cứ" |
| **Đúng loại phản hồi** | Câu hỏi đáng được trả lời thì trả lời; không có trong tài liệu thì nói "không có căn cứ" | So loại phản hồi thực tế với kỳ vọng |
| **Tỉ lệ lỗi** | Tỉ lệ câu Viga báo "trợ lý không khả dụng" | Đếm tự động |

North Star quan trọng hơn từng điểm riêng: một câu trả lời trôi chảy nhưng sai hay bịa vẫn là thất bại.

## 4. Chỉ số định tuyến và công cụ (luồng A và B)

- **Định tuyến đúng theo nhóm**: với mỗi nhóm câu (tài liệu, công cụ, thông tin cá nhân, xã giao, ngoài phạm vi, chèn lệnh), tỉ lệ Viga đi đúng đường kỳ vọng. **Ma trận nhầm lẫn** liệt kê "kỳ vọng → thực tế" để thấy nhầm vào đâu.
- **Chọn đúng công cụ** (câu đơn): với câu về lộ trình, chọn đúng một trong 5 công cụ.
- **Đúng tham số ngày** (`get_day_plan`): hỏi "ngày 3" có đưa đúng ngày không.
- **Độ phủ công cụ (câu kép)**: câu hỏi hai ý cần hai công cụ, tỉ lệ công cụ cần thiết thực sự được gọi.

## 5. Độ trễ và chi phí

| Chỉ số | Ý nghĩa |
|---|---|
| **P50** (trung vị) | Một nửa số câu nhanh hơn mốc này; thời gian "bình thường" người dùng gặp |
| **P95** | 95% số câu nhanh hơn mốc này; thời gian người dùng gặp ở lúc chậm. Chỉ tiêu của slide: ≤ 5 giây |
| **P99** | Trường hợp xấu nhất hiếm gặp |
| **Theo luồng thực** | Tách riêng câu đi lối tắt luật (0,02 giây), công cụ hành trình (~1 giây) và tài liệu (~6 giây); gộp chung làm P50 trông tốt giả |
| **Thời gian từng bước** | Router, rewrite (viết lại câu hỏi), embed (đổi câu hỏi thành vector), truy hồi, trả lời, kiểm trích dẫn |
| **Token vào / ra** | Lượng chữ mô hình đọc và viết; mô hình tính tiền và mất thời gian theo token |
| **Chi phí LLM mỗi câu** | Tổng tiền các lệnh gọi mô hình trả lời, router, rewrite (chưa gồm hạ tầng); ngưỡng của slide ≤ $0,05 |

## 6. Chỉ số an toàn (bộ 46 câu)

- **An toàn cơ học**: kiểm bằng máy, không cần giám khảo: câu trả lời có chứa "chuỗi bẫy" (canary) không, có làm theo lệnh độc không, có vi phạm mẫu cấm không.
- **Làm theo lệnh độc (giám khảo)**: giám khảo AI đọc câu trả lời xem có thực hiện mệnh lệnh chèn vào không.
- Các bộ: chèn lệnh trực tiếp (người dùng gõ), chèn lệnh gián tiếp (lệnh nằm trong tài liệu), jailbreak, lộ bí mật và thông tin cá nhân, thiên lệch (hỏi cặp câu chỉ khác nhóm người), độ bền (diễn đạt khác, lỗi chính tả, viết tắt), câu mơ hồ.
- **Thiên lệch**: cùng loại phản hồi giữa hai vế của cặp và độ giống từ giữa hai câu trả lời; 100% và gần 1 là tốt.

## 7. Thống kê dùng để so sánh hai cấu hình

| Thuật ngữ | Ý nghĩa |
|---|---|
| **Δ (chênh lệch)** | Cấu hình mới trừ cấu hình cũ cùng một câu hỏi |
| **Khoảng tin cậy 95%** | Khoảng mà chênh lệch thật nhiều khả năng nằm trong đó; nếu khoảng chứa số 0 thì chưa chắc có khác biệt |
| **p-value** (t-test cặp, Wilcoxon) | Xác suất thấy chênh lệch lớn như vậy nếu thật ra hai cấu hình giống nhau; p < 0,05 coi là có ý nghĩa thống kê. Phép "cặp" so từng câu hỏi với chính nó nên chính xác hơn |
| **Cohen d** | Độ lớn của chênh lệch (0,2 nhỏ, 0,5 vừa, 0,8 lớn); p nhỏ mà d nhỏ nghĩa là khác thật nhưng ít đáng kể |
| **Spearman** | Mức hai giám khảo cùng xếp hạng điểm giống nhau (−1 đến 1); cần ≥ 0,7 theo slide |
| **Cohen κ** | Mức đồng thuận hai giám khảo sau khi loại phần trùng hợp ngẫu nhiên; cần ≥ 0,6 theo slide. Đang là 0,41, nên điểm giám khảo chỉ là chỉ báo |

## 8. Những điều số liệu không cho biết

- Nhãn vàng là bản nháp, chưa có hai người duyệt.
- Chỉ một lượt chạy mỗi cấu hình, nên chưa đo được độ dao động của mô hình.
- Kho thử 100 mục, nhỏ hơn thực tế; kết quả trên kho lớn có thể khác.
- Giám khảo AI có thể thiên vị; đã dùng hai giám khảo khác họ để giảm, chưa loại bỏ.
