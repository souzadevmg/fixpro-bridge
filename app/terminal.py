"""Safe remote diagnostics commands for the Android Bridge.

This is intentionally not a free shell. The panel sends a command key and the
Bridge executes a small allow-list of read-only diagnostics.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Any

from app.utils import last_log_lines, tailscale_ip


@dataclass(frozen=True)
class BridgeCommand:
    label: str
    command: list[str] | None = None
    timeout: int = 8


COMMANDS: dict[str, BridgeCommand] = {
    "tailscale": BridgeCommand(
        "Tailscale/IP",
        [
            "sh",
            "-lc",
            "command -v tailscale >/dev/null 2>&1 && tailscale ip -4 || true; "
            "command -v ip >/dev/null 2>&1 && ip -4 addr show 2>/dev/null || true; "
            "command -v ifconfig >/dev/null 2>&1 && ifconfig 2>/dev/null || true",
        ],
    ),
    "network": BridgeCommand(
        "Rede Android",
        [
            "sh",
            "-lc",
            "command -v ip >/dev/null 2>&1 && { ip -4 addr show 2>/dev/null; ip route 2>/dev/null; } "
            "|| { command -v ifconfig >/dev/null 2>&1 && ifconfig 2>/dev/null || true; }",
        ],
    ),
    "battery": BridgeCommand(
        "Bateria",
        [
            "sh",
            "-lc",
            "command -v termux-battery-status >/dev/null 2>&1 && termux-battery-status || "
            "{ cat /sys/class/power_supply/battery/capacity 2>/dev/null; "
            "cat /sys/class/power_supply/battery/status 2>/dev/null; }",
        ],
    ),
    "wifi": BridgeCommand("Wi-Fi", ["sh", "-lc", "command -v termux-wifi-connectioninfo >/dev/null 2>&1 && termux-wifi-connectioninfo || true"]),
    "storage": BridgeCommand("Armazenamento", ["df", "-h"]),
    "memory": BridgeCommand("Memória", ["sh", "-lc", "head -n 16 /proc/meminfo"]),
    "processes": BridgeCommand("Processos", ["sh", "-lc", "ps -A 2>/dev/null | head -n 40 || ps | head -n 40"]),
    "packages": BridgeCommand(
        "Dependências",
        [
            "sh",
            "-lc",
            "printf 'ip='; command -v ip || true; "
            "printf 'ifconfig='; command -v ifconfig || true; "
            "printf 'tailscale='; command -v tailscale || true; "
            "printf 'termux-api='; command -v termux-battery-status || true; "
            "python --version",
        ],
    ),
    "logs": BridgeCommand("Logs do Bridge", None),
}


def _clean_stderr(value: str) -> str:
    ignored = {
        "Cannot bind netlink socket: Permission denied",
        "Warning: cannot open /proc/net/dev (Permission denied). Limited output.",
    }
    return "\n".join(
        line for line in (value or "").splitlines()
        if line.strip() and line.strip() not in ignored
    ).strip()


def command_catalog() -> list[dict[str, str]]:
    return [{"key": key, "label": item.label} for key, item in COMMANDS.items()]


def diagnostics() -> dict[str, Any]:
    return {
        "tailscale_ip": tailscale_ip(),
        "commands": command_catalog(),
    }


def run_bridge_command(key: str) -> dict[str, Any]:
    key = key.strip().lower()
    if key not in COMMANDS:
        raise ValueError("Comando de diagnóstico não permitido.")

    item = COMMANDS[key]
    started = time.perf_counter()

    if key == "logs":
        lines = last_log_lines(120)
        return {
            "command": key,
            "label": item.label,
            "exit_code": 0,
            "stdout": "\n".join(lines),
            "stderr": "",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    assert item.command is not None
    try:
        completed = subprocess.run(
            item.command,
            capture_output=True,
            check=False,
            text=True,
            timeout=item.timeout,
        )
        stdout = completed.stdout or ""
        stderr = _clean_stderr(completed.stderr or "")
        return {
            "command": key,
            "label": item.label,
            "exit_code": int(completed.returncode),
            "stdout": stdout[-16000:],
            "stderr": stderr[-8000:],
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": key,
            "label": item.label,
            "exit_code": 124,
            "stdout": (error.stdout or "")[-16000:] if isinstance(error.stdout, str) else "",
            "stderr": "Timeout ao executar diagnóstico.",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }
