#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PID_FILE=".bridge.pid"
if [ ! -f "$PID_FILE" ]; then
    echo "Fix Pro Bridge não está em execução."
    exit 0
fi

BRIDGE_PID="$(cat "$PID_FILE")"
if kill -0 "$BRIDGE_PID" 2>/dev/null; then
    kill "$BRIDGE_PID"
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        kill -0 "$BRIDGE_PID" 2>/dev/null || break
        sleep 1
    done
    if kill -0 "$BRIDGE_PID" 2>/dev/null; then
        kill -9 "$BRIDGE_PID"
    fi
fi

rm -f "$PID_FILE"
if command -v termux-wake-unlock >/dev/null 2>&1; then
    termux-wake-unlock || true
fi
echo "Fix Pro Bridge parado corretamente."
