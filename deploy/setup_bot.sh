#!/usr/bin/env bash
set -euo pipefail

# This script sets up Python venv, installs deps, and creates a systemd service for Telegram bot.

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)" >&2
  exit 1
fi

BOT_DIR=${BOT_DIR:-/opt/wb_bot}
PYTHON_BIN=${PYTHON_BIN:-python3}
SERVICE_NAME=${SERVICE_NAME:-wb-bot}

mkdir -p "${BOT_DIR}"

if [[ ! -d "${BOT_DIR}/.venv" ]]; then
  ${PYTHON_BIN} -m venv "${BOT_DIR}/.venv"
fi

source "${BOT_DIR}/.venv/bin/activate"
pip install --upgrade pip wheel setuptools
if [[ -f "${BOT_DIR}/requirements.txt" ]]; then
  pip install -r "${BOT_DIR}/requirements.txt"
fi

cat >"${BOT_DIR}/run_bot.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/wb_bot
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
source .venv/bin/activate
BOT_ENTRY=${BOT_ENTRY:-bot/main.py}
exec python "$BOT_ENTRY"
EOS

chmod +x "${BOT_DIR}/run_bot.sh"

SERVICE_USER=${SERVICE_USER:-${SUDO_USER:-${USER}}}

cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=WB Telegram Bot Service
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${BOT_DIR}
EnvironmentFile=-${BOT_DIR}/.env
ExecStart=${BOT_DIR}/run_bot.sh
Restart=always
RestartSec=5
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "Bot service '${SERVICE_NAME}' installed. Use: systemctl enable/start ${SERVICE_NAME}"



