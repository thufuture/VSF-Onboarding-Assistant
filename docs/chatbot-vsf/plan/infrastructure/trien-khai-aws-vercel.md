# Triển khai AWS + Vercel — kế hoạch chi tiết (đã duyệt qua trao đổi, chưa thực hiện)

> Thuộc [master-plan.md](../master-plan.md) mục hạ tầng (song song với Phase 11a/11b — kế hoạch VPS Hetzner cũ vẫn giữ nguyên làm phương án dự phòng, không xóa).
> Yêu cầu của bạn: **backend + DB lên AWS, frontend lên Vercel; bạn chỉ tạo tài khoản, còn lại viết file hạ tầng và chạy tự động (Terraform), hạn chế bấm tay trên Console.**
> **Trạng thái (23/09/2026): SẴN SÀNG LÀM H-1.** Tài khoản AWS đã xác minh xong, có **$100 credit AWS Activate, còn 182 ngày (hết hạn 22/03/2027)**, vùng Singapore `ap-southeast-1`. Chưa viết file hạ tầng. Nội dung dưới là kế hoạch đã duyệt trong phiên trao đổi trước — giữ nguyên, chỉ cập nhật trạng thái tài khoản. Xem mục 0.1 (mới) về việc "miễn phí" thực tế đến đâu.

## 0.1 "Miễn phí" thực tế đến đâu — ĐÍNH CHÍNH sau khi kiểm chứng trực tiếp trên Console (23/09/2026)

**Sai lầm ban đầu đã sửa**: tôi từng giả định tài khoản dùng chương trình free-tier 12-tháng cũ (`t3.micro`, 750h/tháng, tách biệt với credit). **Sai** — tài khoản mới của bạn dùng **"Free Plan"** kiểu mới của AWS: $100-200 credit, tài khoản đóng sau **6 tháng hoặc hết credit, tùy cái nào tới trước** (khớp đúng "182 ngày" trong Console). Không có khoản "luôn miễn phí 12 tháng" tách rời nữa — mọi usage đều trừ vào credit, "Free tier eligible" nghĩa là AWS tự đảm bảo instance đó **không tính phí vượt mức trong giới hạn của Free Plan**, không phải "không đụng tới credit".

**Đã xác nhận trực tiếp trên Console của bạn** (ảnh chụp lúc chọn Instance type ở màn Launch Instance — nguồn xác thực nhất, không phải suy đoán): `m7i-flex.large` (2 vCPU, **8GB RAM**) và `t3.micro` (1GB RAM) đều gắn nhãn **"Eligible for the free offer"**.

**Quyết định instance: `m7i-flex.large`** (đổi từ `t3.micro` trong bản kế hoạch gốc) — lý do:
- Đã xác nhận free-tier-eligible thật trong chính tài khoản bạn (ảnh chụp Console, không phải danh sách chung chung).
- 8GB RAM đủ thoải mái cho ParadeDB + FastAPI + Caddy chạy cùng lúc, không cần vá swap nhiều như phương án 1GB ban đầu (vẫn thêm swap 2GB cho chắc, không tốn gì thêm vì EBS free tier 30GB dư sức).
- Kiến trúc x86_64 — khớp Docker image hiện tại, không cần đổi gì (khác `t4g.*` là ARM, sẽ phải xác nhận lại toàn bộ image có hỗ trợ `linux/arm64` không — không cần thiết khi đã có lựa chọn x86_64 free-tier-eligible).

**Elastic IP — ĐÍNH CHÍNH (23/09/2026, đã sai một lần trước đó):** từ 02/2024 AWS tính phí **mọi** IPv4 công
khai $0.005/giờ, **kể cả đang gắn với instance đang chạy** — không phải "gắn thì miễn phí" như câu cũ ghi ở
đây. Với đúng 1 Elastic IP chạy 24/7 (~744h/tháng), khoản này nằm trong ưu đãi riêng **750 giờ IPv4 công
khai/tháng** của tài khoản mới — che phủ đủ cho 1 IP, không phải 12 tháng (tài khoản Free Plan chỉ sống tối
đa **6 tháng**, xem mục 0.1). Nếu tạo thêm IP thứ 2 hoặc account hết hạn 6 tháng, khoản phí này (như mọi
usage khác) trừ vào $100-200 credit. Terraform vẫn tạo `aws_eip` gắn liền `aws_eip_association`, không tách
rời — không phải để "né phí vì đang gắn", mà để tránh tạo dư một Elastic IP idle không lý do (idle cũng bị
tính phí y hệt, chỉ là thêm một IP tốn thêm tiền vô ích).

**Không còn khái niệm "hết 12 tháng thì tính phí ~$7-8/tháng"** như bản gốc ghi — thay vào đó: tài khoản dùng hết $100-200 credit HOẶC quá 6 tháng (22/03/2027) thì dịch vụ dừng, không tự động chuyển sang tính phí thẻ (tài khoản vẫn ở Free Plan cho tới khi bạn tự nâng cấp). Cần theo dõi mức dùng credit định kỳ — xem lại mục 7 (rủi ro) đã cập nhật tương ứng.

## 0. Vì sao làm vậy: bối cảnh và ràng buộc kỹ thuật

**Hiện trạng:** [vsf-onboarding-assistant-deployment-ci.md](../../vsf-onboarding-assistant-deployment-ci.md) và [huong-dan-thiet-lap-may-chu.md](../huong-dan-thiet-lap-may-chu.md) giả định **một VM duy nhất** (Hetzner CX23) chạy cả Postgres/ParadeDB + backend + frontend sau Caddy; cookie phiên là first-party nhờ Caddy route `/api/*` và mọi thứ khác về cùng một domain. Tài liệu deployment-ci còn để ngỏ câu hỏi mở #2: "Frontend: cùng server hay Vercel?".

**ParadeDB không chạy được trên dịch vụ DB quản lý hay serverless.** `pg_search`/BM25 là extension Postgres cần cài trên chính server DB, không có trên RDS (không hỗ trợ extension tùy ý), Neon (đã ngừng hỗ trợ `pg_search`), hay bất kỳ Postgres serverless nào — đã ghi trong [phu-luc-may-chu-va-chi-phi.md](../phu-luc-may-chu-va-chi-phi.md) mục 3. Vì vậy **AWS EC2 chạy Docker Compose** (giống Hetzner, chỉ đổi nhà cung cấp) là lựa chọn đúng, không phải ECS/Fargate/RDS.

**Vấn đề cốt lõi khi tách miền — cookie phiên:** `vsf_session` do backend AWS cấp. Nếu để trình duyệt gọi thẳng AWS từ trang Vercel (kiểu CORS + cookie cross-site `SameSite=None`), thì cookie thuộc domain AWS chứ không thuộc domain Vercel — trình duyệt sẽ **không** gửi kèm khi gọi tới chính trang Vercel. Toàn bộ cơ chế đọc cookie phía server của Next (`proxy.ts` chặn `/chat`, `/admin`; `features/auth/server.ts` gọi `/auth/me` bằng cookie của request; `SessionProvider`) đều dựa trên việc cookie là first-party với trang. Tách domain kiểu CORS sẽ phá vỡ toàn bộ Phase 4 vừa làm xong, buộc viết lại theo hướng auth hoàn toàn ở client — rủi ro cao, không cần thiết.

**Quyết định: dùng Next.js rewrite proxy `/api/*` → AWS backend trên Vercel, giống cách Ralion đã làm.** Trình duyệt luôn thấy một origin duy nhất (domain Vercel); Vercel chuyển tiếp `/api/*` sang AWS ở phía server (server-to-server, không qua trình duyệt). Cookie vẫn first-party với domain Vercel, **không cần sửa gì ở cookie, CORS hay auth** — chỉ cần bật lại rewrite (hiện bị tắt ở production) và trỏ đúng URL AWS.

**Đánh đổi đã chấp nhận:** Vercel Serverless Function có giới hạn thời gian chạy mỗi request (vài chục giây tùy gói). Không ảnh hưởng MVP hiện tại (login/me/refresh/logout, chat minh họa). Cần xem lại khi nối LLM streaming thật ở Phase 2/7 — [vsf-onboarding-assistant-deployment-ci.md](../../vsf-onboarding-assistant-deployment-ci.md) đã ghi rõ đây là điểm đau đã biết của Ralion (phải nới timeout khi upload).

## 1. Kiến trúc

```
Trình duyệt → Vercel (Next.js, miền *.vercel.app hoặc riêng)
                 ├─ trang tĩnh/SSR: Vercel tự phục vụ
                 └─ /api/*  ──(rewrite, server-to-server)──▶  AWS EC2: Caddy (TLS) → backend:8000 → db (ParadeDB, cùng máy)
```

| Thành phần | Trước (Hetzner) | Sau (AWS + Vercel) |
|---|---|---|
| Frontend | Container `frontend` trong compose, sau Caddy | Vercel (Git-based deploy, không cần container) |
| Backend + DB | Cùng VM, sau Caddy | AWS EC2 `m7i-flex.large` (2 vCPU/8GB, free-tier-eligible), cùng VM (đổi nhà cung cấp, không đổi kiến trúc) |
| Same-origin cookie | Caddy route cả `/api/*` và trang | Vercel rewrite `/api/*`; Caddy trên AWS chỉ còn lo backend |
| Tạo hạ tầng | Bấm Console tay (`bootstrap.sh` chạy qua SSH) | **Terraform**: `terraform apply` tạo Key Pair, Security Group, EC2, Elastic IP; `user_data` tự chạy `bootstrap.sh` |
| DNS | `vsf-demo.duckdns.org` (mọi thứ) | `vsf-assistant.duckdns.org` (chỉ API) + domain Vercel miễn phí cho frontend |

## 2. Quyết định cần bạn chốt (mặc định in đậm — đã chốt qua trao đổi)

| # | Quyết định | Mặc định đã chọn | Lựa chọn khác |
|---|---|---|---|
| I1 | Cách trình duyệt gọi API khi frontend và backend khác domain | **Rewrite proxy trên Vercel** (`/api/*` → AWS), cookie vẫn first-party, không sửa auth | CORS + cookie `SameSite=None` cross-site (phải viết lại toàn bộ auth phía client, rủi ro cao) |
| I2 | Cách tạo hạ tầng AWS | **Terraform** (`infra/aws/*.tf`, `terraform apply` một lệnh) | Bấm tay trên Console (chậm, khó lặp lại, khó dọn sạch) |
| I3 | Loại máy EC2 | **m7i-flex.large** (2 vCPU, 8GB RAM — đã xác nhận "Eligible for the free offer" trực tiếp trên Console tài khoản bạn, 23/09/2026) | `t3.micro` (1GB RAM, chật hơn, cũng free-tier-eligible nhưng không đủ thoải mái) |
| I4 | Vùng AWS | **ap-southeast-1 (Singapore)** — đã chọn khi tạo tài khoản | ap-southeast-2 (Sydney, xa hơn) |
| I5 | DNS cho backend AWS | **DuckDNS subdomain mới** `vsf-assistant.duckdns.org` (miễn phí, đã quen quy trình) | Route 53 (mất phí domain) |
| I6 | Có xóa đường Hetzner cũ không | **Không xóa** — giữ `deploy/compose.vps.yml`, `release.yml` làm phương án dự phòng đã chạy thử, chỉ thêm nhánh AWS song song | Xóa hẳn Hetzner |
| I7 | Danh tính Terraform dùng để gọi AWS API | **IAM user riêng** (không dùng root), quyền vừa đủ EC2+VPC, access key lưu bằng `aws configure` trên máy bạn (không qua chat) | Dùng access key của root (không khuyến khích, AWS cảnh báo) |

## 3. File cần viết

### 3.1 Terraform (mới, tạo hạ tầng tự động)

```text
infra/aws/main.tf                  provider aws (region ap-southeast-1); aws_key_pair; aws_security_group
                                    (22 chỉ từ var.my_ip, 80/443 mở); aws_instance (Ubuntu 24.04 x86_64 qua
                                    data "aws_ami", type m7i-flex.large, EBS gp3 30GB mã hoá +
                                    delete_on_termination, IMDSv2 bắt buộc, user_data qua templatefile()
                                    chạy bootstrap.sh qua cloud-init, thêm bước tạo swap 2GB); aws_eip +
                                    aws_eip_association; tag Project=vsf-onboarding-assistant trên mọi
                                    resource (lọc Cost Explorer)
infra/aws/cloud-init.sh.tftpl      template cho user_data — file riêng bắt đầu đúng cột 0, tránh bug
                                    heredoc HCL nuốt/sót khoảng trắng trước "#!" (xem comment trong main.tf)
infra/aws/variables.tf             region, my_ip, ssh_public_key_path, instance_type (mặc định m7i-flex.large)
infra/aws/outputs.tf               in Elastic IP và Instance ID sau khi apply — để trỏ DuckDNS
infra/aws/terraform.tfvars.example mẫu điền my_ip, đường dẫn khóa công khai
infra/aws/README.md                lệnh terraform init/plan/apply/destroy; cách lấy my_ip; trỏ DuckDNS
```

`.gitignore` gốc thêm: `infra/aws/.terraform/`, `infra/aws/terraform.tfstate*`, `infra/aws/*.tfvars` (trừ `.example`) — trạng thái hạ tầng và khóa không vào git.

### 3.2 Hạ tầng AWS phía server (mới, không đụng `deploy/compose.vps.yml` của Hetzner)

```text
deploy/aws/compose.aws.yml         copy từ compose.vps.yml, BỎ service frontend; caddy chỉ depends_on [backend]
deploy/aws/Caddyfile               copy từ deploy/Caddyfile, bỏ nhánh route frontend:3000 (miền này chỉ phục vụ API)
deploy/aws/env/compose.env.example giống bản VPS, PUBLIC_HOST = vsf-assistant.duckdns.org
deploy/aws/env/backend.env.example giống bản VPS
scripts/aws/deploy.sh              phỏng theo scripts/vps/deploy.sh, CHỈ 1 image (backend), bỏ frontend khỏi
                                    run_stack/wait_ready/smoke
scripts/aws/rollback.sh            bản rút gọn của scripts/vps/rollback.sh, gọi deploy.sh mới
```

`scripts/vps/bootstrap.sh` **dùng lại nguyên văn** (Ubuntu 24.04, cài Docker, ufw, cứng hóa SSH) — Terraform gọi nó qua `user_data`, không cần bản riêng cho AWS.
`scripts/vps/backup-db.sh` **dùng lại nguyên văn** (đã thêm biến `COMPOSE_FILE` — mặc định giữ hành vi VPS cũ, AWS truyền `COMPOSE_FILE=$ROOT/deploy/aws/compose.aws.yml` khi gọi qua `VSF_ROOT`). `scripts/vps/smoke-test.sh` **KHÔNG dùng lại được** — nó kiểm cả `/vi/login` và `/` chuyển hướng (frontend), miền AWS chỉ phục vụ `/api/*` (frontend ở Vercel) nên sẽ luôn FAIL 2 kiểm tra đó; viết `scripts/aws/smoke-test.sh` riêng (bớt 2 kiểm tra frontend, giữ nguyên phần `/api/*`).

### 3.3 Frontend (1 thay đổi nhỏ, không đổi logic auth)

`frontend/next.config.ts`: bỏ điều kiện `NODE_ENV === "production"` khiến rewrite bị tắt ở prod; luôn rewrite `/api/:path*` → `API_UPSTREAM_URL` khi biến này có giá trị (áp dụng cả dev lẫn Vercel). Sửa lại comment (Caddy trên AWS không còn lo phần frontend).

**Không đổi:** `proxy.ts`, `features/auth/server.ts`, `SessionProvider.tsx`, `session.ts`, cookie backend (`samesite="lax"`, `secure` theo `APP_ENV`) — tất cả giữ nguyên vì kiến trúc vẫn "same-origin nhìn từ trình duyệt".

### 3.4 CI/CD

`.github/workflows/release-aws.yml` (mới, không sửa `release.yml` của Hetzner): trigger `push main` + `workflow_dispatch`; chạy `verify` → `publish` (tái dùng, chỉ cần digest backend) → job `deploy` điều kiện theo biến repo `DEPLOY_AWS_ENABLED=true`, dùng GitHub Environment `production-aws` (secrets `AWS_EC2_HOST`, `AWS_EC2_USER`, `AWS_EC2_SSH_KEY`, `AWS_EC2_SSH_HOST_KEY`; var `PUBLIC_API_URL`). SSH rsync `deploy/aws/` + `scripts/aws/` + `scripts/vps/backup-db.sh`/`smoke-test.sh`, chạy `scripts/aws/deploy.sh <backend-digest>`.

Vercel **không cần workflow riêng** — tự deploy qua GitHub App khi push, độc lập với Actions.

### 3.5 Tài liệu

- File này (kế hoạch).
- `docs/chatbot-vsf/plan/infrastructure/bao-cao-trien-khai-aws-vercel.md` — viết sau khi làm xong từng bước, theo mẫu `bao-cao-phase-4.md`.
- Cập nhật [vsf-onboarding-assistant-deployment-ci.md](../../vsf-onboarding-assistant-deployment-ci.md): đóng câu hỏi mở #2 → chốt Vercel; thêm mục kiến trúc AWS+Vercel.
- Cập nhật [phu-luc-may-chu-va-chi-phi.md](../phu-luc-may-chu-va-chi-phi.md): thêm chi phí AWS EC2 `m7i-flex.large` trong Free Plan (**ĐÍNH CHÍNH 25/09/2026: không phải $0** — chạy 24/7 tốn khoảng $2,4–3/ngày và trừ vào credit; xem [ke-hoach-giam-chi-phi-aws.md](ke-hoach-giam-chi-phi-aws.md); dịch vụ dừng khi hết 6 tháng/22-03-2027 hoặc hết $100-200 credit, không tự chuyển sang tính phí thẻ) và Vercel Hobby (miễn phí).
- Cập nhật [plan/README.md](../README.md): thêm dòng trỏ tới thư mục `infrastructure/`.

## 4. Kế hoạch theo bước

| Bước | Nội dung | Ai làm | Checkpoint |
|---|---|---|---|
| **H-0** | Tài khoản AWS: MFA, Zero-spend budget, vùng Singapore | **Bạn — ĐÃ XONG** | — |
| **H-1** | Tôi viết `infra/aws/*.tf`, `deploy/aws/*`, `scripts/aws/*.sh`, `release-aws.yml`, sửa `next.config.ts`, viết tài liệu | Tôi | Lint/typecheck/test/build cục bộ xanh; review kỹ script so với bản VPS |
| **H-2** | Bạn tạo IAM user + access key (quyền EC2+VPC), cài Terraform, `aws configure` | Bạn (tôi hướng dẫn từng lệnh) | `aws sts get-caller-identity` trả đúng danh tính IAM user |
| **H-3** | Sinh cặp khóa SSH (`ssh-keygen`), điền `terraform.tfvars` | Bạn | — |
| **H-4** | `terraform init` rồi `terraform apply` | Bạn (tôi đọc output cùng, xác nhận trước khi gõ `yes`) | **CP-H4**: output có Elastic IP và Instance ID |
| **H-5** | Trỏ DuckDNS `vsf-assistant.duckdns.org` sang Elastic IP | Bạn | `nslookup vsf-assistant.duckdns.org` ra đúng IP |
| **H-6** | SSH vào máy, tạo `.env` (mật khẩu sinh bằng `openssl rand`, không qua chat), chạy `scripts/aws/deploy.sh` lần đầu bằng tay | Bạn (tôi không tự SSH khi chưa được xác nhận) | **CP-H6**: `smoke-test.sh https://vsf-assistant.duckdns.org` qua hết |
| **H-7** | Tạo GitHub Environment `production-aws` + secrets, bật `DEPLOY_AWS_ENABLED=true` | Bạn | Push `main` tự deploy qua Action |
| **H-8** | Tạo tài khoản Vercel (đăng nhập GitHub), import repo, Root Directory = `frontend`, env `API_UPSTREAM_URL` = URL AWS | Bạn | **CP-H8**: trang Vercel mở được, `/api/v1/health` qua rewrite trả `{"status":"ok"}` |
| **H-9** | Thử đăng nhập/đăng xuất trên trang Vercel | Bạn | **CP-H9**: hoạt động y như bản chạy cục bộ (cookie vẫn first-party) |

## 5. Việc bắt buộc chỉ mình bạn làm được

Terraform cần danh tính để gọi API AWS thay bạn — 3 việc này không ai làm hộ được:
1. Tạo **IAM user** riêng (không dùng root), quyền vừa đủ (EC2 + VPC) theo nguyên tắc least-privilege — tôi đưa đúng bộ quyền cần tick khi tới bước.
2. Tạo **Access key** cho IAM user đó, lưu vào cấu hình AWS CLI trên máy bạn (`aws configure`) — **khóa không đi qua chat**.
3. Cài chương trình **Terraform** (một lần).

Sau đó mọi việc còn lại (tạo/sửa/hủy EC2, Security Group, Elastic IP) chạy bằng `terraform apply` / `terraform destroy`, không cần vào Console bấm nữa. Muốn dọn dẹp để tránh tốn phí (ví dụ tạm dừng dự án): chỉ cần `terraform destroy`.

## 6. Kiểm chứng

- Cục bộ: `next.config.ts` mới vẫn chạy đúng dev (rewrite tới `127.0.0.1:8000`) — thử bằng `npm run dev` và đăng nhập như hiện tại.
- `scripts/aws/deploy.sh`: review kỹ so với `scripts/vps/deploy.sh` cho khớp biến, nhưng **chỉ chạy thật sau khi có EC2** (không giả lập được ở máy bạn vì cần đúng hệ điều hành/Docker).
- Sau khi có AWS: `smoke-test.sh https://vsf-assistant.duckdns.org` (gọi trực tiếp AWS, không qua Vercel) phải qua hết như bản Hetzner.
- Sau khi có Vercel: mở trang Vercel, `/api/v1/health` qua rewrite phải trả `{"status":"ok"}`; đăng nhập/đăng xuất phải hoạt động y hệt bản chạy cục bộ.
- Không phá vỡ đường Hetzner hiện có: `release.yml` và `deploy/compose.vps.yml` không bị sửa; `git diff` xác nhận.

## 7. Rủi ro và cách xử lý

| Rủi ro | Xử lý |
|---|---|
| Dùng hết $100-200 credit hoặc quá 6 tháng (22/03/2027) → tài khoản Free Plan ngừng cấp quyền, dịch vụ dừng đột ngột | Zero-spend budget đã đặt; theo dõi "Credits remaining" trên Console định kỳ; ghi nhắc hạn 22/03/2027 vào tài liệu; `terraform destroy` dọn sạch khi tạm dừng dự án |
| Vercel Serverless Function timeout khi nối LLM streaming thật (Phase 2/7) | Đã ghi nhận là rủi ro đã biết (giống Ralion); xem lại kiến trúc rewrite khi tới Phase 2-E/7, có thể cần SSE qua kênh khác hoặc tăng `maxDuration` |
| Access key AWS lộ (commit nhầm, dán vào chat) | `.gitignore` chặn `*.tfvars` và state; luôn nhắc không dán khóa vào chat; nếu lộ, vô hiệu hóa access key ngay trong IAM |
| `terraform apply` tạo nhầm tài nguyên hoặc sai vùng | `terraform plan` luôn chạy trước, tôi đọc cùng bạn trước khi bạn xác nhận `apply` |
| Security Group mở SSH cho "Anywhere" thay vì đúng IP của bạn | Biến `my_ip` bắt buộc trong `terraform.tfvars`, không có giá trị mặc định `0.0.0.0/0` cho cổng 22 |
| DuckDNS IP cũ (Elastic IP đổi khi `terraform destroy` rồi `apply` lại) | Elastic IP là địa chỉ tĩnh, chỉ đổi khi hủy `aws_eip`; nếu đổi, cập nhật lại DuckDNS (bước thủ công, ghi trong README) |

## 8. Thứ tự tiếp theo

1. Tôi viết toàn bộ file ở mục 3 (H-1), chạy kiểm tra cục bộ, commit trên nhánh riêng (`deploy-aws-vercel`), báo bạn trước khi bạn thao tác gì trên máy thật.
2. Bạn làm H-2 đến H-9 theo hướng dẫn từng bước.
3. Viết `bao-cao-trien-khai-aws-vercel.md` sau khi cả AWS lẫn Vercel chạy thật và qua hết kiểm chứng.
