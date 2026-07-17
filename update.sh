#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
if [ ! -d .git ]; then echo "Instalação sem Git. Use install-online.sh."; exit 1; fi

# O GitHub pode entregar os scripts como 0644 em instalações Android.
# Corrija a permissão antes de qualquer chamada e repita após o reset.
chmod +x install-online.sh install.sh start.sh stop.sh restart.sh update.sh 2>/dev/null || true
./stop.sh || true
git fetch origin main
git reset --hard origin/main
chmod +x install-online.sh install.sh start.sh stop.sh restart.sh update.sh 2>/dev/null || true
./install.sh
./start.sh
echo "Fix Pro Bridge atualizado com sucesso."
