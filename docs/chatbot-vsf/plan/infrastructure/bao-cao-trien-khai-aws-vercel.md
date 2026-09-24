# Báo cáo triển khai AWS + Vercel — tiến độ (cập nhật 24/09/2026: chạy thật end-to-end)

> Kế hoạch: [trien-khai-aws-vercel.md](trien-khai-aws-vercel.md). **Backend chạy thật trên AWS, HTTPS hợp lệ,
> smoke test 4/4 qua.** Domain: `https://vsf-assistant.duckdns.org` (đổi tên từ `vsf-api` — quyết định của
> bạn, đã đồng bộ toàn bộ file). **24/09: frontend Vercel chạy, đăng nhập và chat thật qua Vercel → AWS đã kiểm chứng** (mục 10–12).

## 1. Checkpoint

| Checkpoint | Nội dung | Trạng thái |
|---|---|---|
| H-0 | Tài khoản AWS: MFA, budget, vùng Singapore | **Xong** (trước phiên này) |
| H-1 | Viết `infra/aws/*.tf`, `deploy/aws/*`, `scripts/aws/*.sh`, `release-aws.yml`, sửa `next.config.ts` | **Xong**, đã qua 2 vòng review (xem mục 3) |
| H-2 | IAM user `terraform-deployer` + access key + `aws configure` | **Xong**, xác nhận bằng `aws sts get-caller-identity` (mục 4) |
| H-3 | SSH key + `terraform.tfvars` | **Xong** (bạn tự làm) |
| CP-H4 | `terraform plan` sạch | **Xong** — 5 resource (mục 5) |
| **H-4 (apply)** | `terraform apply` tạo tài nguyên thật | **Xong** — Elastic IP `3.1.239.21`, instance `i-001256d35e85809ae` |
| Chẩn đoán SSH | Bug thật trong `bootstrap.sh` + IP đổi khi chuyển mạng | **Xong**, xem mục 3.7 và 7 |
| **Xác nhận máy chủ** | SSH vào được, Docker/swap/thư mục `/opt/vsf-aws` đúng | **Xong** (mục 6) |
| H-5 | Trỏ DuckDNS `vsf-assistant.duckdns.org` → `3.1.239.21` | **Xong** (bạn tự làm, `nslookup` xác nhận đúng IP) |
| **H-6** | Tạo `.env` thật, build+deploy image lần đầu, HTTPS, smoke test | **Xong** (mục 9) |
| H-7 | GitHub Environment + secrets, bật CI, OIDC deploy | **Xong** — deploy xanh (run #6, #7) |
| H-8/H-9 | Vercel | **Xong** — `https://vsf-onboarding-assistant.vercel.app` (mục 10) |
| Dữ liệu + tài khoản | Nạp tài liệu, tạo tài khoản thật, chat thật | **Xong** (mục 11–12) |

## 2. Quyết định đã chốt khác với bản kế hoạch gốc

| Việc | Bản gốc | Đã đổi thành | Vì sao |
|---|---|---|---|
| Loại EC2 | `t3.micro` (giả định free-tier 12 tháng cũ) | **`m7i-flex.large`** (2 vCPU/8GB) | Tài khoản dùng "Free Plan" mới (credit-based, 6 tháng) không phải free-tier 12 tháng cũ; xác nhận trực tiếp trên Console (ảnh chụp Launch Instance) rằng `m7i-flex.large` gắn nhãn "Eligible for the free offer" |
| Elastic IP | Ghi "miễn phí khi đang gắn" | Đính chính: **luôn tính phí** $0.005/giờ kể cả đang gắn (đổi từ 02/2024), chỉ $0 thật nhờ ưu đãi riêng 750h/tháng IPv4 | Tra blog AWS chính thức xác nhận |

## 3. Đã tự phát hiện + sửa qua review (không tự nhận là đúng ngay từ đầu)

Hai vòng review (tôi tự làm + đối chiếu góp ý bên ngoài, tự kiểm chứng lại từng điểm trước khi sửa, không
nhận đúng/sai theo lời kể):

1. `user_data` heredoc HCL để sót khoảng trắng trước `#!` (do thụt lề nội dung ≠ thụt lề marker đóng, tra
   tài liệu Terraform chính thức xác nhận cơ chế) → phá nhận diện shebang của cloud-init, bootstrap.sh có
   thể không chạy. Sửa: `templatefile()` + file `.tftpl` riêng, mô phỏng lại bằng Python xác nhận hết lỗi.
2. `scripts/vps/backup-db.sh` hardcode tên file compose VPS, không dùng lại được cho AWS như plan tuyên bố
   → thêm biến `COMPOSE_FILE` (mặc định giữ nguyên hành vi VPS cũ).
3. `scripts/vps/smoke-test.sh` không dùng lại được cho AWS (kiểm cả `/vi/login`, miền AWS không có frontend)
   → viết `scripts/aws/smoke-test.sh` riêng, chỉ kiểm `/api/*`.
4. `release-aws.yml` thiếu `packages: read` → `docker login ghcr.io` trên EC2 sẽ bị từ chối nếu package private.
5. `release-aws.yml` build trùng với `release.yml` mỗi lần push main dù chưa bật AWS deploy → thêm điều kiện
   `DEPLOY_AWS_ENABLED` vào cả `verify`/`publish`, không chỉ `deploy`.
6. Thiếu mã hoá EBS, IMDSv2, tag `Project` → thêm `encrypted = true`, `metadata_options.http_tokens =
   "required"`, `local.common_tags`.
7. **Lỗi thật phát hiện qua `terraform plan`** (không phải review tĩnh): AWS Security Group `description`
   chỉ chấp nhận ASCII hẹp (regex `^[0-9A-Za-z_ .:/()#,@\[\]+=&;{}!$*-]*$`) — dấu tiếng Việt và `'`/`—` trong
   4 dòng description bị từ chối. Sửa toàn bộ description gửi lên AWS sang ASCII thuần, giữ tiếng Việt ở
   comment Terraform (không gửi lên AWS).
8. **Lỗi thật phát hiện qua `terraform apply` + đọc log boot thật** (`ec2:GetConsoleOutput`, thêm quyền tối
   thiểu khi cần, không xin full quyền): `scripts/vps/bootstrap.sh` dùng `systemctl reload ssh` để áp cấu
   hình cứng hoá SSH — nhưng trên máy CHƯA từng chạy sshd lần nào, `reload` chỉ tác dụng lên service ĐANG
   CHẠY nên âm thầm không làm gì, log ghi rõ `Missing privilege separation directory: /run/sshd`, để lại
   sshd không bao giờ khởi động (mất SSH hoàn toàn, "connection refused" suốt ~20 phút chẩn đoán). Sửa:
   `mkdir -p /run/sshd` + đổi `reload` → `restart`. Xác nhận lại qua log boot của máy tạo lại: `Started
   ssh.service - OpenBSD Secure Shell server` — không còn lỗi.

## 4. Xác nhận H-2

```
$ aws sts get-caller-identity
{
    "UserId": "AIDAVFOSJX4A4BOZBGQKP",
    "Account": "355312713473",
    "Arn": "arn:aws:iam::355312713473:user/terraform-deployer"
}
```

IAM user riêng (không phải root), policy tự viết `VSFTerraformDeployerSingapore` — chặt hơn đề xuất ban đầu
của tôi (`AmazonEC2FullAccess`), chỉ đúng các action EC2/SG/EIP cần, giới hạn `ap-southeast-1`, không đụng
IAM/Billing/S3.

## 5. `terraform plan` / `apply`

```
Plan: 5 to add, 0 to change, 0 to destroy.
...
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.
elastic_ip = "3.1.239.21"
```

5 resource: `aws_key_pair.vsf`, `aws_security_group.vsf`, `aws_instance.vsf` (`m7i-flex.large`, EBS 30GB gp3
mã hoá, IMDSv2 bắt buộc), `aws_eip.vsf` + `aws_eip_association.vsf`. Bạn xác nhận rõ ràng trước khi chạy —
đúng quy ước đã thống nhất cho hành động tạo tài nguyên thật.

Sau đó phát hiện lỗi #8 (mục 3) qua log boot thật → phải `terraform apply -replace="aws_instance.vsf"` tạo
lại instance (chỉ EC2, SG/EIP/KeyPair giữ nguyên, Elastic IP không đổi) để chạy lại `bootstrap.sh` bản đã sửa.
`instance_id` cuối cùng: `i-001256d35e85809ae`.

## 6. Xác nhận máy chủ (SSH thật, không mock)

```
$ ssh -i vsf-aws ubuntu@3.1.239.21 "docker --version && swapon --show && ls /opt/vsf-aws"
Docker version 29.8.1, build 4a63305
NAME      TYPE SIZE USED PRIO
/swapfile file   2G   0B   -1
backups  deploy  env  scripts  state
```

Docker cài đúng, swap 2GB hoạt động, cấu trúc thư mục `/opt/vsf-aws` khớp thiết kế (`deploy.sh` sẽ dùng ở H-6).

## 7. Chẩn đoán SSH — tóm tắt để không lặp lại nhầm lẫn

Ba lớp vấn đề chồng lên nhau khiến việc chẩn đoán mất nhiều thời gian nhất phiên này:

1. **Bug thật** (mục 3.8): `reload` thay vì `restart` trong `bootstrap.sh` — đã sửa, xác nhận qua log.
2. **Nhiễu chẩn đoán**: thử SSH từ mạng nhà → thất bại; nghi ngờ mạng nhà chặn cổng 22 (thử SSH tới GitHub
   từ mạng nhà cũng thất bại, có vẻ xác nhận nghi ngờ) — **nhưng đây là trùng hợp**, không phải nguyên nhân
   chính lúc đó (máy AWS thật sự chưa chạy được sshd do bug #8, chưa kịp sửa).
3. **Sau khi sửa bug #8 và tạo lại máy**: đổi sang mạng 4G để loại trừ nghi ngờ mạng nhà → SSH tới GitHub
   thành công (xác nhận cổng 22 không bị chặn chung) → nhưng SSH tới máy AWS **vẫn** thất bại → vì đổi mạng
   làm **IP công khai đổi theo**, trong khi Security Group chỉ cho phép đúng 1 IP cũ. Cập nhật
   `terraform.tfvars` (`my_ip`) + `terraform apply` (chỉ sửa luật SG, không đụng máy) → SSH thành công ngay.

**Bài học ghi lại**: khi đổi mạng để chẩn đoán, luôn nhớ IP công khai đổi theo — kiểm tra `curl
https://checkip.amazonaws.com` trước khi nghi ngờ tầng khác.

## 8. H-5: DuckDNS

Bạn tự tạo `vsf-assistant.duckdns.org` trên duckdns.org (tôi không tự làm được — cần tài khoản/trình duyệt
của bạn). Xác nhận:

```
$ nslookup vsf-assistant.duckdns.org
Address: 3.1.239.21
```

## 9. H-6: tạo `.env` thật, deploy lần đầu, HTTPS, smoke test

**Khác với kế hoạch gốc ở một điểm**: `scripts/aws/deploy.sh` (dùng cho CI) yêu cầu image ghim theo digest
từ `ghcr.io/...` — nhưng `release-aws.yml` chưa từng chạy (còn tắt bằng `DEPLOY_AWS_ENABLED`), nên GHCR
chưa có image nào. Cho đúng lần deploy đầu tiên này, tôi build image **trực tiếp trên EC2 từ source** (rsync
`backend/` qua SSH, `docker build`) thay vì qua GHCR — chỉ áp dụng cho lần bootstrap thủ công này; mọi lần
deploy sau (qua GitHub Actions) sẽ dùng đúng luồng GHCR + digest như thiết kế.

**Bí mật production**: không dùng lại `SESSION_SECRET`/mật khẩu Postgres của dev — sinh mới bằng `openssl
rand` (session 32 byte, Postgres 24 byte), không in ra bất kỳ output/log nào trong suốt quá trình, xoá file
tạm cục bộ ngay sau khi `scp` lên server, đặt quyền `600` trên server. Các khoá LLM/Cloudinary/Embedding lấy
từ `.env` gốc của dự án (đã dùng cho dev từ trước), copy sang bằng script Python đọc-và-ghi (không đi qua
terminal output). `LANGFUSE_ENABLED=false` — gói `langfuse` chưa có trong `requirements.txt` (xem plan
2-e-prompt-guardrail-rerank), bật `true` bây giờ sẽ không lỗi nhưng không theo dõi được gì.

Kết quả:

```
$ docker ps
NAMES           STATUS                        IMAGE
vsf-caddy-1     Up                            caddy:2.10-alpine
vsf-backend-1   Up (healthy)                  vsf-backend:local
vsf-db-1        Up (healthy)                  paradedb/paradedb:v0.25.4-pg16

$ curl https://vsf-assistant.duckdns.org/api/v1/health
{"status":"ok"}   # TLS hợp lệ (Let's Encrypt qua Caddy), HSTS/X-Frame-Options/... đầy đủ

$ scripts/aws/smoke-test.sh https://vsf-assistant.duckdns.org (SMOKE_AUTH_ME=1)
OK   GET /api/v1/health = 200
OK   health trả status ok
OK   GET /api/v1/ready từ ngoài = 404
OK   GET /api/v1/auth/me (chưa đăng nhập) = 401
```

Thử đăng nhập thật (`newhire1@vsf-demo.example`) trả `401 INVALID_CREDENTIALS` — **đúng, không phải lỗi**:
DB production hoàn toàn mới, chưa seed tài khoản nào, và production tự chối chạy `seed_users` (dev-only, xem
`assert_no_dev_accounts`). Sẽ cần tài khoản thật/quy trình mời riêng khi launch thật, không phải việc của
H-6.

## 10. Vercel: nguyên nhân 404 và cách sửa (24/09)

Triệu chứng: `vsf-onboarding-assistant.vercel.app` trả `404 NOT_FOUND` dù deployment "Ready". Có 3 nguyên nhân chồng nhau:

1. **Framework Preset = "Other"** → Vercel coi là site tĩnh (build 0ms). Sửa: `frontend/vercel.json` với `"framework": "nextjs"`.
2. **`output: "standalone"`** (dùng cho Docker) làm bước `onBuildComplete` của Vercel lỗi thiếu `next-server.js.nft.json`. Sửa: `frontend/next.config.ts` chỉ bật standalone khi không có biến `VERCEL`. Docker không đổi.
3. **Dự án ở trạng thái rollback** → domain chính bị ghim vào bản cũ. Sửa: `vercel promote` bản mới.

Khi dùng Vercel CLI, phải chạy từ **thư mục gốc repo** (Root Directory = `frontend` nên chạy trong `frontend/` sẽ nhân đôi đường dẫn). Thư mục `.vercel` đã nằm trong `.gitignore`.

Kiểm chứng: `/` → 307 `/vi`, `/vi/login` 200, `/api/v1/health` qua Vercel → `{"status":"ok"}` (rewrite tới AWS, cookie first-party).

## 11. Dữ liệu và tài khoản production

Trước đó DB production **rỗng** (migration `0001`, mọi bảng 0 dòng), khác hẳn DB local (Docker, pgAdmin "Onboarding Local").

- **Nạp dữ liệu:** `pg_dump --data-only` các bảng `teams`, `document_categories`, `documents`, `document_versions`, `document_sections`, `document_chunks` từ local, nạp vào DB AWS (đặt `session_replication_role = replica` vì các bảng tham chiếu `users`). Không copy `users`.
  Kết quả khớp local: 4 đội, 12 danh mục, 1 tài liệu, 1 phiên bản, 32 section, 34 chunk (đủ 34 embedding). File gốc vẫn ở Cloudinary (dùng chung).
- **Không dùng tài khoản dev:** backend production từ chối khởi động nếu còn email `@vsf-demo.example` (mật khẩu dev nằm trong repo). `seed_users` cũng từ chối chạy ở production.
- **CLI mới `python -m src.cli.create_user`** (`--email --name --role --team [--generate-password]`): hỏi mật khẩu bằng `getpass` hoặc tự sinh mật khẩu mạnh, từ chối email miền dev, mật khẩu <12 ký tự, email trùng.
- **Gán lại chủ sở hữu:** `documents.owner_id`, `document_versions.uploaded_by/reviewed_by` đổi sang admin (id 1); kiểm tra 0 dòng mồ côi.

| Vai trò | Email | Bộ phận |
|---|---|---|
| ADMIN | `quan.nguyen@vsf.example` | — |
| HR | `huong.le@vsf.example` | HR Onboarding |
| USER | `anh.pham@vsf.example` | IT Helpdesk |
| USER | `binh.vo@vsf.example` | VinSOC |
| USER | `thu.tran@vsf.example` | Facilities |

Mật khẩu **không lưu trong repo/báo cáo**: sinh ngẫu nhiên khi tạo và giao riêng cho người dùng. Đổi mật khẩu khi cần bằng cách tạo lại tài khoản hoặc bổ sung chức năng đổi mật khẩu.

## 12. Kiểm chứng end-to-end (24/09)

- Đăng nhập `thu.tran@vsf.example` qua Vercel → 200, `role: USER`, `department: Facilities`.
- `POST /api/v1/chat/ask` "Chính sách nghỉ phép của công ty như thế nào?" → 200, trả lời "12 ngày phép năm" kèm trích dẫn nguyên văn, `document_url` Cloudinary và `version_id`.
- Độ trễ: lần đầu **86s** (Modal khởi động GPU L4 lạnh), lần sau **~4s**.
- Lưu ý: Modal còn ~$28,7 credit; app `ralion-bge-m3-embedder` cần khởi động lại sau thời gian không dùng. Có thể bật `min_containers=1` nếu cần bỏ độ trễ lạnh (tốn credit).

**Cách kiểm tra:** (1) Vercel → project → Deployments: bản Production "Ready"; (2) `curl https://vsf-assistant.duckdns.org/api/v1/health` → `{"status":"ok"}`; (3) EC2 Console → `vsf-aws` running, Security Group cổng 22 chỉ mở khi cần; (4) DB: SSH vào EC2 rồi `sudo docker exec -it $(sudo docker ps -qf name=db) psql -U vsf -d vsf` (chỉ mở rule SSH tạm cho IP của bạn rồi thu hồi); (5) Billing → Credits xem credit AWS còn lại.

## 13. Việc còn lại

- Chức năng đổi mật khẩu / quản lý người dùng qua UI (hiện chỉ có CLI).
- `langfuse` chưa có trong `requirements.txt` (tracing đang tắt).
- Theo dõi credit AWS (Free Plan hết 22/03/2027 hoặc khi hết credit) và Modal.
- Rule SSH trên Security Group: luôn thu hồi sau khi dùng (đã thu hồi 24/09).
