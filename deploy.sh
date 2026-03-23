#!/usr/bin/env bash
set -euo pipefail

echo "==> SafeContract deploy start"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
BACKEND_DIR="$PROJECT_DIR/backend"
BACKEND_VENV="$BACKEND_DIR/.venv"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required but not found."
  exit 1
fi

if command -v pm2 >/dev/null 2>&1; then
  echo "==> Stopping existing PM2 apps before build"
  pm2 stop safe-contract-front safe-contract-back >/dev/null 2>&1 || true
fi

echo "==> Installing root dependencies"
npm install

echo "==> Installing frontend dependencies"
npm --prefix frontend install

echo "==> Building frontend"
rm -rf "$PROJECT_DIR/frontend/.next"
npm --prefix frontend run build

echo "==> Preparing backend virtualenv"
if [ ! -d "$BACKEND_VENV" ]; then
  python3 -m venv "$BACKEND_VENV"
fi

echo "==> Installing backend dependencies"
"$BACKEND_VENV/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

if [ ! -x "$BACKEND_VENV/bin/myth" ]; then
  echo "WARNING: myth CLI not found in backend venv. /scan will fail until Mythril installs successfully."
fi

if ! command -v pm2 >/dev/null 2>&1; then
  echo "==> PM2 not found, installing globally"
  npm install -g pm2
fi

echo "==> Starting/reloading PM2 apps from ecosystem config"
pm2 startOrRestart ecosystem.config.cjs --env production

echo "==> Saving PM2 process list"
pm2 save

echo "==> Deployment finished"
echo "Run once for boot persistence (if not already done):"
echo "  pm2 startup"
