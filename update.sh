#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
if [ ! -d .git ]; then echo "Instalação sem Git. Use install-online.sh."; exit 1; fi
./stop.sh || true
git pull --ff-only
./install.sh
./start.sh
echo "Fix Pro Bridge atualizado com sucesso."
