#!/usr/bin/env bash
set -euo pipefail
REPO_URL="${FIXPRO_BRIDGE_REPO:-https://github.com/souzadevmg/fixpro-bridge.git}"
TARGET="${FIXPRO_BRIDGE_DIR:-$HOME/FixProBridge}"
pkg update -y
pkg install -y git curl iproute2 termux-api
if [ -d "$TARGET/.git" ]; then
  git -C "$TARGET" fetch --depth=1 origin
  git -C "$TARGET" reset --hard origin/HEAD 2>/dev/null || git -C "$TARGET" reset --hard origin/main
else
  rm -rf "$TARGET"
  git clone --depth=1 "$REPO_URL" "$TARGET"
fi
cd "$TARGET"
chmod +x install.sh start.sh stop.sh restart.sh update.sh 2>/dev/null || true
./install.sh
./start.sh
echo "Fix Pro Bridge instalado/atualizado em $TARGET"
echo "Token: python -c \"import json; print(json.load(open('config/config.json'))['token'])\""
