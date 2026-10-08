# Terraform — hạ tầng AWS (EC2 + Elastic IP)

Tạo tự động: Key Pair, Security Group (22 chỉ từ IP bạn, 80/443 mở), EC2 `m7i-flex.large` chạy Ubuntu 24.04
(tự chạy `scripts/vps/bootstrap.sh` lúc khởi tạo qua cloud-init — cài Docker, ufw, swap 2GB, cứng hóa SSH),
Elastic IP gắn cố định với instance. Xem
[trien-khai-aws-vercel.md](../../docs/chatbot-vsf/plan/infrastructure/trien-khai-aws-vercel.md) cho bối cảnh
đầy đủ.

## Chuẩn bị (một lần)

1. Cài AWS CLI + Terraform (nếu máy chưa có):
   ```
   winget install Amazon.AWSCLI
   winget install Hashicorp.Terraform
   ```
2. Tạo IAM user + access key riêng (không dùng root), `aws configure` — xem hướng dẫn trong
   `trien-khai-aws-vercel.md` mục 5. **Khóa không đi qua chat.**
3. Sinh cặp khóa SSH riêng cho máy này:
   ```
   ssh-keygen -t ed25519 -f ~/.ssh/vsf-aws -C vsf-aws
   ```
4. Lấy IP công khai của bạn: `curl -s https://checkip.amazonaws.com`
5. Sao chép `terraform.tfvars.example` → `terraform.tfvars`, điền `my_ip` (dạng `1.2.3.4/32`) và
   `ssh_public_key_path`.

## Chạy

```
terraform init
terraform plan     # đọc kỹ output trước khi apply — không có gì bị tạo/xóa ở bước này
terraform apply    # gõ "yes" sau khi đã xem plan và đồng ý
```

Sau khi `apply` xong, lấy Elastic IP từ output:
```
terraform output elastic_ip
```

## Sau khi có Elastic IP

1. Trỏ DuckDNS `vsf-assistant.duckdns.org` sang Elastic IP đó (đăng nhập duckdns.org, tự làm — chỉ bạn đăng nhập được).
2. Chờ ~1-2 phút để `user_data` (bootstrap.sh) chạy xong, rồi SSH thử:
   ```
   ssh -i ~/.ssh/vsf-aws ubuntu@<elastic-ip>
   ```
3. Làm theo bước H-6 trở đi trong `trien-khai-aws-vercel.md` (tạo `.env`, deploy lần đầu bằng
   `scripts/aws/deploy.sh`).

## Dọn dẹp (tạm dừng dự án, tránh tốn credit)

```
terraform destroy
```
Xóa sạch EC2, Security Group, Key Pair, Elastic IP trong một lệnh. **Mất dữ liệu Postgres** (chưa có cơ chế
backup ra ngoài instance) — chạy `scripts/aws/deploy.sh` sẽ tự backup trước mỗi lần deploy sau lần đầu, nhưng
bản backup nằm trên chính instance đó nên `destroy` cũng xóa luôn — tải bản backup mới nhất về máy bạn trước
khi `destroy` nếu cần giữ dữ liệu.

## Embedding BGE-M3

Máy EC2 `vsf-embedder` riêng đã được **gỡ (08/10/2026)**; embedding chạy như service `embedder` cùng máy `vsf-aws`
(xem `deploy/aws/embedder/README.md`). Không còn resource Terraform nào cho embedder.

## Cảnh báo: không chạy `terraform apply` toàn bộ

`terraform plan` hiện còn hai thay đổi có sẵn từ trước, **sẽ làm hỏng hệ thống nếu apply toàn bộ**:
- `aws_security_group.vsf`: muốn xóa luật SSH `3.0.5.32/29` (EC2 Instance Connect, được thêm tay ngoài Terraform).
- `aws_iam_role_policy.github_deploy`: muốn xóa chính sách `temporary-runner-ssh`, là thứ cho phép CI mở SSH tạm để deploy.

Chỉ apply có chọn lọc (`-target=...`) và luôn đọc kỹ kế hoạch ("Plan: x to add, y to change, z to destroy") trước khi áp dụng.
