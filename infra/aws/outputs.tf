output "elastic_ip" {
  description = "IP tĩnh — trỏ DuckDNS (vsf-assistant.duckdns.org) sang giá trị này sau khi apply."
  value       = aws_eip.vsf.public_ip
}

output "instance_id" {
  value = aws_instance.vsf.id
}

output "ssh_command" {
  description = "Lệnh SSH vào máy (sau khi user_data chạy xong, khoảng 1-2 phút sau khi apply)."
  value       = "ssh -i <đường-dẫn-khóa-riêng-tương-ứng> ubuntu@${aws_eip.vsf.public_ip}"
}
