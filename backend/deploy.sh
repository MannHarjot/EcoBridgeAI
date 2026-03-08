#!/usr/bin/env bash
# deploy.sh — push EchoBridge AI backend to a Vultr Ubuntu VPS
#
# Usage:
#   ./deploy.sh <VULTR_IP>
#
# Prerequisites:
#   • SSH key auth configured for root@<VULTR_IP>
#   • .env file present in backend/ on the local machine
#   • rsync and ssh available locally
set -euo pipefail

VULTR_IP="${1:?Usage: $0 <VULTR_IP>}"
REMOTE="root@${VULTR_IP}"
REMOTE_DIR="/opt/echobridge/backend"

echo ">>> Deploying EchoBridge AI to ${VULTR_IP} ..."

# ---------------------------------------------------------------------------
# 1. Sync source code (exclude secrets and caches)
# ---------------------------------------------------------------------------
rsync -avz --delete \
  --exclude='.env' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv/' \
  --exclude='.git/' \
  "$(dirname "$0")/" \
  "${REMOTE}:${REMOTE_DIR}/"

echo ">>> Code synced."

# ---------------------------------------------------------------------------
# 2. Remote provisioning
# ---------------------------------------------------------------------------
ssh "${REMOTE}" bash <<ENDSSH
set -euo pipefail

# ── System packages ──────────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx

# ── Python venv + dependencies ───────────────────────────────────────────────
cd ${REMOTE_DIR}
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# ── Nginx ────────────────────────────────────────────────────────────────────
cp ${REMOTE_DIR}/nginx.conf /etc/nginx/sites-available/echobridge
ln -sf /etc/nginx/sites-available/echobridge /etc/nginx/sites-enabled/echobridge
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

# ── Systemd service ──────────────────────────────────────────────────────────
cat > /etc/systemd/system/echobridge.service <<'EOF'
[Unit]
Description=EchoBridge AI backend
After=network.target

[Service]
User=root
WorkingDirectory=${REMOTE_DIR}
EnvironmentFile=${REMOTE_DIR}/.env
ExecStart=${REMOTE_DIR}/venv/bin/gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --bind 0.0.0.0:8000 \
    --timeout 600 \
    --access-logfile - \
    --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable echobridge
systemctl restart echobridge

echo ">>> Deployment complete."
systemctl status echobridge --no-pager
ENDSSH
