# Máy embedding BGE-M3 tự host (thử nghiệm giảm độ trễ so với Modal). Kế hoạch và điều kiện dừng:
# docs/value/benchmark-modal-llm-viga/ke-hoach-tu-host-bge-m3-tren-aws.md
#
# - Cùng vùng, cùng AZ với máy chính (vsf-aws) để độ trễ mạng thấp nhất.
# - Cổng 8080 CHỈ nhận từ nhóm bảo mật của máy chính, không mở ra internet. SSH chỉ từ IP của người vận hành (var.my_ip).
# - Mã dịch vụ (server.py, Dockerfile, requirements.txt) được nhúng thẳng vào cloud-init, không cần SSH để triển khai.
# - Gỡ bỏ: `terraform destroy -target=aws_instance.embedder -target=aws_security_group.embedder`.

variable "embedder_instance_type" {
  description = "Loại máy cho dịch vụ embedding (CPU). Bắt đầu bằng m7i-flex.large, tăng lên 4 vCPU nếu đo chưa đủ nhanh."
  type        = string
  default     = "m7i-flex.large"
}

variable "embedder_api_key" {
  description = "Khóa Bearer của dịch vụ embedding (sinh ngẫu nhiên, ví dụ: openssl rand -hex 32). Truyền bằng TF_VAR_embedder_api_key, không ghi vào tfvars."
  type        = string
  sensitive   = true
}

variable "embedder_dtype" {
  description = "fp32 (chuẩn nhất) hoặc bf16 (nhanh hơn trên CPU có AMX; chỉ dùng khi độ chính xác đã được đo)."
  type        = string
  default     = "fp32"
}

variable "dev_ip_cidr" {
  description = "IP (dạng CIDR /32) của máy dev được gọi trực tiếp cổng 8080 của máy embedding, để backend dev dùng chung dịch vụ. Để trống = không mở. Đổi mạng thì IP đổi, cập nhật lại biến này."
  type        = string
  default     = ""
}

variable "extra_dev_cidrs" {
  description = "Các IP /32 khác của máy dev cũng được gọi cổng 8080 (mạng nhà cung cấp có thể ra internet qua nhiều IP luân phiên)."
  type        = list(string)
  default     = []
}

variable "embedder_az" {
  description = "AZ của máy embedding, trùng AZ máy chính để giảm độ trễ."
  type        = string
  default     = "ap-southeast-1b"
}

# Chỉ ĐỌC nhóm bảo mật của máy chính (không tham chiếu resource aws_security_group.vsf): tham chiếu resource sẽ kéo theo cả
# thay đổi đang chờ trên nhóm đó khi apply (Terraform muốn xóa luật SSH 3.0.5.32/29 của EC2 Instance Connect, vốn được thêm
# tay ngoài Terraform). Máy embedding không được phép làm mất đường vào máy chính.
data "aws_security_group" "main" {
  name = "vsf-aws"
}

resource "aws_security_group" "embedder" {
  name        = "vsf-embedder"
  description = "BGE-M3 embedder: 8080 from vsf-aws only; SSH from operator IP."
  tags        = merge(local.common_tags, { Name = "vsf-embedder" })

  ingress {
    description     = "Embedding API - only from the vsf-aws security group"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [data.aws_security_group.main.id]
  }
  dynamic "ingress" {
    for_each = var.dev_ip_cidr == "" ? [] : [var.dev_ip_cidr]
    content {
      description = "Embedding API - dev machine IP only"
      from_port   = 8080
      to_port     = 8080
      protocol    = "tcp"
      cidr_blocks = distinct(concat([ingress.value], var.extra_dev_cidrs))
    }
  }
  ingress {
    description = "SSH - operator IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "embedder" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.embedder_instance_type
  availability_zone      = var.embedder_az
  key_name               = aws_key_pair.vsf.key_name
  vpc_security_group_ids = [aws_security_group.embedder.id]

  root_block_device {
    volume_size           = 40 # GB gp3: hệ điều hành + ảnh Docker (torch + mô hình ~2,3 GB) + bộ nhớ đệm build
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required" # IMDSv2 bắt buộc, như máy chính
  }

  user_data = templatefile("${path.module}/embedder-cloud-init.sh.tftpl", {
    server_py_b64        = filebase64("${path.module}/../../docs/value/benchmark-modal-llm-viga/bge-m3-embedder/server.py")
    dockerfile_b64       = filebase64("${path.module}/../../docs/value/benchmark-modal-llm-viga/bge-m3-embedder/Dockerfile")
    requirements_txt_b64 = filebase64("${path.module}/../../docs/value/benchmark-modal-llm-viga/bge-m3-embedder/requirements.txt")
    api_key              = var.embedder_api_key
    dtype                = var.embedder_dtype
  })
  user_data_replace_on_change = false # đổi cấu hình không tự xóa-tạo lại máy; muốn nạp lại thì chủ động taint

  # user_data: mã dịch vụ có thể được cập nhật trực tiếp trên máy khi thử nghiệm; đừng để Terraform coi đó là lệch cấu hình rồi
  # dừng/khởi động lại máy (AWS chỉ cho đổi user_data khi máy đang tắt).
  lifecycle {
    ignore_changes = [ami, user_data]
  }

  tags = merge(local.common_tags, { Name = "vsf-embedder" })
}

output "embedder_private_ip" {
  description = "IP riêng của máy embedding: đặt EMBEDDING_ENDPOINT=http://<IP>:8080 trên máy chính."
  value       = aws_instance.embedder.private_ip
}

output "embedder_instance_id" {
  value = aws_instance.embedder.id
}
