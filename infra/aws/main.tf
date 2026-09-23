# Hạ tầng AWS cho backend + DB (VSF Onboarding Assistant). Frontend chạy trên Vercel, không ở đây.
# Xem docs/chatbot-vsf/plan/infrastructure/trien-khai-aws-vercel.md cho bối cảnh và quyết định.

terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

# Ubuntu 24.04 LTS chính chủ Canonical, x86_64 — khớp Docker image hiện có (không cần bản ARM).
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_key_pair" "vsf" {
  key_name   = "vsf-aws"
  public_key = file(var.ssh_public_key_path)
}

locals {
  common_tags = {
    Project = "vsf-onboarding-assistant"
  }
}

resource "aws_security_group" "vsf" {
  name = "vsf-aws"
  # AWS chỉ chấp nhận description khớp regex ASCII hẹp (không dấu, không '/—): phát hiện thật qua
  # `terraform plan` báo lỗi "doesn't comply with restrictions" — giữ nguyên tiếng Việt trong comment file
  # này (người đọc), chỉ description gửi lên AWS mới cần ASCII thuần.
  description = "SSH from your IP only; HTTP/HTTPS open (Caddy auto TLS)."
  tags        = local.common_tags

  ingress {
    description = "SSH - your IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }
  ingress {
    description = "HTTP (Lets Encrypt HTTP-01 + redirect to HTTPS)"
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
  ingress {
    description = "HTTP/3 (QUIC)"
    from_port   = 443
    to_port     = 443
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# GitHub Actions nhận credential AWS ngắn hạn qua OIDC. Role chỉ tin đúng repo và Environment
# production-aws; workflow dùng quyền này để mở IP runner /32 trong lúc deploy rồi thu hồi.
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
  ]

  tags = local.common_tags
}

data "aws_iam_policy_document" "github_deploy_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:thufuture/VSF-Onboarding-Assistant:environment:production-aws"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "vsf-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_deploy_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "github_deploy" {
  statement {
    sid = "ManageTemporaryRunnerSshRule"
    actions = [
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:RevokeSecurityGroupIngress",
    ]
    resources = [aws_security_group.vsf.arn]
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "temporary-runner-ssh"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}

resource "aws_instance" "vsf" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.vsf.key_name
  vpc_security_group_ids = [aws_security_group.vsf.id]

  root_block_device {
    volume_size           = 30 # GB, gp3 — trong hạn mức Free Plan
    volume_type           = "gp3"
    encrypted             = true # không tốn thêm phí, không lý do để tắt
    delete_on_termination = true # ổ DB mất theo khi terraform destroy — đúng runbook (README mục "Dọn dẹp")
  }

  # IMDSv2 bắt buộc: chặn kiểu tấn công SSRF lấy credential IAM qua metadata endpoint (vd sự cố Capital One
  # 2019) — IMDSv1 (GET thẳng) không cần token nên dễ bị request độc hại từ container/app đọc trộm.
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  # Chạy bootstrap.sh (dùng chung với VPS Hetzner — cài Docker, ufw, swap 2GB, cứng hóa SSH) ngay lúc khởi
  # tạo máy qua cloud-init, không cần SSH tay vào chạy. Nhúng thẳng nội dung script (thay vì `curl` từ
  # GitHub) để không phụ thuộc repo có public hay không — Terraform đọc file cục bộ lúc apply.
  # Dùng templatefile() với file .tftpl riêng (không phải heredoc HCL inline): heredoc `<<-` của Terraform
  # xoá khoảng trắng đầu dòng theo dòng ÍT thụt nhất trong toàn khối (kể cả dòng đóng EOF) — lệch thụt lề
  # giữa nội dung và marker đóng để sót khoảng trắng trước "#!", phá nhận diện shebang của cloud-init.
  # File .tftpl bắt đầu đúng cột 0 nên không có rủi ro này.
  user_data = templatefile("${path.module}/cloud-init.sh.tftpl", {
    bootstrap_script = file("${path.module}/../../scripts/vps/bootstrap.sh")
  })

  tags = merge(local.common_tags, { Name = "vsf-aws" })
}

resource "aws_eip" "vsf" {
  # ĐÍNH CHÍNH (23/09/2026): từ 02/2024 AWS tính phí MỌI IPv4 công khai $0.005/giờ, kể cả đang gắn với
  # instance đang chạy — không còn "gắn thì free" như trước. Với đúng 1 EIP chạy 24/7 (~744h/tháng), chi phí
  # này nằm trong ưu đãi riêng "750h/tháng IPv4 công khai" của tài khoản mới, nên vẫn $0 thật trong thực tế
  # — nhưng KHÔNG phải vì cơ chế "attached is free", mà vì ưu đãi riêng che phủ đủ. Tài khoản Free Plan chỉ
  # sống tối đa 6 tháng (không phải 12), xem docs/.../trien-khai-aws-vercel.md mục 0.1.
  # Vẫn gắn liền domain + instance (không tách rời aws_eip_association) để không lỡ tạo EIP dư thừa/idle
  # (idle cũng bị tính phí y hệt, không có lý do giữ EIP không gắn).
  domain = "vpc"
  tags   = local.common_tags
}

resource "aws_eip_association" "vsf" {
  instance_id   = aws_instance.vsf.id
  allocation_id = aws_eip.vsf.id
}
