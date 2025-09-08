#!/usr/bin/env bash
set -euo pipefail

# Usage: sudo LETSENCRYPT_EMAIL=you@example.com bash enable_ssl.sh YOUR_DOMAIN

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)" >&2
  exit 1
fi

DOMAIN=${1:-}
EMAIL=${LETSENCRYPT_EMAIL:-}

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Usage: sudo LETSENCRYPT_EMAIL=you@example.com bash enable_ssl.sh YOUR_DOMAIN" >&2
  exit 1
fi

mkdir -p /var/www/letsencrypt

certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --no-eff-email --redirect --non-interactive

systemctl reload nginx
echo "SSL enabled for $DOMAIN"



