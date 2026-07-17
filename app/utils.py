"""Logging, uptime, Android, Wi-Fi, and Tailscale helpers."""

from __future__ import annotations

import logging
import ipaddress
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from collections import deque
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import PROJECT_ROOT, get_config


LOG_PATH = PROJECT_ROOT / "logs" / "bridge.log"
STARTED_AT = time.monotonic()


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("fixpro_bridge")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    if get_config()["log"]:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_PATH,
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


def command_output(command: list[str]) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def android_property(name: str) -> str | None:
    return command_output(["getprop", name])


def wifi_ip() -> str | None:
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connection.connect(("8.8.8.8", 80))
        return str(connection.getsockname()[0])
    except OSError:
        return None
    finally:
        connection.close()


def wifi_info() -> dict[str, str | int | float | None]:
    """Return Wi-Fi details when Termux:API is installed.

    The bridge keeps working without the optional Termux API; in that case
    values are simply omitted from the response.
    """
    raw = command_output(["termux-wifi-connectioninfo"])
    data: dict = {}
    if raw:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            data = {}
    rssi = data.get("rssi")
    try:
        rssi = int(rssi) if rssi is not None else None
    except (TypeError, ValueError):
        rssi = None
    speed = data.get("link_speed_mbps")
    try:
        speed = float(speed) if speed is not None else None
    except (TypeError, ValueError):
        speed = None
    return {
        "wifi_ssid": data.get("ssid") or None,
        "wifi_signal_dbm": rssi,
        "wifi_link_speed_mbps": speed,
    }


def memory_info() -> dict[str, int | None]:
    total = available = None
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])
        total = round(values.get("MemTotal", 0) / 1024) or None
        available = round(values.get("MemAvailable", values.get("MemFree", 0)) / 1024) or None
    except (OSError, ValueError, IndexError):
        pass
    return {"memory_total_mb": total, "memory_available_mb": available}


def storage_info() -> dict[str, float | None]:
    try:
        usage = shutil.disk_usage(PROJECT_ROOT)
        total = round(usage.total / (1024 ** 3), 2)
        free = round(usage.free / (1024 ** 3), 2)
        return {"storage_total_gb": total, "storage_free_gb": free,
                "storage_used_percent": round((usage.used / usage.total) * 100, 1)}
    except OSError:
        return {"storage_total_gb": None, "storage_free_gb": None, "storage_used_percent": None}


def _is_tailscale_address(value: str) -> bool:
    try:
        return ipaddress.ip_address(value) in ipaddress.ip_network("100.64.0.0/10")
    except ValueError:
        return False


def _addresses_from_ip_output(output: str | None) -> list[str]:
    if not output:
        return []
    addresses: list[str] = []
    for part in output.replace("\n", " ").split():
        if "/" not in part:
            continue
        address = part.split("/", 1)[0]
        if _is_tailscale_address(address):
            addresses.append(address)
    return addresses


def tailscale_ip() -> str | None:
    value = command_output(["tailscale", "ip", "-4"])
    if value:
        for line in value.splitlines():
            address = line.strip()
            if _is_tailscale_address(address):
                return address

    for command in (["ip", "-4", "addr", "show", "tailscale0"], ["ip", "-4", "addr", "show"]):
        addresses = _addresses_from_ip_output(command_output(command))
        if addresses:
            return addresses[0]
    return None


def uptime() -> str:
    return str(timedelta(seconds=int(time.monotonic() - STARTED_AT)))


def health_data() -> dict[str, str]:
    return {
        "status": "ok",
        "uptime": uptime(),
        "python": platform.python_version(),
    }


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def battery_info() -> dict[str, str | int | float | bool | None]:
    """Read Termux:API first and Android power_supply as fallback."""
    raw = command_output(["termux-battery-status"])
    data: dict = {}
    if raw:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            data = {}
    percent = data.get("percentage")
    if percent is None:
        fallback = _read_text("/sys/class/power_supply/battery/capacity")
        percent = int(fallback) if fallback and fallback.isdigit() else None
    temperature = data.get("temperature")
    if temperature is None:
        fallback_temp = _read_text("/sys/class/power_supply/battery/temp")
        if fallback_temp:
            try:
                temperature = float(fallback_temp)
                if temperature > 100:
                    temperature /= 10
            except ValueError:
                temperature = None
    return {
        "battery_percent": percent,
        "battery_status": data.get("status") or _read_text("/sys/class/power_supply/battery/status"),
        "battery_temperature_c": temperature,
        "battery_plugged": data.get("plugged"),
        "battery_health": data.get("health") or _read_text("/sys/class/power_supply/battery/health"),
    }


def system_info() -> dict[str, str | int | float | bool | None]:
    info = {
        "android_model": android_property("ro.product.model") or platform.machine(),
        "hostname": socket.gethostname(),
        "android_version": android_property("ro.build.version.release") or platform.release(),
        "wifi_ip": wifi_ip(),
        "tailscale_ip": tailscale_ip(),
        "uptime": uptime(),
        "bridge_version": "2.2",
        "python": platform.python_version(),
        "pid": str(os.getpid()),
    }
    info.update(battery_info())
    info.update(wifi_info())
    info.update(memory_info())
    info.update(storage_info())
    return info


def last_log_lines(limit: int = 100) -> list[str]:
    if not LOG_PATH.is_file():
        return []
    with LOG_PATH.open("r", encoding="utf-8", errors="replace") as file:
        return [line.rstrip("\n") for line in deque(file, maxlen=limit)]


def python_is_supported() -> bool:
    """The target is CPython 3.14.6 or a newer 3.14 patch."""

    return sys.version_info[:2] == (3, 14) and sys.version_info[:3] >= (3, 14, 6)
