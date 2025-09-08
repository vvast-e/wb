#!/usr/bin/env bash
set -euo pipefail

# Base packages: nginx, certbot, python, postgres, ufw

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  nginx \
  python3 python3-venv python3-pip \
  postgresql postgresql-contrib \
  certbot python3-certbot-nginx \
  ufw git curl

# UFW basic rules
ufw allow OpenSSH || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
echo "y" | ufw enable || true

systemctl enable nginx
systemctl start nginx

echo "Base installation complete."



