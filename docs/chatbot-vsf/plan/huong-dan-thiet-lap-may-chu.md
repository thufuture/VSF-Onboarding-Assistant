# Hướng dẫn thiết lập máy chủ demo (cho người chưa từng deploy)

> Thuộc [master-plan.md](master-plan.md), **Phase 0** (bước 8) và nền cho Phase 1. Thời gian ước tính: 1–2 giờ nếu không vướng xác minh tài khoản (chưa đo).
> Đã chốt (cập nhật 2026-09-21): máy chính **Oracle Cloud Always Free (ARM A1.Flex, thử nghiệm)**, **dự phòng Hetzner Cloud CX23**; tên miền miễn phí **DuckDNS**; CI **GitHub Actions**. **Quy tắc thử: tạo máy Oracle tối đa khoảng 1 giờ; không được thì làm mục 3B (Hetzner).** Lý do, rủi ro thu hồi máy và bảng "đủ hay không" ở [phu-luc-may-chu-va-chi-phi.md](phu-luc-may-chu-va-chi-phi.md).
> **Cập nhật 2026-09-21: Oracle không tạo được, dùng Hetzner CX23 (mục 3B).** Thứ tự làm: (1) CI trên GitHub, (2) đẩy image lên GHCR bằng `publish.yml` (chỉ `amd64`), (3) thuê VPS, (4) DuckDNS, (5) deploy tay lần đầu, (6) `release.yml` tự động. Sau (2) chưa tốn phí; VPS mới tốn tiền. Nếu quay lại Oracle (ARM) thì thêm `linux/arm64` vào `publish.yml`.
> Giá, gói và giao diện các trang bên dưới thay đổi theo thời gian: nếu màn hình khác hướng dẫn, làm theo trang chính thức.

## 0. Việc nào bạn phải tự làm, việc nào tôi làm

| Bạn tự làm (cần tài khoản, thanh toán, khóa riêng) | Tôi làm sau khi bạn xong |
|---|---|
| Đăng ký Oracle (hoặc Hetzner), tạo server, thêm khóa SSH | Viết `bootstrap.sh`, Dockerfile, `compose.vps.yml`, Caddyfile, `deploy.sh`, `release.yml` |
| Đăng ký tên miền DuckDNS | Hướng dẫn cấu hình secrets trên GitHub |
| Tạo secrets/variables trong GitHub Environment | Gỡ lỗi khi bạn dán **thông báo lỗi** (không dán khóa/mật khẩu) |

**Không bao giờ** dán khóa riêng (private key), mật khẩu, token API vào chat hay commit vào repo.

## 1. Cài công cụ trên máy Windows của bạn

| Công cụ | Dùng để | Link |
|---|---|---|
| Git for Windows | Quản lý mã, đẩy lên GitHub | https://git-scm.com/download/win |
| Docker Desktop | Chạy `docker compose` cục bộ | https://docs.docker.com/desktop/setup/install/windows-install/ |
| Node.js (LTS) | Frontend Next.js | https://nodejs.org/en/download |
| Python 3.12 | Backend FastAPI, công cụ dữ liệu seed | https://www.python.org/downloads/ |
| GitHub CLI (`gh`, tùy chọn) | Tạo secrets/PR bằng dòng lệnh | https://cli.github.com/ |
| OpenSSH client | Kết nối máy chủ | Có sẵn trên Windows 10/11 ([hướng dẫn bật nếu thiếu](https://learn.microsoft.com/windows-server/administration/openssh/openssh_install_firstuse)) |

Kiểm tra trong PowerShell: `git --version`, `docker --version`, `node --version`, `python --version`, `ssh -V`.

## 2. Tạo khóa SSH (2 khóa riêng biệt)

Khóa SSH thay mật khẩu khi đăng nhập máy chủ. Có **hai khóa**: một cho bạn đăng nhập tay, một chỉ cho CI deploy (để lộ khóa CI không lộ khóa cá nhân).

```powershell
ssh-keygen -t ed25519 -C "vsf-demo-admin"  -f $HOME\.ssh\vsf_admin
ssh-keygen -t ed25519 -C "vsf-demo-deploy" -f $HOME\.ssh\vsf_deploy -N '""'
```

- Khóa `vsf_admin`: nên đặt passphrase khi được hỏi.
- Khóa `vsf_deploy`: không passphrase (CI cần dùng tự động).
- File `.pub` là **khóa công khai** (đưa lên máy chủ được). File không có đuôi là **khóa riêng** (giữ kín).
- Xem khóa công khai: `Get-Content $HOME\.ssh\vsf_admin.pub`.

## 3A. Máy chính: Oracle Cloud Always Free (ARM)

Tài liệu chính thức: [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). Giao diện Oracle thay đổi thường xuyên; nếu màn hình khác hướng dẫn, làm theo tài liệu của Oracle. **Bắt đầu đếm 1 giờ khi bấm đăng ký.**

1. Đăng ký tại https://www.oracle.com/cloud/free/ . Cần email và thường cần thẻ để xác minh (điều kiện chính xác **chưa xác minh**, trang FAQ chặn truy cập lúc tra cứu). **Chọn home region cẩn thận (đề xuất Singapore): theo hiểu biết chung, không đổi được sau này.** Giữ tài khoản ở mức **Always Free**, không nâng lên trả phí nếu không cần.
2. Vào **Compute → Instances → Create instance** với:
   - Image: **Canonical Ubuntu 24.04** (bản aarch64/ARM).
   - Shape: **Ampere → VM.Standard.A1.Flex**, **1–2 OCPU, 4–6 GB RAM**. Không cần hết 2 OCPU / 12 GB: cấp vừa đủ giúp mức dùng bộ nhớ không quá thấp (xem rủi ro thu hồi máy nhàn rỗi ở [phụ lục mục 2](phu-luc-may-chu-va-chi-phi.md)). Có thể chỉnh lại sau (cần khởi động lại máy).
   - Boot volume: **khoảng 50 GB** (tối thiểu 47 GB; tổng 200 GB cho tài khoản).
   - Mạng: dùng VCN mặc định, bật **public IPv4**; sau khi tạo nên gán **Reserved public IP** để IP không đổi khi tắt/bật.
   - SSH key: dán nội dung `vsf_admin.pub`.
3. Nếu gặp lỗi **"Out of host capacity"**: Oracle nêu đây là tình trạng tạm thời hết máy Always Free tại vùng của bạn. Thử availability domain khác, giảm cấu hình, rồi thử lại sau vài phút. **Nếu quá khoảng 1 giờ vẫn không tạo được, dừng và làm mục 3B.**
4. Mở cổng ở **VCN Security List** (Networking → Virtual cloud networks → Subnet → Security Lists → Add ingress rules): TCP 22, TCP 80, TCP 443, UDP 443, nguồn `0.0.0.0/0`.
5. Ghi lại **địa chỉ IPv4 công khai**. Người dùng mặc định của Ubuntu trên Oracle là **`ubuntu`** (không phải `root`):

```powershell
ssh -i $HOME\.ssh\vsf_admin ubuntu@<IP-server>
```

**Khác biệt so với Hetzner ở mục 5:**
- Đăng nhập bằng `ubuntu`, dùng `sudo` (thay cho `root`); khóa cho `deploy` lấy từ `/home/ubuntu/.ssh/authorized_keys`.
- Ảnh Ubuntu trên Oracle thường có sẵn quy tắc `iptables` chặn cổng trong máy, **ngoài** Security List. Nếu Security List đã mở mà vẫn không vào được cổng 80/443, mở cả trong máy (theo kinh nghiệm chung, kiểm bằng cách thử): `sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT` (tương tự 443, cổng UDP 443), rồi lưu quy tắc (`sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save`). `bootstrap.sh` sẽ làm bước này. Dùng `ufw` **hoặc** `iptables` cho một nguồn quy tắc, tránh trộn hai bên.
- Máy là **ARM (aarch64)**: ảnh Docker phải có bản `linux/arm64` (`paradedb`, `caddy`, `traefik/whoami` đều nên có; kiểm bằng `docker manifest inspect <image>` nếu nghi ngờ). Ảnh của dự án sẽ được build đa kiến trúc ở CI.
- Không có "Firewall Hetzner" riêng: lớp ngoài là Security List.
- Nên tạo **bản sao lưu ổ khởi động** (Boot volume backup) sau khi cấu hình xong; Always Free có 5 bản sao lưu volume.

**Trước khi coi Oracle là dùng được:** chạy ổn định cả ngày và không mất SSH. **Chưa đặt lịch demo lên Oracle** khi chưa chạy ổn định vài ngày liên tục.

## 3B. Máy dự phòng: Hetzner (dùng khi Oracle không tạo được hoặc không ổn định)

1. Đăng ký tại https://www.hetzner.com/cloud/ rồi vào https://console.hetzner.cloud/. Có thể bị yêu cầu xác minh thẻ hoặc danh tính; nếu bị từ chối, xem đường lui ở [master-plan.md mục 5](master-plan.md) và [phụ lục](phu-luc-may-chu-va-chi-phi.md) (lưu ý: Quick Tunnel của Cloudflare không hỗ trợ SSE nên chat phải dùng chế độ không stream).
2. Tạo **Project** (ví dụ `vsf-demo`).
3. Vào **Security → SSH keys → Add SSH key**, dán nội dung `vsf_admin.pub`.
4. **Add Server** với các lựa chọn:
   - Location: Falkenstein/Nuremberg (Đức) hoặc Helsinki (Phần Lan); gói CX chỉ có ở châu Âu ([nguồn](https://www.hetzner.com/pressroom/new-cx-plans/)).
   - Image: **Ubuntu 24.04**.
   - Type: **CX23** (2 vCPU, 4 GB RAM, 40 GB NVMe). Trang tạo server sẽ hiện **giá thật**; theo tra cứu ngày 2026-09-20 khoảng **€5,49/tháng**, tính theo giờ và có trần theo tháng. Có thể có phụ phí địa chỉ IPv4 nhỏ: xem dòng tổng ở trang tạo server.
   - SSH key: chọn khóa `vsf_admin` đã thêm.
   - **Firewall:** tạo firewall cho phép vào các cổng 22 (SSH), 80, 443 (TCP) và 443 (UDP), chặn phần còn lại.
   - Backups (trả phí thêm): không bật; sao lưu bằng `pg_dump` ở Phase 11.
5. Ghi lại **địa chỉ IPv4** của server.

**Ngày kết thúc:** để ngừng tính tiền phải **xóa** server, không chỉ tắt (Hetzner tính tiền cả khi tắt, [FAQ thanh toán của Hetzner](https://docs.hetzner.com/cloud/billing/faq/)). Đặt lời nhắc ngày xóa.

## 4. Tên miền miễn phí DuckDNS

1. Vào https://www.duckdns.org/ và đăng nhập bằng tài khoản GitHub hoặc Google.
2. Ở ô **domains**, nhập tên (ví dụ `vsf-demo`) rồi **add domain**. Tên đầy đủ sẽ là `vsf-demo.duckdns.org`.
3. Điền **địa chỉ IPv4 của server** ở ô current ip rồi **update ip**.
4. Kiểm tra (chờ vài phút nếu chưa ra):

```powershell
nslookup vsf-demo.duckdns.org
```

Kết quả phải là IP của server. Nếu xóa và tạo lại server (hoặc chuyển từ Oracle sang Hetzner) thì IP đổi, phải cập nhật lại ở bước này.

Không dùng `<ip>.sslip.io` để lấy HTTPS: hạn mức chứng chỉ chung của nó [đã từng cạn](https://github.com/cunnie/sslip.io/issues/108).

## 5. Đăng nhập lần đầu và chuẩn bị máy chủ

```powershell
ssh -i $HOME\.ssh\vsf_admin root@<IP-server>      # Hetzner
ssh -i $HOME\.ssh\vsf_admin ubuntu@<IP-server>    # Oracle (sau đó gõ: sudo -i để có quyền root)
```

Gõ `yes` khi hỏi về host key lần đầu. Trên server (Ubuntu, quyền root), chạy lần lượt. **Trên Oracle:** thay `/root/.ssh/authorized_keys` bằng `/home/ubuntu/.ssh/authorized_keys` ở bước tạo `deploy`, và xem lưu ý `iptables` ở mục 3A (thay cho `ufw` nếu bạn chọn `iptables`); lệnh cài Docker giống nhau vì `$(dpkg --print-architecture)` tự chọn `arm64`.

```bash
# cập nhật hệ thống
apt-get update && apt-get -y upgrade

# tường lửa trong máy (cùng với firewall của Hetzner)
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 443/udp
ufw --force enable

# 2 GB swap phòng khi thiếu RAM
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# người dùng deploy riêng (không dùng root để chạy ứng dụng)
adduser --disabled-password --gecos "" deploy
mkdir -p /home/deploy/.ssh
cat /root/.ssh/authorized_keys > /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
```

### Cài Docker

Làm theo trang chính thức (**ưu tiên trang này nếu khác bên dưới**): https://docs.docker.com/engine/install/ubuntu/ , phương pháp "Install using the apt repository". Tóm tắt:

```bash
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker deploy
docker run --rm hello-world
```

Người dùng thuộc nhóm `docker` có quyền tương đương root trên máy: chỉ dùng cho tài khoản `deploy`, không chia sẻ khóa (rủi ro này đã ghi ở [deployment-ci mục 12](../vsf-onboarding-assistant-deployment-ci.md)).

Từ máy bạn, kiểm tra đăng nhập bằng người dùng `deploy` rồi mới thoát khỏi root:

```powershell
ssh -i $HOME\.ssh\vsf_admin deploy@<IP-server>
```

## 6. Thử nghiệm "hello" có HTTPS (cổng hoàn thành của bước này)

Trên server, với người dùng `deploy`:

```bash
mkdir -p ~/hello && cd ~/hello
cat > Caddyfile <<'EOF'
vsf-demo.duckdns.org {
    reverse_proxy hello:80
}
EOF
cat > compose.yml <<'EOF'
services:
  caddy:
    image: caddy:2-alpine
    ports: ["80:80", "443:443", "443:443/udp"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on: [hello]
  hello:
    image: traefik/whoami
volumes:
  caddy_data:
  caddy_config:
EOF
docker compose up -d
docker compose logs -f caddy
```

(Đổi `vsf-demo` thành tên DuckDNS của bạn.) Caddy tự xin chứng chỉ Let's Encrypt ([cách hoạt động](https://caddyserver.com/docs/automatic-https)); cần cổng 80/443 mở và DNS đã trỏ đúng IP.

**Xong khi:** từ máy khác (hoặc điện thoại dùng 4G), mở `https://vsf-demo.duckdns.org` thấy trang `whoami` và có ổ khóa HTTPS. Sau đó dọn: `docker compose down`.

Nếu không ra HTTPS: kiểm `nslookup`, kiểm firewall (Hetzner và `ufw`), đọc `docker compose logs caddy`; chụp/dán **thông báo lỗi** cho tôi (không dán khóa).

## 7. Phía GitHub (chuẩn bị cho CI/CD ở Phase 1 và 11)

1. Trên máy chủ, thêm khóa **deploy** (khóa công khai `vsf_deploy.pub`) vào `/home/deploy/.ssh/authorized_keys` (thêm một dòng mới).
2. Lấy host key của server để ghim: trên máy bạn chạy `ssh-keyscan -t ed25519 <IP-server>` và giữ kết quả.
3. Trên repo GitHub: **Settings → Environments → New environment** tên `staging`, giới hạn chạy cho nhánh `main`.
4. Trong Environment `staging`:
   - Secrets: `VPS_HOST` (IP hoặc tên miền), `VPS_USER` (`deploy`), `VPS_SSH_KEY` (nội dung **khóa riêng** `vsf_deploy`), `VPS_SSH_HOST_KEY` (kết quả `ssh-keyscan`).
   - Variables: `VPS_PORT` (`22`), `PUBLIC_URL` (`https://vsf-demo.duckdns.org`).
5. Bí mật chạy của ứng dụng (khóa LLM, khóa embedding, `SESSION_SECRET`, mật khẩu DB) **không** đưa vào GitHub: đặt ở `/opt/vsf/env/*.env` trên máy chủ theo [deployment-ci mục 7](../vsf-onboarding-assistant-deployment-ci.md). Tôi sẽ viết script cấu hình một lần ở Phase 1.

Tài liệu tham khảo: https://docs.github.com/actions

## 8. CI có đủ không

- CI chạy trên **runner do GitHub cấp**, không chạy trên VPS của bạn. Gói Free cho repo private có [2.000 phút Actions mỗi tháng](https://docs.github.com/en/actions/concepts/billing-and-usage) (theo GitHub Docs, tra cứu ngày 2026-09-20). Nếu mỗi lần chạy ≈ 8 phút (giả định, cần đo) thì cỡ vài trăm lần chạy mỗi tháng, đủ cho 4 tuần nếu không chạy đánh giá LLM tốn kém trong CI.
- Image lưu ở GHCR; điều kiện lưu trữ và băng thông xem ở [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages) (có thể đổi): giữ image nhỏ, xóa tag cũ định kỳ.
- Đánh giá golden bằng LLM **không** đưa vào mỗi PR (tốn tiền API): chạy thủ công.

## 9. Chi phí một tháng (ước tính)

| Khoản | Ước tính |
|---|---|
| Server Oracle Always Free (máy chính) | 0 (trong hạn mức) |
| Server Hetzner CX23 (chỉ khi phải dùng dự phòng) | ≈ €5,49 (trần theo tháng; tính theo giờ nên xóa sớm thì ít hơn); có thể có phụ phí IPv4 nhỏ; chưa gồm thuế |
| Tên miền DuckDNS | 0 |
| CI GitHub Actions + GHCR | 0 nếu trong hạn mức |
| **Gọi LLM và embedding (Modal/API)** | **Chưa biết**, phụ thuộc số câu hỏi và số lần chạy đánh giá; là khoản dễ vượt nhất, cần đặt cảnh báo chi phí ở nhà cung cấp |

## 10. Danh sách "đã sẵn sàng cho Phase 1"

- [ ] Công cụ ở mục 1 chạy được.
- [ ] Có hai khóa SSH (`vsf_admin`, `vsf_deploy`), khóa riêng không nằm trong repo.
- [ ] Server Ubuntu 24.04 chạy (Oracle A1.Flex, hoặc Hetzner CX23 nếu quá 1 giờ không tạo được Oracle); SSH bằng người dùng `deploy` được.
- [ ] Nếu là Oracle: Security List và `iptables` đã mở 80/443; đã gán Reserved public IP; đã ghi nhận máy chạy ổn định trước khi đặt lịch demo.
- [ ] `nslookup <tên>.duckdns.org` ra đúng IP.
- [ ] Trang `hello` truy cập được qua HTTPS từ máy khác.
- [ ] Environment `staging` có đủ secrets/variables ở mục 7.
- [ ] Nếu dùng Hetzner: đã ghi ngày xóa server. Với mọi máy: đã đặt cảnh báo chi phí ở nhà cung cấp API.
