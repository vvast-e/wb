#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sudo DB_NAME=wb_db DB_USER=wb_user DB_PASS='CHANGE_ME' bash setup_postgres.sh

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)" >&2
  exit 1
fi

DB_NAME=${DB_NAME:-wb_db}
DB_USER=${DB_USER:-wb_user}
DB_PASS=${DB_PASS:-change_me}

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres createdb "${DB_NAME}"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

cat >/etc/postgresql/$(ls /etc/postgresql)/main/conf.d/pg-custom.conf <<EOF
listen_addresses = 'localhost'
EOF

systemctl restart postgresql
echo "PostgreSQL database '${DB_NAME}' and user '${DB_USER}' are ready."



