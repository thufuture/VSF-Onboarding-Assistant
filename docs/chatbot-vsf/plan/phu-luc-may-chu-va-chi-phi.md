# Phụ lục: lựa chọn máy chủ, tên miền, CI và chi phí

> Phụ lục của [master-plan.md](master-plan.md) (mục 5). Master plan chỉ giữ quyết định; lý do và so sánh nằm ở đây. Thao tác từng bước ở [huong-dan-thiet-lap-may-chu.md](huong-dan-thiet-lap-may-chu.md).
> Tra cứu ngày 2026-09-20. Giá và gói thay đổi thường xuyên: **kiểm lại trên trang chính thức trước khi đăng ký**. Chỉ dẫn nguồn chính thức của nhà cung cấp; nhận định không có nguồn chính thức được ghi là "chưa xác minh".

## 1. Quyết định

| Hạng mục | Chọn | Lý do ngắn |
|---|---|---|
| Máy chủ | VPS cá nhân **Hetzner Cloud CX23** (2 vCPU, 4 GB RAM, 40 GB NVMe) | 4 GB đủ cho thiết kế (embedding và LLM là dịch vụ ngoài); x86; tính tiền theo giờ có trần theo tháng nên thuê 1 tháng rồi xóa |
| Tên miền | `<tên>.duckdns.org` | Miễn phí; Caddy lấy chứng chỉ Let's Encrypt được; đổi sang tên miền riêng sau chỉ cần đổi `PUBLIC_HOST` và DNS |
| CI/CD | GitHub Actions + GHCR | Không phụ thuộc runner tự dựng; đã có sẵn trong thiết kế |

## 2. Vì sao không dùng Vercel (hoặc PaaS) thay máy chủ

Hệ này cần Postgres có `pgvector` và `pg_search` (ParadeDB), một worker chạy liên tục cho hàng đợi ingest, và backend FastAPI. Nền tảng serverless như Vercel không có DB ParadeDB và không có tiến trình nền dài hạn. Đặt riêng frontend lên Vercel vẫn cần máy chủ cho phần còn lại và thêm rủi ro cookie phiên khác origin (Ralion phải rewrite `/api` và nâng timeout upload vì lý do này). Các PaaS chạy container (Render, Railway, Fly.io) là khả thi về nguyên tắc nhưng: tính tiền theo từng dịch vụ (4 tiến trình chạy liên tục), phải viết lại phần triển khai (không còn Caddy và `deploy.sh`), và ParadeDB phải chạy như một dịch vụ riêng có ổ đĩa (chưa thử).

| PaaS | Trang chính thức | Điểm cần biết khi tra cứu |
|---|---|---|
| Render | [Deploy for Free](https://render.com/docs/free) | Dịch vụ miễn phí ngủ khi không dùng; Postgres miễn phí có hạn dùng (kiểm số ngày trên trang) → không hợp worker và DB lâu dài |
| Railway | [Pricing Plans](https://docs.railway.com/pricing/plans) | Gói trả phí tính theo mức dùng (CPU, RAM, ổ đĩa, băng thông) → khó đoán chi phí |
| Fly.io | [Pricing](https://fly.io/pricing/) | Kiểm xem tài khoản mới còn gói miễn phí không; mỗi máy tính tiền riêng, ổ đĩa tính theo dung lượng cấp |

## 3. Các lựa chọn máy chủ khác

| Lựa chọn | Trạng thái |
|---|---|
| Contabo, OVHcloud | Có bài tổng hợp bên thứ ba cho thấy gói 4 GB rẻ hơn trên giấy; **chưa xác minh bằng tài liệu chính thức** điều khoản (phí khởi tạo, hợp đồng tối thiểu, cách tính tiền) nên không dùng để quyết định |
| Oracle Cloud Always Free | Hạn mức đã thay đổi theo các bản tin năm 2026, máy là ARM (phải build `linux/arm64`, kiểm ParadeDB có bản arm64), hay hết capacity; **chưa xác minh bằng tài liệu Oracle**; không khuyến nghị cho lần deploy đầu |
| Azure for Students, credit sinh viên khác | Điều kiện thay đổi; kiểm trên [GitHub Education](https://education.github.com/pack) và trang nhà cung cấp; cần xác minh sinh viên |
| Laptop + tunnel | Chỉ là đường lui. **[Quick Tunnel của Cloudflare](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/) không hỗ trợ SSE** và giới hạn 200 request đồng thời, URL ngẫu nhiên; chat của dự án dùng SSE nên phải dùng chế độ chat không stream (một POST trả `result` JSON) |

## 4. Sự thật về Hetzner cần nhớ

- Giá CX23 khoảng €5,49/tháng theo tra cứu, chỉ ở Đức/Phần Lan ([thông báo gói CX](https://www.hetzner.com/pressroom/new-cx-plans/)); **trang tạo server hiện giá thật**, có thể kèm phụ phí IPv4 nhỏ, chưa gồm thuế.
- Tính theo giờ, làm tròn lên, không vượt trần tháng; **server tắt máy vẫn bị tính tiền, chỉ xóa server mới ngừng** ([FAQ thanh toán của Hetzner](https://docs.hetzner.com/cloud/billing/faq/)). Ghi ngày xóa server vào lịch.
- Máy ở châu Âu nên độ trễ từ Việt Nam cao hơn; chấp nhận được cho demo, nên tự đo.

## 5. Tên miền

- **DuckDNS** ([duckdns.org](https://www.duckdns.org/)): miễn phí. Caddy tự xin và gia hạn chứng chỉ ([Automatic HTTPS](https://caddyserver.com/docs/automatic-https)); cần cổng 80 và 443 mở và DNS trỏ đúng IP.
- **Không dùng `<ip>.sslip.io` cho HTTPS:** hạn mức chứng chỉ Let's Encrypt dùng chung của nó đã từng cạn ([issue của chính dự án](https://github.com/cunnie/sslip.io/issues/108)).

## 6. CI có đủ không

- CI chạy trên **runner do GitHub cấp**, không tốn tài nguyên VPS. GitHub Free cho repo private có 2.000 phút Actions/tháng ([GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage)). Số lần chạy tối đa phụ thuộc thời gian mỗi lần (chưa đo).
- Image ở GHCR: xem [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages); điều kiện có thể đổi, nên giữ image nhỏ và xóa tag cũ.
- Đánh giá golden bằng LLM **không** đưa vào mỗi PR (tốn tiền API): chạy thủ công.

## 7. Bảng "đủ hay không" cho demo

| Thành phần | Chạy ở đâu | Đủ không |
|---|---|---|
| ParadeDB (`pgvector`, `pg_search`, `btree_gist`) | Container trên VPS | Đủ trên 4 GB theo thiết kế; **chưa đo**, kiểm bằng `docker stats` ở Phase 2 |
| Backend FastAPI + worker | Container trên VPS | Đủ |
| Frontend Next.js (`standalone`) | Container trên VPS | Đủ (build ở CI, không build trên VPS) |
| Caddy (HTTPS, một origin) | Container trên VPS | Đủ |
| CI: lint, test, build, deploy | Runner GitHub | Đủ trong 2.000 phút/tháng nếu không chạy LLM thật trong CI |
| Embedding BGE-M3 | Modal (dịch vụ ngoài) | Không chạy trên VPS 4 GB. Modal có credit miễn phí hằng tháng ở gói Starter và budget/spend limit cấp workspace ([Pricing](https://modal.com/pricing), [Budgets](https://modal.com/docs/guide/budgets)); kiểm số hiện hành khi đăng ký và **đặt budget ngay** |
| LLM | DeepSeek (giao diện tương thích OpenAI, `deepseek-flash`) | Chi phí riêng. Giá theo [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) có khoảng giá (giờ cao điểm/thấp điểm) và giá riêng cho phần đã lưu cache; kiểm trang chính thức và đặt hạn mức chi tiêu. Lưu ý Ralion đang khai báo đơn giá cũ trong `src/config.py` (`deepseek_input_usd_per_mtok`), không dùng lại con số đó |
| Langfuse | Không tự host trên VPS này | Bản tự host cần thêm nhiều dịch vụ phụ (kiểm tài liệu Langfuse); dùng Cloud hoặc tắt |
| Sao lưu | `pg_dump` trên VPS, tải về máy | Đủ cho demo |

**Không đủ cho:** nhiều người dùng đồng thời, embedding chạy cục bộ, Langfuse tự host. Nếu thiếu RAM khi đo, đổi sang gói lớn hơn của cùng dòng hoặc bỏ dịch vụ không cần.

## 8. Chi phí một tháng (ước tính)

| Khoản | Ước tính |
|---|---|
| Server Hetzner CX23 | ≈ €5,49 (trần tháng, tính theo giờ; xóa sớm thì ít hơn), có thể phụ phí IPv4, chưa gồm thuế |
| Tên miền DuckDNS | 0 |
| CI GitHub Actions + GHCR | 0 nếu trong hạn mức |
| **LLM và embedding** | **Chưa biết**; phụ thuộc số câu hỏi và số lần chạy đánh giá; là khoản dễ vượt nhất, cần hạn mức chi tiêu ở nhà cung cấp và Modal |
