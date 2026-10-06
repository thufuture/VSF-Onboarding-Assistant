# Báo cáo kiểm tra Viga, task do AI sinh và giao diện roadmap (02/10/2026)

> **Đã sửa xong (02/10/2026): xem [bao-cao-hoan-thanh-viga-task-ai.md](bao-cao-hoan-thanh-viga-task-ai.md)** (kết quả sau khi sửa, sơ đồ luồng, kiểm thử). Nội dung dưới đây giữ nguyên là **bản kiểm tra trước khi sửa** để đối chiếu.
> Dữ liệu kiểm tra: hai tài liệu đang có trong DB dev (`Huong_dan_ngay_1_onboarding` 18 mục, `Cac_truong_hop_ngoai_le_ngay_1` 22 mục) và 12 task đã tạo từ tài liệu thứ nhất.
> Cách đo: đăng nhập thật bằng tài khoản nhân viên `newhire1@vsf-demo.example` (đã có lộ trình 12 task), hỏi **20 câu**, mỗi câu một cuộc hội thoại mới (không dính lịch sử), gọi `POST /api/v1/viga/ask` trên backend thật (DeepSeek + embedding Modal). Chỉ đọc, không đổi dữ liệu. Kịch bản chạy lại được: [eval/viga_eval.py](eval/viga_eval.py); kết quả thô: [eval/viga_eval.json](eval/viga_eval.json).

## 1. Kết luận ngắn

| Hạng mục | Kết quả | Mức độ |
|---|---|---|
| Viga trả lời 20 câu | **6 hài lòng, 10 đúng thông tin nhưng trình bày chưa đạt, 4 sai hoặc không trả lời được** (30% hài lòng; 80% có đúng thông tin) | Cần sửa |
| Định dạng câu trả lời | Hiện nguyên ký hiệu Markdown (`##`, `*`) vì giao diện chỉ hiển thị chữ thường | Lỗi giao diện |
| 12 task AI tạo từ tài liệu 1 | **Thiếu 4 mục quan trọng** (hồ sơ phải nộp, đào tạo hội nhập, nghe nội quy, T3 đồng thuận); nội dung nhiều task chép nguyên văn tài liệu; **không có tiên quyết**; thứ tự chưa chuẩn | Cần sửa |
| "Xem nguồn" | Task tạo ra **không có chỗ xem nguồn**; Viga mở cả tài liệu và tô cả mục, không trỏ đúng câu | Chưa làm |
| Khoảng cách thẻ roadmap | Hai thẻ cùng hàng cách nhau chỉ **~4px** khi có 12 task | Lỗi bố cục |
| Viga mở rộng như ChatGPT | Chưa có | Chưa làm |
| Trang **Phản hồi Viga** (HR) | Liệt kê cả những câu tài liệu **có** trả lời được; nút "Bổ sung tài liệu" chỉ chuyển sang trang Tài liệu, không mang theo câu hỏi, không kiểm lại sau khi bổ sung | Cần thiết kế lại, xem mục 8 |
| Đánh giá hài lòng của nhân viên cho từng câu trả lời | Chưa có | Đề xuất ở mục 8.1 |

## 2. Hiện trạng khớp với lời anh nói

1. *"Hình như không có task chuẩn bị nội dung"*: **đúng**. Mục "Chuẩn bị hồ sơ phải nộp trong ngày đầu" (CV, lý lịch tư pháp, khám sức khỏe, nơi cư trú, căn cước, chứng chỉ, đầu mối Phòng tuyển dụng) **không có task nào**; "Tham gia chương trình Đào tạo Hội nhập (bắt buộc, điều kiện ≥80%)" cũng không có.
2. *"Hỏi Viga ngáo, hiện `**`"*: **đúng**, xem mục 4.
3. *"Khoảng cách task hơi sát"*: **đúng**, xem mục 6.
4. *"Xem nguồn phải trỏ đúng đoạn như Viga"*: hiện **cả Viga cũng chỉ trỏ tới mục (section)**, chưa trỏ tới câu; xem mục 5.

## 3. Bộ 20 câu hỏi và kết quả

Ký hiệu: ✓ hài lòng, ~ đúng thông tin nhưng chưa đạt (không trực tiếp, dán nguyên văn, lặp), ✗ sai hoặc không trả lời được.

| # | Tài liệu | Câu hỏi | Kết quả | Nhận xét |
|---|---|---|---|---|
| 1 | TL1 | Hồ sơ cần nộp trong ngày đầu gồm những gì? | ✗ | Trả "chưa có căn cứ". **Cùng câu hỏi chạy lại lần 2 thì đúng** (không ổn định), xem V5 |
| 2 | TL1 | Nộp hồ sơ ngày đầu thì liên hệ đầu mối nào? | ✓ | "Liên hệ Phòng tuyển dụng", trích đúng |
| 3 | TL1 | Đào tạo Hội nhập có bắt buộc không, điều kiện hoàn thành? | ~ | Có điều kiện (điểm danh, khảo sát, ≥80%) nhưng **thiếu "bắt buộc"**, kèm một ý "không có căn cứ" thừa, trích từ tài liệu thử nghiệm |
| 4 | TL1 | Bài test cuối khóa phải đạt bao nhiêu? | ✓ | "Từ 80% trở lên" |
| 5 | TL1 | Đầu mối đào tạo hội nhập là ai, email gì? | ✓ | Đúng cả tên phòng và email |
| 6 | TL1 | Khi nào tôi ký hợp đồng lao động? | ~ | Dán cả nội dung task (`## Vì sao phải làm…`) thay vì "Cuối ngày, qua email" |
| 7 | TL1 | Đăng ký faceid chấm công ở đâu? | ~ | Như trên, có thông tin (tầng 14, Vincom Đồng Khởi) nhưng là khối văn bản dán nguyên |
| 8 | TL1 | Tôi nhận laptop ở đâu? | ~ | Như trên (tầng 12, ITHD và HR) |
| 9 | TL1 | Nhận laptop xong thì làm gì tiếp theo? | ✗ | Trả "làm ngay việc Check-in" vì không có quan hệ tiên quyết; **đáp án đúng là đăng nhập Outlook và Teams** |
| 10 | TL1 | Email hỗ trợ ITHD gửi đâu, tiêu đề thế nào? | ~ | Dán nguyên mẫu email; có đủ địa chỉ và quy tắc tiêu đề |
| 11 | TL1 | Trước khi viết ticket cần kiểm tra gì? | ~ | Dán nguyên task; có "Quick access" |
| 12 | TL1 | Dùng VPN/exception USB cần ai đồng thuận? | ~ | Đúng (T3) nhưng **câu trả lời lặp hai lần** |
| 13 | TL1 | Máy đã dùng sẵn Ubuntu thì xin phê duyệt thế nào? | ~ | Dán nguyên task; có "qua Team và chụp ảnh" |
| 14 | TL1 | Sau khi VinSOC phản hồi thì làm gì? | ~ | Dán nguyên task; có "tạo ticket, thực hiện tại ITHD tầng 14" |
| 15 | TL1 | Yêu cầu tủ gửi đồ như thế nào? | ~ | Nguồn tự lặp ("request tủ gửi đồ request tủ gửi đồ"), chưa có hướng dẫn thật |
| 16 | TL2 | Tôi chưa có lý lịch tư pháp thì sao? | ✓ | "Nộp giấy hẹn lấy lý lịch tư pháp; đầu mối Phòng tuyển dụng" |
| 17 | TL2 | Chỉ có CMND, không có CCCD thì thay được không? | ✓ | Nói trung thực "chưa có quy định, cần hỏi Phòng tuyển dụng" |
| 18 | TL2 | T3 chưa trả lời email phê duyệt thì sao? | ✗ | Hỏi lại "bạn đang hỏi việc nào?"; đáp án đúng là chờ 1 ngày làm việc rồi nhắn nhắc |
| 19 | TL2 | Có bắt buộc làm chuỗi yêu cầu ngoại lệ không? | ✗ | Ra nội dung task Ubuntu không liên quan; đáp án đúng là "Không, chỉ làm khi có nhu cầu" |
| 20 | TL2 | VP không phải Vincom Đồng Khởi thì đăng ký faceid thế nào? | ✓ | "Chưa có căn cứ" hợp lý (tài liệu ghi CHƯA CÓ QUY ĐỊNH); lý tưởng là nói rõ "chưa có quy định" |

Thời gian: câu trả lời từ task ~1 giây (không gọi mô hình trả lời), câu hỏi tài liệu 5 đến 9 giây.

### 3.1 Sáu câu hỏi bổ sung (anh yêu cầu thêm)

Chạy cùng cách, kết quả thô ở [eval/viga_more.json](eval/viga_more.json).

| # | Câu hỏi | Kết quả | Nhận xét |
|---|---|---|---|
| 21 | tôi ở hồ chí minh checkin ở đâu á | ~ | Dán cả khối task "Check-in" (`## Vì sao phải làm...`). Trong đó có câu đúng "tài liệu không nêu rõ quy trình check-in cụ thể, chỉ nói theo hướng dẫn tùy nơi" nhưng người hỏi phải tự tìm; **câu trả lời tốt** là: "Tài liệu chỉ nói check-in theo hướng dẫn của nơi onboard, chưa nêu địa điểm ở TP.HCM; bạn hỏi Phòng nhân sự" |
| 22 | Tôi chỉ có CMND, không có căn cước công dân, có thay được không? | ✗ | **Lần này "chưa có căn cứ"; lần chạy trước (câu 17) lại trả lời đúng "chưa có quy định, hỏi Phòng tuyển dụng"**: cùng câu, hai kết quả khác nhau (V5) |
| 23 | tôi không có căn cước công dân sài vnid được không | ✗ | "Chưa có căn cứ". Tài liệu chỉ yêu cầu CCCD bản photo và nhắc VNeID mức 2 cho **giấy xác nhận nơi cư trú**, không nói VNeID thay CCCD. Trả lời tốt: "Tài liệu chưa quy định dùng VNeID thay CCCD (VNeID chỉ được nhắc cho giấy xác nhận nơi cư trú); hỏi Phòng tuyển dụng" kèm trích dẫn phần liên quan |
| 24 | Check-in ngày đầu làm thế nào? | ~ | Dán nguyên task như câu 21 |
| 25 | Tôi làm ở Hà Nội thì check-in ở đâu? | ✓ | Trả "theo hướng dẫn tùy nơi onboard", trung thực |
| 26 | Tôi không có VNeID thì nộp giấy xác nhận nơi cư trú thế nào? | ✓ | "Nộp bản photo giấy xác nhận nơi cư trú cho Phòng tuyển dụng trong ngày đầu" |

**Rút ra:** với câu mà tài liệu **chỉ trả lời một phần hoặc chưa quy định** (21, 22, 23), Viga hoặc trả "chưa có căn cứ" trơ trọi, hoặc dán cả task. Hành vi mong muốn là *trả lời phần có căn cứ + nói rõ phần chưa có quy định + chỉ đầu mối + nút gửi HR* (mục 8.3).

## 4. Vấn đề của Viga và nguyên nhân

| Mã | Vấn đề | Nguyên nhân (đã đối chiếu mã) | Đề xuất sửa |
|---|---|---|---|
| V1 | **Hiện `##`, `*`, `**`, xuống dòng lạ** | `VigaReply` hiển thị `message` và `quote` bằng `white-space: pre-line`, không dựng Markdown. Câu trả lời công cụ lại ghép nguyên `body_markdown` của task (có `## Vì sao phải làm`). Trích dẫn giữ nguyên `* ` của danh sách vì nội dung mục lưu dạng Markdown phẳng | Dựng Markdown an toàn (đã có `react-markdown`, `remark-gfm`) cho câu trả lời và trích dẫn; làm sạch ký hiệu danh sách trong `quote` trước khi hiển thị; bỏ tiêu đề `##` khỏi câu trả lời dạng công cụ |
| V2 | **Hỏi một ý cụ thể mà nhận cả khối task** (câu 6, 7, 8, 10, 11, 13, 14, 15) | Bộ định tuyến chọn công cụ `get_task_detail` khi câu hỏi nhắc tên task, và công cụ này trả toàn bộ nội dung task thay vì trả lời đúng ý hỏi | Với câu hỏi sự kiện ("ở đâu, khi nào, ai, bao nhiêu, có bắt buộc không") chạy hỏi đáp tài liệu giới hạn trong **các mục nguồn của task đó**; `get_task_detail` chỉ dùng khi người dùng xin "hướng dẫn làm việc X" |
| V3 | **Định tuyến sai** (câu 9, 18, 19) | Lối tắt `làm gì tiếp` bắt cả câu "nhận laptop xong làm gì tiếp theo"; câu về T3 bị hỏi lại làm rõ; câu "có bắt buộc" bị gán nhầm task | Lối tắt chỉ áp dụng khi câu **không** nhắc việc/sự kiện cụ thể; hạ ngưỡng làm rõ, ưu tiên hỏi đáp tài liệu; thêm các câu này vào bộ kiểm thử hồi quy |
| V4 | **Thiếu quan hệ tiên quyết** nên Viga không biết "xong laptop thì làm gì" và lộ trình báo 11/12 việc "làm được ngay" | Task do AI tạo không có tiên quyết; tài liệu có ghi "sau khi có laptop và đăng nhập được Outlook, Teams thì mới tiếp tục bước tiếp theo" | Cho AI đề xuất tiên quyết (kèm trích dẫn câu nói điều đó); HR duyệt ở bước duyệt roadmap (xem mục 7) |
| V5 | **Cùng một câu, lúc đúng lúc "chưa có căn cứ"** (câu 1) | Bước kiểm trích dẫn của Viga (`validator.py`) so khớp **chuỗi con** sau khi chuẩn hóa khoảng trắng nhưng không chuẩn hóa ký hiệu danh sách; mô hình lúc trích có `* `, lúc bỏ `*` thì bị loại thành `NO_BASIS` | Chuẩn hóa ký hiệu Markdown ở **cả nội dung mục và trích dẫn** trước khi so khớp; thử lại một lần khi bị loại; lưu và đưa cho mô hình văn bản đã làm sạch |
| V6 | **Câu trả lời lặp** (câu 12) và đoạn "không có căn cứ" thừa (câu 3) | Câu hỏi nhiều ý bị tách thành nhiều "claim"; hai claim cho cùng đáp án vẫn được in cả hai; claim không có căn cứ vẫn được giữ trong câu trả lời có đáp án | Gộp claim trùng; khi đã có claim trả lời được thì ẩn claim không căn cứ thay vì hiện kèm |
| V7 | **Tài liệu thử nghiệm lẫn vào câu trả lời thật** (câu 3, 4 trích mục của TL2 có nhãn `[TRONG TÀI LIỆU NGÀY 1]`) | TL2 là tài liệu thử nghiệm nằm cùng kho với TL1 | Ưu tiên nguồn gốc (TL1) khi hai nguồn trùng ý; hoặc đánh dấu TL2 là "thử nghiệm" và không dùng cho nhân viên thật |
| V8 | Chất lượng tách mục của TL1 | Tiêu đề thật nằm lẫn với nội dung (mục "Check-in", "Hợp đồng", "Tủ gửi đồ" nội dung **chính là tiêu đề**; liên kết bị cắt `…`; "windown", "Tittle" chép nguyên) | Chấp nhận phần lỗi chính tả nguồn; thêm bước cảnh báo "mục chỉ có tiêu đề" khi nạp để HR bổ sung |

## 5. "Xem nguồn" có trỏ đúng đoạn không

- **Task đã tạo**: bảng `task_source_mappings` chỉ lưu `document_section_id` (cả mục), **không lưu câu trích**, và giao diện (Quản lý task, trang task của nhân viên) **không có nút xem nguồn**. Vì vậy không thể trỏ đúng đoạn.
- **Viga**: trích dẫn có câu `quote` nhưng nút nguồn mở cả tài liệu rồi cuộn tới mục có tiêu đề trùng và tô **cả mục** (`DocumentModal`, so khớp theo tiêu đề), không tô đúng câu.
- **Bước duyệt roadmap AI mới làm hôm nay**: hộp "xem đúng đoạn nguồn" hiện danh sách câu trích, chưa mở tài liệu tại đúng vị trí.

**Đề xuất:** (1) lưu `quote` (và vị trí ký tự trong mục) vào `task_source_mappings` (migration mới); (2) một trình xem tài liệu dùng chung (`DocumentReader`) nhận `section_id + quote`, cuộn đến đúng chỗ và **tô vàng đúng câu** (so khớp sau chuẩn hóa); (3) dùng cho cả Viga, bước duyệt AI và nút "Nguồn" trên task (HR và nhân viên).

## 6. Giao diện

1. **Khoảng cách thẻ roadmap quá sát.** Thẻ rộng 196px; với `N` task canvas rộng tối thiểu `124·N` px, bước giữa hai nút liên tiếp ≈ 100px nên hai thẻ **cùng hàng** (cách nhau hai bước = 200px) chỉ hở ~4px. Cần rộng khoảng `(N+1)·128` px (hai thẻ cùng hàng cách ≥ 24px) hoặc thu thẻ về 180px. Hằng số này nằm ở **hai nơi** (`JourneyRoad.tsx` và `TaskManagementPage.tsx`) nên cũng là lý do nên cho trang Quản lý task dùng chung `JourneyRoad` như anh nói: sửa một chỗ, ba nơi (Quản lý task, duyệt AI, lộ trình nhân viên) cùng đẹp.
2. **Viga chưa có chế độ mở rộng.** Đề xuất nút "Mở rộng" ở đầu ngăn Viga dẫn tới trang đầy đủ (`/me/viga`) kiểu ChatGPT: cột trái là lịch sử hội thoại, giữa là khung chat rộng, dùng lại cùng kho hội thoại; HR/Admin đã có `/chat`, làm tương tự.
3. **Đã làm trong ngày** (không nằm trong báo cáo này): duyệt đề xuất AI dạng roadmap; khoảng cách tới chân trang; icon nhiều màu...

## 7. Chất lượng 12 task AI so với tài liệu 1

### 7.1 Độ phủ theo từng mục của tài liệu

| Mục TL1 | Có task? | Ghi chú |
|---|---|---|
| 2. Chuẩn bị hồ sơ phải nộp | **Không** | Mục quan trọng nhất của ngày đầu bị bỏ |
| 3. Check-in | Có (T1) | Nội dung chỉ chép lại tiêu đề, không có hướng dẫn thật vì tài liệu không nêu |
| 4. Đào tạo Hội nhập (bắt buộc, ≥80%) | **Không** | Mất cả điều kiện hoàn thành lẫn email đầu mối |
| 5. Ký hợp đồng (email cuối ngày) | Có (T2) | Bước 1 chép nguyên chữ IN HOA của tiêu đề; nên đặt **cuối ngày** |
| 6. Faceid Vincom Đồng Khởi | Có (T3) | Tốt, có ghi rõ chỉ áp dụng cho văn phòng này |
| 7. Nghe kỹ nội quy | **Không** | |
| 8. Nhận laptop, đăng nhập Outlook/Teams | Có (T4) | Tốt; có điều kiện hoàn thành. Thiếu tiên quyết cho các task sau |
| 9. Ảnh đại diện, chữ ký, slide | Có (T5) | Liên kết bị cắt (`…`), chưa đủ để làm |
| 10. Trước khi viết ticket | Có (T6) | Ổn |
| 11. Cách viết email ITHD | Có (T7) | Ổn; mẫu nên giữ thành khối mẫu, chưa là "các bước" |
| 12. Trường hợp riêng ticket không hỗ trợ | Có (T8) | Các bước **rối** (`Đăng ký web mail:`, `hoặc :` đứng trơ trọi vì liên kết bị mất) |
| 13. Cần T3 đồng thuận trước khi điền form | **Không** | Mất mẫu email xin phê duyệt và biểu mẫu VinSOC |
| 14. Máy đã có Ubuntu | Có (T9) | Chép cả câu tiếng Anh nguồn |
| 15. Máy Windows | Có (T10) | Bước 1 là câu tiếng Anh về tiêu chí email phê duyệt, không phải hành động |
| 16. Sau khi VinSOC phản hồi | Có (T11) | Ổn |
| 17. Tủ gửi đồ | Có (T12) | Nguồn tự lặp, task rỗng nội dung hướng dẫn |

Kết luận: **12/16 mục có nội dung được phủ; 4 mục quan trọng (2, 4, 7, 13) bị thiếu**; nhiều "các bước" chỉ chép lại câu nguồn.

### 7.2 Thứ tự và quan hệ

- Cột `sort_order` của cả 12 task đều bằng 0; thứ tự hiện tại chỉ là thứ tự chấp nhận (mã tăng dần), tình cờ trùng thứ tự tài liệu.
- Không task nào có tiên quyết, nên nhân viên thấy 11 trên 12 task "làm được ngay". Tài liệu có hai ràng buộc rõ: *sau khi có laptop và đăng nhập Outlook/Teams mới tiếp tục*; *cần T3 đồng thuận và email VinSOC phản hồi rồi mới tạo ticket (chuỗi T3 → VinSOC → ticket ITHD)*.
- Thứ tự hợp lý theo tài liệu: Hồ sơ → Check-in → Đào tạo Hội nhập và nội quy → Nhận laptop + Outlook/Teams → Ảnh đại diện/chữ ký → Faceid → (chuỗi ticket) → Ký hợp đồng cuối ngày → Tủ gửi đồ.

### 7.3 Nguyên nhân nghi ngờ (cần xác nhận khi chạy lại)

| Mã | Nguyên nhân | Căn cứ |
|---|---|---|
| T-A | **Đề xuất bị loại vì trích dẫn không khớp từng chữ.** `ai_task_service` yêu cầu `quote` là chuỗi con **nguyên văn** của nội dung mục (không chuẩn hóa khoảng trắng hay ký hiệu `* `). Mục 2, 4, 13 có nhiều dòng danh sách `* ...` nên mô hình trích lại bằng chữ liền là bị loại; các mục chỉ một dòng thì qua | Các mục bị thiếu đều là mục nhiều dòng/danh sách; các mục được tạo đều một dòng hoặc đoạn ngắn. Cùng cơ chế gây câu hỏi 1 của Viga lúc đúng lúc sai |
| T-B | Gộp theo tên (`mergeProposals`) và ngân sách prompt có thể bỏ thêm đề xuất | Cần log của lượt chạy; bảng việc nền đã được dọn nên chưa xác minh |
| T-C | AI không được yêu cầu **phủ hết mục** nên bỏ những mục khó (đoạn dài) | Prompt chưa có bước kiểm "mục nào chưa có task" |
| T-D | Dữ liệu nguồn kém: nhiều mục nội dung trùng tiêu đề, liên kết bị cắt | Mục 4 (V8) |

### 7.4 Đề xuất sửa phần sinh task

1. Chuẩn hóa so khớp trích dẫn (bỏ `* `, `\*`, khoảng trắng thừa, chữ hoa chữ thường tiêu đề) ở cả lúc kiểm và lúc lưu; lưu đoạn nguyên văn đã khớp.
2. Sau khi AI trả về, **đối chiếu độ phủ**: liệt kê các mục chưa có task và hiện "Mục chưa có task: …" ở bước duyệt, kèm nút "Đề xuất bổ sung cho các mục này".
3. Cho AI đề xuất **tiên quyết** (kèm câu trích) và **thứ tự** theo trình tự tài liệu; gán `sort_order` đúng khi tạo.
4. Viết "Các bước" thành hành động rõ ràng, không chép nguyên câu in hoa; bỏ bước nếu chỉ lặp tiêu đề.
5. Ghi chú các mục "chỉ có tiêu đề" để HR bổ sung thay vì sinh task rỗng (Check-in, Tủ gửi đồ).

## 8. Trang "Phản hồi Viga" và đánh giá hài lòng (chưa code)

### 8.0 Hiện trạng và khuyết điểm của trang Phản hồi Viga

Ảnh anh gửi cho thấy trang liệt kê cả những câu như "Hồ sơ cần nộp trong ngày đầu gồm những gì?" và "Chương trình Đào tạo Hội nhập có bắt buộc không...?" là **câu chưa trả lời được**, trong khi tài liệu có trả lời (các câu này nằm trong 20 câu chạy thử, nên cũng tự chúng làm bẩn danh sách của phòng HR Onboarding; sau khi duyệt xong sẽ đánh dấu xử lý hoặc dọn). Khuyết điểm đã xác minh trong mã (`services/viga/gaps.py`, `service.py`):

| Mã | Khuyết điểm | Nguyên nhân |
|---|---|---|
| G1 | **Báo thiếu tài liệu oan** | Câu bị ghi là "chưa trả lời được" khi **bất kỳ** một ý nào của câu trả lời là `NO_BASIS`, kể cả khi các ý còn lại đã trả lời được (câu 3), và khi lần hỏi bị rớt ngẫu nhiên do V5 (câu 1, 22) |
| G2 | **Không tự đóng khi đã trả lời được** | Chỉ có nút "Đã xử lý" bằng tay; không ai kiểm lại câu hỏi sau khi bổ sung tài liệu nên HR không biết bổ sung đã đủ chưa |
| G3 | **"Bổ sung tài liệu" chỉ là liên kết sang trang Tài liệu** | Không mang theo câu hỏi; HR phải tự nhớ câu, tự soạn nội dung, tự tải file; không có liên kết giữa câu hỏi và tài liệu được thêm |
| G4 | Không có ngữ cảnh | Chỉ có chữ câu hỏi, số lần, ngày gần nhất; không biết hỏi ở việc nào, Viga đã trả lời gì dở, ý nào thiếu |
| G5 | Không tìm kiếm, không lọc trạng thái, không sắp xếp theo số lần hỏi | Danh sách tĩnh |
| G6 | Chỉ có một nguồn tín hiệu (câu bị bỏ trống) | Không biết nhân viên **có hài lòng** với những câu Viga đã trả lời hay không (câu sai nhưng trông tự tin sẽ không bao giờ xuất hiện ở đây) |
| G7 | Giao diện đơn điệu | Một icon duy nhất ở đầu trang, không icon theo trạng thái; không cùng kiểu với các trang khác (tìm kiếm + ô chọn lọc) |

### 8.1 Đánh giá hài lòng của nhân viên cho từng câu trả lời (đề xuất)

- **Giao diện (ngăn Viga và trang Viga mở rộng):** dưới mỗi câu trả lời có hai nút 👍 "Đúng ý" và 👎 "Chưa đúng". Bấm 👎 mở hàng chọn nhanh lý do: *Sai thông tin · Thiếu thông tin · Khó hiểu / lộn xộn · Không đúng ý tôi hỏi*, kèm ô ghi chú tùy chọn và dòng "Gửi câu hỏi này cho HR" (đã có). Bấm lại để đổi hoặc bỏ đánh giá. Mỗi câu trả lời một đánh giá.
- **Dữ liệu:** bảng mới `viga_feedback` (`message_id` duy nhất, `user_id`, `rating` UP/DOWN, `reason`, `comment`, `created_at`); không lưu thêm nội dung câu hỏi (đã nằm trong `chat_messages`). Migration mới.
- **Riêng tư (giữ quyết định 8):** HR chỉ thấy đánh giá **ẩn danh theo phòng ban**: câu hỏi, câu trả lời tóm tắt, lý do, số lần; không thấy tên người đánh giá hay hội thoại.
- **Hiển thị cho HR:** trang Phản hồi Viga có hai thẻ: **"Chưa có căn cứ"** (danh sách hiện nay, đã sửa G1 đến G5) và **"Chưa hài lòng"** (câu bị 👎, nhóm theo câu hỏi, hiện lý do và câu Viga đã trả lời). Một dòng tóm tắt trên đầu: tỉ lệ hài lòng 7 ngày, số 👎 mới.
- **Số liệu:** thêm "Hài lòng %" vào trang Tổng quan của HR (chỉ nếu vẫn giữ ít biểu đồ; là một con số nhỏ chứ không thêm thẻ) và vào `analytics` (`viga.satisfaction`).
- **Vòng cải tiến:** mỗi câu 👎 trở thành ứng viên cho bộ kiểm thử `eval/` (HR/dev bấm "Thêm vào bộ kiểm thử").

### 8.2 Form "Bổ sung tài liệu" gắn với câu hỏi (đề xuất)

Nút **"Bổ sung tài liệu"** trên mỗi dòng mở một hộp thoại (không chuyển trang), mang sẵn câu hỏi:

1. **Tab "Viết câu trả lời" (nhanh, mặc định):** hiện câu hỏi (sửa được cho rõ nghĩa), ô "Câu trả lời đúng", ô "Đầu mối" (tùy chọn), nhóm tài liệu (Onboarding/Tài liệu khác). Khi lưu, hệ thống thêm một mục **Hỏi đáp** (tiêu đề = câu hỏi, nội dung = câu trả lời) vào tài liệu "Hỏi đáp bổ sung" của phòng ban (tạo bản nháp mới rồi kích hoạt qua việc nền có phần trăm như hiện nay). Chọn cách này vì dữ liệu cho thấy **tài liệu dạng "câu hỏi là tiêu đề" được Viga trả lời tốt nhất** (câu 2, 16 đều đạt, trích đúng).
2. **Tab "Chọn hoặc tải tài liệu":** chọn tài liệu có sẵn (mở bản mới) hoặc tải tệp mới; câu hỏi đi kèm để ghi nhớ nguồn.
3. **Sau khi lưu và kích hoạt xong, tự kiểm lại:** hệ thống hỏi lại đúng câu đó và hiện kết quả ngay trong hộp ("✓ Viga đã trả lời được: ..." hoặc "✗ Vẫn chưa có căn cứ, hãy bổ sung rõ hơn"). **Chỉ khi đạt mới tự đánh dấu đã xử lý**; không đạt thì để mở.
4. Lưu liên kết **câu hỏi ↔ phiên bản tài liệu** (cột mới `content_gaps.resolved_by_version_id`) để HR thấy "đã bổ sung ở đâu" và để sau này truy ngược.
5. Câu hỏi gần giống nhau (đã gom theo không dấu) cùng được đóng khi kiểm lại đạt.

### 8.3 Cách Viga nên trả lời khi tài liệu chỉ có một phần hoặc chưa quy định

Thêm một đường thoát chuẩn **"PARTIAL / CHƯA QUY ĐỊNH"** (câu 21 đến 23): trả lời phần có căn cứ kèm trích dẫn, nói thẳng phần chưa có quy định, nêu đầu mối có trong tài liệu (ví dụ Phòng tuyển dụng) và hiện nút "Gửi câu hỏi này cho HR". Câu loại này **không** bị ghi là "chưa trả lời được" nếu đã nêu được đầu mối; ghi ở mức thấp hơn ("tài liệu chưa quy định") để HR biết quy định còn thiếu.

### 8.4 Icon và giao diện trang Phản hồi Viga

- Tiêu đề trang dùng FlatIcon nhiều màu (hộp thư, hổ phách); mỗi dòng có icon trạng thái màu (cảnh báo hổ phách = chưa xử lý, dấu tích xanh = đã xử lý, 👎 đỏ nhạt = chưa hài lòng); số lần hỏi và lý do dạng nhãn màu.
- Thanh công cụ cùng kiểu các trang khác: **ô tìm kiếm** (theo câu hỏi) + **ô chọn lọc** (Chưa xử lý / Đã xử lý / Tất cả; loại: Chưa có căn cứ / Chưa hài lòng) + sắp xếp (nhiều lần nhất, mới nhất).
- Thẻ cuối chạm sát chân trang (đã có quy tắc 2px), bảng không trượt ngang, chữ dài cắt có chú giải khi trỏ chuột.

## 9. Thứ tự sửa đề xuất (chờ anh duyệt)

| Ưu tiên | Việc | Phạm vi | Ghi chú |
|---|---|---|---|
| 1 | Chuẩn hóa so khớp trích dẫn (Viga và AI tạo task) | Backend nhỏ | Sửa gốc của V5 và T-A; có test hồi quy từ bộ 20 câu |
| 2 | Dựng Markdown cho câu trả lời Viga, làm sạch trích dẫn, gộp claim trùng | Frontend + backend nhỏ | V1, V6 |
| 3 | Định tuyến Viga: câu hỏi sự kiện chạy trong phạm vi nguồn của task; siết lối tắt | Backend vừa | V2, V3 |
| 4 | Roadmap: sửa khoảng cách; cho Quản lý task dùng chung `JourneyRoad` | Frontend vừa | Mục 6.1 |
| 5 | Sinh task: đối chiếu độ phủ, tiên quyết, thứ tự, văn phong bước | Backend + frontend vừa | Mục 7.4 |
| 6 | Lưu câu trích vào nguồn của task; trình xem tô đúng câu; nút Nguồn trên task | Migration + backend + frontend | Mục 5 |
| 7 | Viga mở rộng toàn trang | Frontend vừa | Mục 6.2 |
| 8 | Trang Phản hồi Viga: sửa báo oan (G1), tự kiểm lại sau khi bổ sung, form Bổ sung tài liệu, tìm kiếm và lọc, icon | Backend + frontend vừa | Mục 8.0, 8.2, 8.4 |
| 9 | Đánh giá hài lòng 👍/👎 cho từng câu trả lời và thẻ "Chưa hài lòng" cho HR | Migration + backend + frontend | Mục 8.1 |
| 10 | Đường thoát "PARTIAL / chưa quy định" | Backend vừa | Mục 8.3 |
| 11 | Bộ 26 câu thành test tự động (CI dùng mô hình giả; bản chạy thật để chạy tay) | Test | Báo cáo trước/sau mỗi lần sửa |

**Cần anh quyết:** (d) tab "Viết câu trả lời" có tạo thành tài liệu "Hỏi đáp bổ sung" của phòng ban như mục 8.2 hay mỗi câu một tài liệu riêng; (e) đánh giá 👎 có bắt buộc chọn lý do không (đề xuất: không bắt buộc, chọn nhanh một chạm); (a) tài liệu thử nghiệm TL2 có để chung kho với TL1 không (V7); (b) Viga toàn trang chỉ cho nhân viên hay cả HR/Admin; (c) có cho AI tự đề xuất tiên quyết hay chỉ gợi ý để HR bấm chấp nhận.

## 10. Phụ lục: câu trả lời thô của Viga

Nằm ở [eval/viga_eval.json](eval/viga_eval.json) (mỗi câu: loại trả lời, đường xử lý, thời gian, câu trả lời, các claim và đoạn trích). Chạy lại bằng [eval/viga_eval.py](eval/viga_eval.py) sau mỗi lần sửa để so trước và sau.
