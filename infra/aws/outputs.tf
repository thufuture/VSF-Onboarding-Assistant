output "elastic_ip" {
  description = "IP tĩnh — trỏ DuckDNS (vsf-assistant.duckdns.org) sang giá trị này sau khi apply."
  value       = aws_eip.vsf.public_ip
}

output "instance_id" {
  value = aws_instance.vsf.id
}

output "security_group_id" {
  description = "Security Group mà GitHub Actions mở IP runner /32 tạm thời khi deploy."
  value       = aws_security_group.vsf.id
}

output "github_deploy_role_arn" {
  description = "IAM role GitHub Actions assume qua OIDC; lưu làm Environment variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.github_deploy.arn
}

output "ssh_command" {
  description = "Lệnh SSH vào máy (sau khi user_data chạy xong, khoảng 1-2 phút sau khi apply)."
  value       = "ssh -i <đường-dẫn-khóa-riêng-tương-ứng> ubuntu@${aws_eip.vsf.public_ip}"
}
