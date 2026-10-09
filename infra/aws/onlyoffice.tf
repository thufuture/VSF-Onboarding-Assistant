# Máy chủ soạn thảo kiểu Word (ONLYOFFICE Docs) cho trang Tài liệu. Máy RIÊNG vì ONLYOFFICE cần từ 4 GB RAM (đo thật: ~1 GB
# lúc rảnh, tăng khi có người sửa) còn vsf-aws đã chạy backend, DB và embedder.
#
# Kiến trúc: Caddy (TLS tự động, tên miền sslip.io suy ra từ Elastic IP nên không cần DuckDNS) -> ONLYOFFICE Document Server
# trong Docker, JWT bật. Trình duyệt tải trình soạn thảo qua HTTPS; backend trên vsf-aws gọi chuyển đổi/lưu qua cùng địa chỉ
# HTTPS; ONLYOFFICE gọi ngược về backend qua https://vsf-assistant.duckdns.org/api/v1/portal/editor-* (đường dẫn có mã ký
# ngắn hạn + JWT, xem backend/src/services/portal/word_editor.py).
#
# CẢNH BÁO: chỉ apply có chọn lọc, xem infra/aws/README.md. Ví dụ:
#   terraform apply -target=aws_security_group.onlyoffice -target=aws_eip.onlyoffice \
#     -target=aws_instance.onlyoffice -target=aws_eip_association.onlyoffice

variable "onlyoffice_instance_type" {
  description = "c7i-flex.large (2 vCPU/4 GiB) nằm trong danh sách Free Plan (đã kiểm bằng ec2 describe-instance-types free-tier-eligible=true, 09/10/2026) và đúng mức 4 GB ONLYOFFICE yêu cầu."
  type        = string
  default     = "c7i-flex.large"
}

variable "onlyoffice_jwt_secret" {
  description = "Khóa JWT dùng chung với backend (ONLYOFFICE_JWT_SECRET). Đặt trong terraform.tfvars (đã bị git bỏ qua), không đưa vào repo."
  type        = string
  sensitive   = true
}

# Ảnh cố định theo digest (bản đã thử ở máy dev, ONLYOFFICE 9.4.0) để không bị đổi phiên bản ngoài ý muốn khi máy dựng lại.
variable "onlyoffice_image" {
  type    = string
  default = "onlyoffice/documentserver@sha256:3ab6ebc7c605e5a32b7ae3ff19daed4925090245acc8100ce2230bd766c88212"
}

resource "aws_security_group" "onlyoffice" {
  name        = "vsf-onlyoffice"
  description = "ONLYOFFICE editor server: HTTP/HTTPS open (Caddy auto TLS), SSH from your IP only."
  tags        = local.common_tags

  ingress {
    description = "SSH - your IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }
  ingress {
    description = "HTTP (Lets Encrypt HTTP-01 + redirect)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Tạo EIP trước máy để tên miền sslip.io (suy ra từ IP) đã biết khi cloud-init cấu hình Caddy.
resource "aws_eip" "onlyoffice" {
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "vsf-onlyoffice" })
}

locals {
  onlyoffice_host = "${replace(aws_eip.onlyoffice.public_ip, ".", "-")}.sslip.io"
}

resource "aws_instance" "onlyoffice" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.onlyoffice_instance_type
  key_name               = aws_key_pair.vsf.key_name
  vpc_security_group_ids = [aws_security_group.onlyoffice.id]

  root_block_device {
    volume_size           = 30 # ảnh ONLYOFFICE ~5 GB + dữ liệu; gp3 trong hạn mức Free Plan
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  user_data = templatefile("${path.module}/onlyoffice-cloud-init.sh.tftpl", {
    bootstrap_script = file("${path.module}/../../scripts/vps/bootstrap.sh")
    public_host      = local.onlyoffice_host
    image            = var.onlyoffice_image
    jwt_secret       = var.onlyoffice_jwt_secret
  })

  lifecycle {
    ignore_changes = [ami]
  }

  tags = merge(local.common_tags, { Name = "vsf-onlyoffice" })
}

resource "aws_eip_association" "onlyoffice" {
  instance_id   = aws_instance.onlyoffice.id
  allocation_id = aws_eip.onlyoffice.id
}

output "onlyoffice_url" {
  description = "Địa chỉ HTTPS công khai của máy chủ soạn thảo (đặt vào ONLYOFFICE_PUBLIC_URL và ONLYOFFICE_INTERNAL_URL của backend)."
  value       = "https://${local.onlyoffice_host}"
}

output "onlyoffice_instance_id" {
  value = aws_instance.onlyoffice.id
}
