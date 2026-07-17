#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PID_FILE=".bridge.pid"
CONFIG_FILE="config/config.json"
LOG_FILE="logs/bridge.log"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Arquivo $CONFIG_FILE não encontrado. Execute ./install.sh."
    exit 1
fi

python - <<'PY'
import sys

if sys.version_info[:2] != (3, 14) or sys.version_info[:3] < (3, 14, 6):
    raise SystemExit("Fix Pro Bridge requer Python 3.14.6 ou 3.14.x mais novo.")
PY

read -r HOST PORT TOKEN LOG_ENABLED TIMEOUT < <(PYTHONPATH="$ROOT_DIR" python - <<'PY'
from app.config import get_config

config = get_config()
print(config["host"], config["port"], config["token"], int(config["log"]), config["timeout"])
PY
)

if [ "$TOKEN" = "GERAR_AUTOMATICAMENTE" ] || [ "${#TOKEN}" -lt 8 ]; then
    echo "Token não inicializado. Execute ./install.sh."
    exit 1
fi

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Fix Pro Bridge já está em execução (PID $(cat "$PID_FILE"))."
    exit 0
fi

mkdir -p logs
touch "$LOG_FILE"

if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock || true
fi

export PYTHONPATH="$ROOT_DIR"
nohup waitress-serve \
    --host="$HOST" \
    --port="$PORT" \
    --threads=2 \
    --channel-timeout="$TIMEOUT" \
    app:app \
    >> "$LOG_FILE" 2>&1 &

BRIDGE_PID=$!
echo "$BRIDGE_PID" > "$PID_FILE"
sleep 2

if ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "Falha ao iniciar o Bridge. Consulte $LOG_FILE."
    exit 1
fi

echo "Fix Pro Bridge 2.5.0 iniciado em http://$HOST:$PORT (PID $BRIDGE_PID)."
