"""Interactive terminal streaming for the authenticated Fix Pro Bridge API."""

from __future__ import annotations

import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any, TextIO
from urllib.parse import urlparse

import requests

from app.config import get_config
from app.utils import configure_logging, last_log_lines, tailscale_ip


logger = configure_logging()


@dataclass(frozen=True)
class BridgeCommand:
    label: str
    command: list[str] | None = None
    timeout: int = 12


COMMANDS: dict[str, BridgeCommand] = {
    "tailscale": BridgeCommand("Tailscale/IP", ["sh", "-lc", "command -v tailscale >/dev/null 2>&1 && tailscale ip -4 || true; command -v ip >/dev/null 2>&1 && ip -4 addr show 2>/dev/null || true; command -v ifconfig >/dev/null 2>&1 && ifconfig 2>/dev/null || true"]),
    "network": BridgeCommand("Rede Android", ["sh", "-lc", "command -v ip >/dev/null 2>&1 && { ip -4 addr show 2>/dev/null; ip route 2>/dev/null; } || { command -v ifconfig >/dev/null 2>&1 && ifconfig 2>/dev/null || true; }"]),
    "battery": BridgeCommand("Bateria", ["sh", "-lc", "command -v termux-battery-status >/dev/null 2>&1 && termux-battery-status || { cat /sys/class/power_supply/battery/capacity 2>/dev/null; cat /sys/class/power_supply/battery/status 2>/dev/null; }"]),
    "wifi": BridgeCommand("Wi-Fi", ["sh", "-lc", "command -v termux-wifi-connectioninfo >/dev/null 2>&1 && termux-wifi-connectioninfo || true"]),
    "storage": BridgeCommand("Armazenamento", ["sh", "-lc", "df -h /data /storage/emulated 2>/dev/null || df -h"]),
    "memory": BridgeCommand("Memória", ["sh", "-lc", "head -n 16 /proc/meminfo"]),
    "processes": BridgeCommand("Processos", ["sh", "-lc", "ps -A 2>/dev/null | head -n 40 || ps | head -n 40"]),
    "packages": BridgeCommand("Dependências", ["sh", "-lc", "printf 'ip='; command -v ip || true; printf 'ifconfig='; command -v ifconfig || true; printf 'tailscale='; command -v tailscale || true; printf 'termux-api='; command -v termux-battery-status || true; python --version"]),
    "logs": BridgeCommand("Logs do Bridge", None),
}


def command_catalog() -> list[dict[str, str]]:
    return [{"key": key, "label": item.label} for key, item in COMMANDS.items()]


def diagnostics() -> dict[str, Any]:
    return {"tailscale_ip": tailscale_ip(), "commands": command_catalog(), "interactive": bool(get_config().get("allow_remote_terminal", True))}


def _callback(url: str, token: str, payload: dict[str, Any]) -> None:
    try:
        response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}", "User-Agent": "FixProBridge/2.5.0"}, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        logger.error("terminal_callback_error error=%s", error)


def _reader(pipe: TextIO, channel: str, events: queue.Queue[tuple[str, str | None]]) -> None:
    try:
        for chunk in iter(pipe.readline, ""):
            events.put((channel, chunk))
    finally:
        events.put((channel, None))
        pipe.close()


def _command_args(command: str) -> tuple[list[str] | None, int]:
    preset = COMMANDS.get(command.strip().lower())
    if preset:
        if command.strip().lower() == "logs":
            return None, preset.timeout
        return preset.command, preset.timeout
    if not get_config().get("allow_remote_terminal", True):
        raise ValueError("O terminal interativo está desativado na configuração do Bridge.")
    if not command.strip() or len(command) > 4000:
        raise ValueError("Informe um comando com até 4.000 caracteres.")
    return ["sh", "-lc", command], min(300, int(get_config().get("terminal_timeout", 120)))


def _run(command: str, callback_url: str, callback_token: str) -> None:
    started = time.perf_counter()
    try:
        args, timeout = _command_args(command)
        if args is None:
            output = "\n".join(last_log_lines(200)) + "\n"
            _callback(callback_url, callback_token, {"event": "chunk", "channel": "stdout", "content": output})
            _callback(callback_url, callback_token, {"event": "finish", "exit_code": 0, "message": "Logs carregados."})
            return

        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", bufsize=1)
        assert process.stdout is not None and process.stderr is not None
        events: queue.Queue[tuple[str, str | None]] = queue.Queue()
        for pipe, channel in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            threading.Thread(target=_reader, args=(pipe, channel, events), daemon=True).start()

        closed = 0
        timed_out = False
        while closed < 2:
            if time.perf_counter() - started > timeout and process.poll() is None:
                timed_out = True
                process.kill()
            try:
                channel, chunk = events.get(timeout=0.1)
            except queue.Empty:
                continue
            if chunk is None:
                closed += 1
                continue
            _callback(callback_url, callback_token, {"event": "chunk", "channel": channel, "content": chunk})

        exit_code = 124 if timed_out else int(process.wait())
        message = f"Timeout após {timeout} segundos." if timed_out else ("Comando concluído." if exit_code == 0 else f"Comando finalizado com código {exit_code}.")
        _callback(callback_url, callback_token, {"event": "finish", "exit_code": exit_code, "message": message})
    except Exception as error:
        logger.exception("terminal_stream_error")
        _callback(callback_url, callback_token, {"event": "chunk", "channel": "stderr", "content": str(error) + "\n"})
        _callback(callback_url, callback_token, {"event": "finish", "exit_code": 1, "message": str(error)})


def start_terminal_stream(command: str, callback_url: str, callback_token: str) -> None:
    parsed = urlparse(callback_url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("URL de callback inválida.")
    if not callback_token or len(callback_token) < 32:
        raise ValueError("Token de callback inválido.")
    _command_args(command)
    threading.Thread(target=_run, args=(command, callback_url, callback_token), name="FixProTerminal", daemon=True).start()


def start_interactive_terminal(command: str, gateway_url: str, gateway_token: str, timeout: int | None = None, gateway_session: str = "") -> None:
    """Start a PTY session paired with the panel WebSocket gateway."""
    if not get_config().get("allow_remote_terminal", True):
        raise ValueError("O terminal interativo está desativado na configuração do Bridge.")
    if not gateway_url or not gateway_token:
        raise ValueError("Gateway ou token da sessão ausente.")
    if not command.strip() or len(command) > 4000:
        raise ValueError("Informe um comando com até 4.000 caracteres.")
    from app.terminal_pty import run
    threading.Thread(
        target=run,
        args=(command, gateway_url, gateway_token, timeout or int(get_config().get("terminal_timeout", 120)), gateway_session),
        name="FixProTerminalPTY",
        daemon=True,
    ).start()
