# Hướng dẫn kiểm tra hạ tầng trên AWS

> Dành cho người vận hành dự án VSF Onboarding Assistant. Không cần biết Terraform hay Docker sâu: chỉ cần
> trình duyệt và tài khoản AWS. Bối cảnh triển khai: [bao-cao-trien-khai-aws-vercel.md](bao-cao-trien-khai-aws-vercel.md).

## 1. Dự án dùng những gì và lưu ở đâu

| Thành phần | Nằm ở | Công dụng |
|---|---|---|
| **EC2 `vsf-aws`** (`m7i-flex.large`, Singapore) | AWS | Máy chủ chạy backend, DB và Caddy |
| **Ổ EBS 30GB** (gắn vào EC2) | AWS | Nơi lưu dữ liệu Postgres, mã hóa sẵn |
| **Elastic IP `3.1.239.21`** | AWS | IP cố định để tên miền DuckDNS trỏ vào |
| **Security Group `vsf-aws`** | AWS | Tường lửa: 80/443 mở cho mọi người, 22 (SSH) chỉ mở cho IP được phép |
| **Key pair `vsf-aws`** | AWS | Khóa SSH vào máy chủ |
| **IAM role `vsf-github-deploy` + OIDC** | AWS | Cho GitHub Actions deploy, không cần lưu key AWS dài hạn |
| Container `vsf-backend-1` | trong EC2 | API FastAPI (cổng 8000, chỉ trong mạng Docker) |
| Container `vsf-db-1` | trong EC2 | Postgres/ParadeDB (cổng 5432, không lộ ra internet) |
| Container `vsf-caddy-1` | trong EC2 | HTTPS: cấp chứng chỉ tự động, chuyển yêu cầu tới backend |
| File khóa `/opt/vsf-aws/env/backend.env` | trong EC2 | Mọi khóa bí mật (chỉ nằm trên server, không có trong repo) |
| Vercel | ngoài AWS | Giao diện web, chuyển `/api/*` sang AWS |
| Cloudinary | ngoài AWS | File tài liệu gốc |
| Modal | ngoài AWS | Tạo embedding (bge-m3) |
| DuckDNS | ngoài AWS | Tên miền `vsf-assistant.duckdns.org` |

**Lưu ý:** AWS Console **không** có màn hình xem bảng DB, container hay biến env, vì DB và app chạy trong Docker
trên EC2 (không dùng RDS). Trên Console chỉ xem được trạng thái máy, ổ đĩa, IP, tường lửa và chi phí. Phần bên
trong xem qua terminal trên web (mục 4).

## 2. Chuẩn bị: đổi sang vùng Singapore

Console thường mở ở vùng khác (ví dụ Sydney). Tài nguyên dự án ở **Asia Pacific (Singapore) `ap-southeast-1`**.
Bấm tên vùng ở góc trên bên phải và chọn Singapore, nếu không sẽ không thấy gì.

## 3. Xem trạng thái bằng chuột (không cần terminal)

| Muốn xem | Đường dẫn | Bình thường là |
|---|---|---|
| Máy chủ | EC2 → Instances → `vsf-aws` | *Running*, *Status check* passed |
| IP cố định | EC2 → Elastic IPs | `3.1.239.21` gắn với `vsf-aws` |
| Ổ đĩa | EC2 → Volumes | 1 ổ 30GB, *In-use* |
| Tường lửa | EC2 → Security Groups → `vsf-aws` → Inbound rules | 80, 443 (TCP+UDP) mở; 22 chỉ IP được phép |
| CPU/mạng | EC2 → Instances → `vsf-aws` → tab Monitoring | CPU thấp (dưới 10% khi rảnh) |
| Credit còn lại | Billing → Credits | Xem số USD và ngày hết hạn |
| Chi phí theo dịch vụ | Billing → Cost Explorer (nhóm theo Service) | Vài USD/tháng |

Các khoản chi phí điển hình: **EC2 - Compute** (máy chủ, khoản chính), **Virtual Private Cloud** (phí IPv4 công
khai), **EC2 - Other** (ổ EBS).

## 4. Mở terminal trên web để xem bên trong máy chủ

Cách này dùng EC2 Instance Connect, không cần cài SSH trên máy bạn.

1. **Mở cổng 22 tạm thời.** EC2 → Security Groups → `vsf-aws` → *Edit inbound rules* → *Add rule*:
   *Type* = SSH, *Source* = Custom `3.0.5.32/29` (dải IP của nút Connect trên web ở Singapore) → *Save rules*.
   Đừng sửa hay xóa 4 rule có sẵn.
2. **Kết nối.** EC2 → Instances → chọn `vsf-aws` → **Connect** → tab **EC2 Instance Connect**, *Username* =
   `ubuntu` → **Connect**. Một terminal đen mở ra trong trình duyệt.
3. **Chạy các lệnh ở mục 5.**
4. **Đóng cổng 22.** Quay lại Security Group, xóa dòng SSH `3.0.5.32/29` → *Save rules*. **Bắt buộc**, đừng để
   quên.

Nếu báo *Failed to connect*: kiểm tra rule ở bước 1 đã lưu chưa; hoặc đổi *Source* thành **My IP** rồi thử lại.

## 5. Các lệnh kiểm tra (dán từng dòng, Enter)

| Muốn xem | Lệnh | Bình thường là |
|---|---|---|
| Container chạy chưa | `sudo docker ps` | 3 dòng `vsf-backend-1`, `vsf-caddy-1`, `vsf-db-1`; backend và db ghi *(healthy)* |
| Tên các biến env (giá trị che) | `sudo sed -E 's/=.*/=<da dat>/' /opt/vsf-aws/env/backend.env` | 16 dòng: `APP_ENV`, `DATABASE_URL`, `SESSION_SECRET`, `EMBEDDING_*`, `CLOUDINARY_*`, `LLM_*`... |
| Số dòng trong DB | `sudo docker exec vsf-db-1 psql -U vsf -d vsf -Atc "select count(*) from users; select count(*) from documents; select count(*) from document_chunks;"` | Ba số (hiện tại `5`, `1`, `34`) |
| Danh sách tài khoản | `sudo docker exec vsf-db-1 psql -U vsf -d vsf -c "select id,email,role from users;"` | 5 tài khoản `@vsf.example` |
| Danh sách bảng | `sudo docker exec vsf-db-1 psql -U vsf -d vsf -c "\dt"` | 12 bảng |
| Log của API | `sudo docker logs --tail 50 vsf-backend-1` | Không có lỗi đỏ lặp lại |
| Ổ đĩa và RAM | `df -h / ; free -h` | Ổ dưới 80%, RAM dư nhiều |

**Không** dán hoặc chụp nội dung file `backend.env` (chứa khóa thật). Chỉ xem **tên** biến như lệnh trên.

## 6. Kiểm tra API từ trình duyệt (không cần đăng nhập AWS)

| Link | Kỳ vọng |
|---|---|
| `https://vsf-assistant.duckdns.org/api/v1/health` | `{"status":"ok"}` (API AWS sống) |
| `https://vsf-onboarding-assistant.vercel.app/api/v1/health` | `{"status":"ok"}` (Vercel nối đúng tới AWS) |
| `https://vsf-onboarding-assistant.vercel.app/vi/login` | Trang đăng nhập |

## 7. Xử lý khi có sự cố

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Trang web 404 | Domain bị ghim vào bản cũ, hoặc Framework Preset sai | Vercel → Deployments → promote bản mới nhất; kiểm tra `frontend/vercel.json` |
| Đăng nhập báo sai | DB production chưa có tài khoản đó | Tạo bằng `python -m src.cli.create_user` (mục 8) |
| Chat rất chậm lần đầu (~90s) | Modal khởi động GPU lạnh | Hỏi thử một câu để làm nóng; lần sau ~4s |
| Chat báo lỗi ngay | Modal hết credit hoặc key sai | Kiểm tra Modal → Credits và biến `EMBEDDING_*` |
| `docker ps` thiếu container | Container sập | `sudo docker logs vsf-<tên>-1`, rồi `sudo docker compose ... up -d` (xem `scripts/aws/deploy.sh`) |
| Không SSH được | IP máy bạn đổi hoặc mạng chặn cổng 22 | Đổi mạng, hoặc dùng EC2 Instance Connect (mục 4) |
| Backend không khởi động, log nhắc "tài khoản dev" | DB còn email `@vsf-demo.example` | Xóa các tài khoản đó khỏi bảng `users` (production cấm tài khoản dev) |

## 8. Tạo tài khoản mới trên production

Chạy trong terminal của mục 4 (mật khẩu ngẫu nhiên hiện ra một lần, hãy lưu lại):

```
sudo docker exec -i vsf-backend-1 python -m src.cli.create_user --generate-password \
  --email ten.ho@vsf.example --name "Họ Tên" --role USER --team IT
```

- `--role`: `USER`, `HR` hoặc `ADMIN`.
- `--team`: `HR_ONBOARDING`, `IT`, `VINSOC` hoặc `FACILITIES` (bỏ qua nếu không thuộc đội).
- Bỏ `--generate-password` để tự gõ mật khẩu (tối thiểu 12 ký tự).
- Không dùng email đuôi `@vsf-demo.example`.

## 9. Nguyên tắc an toàn

- Chỉ mở cổng 22 khi cần và xóa ngay sau khi xong.
- Không đưa nội dung `backend.env`, khóa `~/.ssh/vsf-aws`, hoặc mật khẩu vào chat, ảnh chụp màn hình hay repo.
- Bật cảnh báo chi phí ở Billing → Budgets. Gói Free Plan hết ngày 22/03/2027 hoặc khi hết credit.
- Sau khi đổi hạ tầng bằng Terraform, dùng `terraform plan` xem trước, không sửa tay tài nguyên đã do Terraform quản lý.
