#!/usr/bin/env bash
set -euo pipefail

echo "==> SafeContract deploy start"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "==> Installing root dependencies"
npm install

echo "==> Installing frontend dependencies"
npm --prefix frontend install

echo "==> Building frontend"
npm run build

if ! command -v pm2 >/dev/null 2>&1; then
  echo "==> PM2 not found, installing globally"
  npm install -g pm2
fi

if pm2 describe safe-contract-front >/dev/null 2>&1; then
  echo "==> Restarting existing PM2 app"
  pm2 restart safe-contract-front --update-env
else
  echo "==> Starting PM2 app from ecosystem config"
  pm2 start ecosystem.config.js --env production
fi

echo "==> Saving PM2 process list"
pm2 save

echo "==> Deployment finished"
echo "Run once for boot persistence (if not already done):"
echo "  pm2 startup"
