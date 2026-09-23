#!/usr/bin/env bash
# Chuẩn bị máy Ubuntu 24.04 mới (Oracle A1 ARM hoặc Hetzner x86). Chạy một lần với sudo; chạy lại vẫn an toàn.
# Dùng: sudo DEPLOY_USER=ubuntu ./bootstrap.sh
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Chạy bằng sudo." >&2; exit 1; }
DEPLOY_USER="${DEPLOY_USER:-${SUDO_USER:-ubuntu}}"
ROOT="${VSF_ROOT:-/opt/vsf}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg unattended-upgrades

# Docker Engine + compose plugin từ kho chính thức của Docker.
if ! command -v docker > /dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $codename stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
usermod -aG docker "$DEPLOY_USER"

# Tường lửa: CHỈ MỘT công cụ. Ubuntu trên Oracle đã có sẵn luật iptables (REJECT cuối chuỗi INPUT),
# nên ở đó chèn luật iptables và không bật ufw. Nhớ mở thêm Security List trong console Oracle.
if grep -qi oracle /sys/class/dmi/id/chassis_asset_tag 2> /dev/null; then
  apt-get install -y iptables-persistent
  for spec in "tcp 22" "tcp 80" "tcp 443" "udp 443"; do
    proto="${spec% *}"
    port="${spec#* }"
    iptables -C INPUT -p "$proto" --dport "$port" -j ACCEPT 2> /dev/null \
      || iptables -I INPUT 1 -p "$proto" --dport "$port" -j ACCEPT
  done
  netfilter-persistent save
else
  apt-get install -y ufw
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw allow 443/udp
  ufw --force enable
fi

# Cứng hóa SSH: chỉ tắt mật khẩu khi người dùng deploy đã có khóa, để không tự khóa mình ngoài máy.
# `restart` (không phải `reload`): trên máy chưa từng khởi động sshd một lần nào (gặp thật trên EC2 mới —
# /run/sshd nằm tmpfs, có thể chưa được tạo kịp lúc cloud-init chạy), `reload` chỉ áp dụng cho service ĐANG
# CHẠY nên âm thầm không làm gì, để sshd không bao giờ khởi động (mất SSH hoàn toàn, "connection refused").
# `mkdir -p /run/sshd` phòng đúng ca thiếu thư mục privilege-separation đó.
home="$(getent passwd "$DEPLOY_USER" | cut -d: -f6)"
if [ -s "$home/.ssh/authorized_keys" ]; then
  printf 'PasswordAuthentication no\nPermitRootLogin no\n' > /etc/ssh/sshd_config.d/99-vsf.conf
  mkdir -p /run/sshd
  sshd -t && systemctl restart ssh
else
  echo "CẢNH BÁO: $home/.ssh/authorized_keys trống, chưa tắt đăng nhập mật khẩu." >&2
fi

systemctl enable --now unattended-upgrades

# Swap 2GB: đệm an toàn cho Postgres/ParadeDB khi RAM máy chủ thấp (đặc biệt hữu ích trên instance nhỏ);
# vô hại và không tốn gì thêm trên máy nhiều RAM. Bỏ qua nếu đã có swap (chạy lại script vẫn an toàn).
if [ "$(swapon --show=NAME --noheadings | wc -l)" -eq 0 ] && [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$ROOT" "$ROOT/deploy" "$ROOT/env" "$ROOT/state" "$ROOT/backups" "$ROOT/scripts"
chmod 700 "$ROOT/env"
echo "Xong. Đăng xuất và đăng nhập lại để nhóm docker có hiệu lực."
