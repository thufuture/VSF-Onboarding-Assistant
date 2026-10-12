# Báo cáo triển khai: đưa cấu hình tối ưu vào sản phẩm Viga

Ngày: 12/10/2026. Nhánh: `feat/pdf-sang-word-va-ocr`. Đọc cùng [BAO-CAO-TONG-HOP-BENCHMARK-VIGA.md](BAO-CAO-TONG-HOP-BENCHMARK-VIGA.md) (lý do chọn) và [bao-cao-benchmark-toi-uu-cuoi.md](bao-cao-benchmark-toi-uu-cuoi.md) (số liệu đợt 3).

## 1. Đã làm gì trong sản phẩm

| Thay đổi | Tệp | Mặc định |
|---|---|---|
| Tham số RRF (`k`, hệ số hai nhánh) và hồ sơ truy hồi | `backend/src/config.py` (`retrieval_profile`, `rrf_k`, `rrf_weight_bm25`, `rrf_weight_vector`, `retrieval_max_sections`, hàm `resolve_retrieval_tuning`), `services/retrieval/hybrid_search.py` (`reciprocal_rank_fusion(..., weights=)`, `search_to_sections(rrf_k, bm25_weight, vector_weight)`), `services/viga/pipeline.py` | `legacy` = đúng hành vi cũ |
| Sửa lỗi ký tự đặc biệt trong truy vấn BM25 | `services/retrieval/hybrid_search.py` | luôn bật (chỉ thử lại khi truy vấn gốc bị từ chối) |
| Router v2 (ngoài phạm vi, chèn lệnh) | `services/viga/router.py`, `service.py` | tắt (`VIGA_ROUTER_V2`) |
| Chế độ suy luận ở bước trả lời | `config.py`, `services/viga/answer_service.py` | `always` (như cũ) |
| Giới hạn ngữ cảnh khác (trần token, khử trùng lặp) | `services/viga/context_limit.py` | tắt, chưa đề xuất dùng |

**Hồ sơ `optimized`** = RRF `k=10`, BM25 : vector = 0,1 : 1, giữ 5 mục mỗi câu hỏi con. Từng biến môi trường (`RRF_K`, `RRF_WEIGHT_BM25`, `RRF_WEIGHT_VECTOR`, `RETRIEVAL_MAX_SECTIONS`) nếu đặt sẽ ghi đè hồ sơ. Hồ sơ gói sẵn các tham số phải đi cùng nhau, vì cắt 5 mục với RRF mặc định làm Recall tụt từ 98,7% xuống 77% (đợt 2). Cờ được ghi trong `.env.example` kèm giải thích.

## 2. Kiểm chứng

### 2.1 Test tự động
`pytest tests`: 392 đạt, 191 bỏ qua (cần DB), 0 lỗi; `ruff` và `mypy` sạch. Test mới: trọng số RRF (3 ca), giải quyết hồ sơ truy hồi (3 ca: legacy, optimized, ghi đè), `use_reasoning`, `limit_context`, `parse_route` với `kind`, làm sạch ký tự truy vấn.

### 2.2 Chạy lại benchmark bằng chính mã sản phẩm
Cấu hình: `RETRIEVAL_PROFILE=optimized`, `VIGA_ROUTER_V2=1`, suy luận bật. Không dùng cờ riêng của công cụ đo. Tập kiểm 50 câu, 1 lượt, giám khảo DeepSeek. So với ô C-bật của đợt 3 (cùng ý đồ nhưng đo bằng công cụ):

| Chỉ số (26 câu có đáp án) | C-bật (công cụ đo) | Hồ sơ sản phẩm |
|---|---|---|
| Context Recall | 100% | 96,2% |
| Hit@1 | 75,6% | 73,7% |
| Faithfulness | 97,8% | 93,8% |
| Đúng (1–5) | 4,73 | 4,50 |
| North Star | 80,8% | 84,6% |
| Token vào mỗi câu | 5.217 | 5.473 |
| P50 / P95 luồng tài liệu | 5,92 / 9,73 giây | 6,36 / 11,20 giây |
| Tỉ lệ lỗi | 0% | 0% |
| Câu ngoài phạm vi và chèn lệnh (5 câu) → OUT_OF_SCOPE | 0/5 (xã giao) | **5/5** |

Kết luận: hai kết quả khớp nhau trong khoảng nhiễu đã biết (Hit@1 cùng cấu hình dao động 69,9 đến 75,6%; chênh Faithfulness, Recall nằm trong phạm vi của 26 câu và một lượt). **Mã sản phẩm tái tạo đúng hành vi đã đo.** Router v2 hoạt động đúng với 5/5 câu.

**Lưu ý về thời gian:** P95 luồng tài liệu 11,2 giây vượt 10 giây một chút (P95 toàn bộ 50 câu là 10,0 giây). Đây là chênh trong nhiễu (lượt trước 9,7 giây) nhưng cho thấy bật suy luận chỉ vừa sát trần. Nếu cần biên an toàn, đặt `ANSWER_THINKING_MODE=off` (P95 đã đo 5,8 giây, đổi lại Faithfulness có xu hướng giảm).

## 3. Trạng thái các môi trường

| Môi trường | Trạng thái |
|---|---|
| Mã | Trên nhánh `feat/pdf-sang-word-va-ocr` (chưa push, chưa PR) |
| **Dev (máy của bạn)** | Backend đã build lại; `.env` đặt `RETRIEVAL_PROFILE=optimized`, `VIGA_ROUTER_V2=true`, suy luận `always`. Đã kiểm trong container: tham số hiệu lực là `k=10`, 0,1 : 1, giữ 5 mục |
| **Production** | **Không đổi**: mặc định `legacy`; chỉ bản sửa BM25 (an toàn) có hiệu lực khi triển khai |

## 4. Cách bật, theo dõi và hoàn tác
- **Bật:** thêm `RETRIEVAL_PROFILE=optimized` và `VIGA_ROUTER_V2=true` vào `.env` (hoặc biến môi trường của dịch vụ), tạo lại container backend.
- **Hoàn tác:** đặt `RETRIEVAL_PROFILE=legacy`, `VIGA_ROUTER_V2=false`, tạo lại container. Không cần migrate DB hay build lại.
- **Theo dõi sau khi bật:** độ trễ P50/P95 luồng tài liệu, tỉ lệ "không có căn cứ", 👍👎, tỉ lệ lỗi, chi phí mỗi câu (kỳ vọng giảm khoảng 65%).
- **Triển khai production đề nghị:** bật cho một nhóm nhỏ trước, so sánh 1 đến 2 tuần, rồi mở rộng.

## 5. Việc chưa làm (và vì sao)
| Việc | Lý do |
|---|---|
| Duyệt nhãn vàng bởi 2 người, chạy ≥ 3 lượt | Hiện 26 câu, một lượt: chênh dưới 6 điểm là nhiễu; cần trước khi bật production |
| Giám khảo thứ hai | Khóa OpenAI bị vô hiệu hóa; các khóa khác hết hạn mức; đợt 3 chỉ có DeepSeek |
| Bật `ANSWER_THINKING_MODE=off` | Chưa đủ bằng chứng chất lượng; để chọn sau khi có nhiều lượt |
| Rerank | Không đáng ở quy mô kho hiện tại (chậm thêm 6 giây, câu trả lời không tốt hơn) |
| Test tích hợp `_bm25_search` với DB thật | Mới kiểm tay trên bản chụp |
| Đo trên AWS 2 vCPU và kho lớn hơn | Số đo hiện từ máy dev 6 CPU, kho 100 mục |
| Bộ an toàn chạy lại với hồ sơ mới | Chưa chạy; cắt ngữ cảnh có thể ảnh hưởng chèn lệnh gián tiếp |

## 6. Rủi ro cần theo dõi
- Với câu hỏi cần nhiều mục tài liệu, cắt 5 mục mỗi câu hỏi con có thể bỏ sót. Đo cho thấy Recall 96 đến 100% và phủ ý không tụt có ý nghĩa, nhưng chỉ 12 câu nhiều ý.
- Router v2 làm độ phủ công cụ ở câu kép tụt (58% xuống 33% ở đợt 2, 6 câu). Theo dõi nhóm này sau khi bật.
- Kho tài liệu lớn lên có thể làm RRF `k=10` và cắt 5 mục kém hơn; chạy lại benchmark khi kho thay đổi nhiều.

## 7. Bổ sung 12/10: rủi ro thiên vị vector và "giữ chỗ BM25"

RRF tối ưu cho BM25 trọng số rất thấp (0,1) nên một mục chỉ BM25 tìm ra, dù xếp hạng 1, không thể vào 5 mục đầu nếu vector không xếp nó trong top 30. Đã đo bằng 18 câu cần khớp đúng chuỗi (mã form, email, địa chỉ, viết tắt; [bo-cau-hoi/khop_chinh_xac_10.json](bo-cau-hoi/khop_chinh_xac_10.json), kết quả [ket-qua/quet-tham-so/khop_chinh_xac.md](ket-qua/quet-tham-so/khop_chinh_xac.md)):

| Cách xếp hạng | Hit@1 | Hit@5 |
|---|---|---|
| BM25 riêng | 94% | 100% |
| vector riêng | 72% | 100% |
| RRF mặc định | 94% | 100% |
| **RRF tối ưu (đang dùng)** | 89% | **100%** |

Mục đúng bị đẩy xuống hạng 2 đến 4 nhưng vẫn nằm trong 5 mục. Biên an toàn mỏng (chuỗi ngẫu nhiên `OSlq7VPRkk` xuống hạng 4).

**Đã cài "giữ chỗ BM25" sau cờ `RETRIEVAL_BM25_RESERVE` (mặc định 0 = tắt)** trong `hybrid_search.select_with_bm25_reserve`: dành vài chỗ trong số mục giữ lại cho mục đứng đầu của BM25. Kết quả đo ([ket-qua/quet-tham-so/giu_cho_bm25.md](ket-qua/quet-tham-so/giu_cho_bm25.md)):

| Giữ N mục, chỗ BM25 | Ngữ nghĩa: mục đúng có mặt | Khớp chuỗi: mục đúng có mặt |
|---|---|---|
| 5, không giữ chỗ | 87,7% | 100% |
| 5, 1 chỗ | 83,1% | 100% |
| 3, không giữ chỗ | 76,9% | 94,4% |
| 3, 1 chỗ | 70,8% | 100% |

**Kết luận: không bật với N = 5.** Nó không cải thiện bộ khớp chuỗi (đã 100%) và làm tụt bộ ngữ nghĩa khoảng 4,6 điểm, vì lấy chỗ của mục RRF. Nó chỉ có lợi khi số mục giữ lại rất nhỏ (3 hoặc 2), điều chưa cần. Giữ cờ ở dạng bảo hiểm cho trường hợp kho lớn hơn và phải cắt ít mục; khi đó đo lại trước khi bật. Test đơn vị: 4 ca cho hàm chọn mục.

## 8. LLM dự phòng (Claude Haiku) cho chatbot và sinh task

**Đã cài** `FallbackChatCompletion` (`backend/src/infrastructure/ai/fallback_chat_completion.py`), nối qua `get_chat_completion_port` nên cả Viga và sinh task dùng chung.

| Quy tắc | Chi tiết |
|---|---|
| Khi nào chuyển | Nhà cung cấp chính đã thử lại xong mà vẫn lỗi hạ tầng: hết giờ, mạng, 429, 5xx, từ chối xác thực. Lỗi nội dung (phản hồi sai định dạng) không chuyển |
| Bộ ngắt mạch | 3 lỗi liên tiếp thì bỏ qua nhà cung cấp chính 60 giây, rồi thử lại; dùng chung toàn tiến trình |
| Việc nền (sinh task) | Mặc định **không** dùng dự phòng (`LLM_FALLBACK_FOR_BACKGROUND=false`) vì đổi mô hình có thể đổi chất lượng task; thử lại sau là đủ |
| Nhà cung cấp dự phòng | `anthropic/claude-haiku-5.5` qua OpenRouter; không dùng JSON mode (tự lấy phần JSON), tắt suy luận bằng `reasoning.enabled=false`, không stream, trần đầu ra 4.000 token |
| Cờ | `LLM_FALLBACK_ENABLED` (mặc định `false`), cần `LLM_FALLBACK_API_KEY`; thiếu khóa thì tự tắt |

Test: 12 ca mới (chuyển theo từng mã lỗi, lỗi nội dung không chuyển, ngắt mạch mở và hồi phục, việc nền, lỗi của dự phòng được báo lên, thân yêu cầu của adapter dự phòng, adapter chính không đổi).

**Thử thật (12/10):** nhà cung cấp chính bị ép lỗi xác thực → lớp bọc chuyển sang Haiku đúng; Haiku bị OpenRouter từ chối 402 vì khóa **hết số dư**, và Viga trả lại thông báo "tạm thời chưa trả lời được" thay vì lỗi 500. **Chưa kiểm được một câu trả lời hoàn chỉnh bằng Haiku**, nên chưa đo chất lượng tiếng Việt và độ ổn định JSON của Haiku trong luồng Viga.

**Cần để bật:** khóa OpenRouter có số dư (vài đô-la là thừa, mỗi câu khoảng $0,001), đặt vào `.env` ngoài repo, rồi chạy lại 9 đến 50 câu bằng dự phòng để xác nhận chất lượng. Nội dung tài liệu nội bộ sẽ được gửi cho hãng thứ hai khi dự phòng chạy: cần xác nhận chính sách dữ liệu.
