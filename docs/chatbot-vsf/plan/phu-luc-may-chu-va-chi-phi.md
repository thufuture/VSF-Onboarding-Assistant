# Phụ lục: lựa chọn máy chủ, tên miền, CI và chi phí

> Phụ lục của [master-plan.md](master-plan.md) (mục 5). Master plan chỉ giữ quyết định; lý do và so sánh nằm ở đây. Thao tác từng bước ở [huong-dan-thiet-lap-may-chu.md](huong-dan-thiet-lap-may-chu.md).
> Cập nhật 2026-09-21 (chuyển máy chính sang Oracle). Giá và gói thay đổi thường xuyên: **kiểm lại trên trang chính thức trước khi đăng ký**. Chỉ dẫn nguồn chính thức của nhà cung cấp; nhận định không có nguồn chính thức được ghi là "chưa xác minh".

## 1. Quyết định

| Hạng mục | Chọn | Lý do ngắn |
|---|---|---|
| **Máy chủ chính** | **Oracle Cloud Always Free**, máy `VM.Standard.A1.Flex` (ARM), Ubuntu 24.04, **1–2 OCPU, 4–6 GB RAM**, ổ khởi động 50 GB | Miễn phí thật và đủ cấu hình. Đây là **thử nghiệm có giới hạn**, không phải máy demo đã được bảo đảm (xem mục 2) |
| **Máy chủ dự phòng** | **Hetzner Cloud CX23** (2 vCPU, 4 GB RAM, 40 GB NVMe, x86) | Ổn định; thuê 1 tháng rồi xóa; dùng khi Oracle không tạo được hoặc không ổn định |
| Quy tắc thử | Tạo máy Oracle **tối đa khoảng 1 giờ**; không được thì chuyển sang Hetzner. **Không đặt lịch demo lên Oracle** khi chưa chạy ổn định vài ngày liên tục | Không để Oracle ăn cả ngày của Phase 1b |
| Kiến trúc image | **Đa kiến trúc `linux/amd64` + `linux/arm64`** | Chuyển giữa Oracle (ARM) và Hetzner (x86) không phải build lại |
| Tên miền | `<tên>.duckdns.org` | Miễn phí; Caddy lấy chứng chỉ Let's Encrypt được; đổi sang tên miền riêng sau chỉ cần đổi `PUBLIC_HOST` và DNS |
| CI/CD | GitHub Actions + GHCR | Không phụ thuộc runner tự dựng; đã có sẵn trong thiết kế |

## 2. Oracle Cloud Always Free: dữ kiện và rủi ro

**Đã kiểm (tài liệu chính thức: [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)):**
- Máy ARM `VM.Standard.A1.Flex`: tài khoản Always Free được **tổng 2 OCPU và 12 GB RAM**, chia tùy ý (một máy lớn hoặc tối đa hai máy 1 OCPU).
- **200 GB** Block Volume (tính chung cho ổ khởi động và ổ dữ liệu), kèm 5 bản sao lưu volume; ổ khởi động tối thiểu **47 GB**.
- **10 TB/tháng** dữ liệu ra ngoài.
- Dùng được ở mọi availability domain trừ South Korea North (Chuncheon).
- Image `paradedb/paradedb:v0.25.4-pg16` **có bản `linux/arm64`** (đọc manifest trên Docker Hub ngày 2026-09-21), nên DB chạy được trên ARM.

**Rủi ro (cũng từ tài liệu chính thức, trừ dòng cuối):**
1. **Máy nhàn rỗi có thể bị thu hồi.** Oracle coi máy là "idle" nếu trong 7 ngày cả ba điều đúng: CPU (phân vị 95) dưới 20%, mạng dưới 20%, và với máy ARM thì bộ nhớ dưới 20%; khi đó máy "may be reclaimed". Demo thưa người dùng dễ rơi đúng định nghĩa này.
2. **Có thể không tạo được máy:** Oracle tự nêu lỗi "out of host capacity" là "temporary lack of Always Free shapes in your home region"; cách xử lý là thử availability domain khác hoặc chờ rồi thử lại.
3. **Báo cáo bị vô hiệu hóa ngoài ý muốn:** cộng đồng Oracle có [báo cáo instance A1 bị vô hiệu hóa dù nằm trong hạn mức mới](https://community.oracle.com/customerconnect/discussion/974476/always-free-a1-instance-disabled-despite-being-within-new-2-ocpu-12-gb-limit) (nguồn cộng đồng, không phải tài liệu chính thức).
4. **Chưa xác minh** (trang FAQ của Oracle chặn truy cập lúc tra cứu): đăng ký có cần thẻ không (theo hiểu biết chung thì thường có), có nên nâng lên Pay As You Go hay không, và home region có đổi được không (theo hiểu biết chung là không).

**Giảm rủi ro:**
- **Cấp RAM vừa phải** để mức dùng bộ nhớ thường trên 20% (stack ước ~1,5 GB thì 4–6 GB cho ~25–37%); vì ba điều kiện phải cùng đúng mới bị coi là idle. Chưa chắc cách Oracle đo bộ nhớ; đo `docker stats` ở Phase 2 rồi chỉnh (A1 Flex chỉnh được cấu hình, cần khởi động lại).
- **Dựng lại được nhanh:** mọi thứ chạy bằng `docker compose` và nạp seed bằng lệnh; bí mật lưu ngoài máy; `pg_dump` định kỳ tải về laptop; tạo bản sao lưu ổ khởi động của Oracle.
- **Không nâng lên Pay As You Go nếu không cần** (có thể phát sinh phí); nếu nâng thì đặt budget alert.
- **Chọn home region cẩn thận** (đề xuất Singapore cho gần Việt Nam).

**Việc kỹ thuật riêng của ARM:**
- Build `linux/arm64` (buildx, hoặc runner ARM; với repo private tôi chưa kiểm được có dùng runner ARM miễn phí không). Python và Node có bản ARM theo kiến thức chung; kiểm khi build.
- Ảnh Ubuntu trên Oracle thường có quy tắc `iptables` chặn cổng trong máy, ngoài quy tắc ở VCN, nên `bootstrap.sh` phải mở 80/443 ở cả hai lớp (theo kinh nghiệm chung, kiểm bằng cách thử).

## 3. Vì sao không dùng Vercel (hoặc PaaS) thay máy chủ

Hệ này cần Postgres có `pgvector` và `pg_search` (ParadeDB), một worker chạy liên tục cho hàng đợi ingest, và backend FastAPI. Nền tảng serverless như Vercel không có DB ParadeDB và không có tiến trình nền dài hạn. Đặt riêng frontend lên Vercel vẫn cần máy chủ cho phần còn lại và thêm rủi ro cookie phiên khác origin (Ralion phải rewrite `/api` và nâng timeout upload vì lý do này). Các PaaS chạy container (Render, Railway, Fly.io) là khả thi về nguyên tắc nhưng tính tiền theo từng dịch vụ, phải viết lại phần triển khai, và ParadeDB phải chạy như một dịch vụ riêng có ổ đĩa (chưa thử).

| PaaS | Trang chính thức | Điểm cần biết khi tra cứu |
|---|---|---|
| Render | [Deploy for Free](https://render.com/docs/free) | Dịch vụ miễn phí ngủ khi không dùng; Postgres miễn phí có hạn dùng → không hợp worker và DB lâu dài |
| Railway | [Pricing Plans](https://docs.railway.com/pricing/plans) | Gói trả phí tính theo mức dùng; bản dùng thử ngắn |
| Fly.io | [Pricing](https://fly.io/pricing/) | Kiểm xem tài khoản mới còn gói miễn phí không; mỗi máy tính tiền riêng |

## 4. Các lựa chọn máy chủ khác đã xem xét

| Lựa chọn | Miễn phí? | Đủ chạy hết? | Điểm chính (nguồn) |
|---|---|---|---|
| **Hetzner CX23** (dự phòng) | Trả phí ~€5,49/tháng | Đủ | Giá theo tra cứu, chỉ ở Đức/Phần Lan ([thông báo gói CX](https://www.hetzner.com/pressroom/new-cx-plans/)); tính theo giờ, làm tròn lên, không vượt trần tháng; **máy tắt vẫn bị tính tiền, chỉ xóa mới ngừng** ([FAQ thanh toán](https://docs.hetzner.com/cloud/billing/faq/)); trang tạo server hiện giá thật; độ trễ từ Việt Nam cao hơn |
| **AWS free plan** | Không vĩnh viễn: [$100 credit ngay, thêm tối đa $100 khi làm 5 hoạt động ($20 mỗi hoạt động, tốn phí trừ vào credit)](https://docs.aws.amazon.com/accounts/latest/reference/bcm-lite-free-tier-credits.html); gói hết sau 6 tháng hoặc khi hết credit | Đủ với `c7i-flex.large` (x86, theo trí nhớ 4 GB, cần kiểm) | [Loại máy miễn phí cho tài khoản từ 15/07/2025](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html): `t3.micro/small`, `t4g.micro/small`, `c7i-flex.large`, `m7i-flex.large`. Cần thẻ. **Hết hạn thì tài khoản tự đóng**, dữ liệu giữ 90 ngày ([chọn gói](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)). Credit ước tính đủ ~1,5–3 tháng nếu chạy 24/7 (chưa kiểm giá) |
| **Azure for Students** | [$100 credit dùng trong 12 tháng, **không cần thẻ**, chỉ dành cho sinh viên đại học toàn thời gian, gia hạn hằng năm](https://azure.microsoft.com/en-us/free/students) | Đủ nếu dùng credit cho VM x86 4 GB; VM miễn phí trong gói nhỏ hoặc ARM (chưa kiểm cấu hình) | Hết credit thì subscription bị vô hiệu hóa trừ khi chuyển trả phí. Trang không nêu hạn chế vùng/kích cỡ, nhưng gói sinh viên thường có quota nhỏ: kiểm khi tạo máy. GitHub Student Developer Pack cũng cấp [Azure $100](https://education.github.com/pack/) |
| Google Cloud | Vĩnh viễn: [1 VM e2-micro, chỉ vùng Mỹ, 1 GB egress/tháng](https://cloud.google.com/free) | **Không** (1 GB RAM theo kiến thức chung) | Thiếu RAM, độ trễ xa, giới hạn băng thông |
| Neon (Postgres) | Có gói miễn phí ([0,5 GB/dự án, 100 giờ compute](https://neon.com/pricing)) | **Không đúng thiết kế** | Tài liệu Neon ghi [`pg_search` đã deprecated, không dùng cho dự án mới](https://neon.com/docs/extensions/pg-extensions): mất tìm kiếm BM25 |
| Hugging Face Spaces | Tài liệu nêu [tạo Space chạy Docker cần gói trả phí](https://huggingface.co/docs/hub/en/spaces-overview) (chưa thử) | Không | Ổ đĩa không bền, ngủ sau 48 giờ |
| Contabo, OVHcloud | Trả phí | **Chưa xác minh** | Có bài tổng hợp bên thứ ba cho thấy gói 4 GB rẻ hơn trên giấy; chưa xác minh điều khoản (phí khởi tạo, hợp đồng tối thiểu) nên không dùng để quyết định |
| Laptop + tunnel | 0 đồng | Chỉ demo | **[Quick Tunnel của Cloudflare](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/) không hỗ trợ SSE**, giới hạn 200 request đồng thời, URL ngẫu nhiên; chat dùng SSE nên phải dùng chế độ chat không stream |

Email sinh viên **không** cho AWS lợi thế thêm (free plan dành cho mọi khách hàng mới); AWS Educate hiện chỉ nêu [học và lab miễn phí](https://aws.amazon.com/education/awseducate/), không nhắc tới credit.

## 5. Tên miền

- **DuckDNS** ([duckdns.org](https://www.duckdns.org/)): miễn phí. Caddy tự xin và gia hạn chứng chỉ ([Automatic HTTPS](https://caddyserver.com/docs/automatic-https)); cần cổng 80 và 443 mở và DNS trỏ đúng IP.
- **Không dùng `<ip>.sslip.io` cho HTTPS:** hạn mức chứng chỉ Let's Encrypt dùng chung của nó đã từng cạn ([issue của chính dự án](https://github.com/cunnie/sslip.io/issues/108)).

## 6. CI có đủ không

- CI chạy trên **runner do GitHub cấp**, không tốn tài nguyên máy chủ. GitHub Free cho repo private có 2.000 phút Actions/tháng ([GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage)). Số lần chạy tối đa phụ thuộc thời gian mỗi lần (chưa đo). **Build đa kiến trúc (QEMU cho ARM) chậm hơn**, cần đo.
- Image ở GHCR: xem [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages); điều kiện có thể đổi, nên giữ image nhỏ và xóa tag cũ.
- Đánh giá golden bằng LLM **không** đưa vào mỗi PR (tốn tiền API): chạy thủ công.

## 7. Bảng "đủ hay không" cho demo

| Thành phần | Chạy ở đâu | Đủ không |
|---|---|---|
| ParadeDB (`pgvector`, `pg_search`, `btree_gist`) | Container trên máy chủ | Đủ trên 4 GB theo thiết kế; **chưa đo**, kiểm bằng `docker stats` ở Phase 2 |
| Backend FastAPI + worker | Container trên máy chủ | Đủ |
| Frontend Next.js (`standalone`) | Container trên máy chủ | Đủ (build ở CI, không build trên máy chủ) |
| Caddy (HTTPS, một origin) | Container trên máy chủ | Đủ |
| CI: lint, test, build, deploy | Runner GitHub | Đủ trong 2.000 phút/tháng nếu không chạy LLM thật trong CI |
| Embedding BGE-M3 | Modal (dịch vụ ngoài) | Không chạy trên máy 4 GB. Modal có credit miễn phí hằng tháng ở gói Starter và budget/spend limit cấp workspace ([Pricing](https://modal.com/pricing), [Budgets](https://modal.com/docs/guide/budgets)); kiểm số hiện hành khi đăng ký và **đặt budget ngay** |
| LLM | DeepSeek (giao diện tương thích OpenAI, `deepseek-flash`) | Chi phí riêng. Giá theo [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) có khoảng giá (giờ cao điểm/thấp điểm) và giá riêng cho phần đã lưu cache; kiểm trang chính thức và đặt hạn mức chi tiêu. Lưu ý Ralion đang khai báo đơn giá cũ trong `src/config.py` (`deepseek_input_usd_per_mtok`), không dùng lại con số đó |
| Langfuse | Không tự host trên máy chủ này | Bản tự host cần thêm nhiều dịch vụ phụ (kiểm tài liệu Langfuse); dùng Cloud hoặc tắt |
| Sao lưu | `pg_dump` trên máy chủ, tải về máy; bản sao lưu ổ khởi động của Oracle | Đủ cho demo |

**Không đủ cho:** nhiều người dùng đồng thời, embedding chạy cục bộ, Langfuse tự host. Nếu thiếu RAM khi đo, tăng cấu hình (Oracle A1 Flex chỉnh được, tối đa 12 GB tổng) hoặc bỏ dịch vụ không cần.

## 8. Chi phí một tháng (ước tính)

| Khoản | Ước tính |
|---|---|
| Máy chủ Oracle Always Free | 0 (trong hạn mức) |
| Máy chủ dự phòng Hetzner CX23 (chỉ khi phải dùng) | ≈ €5,49 (trần tháng, tính theo giờ; xóa sớm thì ít hơn), có thể phụ phí IPv4, chưa gồm thuế |
| Tên miền DuckDNS | 0 |
| CI GitHub Actions + GHCR | 0 nếu trong hạn mức |
| **LLM và embedding** | **Chưa biết**; phụ thuộc số câu hỏi và số lần chạy đánh giá; là khoản dễ vượt nhất, cần hạn mức chi tiêu ở nhà cung cấp và Modal |
