# Kế hoạch: tự host BGE-M3 trên AWS để giảm độ trễ embedding (chưa làm gì trên AWS)

Ngày viết: 06/10/2026. Trạng thái: **đã thực hiện đến bước đo và báo cáo**; xem `bao-cao-embedding-tu-host.md`. Đây là bản kế hoạch gốc, giữ nguyên để đối chiếu; những chỗ khác với thực tế được ghi ở phần cuối.

## 1. Vì sao làm

Trong một câu hỏi Viga (trace anh gửi), bước `embed_questions` mất **1,58 giây** khi GPU Modal đã ấm, và lần nguội từng mất tới **86 giây** (báo cáo triển khai AWS, mục Modal). Phần này gồm: đường mạng từ backend tới Modal, hàng đợi GPU, và thời gian suy luận thật. Tôi **chưa tách được** ba phần đó, nên chưa biết tự host sẽ giảm bao nhiêu. Việc đầu tiên của kế hoạch là đo để biết.

Giả thuyết cần kiểm chứng: backend nằm ở Singapore (AWS `ap-southeast-1`), nếu embedding cũng nằm cùng vùng, cùng mạng riêng thì phần đường mạng gần như bằng 0, và một câu hỏi ngắn (vài chục token) chạy trên CPU hiện đại có thể đủ nhanh. Đây là **giả thuyết, chưa phải kết quả**.

## 2. Hiện trạng tôi đã đọc được (chỉ đọc)

| Mục | Giá trị | Nguồn |
|---|---|---|
| Tài khoản AWS | `<id-tài-khoản-AWS>`, người dùng IAM `terraform-deployer`, vùng `ap-southeast-1` | `aws sts get-caller-identity` |
| EC2 đang dùng | `vsf-aws` (`i-001256d35e85809ae`), loại **`m7i-flex.large`**: 2 vCPU, 8 GiB RAM, **không có GPU**, mạng tới 12,5 Gbps, kiến trúc x86_64 | `describe-instances`, `describe-instance-types` |
| Trạng thái | Lúc đầu phiên là `stopped`; **lúc tôi hỏi lại là `running`** (khởi động lúc 07:04 UTC, tức 14:04 giờ VN), nên đã có người bật | `describe-instances` |
| Ổ đĩa | 30 GB gp3, một Elastic IP `3.1.239.21` gắn vào máy | `describe-volumes`, `describe-addresses` |
| Phần mềm trên máy | Docker: Postgres (ParadeDB), backend, Caddy (HTTPS tự động); frontend ở Vercel | `docs/chatbot-vsf/plan/infrastructure/bao-cao-trien-khai-aws-vercel.md` |
| Cách quản lý hạ tầng | Terraform trong `infra/aws/` (`main.tf`, `variables.tf`, `outputs.tf`) | repo |
| Gói tài khoản | "Free Plan" dạng **credit** (hết khoảng 22/03/2027 hoặc khi hết credit); `m7i-flex.large` được ghi là "Eligible for the free offer" | báo cáo triển khai AWS, mục 0.1 |
| Embedding hiện tại | App Modal `ralion-bge-m3-embedder`, GPU **L4**, đơn giá tính trong code `0,000222 USD/giây`; báo cáo cũ ghi còn khoảng 28,7 USD credit Modal | `config.py`, báo cáo AWS |
| Giao thức embedding | `POST {endpoint}/embed` với `{"texts":[...]}` (≤ 32 chuỗi), header `Authorization: Bearer`, trả `{"vectors","model_version","dimension"}`, vector 1024 chiều | `modal_adapter.py` |

**Những gì tôi chưa biết, nói thẳng:**
- Hạn mức vCPU cho máy GPU (nhóm G/VT) của tài khoản: người dùng `terraform-deployer` không có quyền đọc Service Quotas (`AccessDenied`). Tài khoản "Free Plan" mới cũng thường bị giới hạn loại máy.
- Mức dùng RAM/CPU thật của máy `vsf-aws` khi backend và Postgres đang chạy: tôi không SSH vào máy (cổng 22 chỉ mở cho IP của anh và tôi sẽ không tự mở thêm).
- Giá theo giờ chính xác của từng loại máy: tôi sẽ **tra trên trang giá chính thức** trước khi tạo, không đoán.

## 3. Dịch vụ tự host: cái tôi đã viết sẵn (chưa chạy ở đâu)

Thư mục `docs/value/benchmark-modal-llm-viga/bge-m3-embedder/`:

| File | Làm gì |
|---|---|
| `server.py` | FastAPI, **cùng hợp đồng `/embed` với Modal**, nên backend chỉ đổi `EMBEDDING_ENDPOINT` và `EMBEDDING_API_KEY`, không sửa mã. Trả vector dense đã chuẩn hóa. Từ chối khởi động nếu thiếu khóa. |
| `Dockerfile` | Ảnh CPU mặc định (có thể build bản GPU bằng `--build-arg TORCH_INDEX=...`). Mô hình được **tải sẵn lúc build**. Khóa API truyền lúc chạy, không ghi vào ảnh. |
| `requirements.txt` | `fastapi`, `uvicorn`, `sentence-transformers` (torch cài riêng trong Dockerfile). |

Phía đo: `scripts/bench_embedding.py` (so Modal với tự host), `golden_set.json` (25 câu).

## 4. Mô hình lấy ở đâu, cấu hình thế nào

- **Nguồn: Hugging Face, mô hình `BAAI/bge-m3`** (bản gốc do BAAI phát hành). Thư viện `sentence-transformers` tự tải khi lần đầu khởi tạo. Trọng số khoảng 2 đến 2,5 GB (con số tôi nhớ, **cần xác nhận khi tải thật**); giấy phép tôi nhớ là MIT, **cần xác nhận lại trên trang mô hình** trước khi dùng cho sản phẩm.
- **Tải ở đâu:** tải một lần lúc `docker build` (máy build cần ra internet, tới `huggingface.co`). Nếu không muốn phụ thuộc Hugging Face lúc triển khai, có thể đẩy bản sao sang S3 của anh rồi build từ đó.
- **Cấu hình chính (biến môi trường của `server.py`):**
  - `EMBEDDING_API_KEY`: khóa Bearer (bắt buộc).
  - `DTYPE`: `fp32` (mặc định, chuẩn nhất) hoặc `bf16` (nhanh hơn trên CPU Intel đời Sapphire Rapids có AMX như họ `m7i`; **phải đo độ chính xác** trước khi dùng).
  - `MAX_LENGTH=512`, `MODEL_VERSION`: phải **trùng** giá trị đang lưu ở cột `document_chunks.embedding_model_version`. **Đính chính sau khi làm thật:** giá trị đó là `BAAI/bge-m3@5617a9f6…` (Modal trả cả mã bản), không phải `bge-m3`; dịch vụ giờ tự lấy đúng dạng này, nếu không thì tìm kiếm trả rỗng.
- **Vì sao không phải re-embed tài liệu:** nếu vector tự host trùng vector Modal (cosine ≈ 1,0) thì các vector đã lưu trong DB vẫn dùng được. Phép đo ở mục 6 sẽ kiểm tra đúng điều này.

## 5. Ba phương án nơi chạy (cần anh chọn)

| | Phương án | Ưu | Nhược / rủi ro |
|---|---|---|---|
| **A** | Chạy cùng máy `vsf-aws` (thêm một container) | Không tốn thêm tiền, gần như không có độ trễ mạng | Máy chỉ 8 GiB RAM, đã chạy Postgres + backend. Mô hình cộng torch có thể ăn vài GiB RAM và tranh CPU với backend, **có thể làm chậm cả hệ thống đang dùng thật**. |
| **B** | **Máy CPU thứ hai** trong cùng VPC, chỉ nhận kết nối từ `vsf-aws` | Tách biệt, không ảnh hưởng máy chính, dễ tắt khi không dùng, có thể thử `m7i-flex` hoặc dòng `c7i`/`m7i` có AMX | Tốn credit theo giờ (cần tra giá), phải thêm tài nguyên vào Terraform |
| **C** | Máy GPU (ví dụ họ `g4dn`) | Nhanh nhất cho nạp tài liệu hàng loạt | Hạn mức G/VT chưa biết (có thể bằng 0 và phải xin tăng), Free Plan có thể chặn, đắt nhất |

**Tôi đề xuất B bắt đầu bằng đo cục bộ trước** (mục 6, bước 1), rồi mới tạo máy. Lý do: câu hỏi người dùng chỉ là vài chục token, CPU có khả năng đủ; A rủi ro cho hệ thống đang chạy; C chưa chắc tạo được.

## 6. Các bước, và điều kiện dừng

1. **Đo cục bộ trên máy dev (không đụng AWS).** Build ảnh CPU, chạy trên máy anh, chạy `bench_embedding.py` để kiểm **độ chính xác**: cosine giữa vector tự host và vector Modal (cùng câu hỏi, và cùng đoạn văn đã lưu trong DB), độ trùng top-5 truy hồi, hit@5 trên 25 câu golden. Độ trễ của máy dev **không đại diện cho AWS**, bước này chỉ để chốt chuyện đúng/sai. *Cần tải khoảng 2 đến 3 GB về máy anh.*
   - **Dừng nếu** cosine trung bình < 0,999 hoặc hit@5 thấp hơn Modal: tìm nguyên nhân (dtype, độ dài tối đa, cách chuẩn hóa) trước khi đi tiếp.
2. **Tạo máy CPU trên AWS bằng Terraform (phương án B).** Tôi viết thay đổi vào `infra/aws/`, **chạy `terraform plan` và đưa anh xem trước khi `apply`**. Quy tắc bảo mật: nhóm bảo mật chỉ cho cổng 8080 từ nhóm bảo mật của `vsf-aws`, không mở ra internet; khóa Bearer sinh ngẫu nhiên, lưu ngoài repo.
   - Quyền: người dùng `terraform-deployer` hiện có quyền EC2/SG/EIP ở `ap-southeast-1`; nếu thiếu quyền tôi sẽ **báo anh**, không tự nâng quyền.
3. **Đo độ trễ thật từ `vsf-aws` tới máy mới** và so với Modal bằng cùng bộ golden (xen kẽ hai nguồn để cùng điều kiện mạng): p50, p95, câu một chuỗi, lô 32 đoạn.
4. **Chạy lại bộ Viga đầy đủ (40 câu × 2 lượt)** với backend trỏ vào embedding tự host, để thấy ảnh hưởng lên độ trễ cả câu hỏi và độ chính xác câu trả lời.
5. **Báo cáo** vào `docs/value/benchmark-modal-llm-viga/` (số liệu thô, bảng, hạn chế). Nếu số không tốt hơn Modal, tôi **nói rõ là không đáng**, tắt máy và đưa lại kết quả.

**Cách quay lại:** đổi `EMBEDDING_ENDPOINT`/`EMBEDDING_API_KEY` về Modal (khóa Modal vẫn giữ nguyên). Không có dữ liệu nào bị đổi nên không phải khôi phục. Máy mới tắt hoặc xóa bằng `terraform destroy` đúng tài nguyên đó.

## 7. Thay đổi mã sản phẩm có thể cần (chỉ làm sau khi anh duyệt)

- `modal_adapter.py` ghi cứng `provider="modal"` vào số liệu chi phí, và đơn giá tính theo giây GPU của Modal. Với tự host, chi phí thật là tiền thuê máy theo giờ, **không** phải giây GPU. Tôi sẽ thêm cấu hình tên nhà cung cấp và đơn giá riêng để thống kê chi phí không sai.
- `embedding_keep_warm_enabled`: tự host không có khởi động nguội, tắt cơ chế giữ ấm để khỏi gửi yêu cầu thừa.
- Không đổi hợp đồng `/embed`, không đổi cách lưu vector.

## 8. Chi phí và rủi ro

- **Tiền:** máy CPU thứ hai tính theo giờ trên credit; tôi sẽ **tra giá chính thức và báo con số cụ thể** trước khi `apply`, và tắt máy ngay sau khi đo xong nếu không giữ lại.
- **Bảo mật:** dịch vụ chỉ nằm trong mạng riêng, có khóa, nhóm bảo mật hẹp; ảnh Docker không chứa khóa.
- **Độ chính xác:** `bf16` có thể làm vector lệch nhẹ; chỉ bật khi cosine đạt ngưỡng ở bước 1.
- **Nạp tài liệu lớn:** CPU chậm hơn GPU khi nhúng hàng trăm đoạn một lúc; đây là nhược điểm dự kiến, tôi sẽ đo luôn lô 32 đoạn để anh thấy.
- **Hạn chế của phép đo:** golden set chỉ 25 câu trên 2 tài liệu nhỏ; số lượt đo ít nên p95 chỉ mang tính tham khảo.

## 9. Việc song song đang chạy (không liên quan AWS)

Bộ đo Viga cho ba phương án thinking (A hiện trạng, B tắt ở route+rewrite, C tắt cả ba bước): **bản A xong** (73/80 câu đạt, trung vị 7,66 giây), bản B đang chạy, bản C chưa chạy. Kết quả sẽ vào cùng thư mục.

## 10. Cần anh trả lời để làm tiếp

1. Chọn phương án nơi chạy: **A, B (đề xuất), hay C**.
2. Cho phép tôi **tải khoảng 2 đến 3 GB** và chạy Docker trên máy dev cho bước 1?
3. Có cho phép tôi chạy `terraform plan` (chỉ xem, không tạo gì) để lấy cấu hình và giá trước không?
4. Có muốn mô hình tải từ Hugging Face trực tiếp, hay sao chép sang S3 của anh trước?

## 11. Khác với kế hoạch khi thực hiện (cập nhật 06/10/2026)

- Bỏ bước đo trên máy dev: tải mô hình về máy anh chỉ đạt khoảng 0,2 đến 0,3 MB/giây; anh chọn đo thẳng trên AWS.
- SSH từ máy dev bị chặn lúc đầu vì mạng chặn cổng 22 đi ra rồi vì IP đổi; sau khi anh đổi mạng và tôi cập nhật luật SSH chỉ trên nhóm bảo mật của máy embedder thì dùng được.
- Không chạy được script đo trên máy chính `vsf-aws` (tôi không vào được máy chính): đo độ trễ trên chính máy embedder, cùng vùng và cùng AZ.
- Phát hiện lỗi chuỗi phiên bản mô hình (mục 4) và đã sửa.
