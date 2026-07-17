#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "[Fix Pro Bridge 2.2] Atualizando o Termux..."
pkg update -y
pkg install -y python

python - <<'PY'
import sys

current = sys.version_info[:3]
if sys.version_info[:2] != (3, 14) or current < (3, 14, 6):
    raise SystemExit(
        f"Python incompatível: {sys.version.split()[0]}. "
        "É necessário Python 3.14.6 ou uma revisão 3.14 mais nova."
    )
print(f"[Fix Pro Bridge 2.2] Python {sys.version.split()[0]} compatível.")
PY

python -m pip --version >/dev/null

mkdir -p config logs
if [ ! -f config/config.json ]; then
    cat > config/config.json <<'JSON'
{
  "host": "0.0.0.0",
  "port": 8080,
  "token": "GERAR_AUTOMATICAMENTE",
  "log": true,
  "timeout": 10
}
JSON
fi

echo "[Fix Pro Bridge 2.2] Instalando somente wheels Python universais..."
python -m pip install \
    --only-binary=:all: \
    --no-deps \
    --requirement requirements.txt

GENERATED_TOKEN="$(python - <<'PY'
import json
import secrets
from pathlib import Path

path = Path("config/config.json")
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("token") == "GERAR_AUTOMATICAMENTE":
    data["token"] = secrets.token_urlsafe(32)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(data["token"])
PY
)"

touch logs/bridge.log
chmod 600 config/config.json
chmod 700 start.sh stop.sh restart.sh

PYTHONPATH="$ROOT_DIR" python - <<'PY'
from app import app

required = {"/", "/health", "/api/wake", "/api/info", "/api/test", "/api/logs", "/api/reload"}
available = {rule.rule for rule in app.url_map.iter_rules()}
missing = required - available
if missing:
    raise SystemExit(f"Endpoints ausentes: {sorted(missing)}")
print("[Fix Pro Bridge 2.2] Importação e endpoints verificados.")
PY

if find app -type f \( -name '*.so' -o -name '*.dylib' -o -name '*.pyd' \) | grep -q .; then
    echo "Dependência nativa encontrada dentro do projeto. Instalação cancelada."
    exit 1
fi

echo
echo "[Fix Pro Bridge 2.2] Instalação concluída sem Rust, Maturin ou compilação nativa."
if [ -n "$GENERATED_TOKEN" ]; then
    echo "[Fix Pro Bridge 2.2] Token gerado — copie para o painel:"
    echo "$GENERATED_TOKEN"
else
    echo "[Fix Pro Bridge 2.2] Token existente preservado."
fi
echo "[Fix Pro Bridge 2.2] Inicie com: ./start.sh"
