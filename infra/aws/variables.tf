variable "region" {
  description = "Vùng AWS — Singapore, gần Việt Nam nhất."
  type        = string
  default     = "ap-southeast-1"
}

variable "my_ip" {
  description = "IP công khai của bạn (dạng CIDR, ví dụ 1.2.3.4/32) — CHỈ IP này được SSH vào máy. Lấy bằng: curl -s https://checkip.amazonaws.com"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Đường dẫn khóa công khai SSH (ví dụ ~/.ssh/vsf-aws.pub), sinh bằng: ssh-keygen -t ed25519 -f ~/.ssh/vsf-aws -C vsf-aws"
  type        = string
}

variable "instance_type" {
  description = "Loại máy EC2 — m7i-flex.large (2 vCPU/8GB) đã xác nhận \"Eligible for the free offer\" trực tiếp trên Console tài khoản (23/09/2026), xem trien-khai-aws-vercel.md mục 0.1."
  type        = string
  default     = "m7i-flex.large"
}
