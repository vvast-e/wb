#!/usr/bin/env bash
set -euo pipefail

# This script sets up Python venv, installs deps, and creates a systemd service for backend.

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)" >&2
  exit 1
fi

BACKEND_DIR=${BACKEND_DIR:-/opt/wb_api}
PYTHON_BIN=${PYTHON_BIN:-python3}
SERVICE_NAME=${SERVICE_NAME:-wb-backend}

mkdir -p "${BACKEND_DIR}"

if [[ ! -d "${BACKEND_DIR}/.venv" ]]; then
  ${PYTHON_BIN} -m venv "${BACKEND_DIR}/.venv"
fi

source "${BACKEND_DIR}/.venv/bin/activate"
pip install --upgrade pip wheel setuptools
if [[ -f "${BACKEND_DIR}/requirements.txt" ]]; then
  pip install -r "${BACKEND_DIR}/requirements.txt"
fi

cat >"${BACKEND_DIR}/run_backend.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/wb_api
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
source .venv/bin/activate
APP_MODULE=${APP_MODULE:-app.main:app}
BIND_HOST=${BIND_HOST:-127.0.0.1}
BIND_PORT=${BIND_PORT:-8000}
WORKERS=${WORKERS:-2}
exec uvicorn "$APP_MODULE" --host "$BIND_HOST" --port "$BIND_PORT" --workers "$WORKERS"
EOS

chmod +x "${BACKEND_DIR}/run_backend.sh"

SERVICE_USER=${SERVICE_USER:-${SUDO_USER:-${USER}}}

cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=WB API Backend Service
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${BACKEND_DIR}
EnvironmentFile=-${BACKEND_DIR}/.env
ExecStart=${BACKEND_DIR}/run_backend.sh
Restart=always
RestartSec=5
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "Backend service '${SERVICE_NAME}' installed. Use: systemctl enable/start ${SERVICE_NAME}"



