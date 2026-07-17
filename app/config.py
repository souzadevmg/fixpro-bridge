"""Small, thread-safe JSON configuration manager with no third-party code."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
DEFAULT_CONFIG: dict[str, Any] = {
    "host": "0.0.0.0",
    "port": 8080,
    "token": "GERAR_AUTOMATICAMENTE",
    "log": True,
    "timeout": 10,
}


class ConfigurationError(RuntimeError):
    """Raised when config.json is missing or contains invalid values."""


def validate_config(data: object) -> dict[str, Any]:
    """Validate and normalize configuration without Pydantic."""

    if not isinstance(data, dict):
        raise ConfigurationError("config.json must contain a JSON object")

    required = set(DEFAULT_CONFIG)
    missing = sorted(required.difference(data))
    if missing:
        raise ConfigurationError(f"missing configuration fields: {', '.join(missing)}")

    host = data.get("host")
    port = data.get("port")
    token = data.get("token")
    enabled_log = data.get("log")
    timeout = data.get("timeout")

    if not isinstance(host, str) or not host.strip():
        raise ConfigurationError("host must be a non-empty string")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigurationError("port must be an integer between 1 and 65535")
    if not isinstance(token, str) or len(token.strip()) < 8:
        raise ConfigurationError("token must contain at least 8 characters")
    if not isinstance(enabled_log, bool):
        raise ConfigurationError("log must be a boolean")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 120:
        raise ConfigurationError("timeout must be an integer between 1 and 120")

    return {
        "host": host.strip(),
        "port": port,
        "token": token.strip(),
        "log": enabled_log,
        "timeout": timeout,
    }


class ConfigManager:
    """Atomically replace configuration after complete validation."""

    def __init__(self, path: Path = CONFIG_PATH) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._data = self._load()

    def get(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def reload(self) -> dict[str, Any]:
        new_data = self._load()
        with self._lock:
            self._data = new_data
            return dict(self._data)

    def _load(self) -> dict[str, Any]:
        if not self._path.is_file():
            raise ConfigurationError(f"configuration file not found: {self._path}")
        try:
            with self._path.open("r", encoding="utf-8") as file:
                return validate_config(json.load(file))
        except (OSError, json.JSONDecodeError) as error:
            raise ConfigurationError(f"invalid config.json: {error}") from error


config_manager = ConfigManager()


def get_config() -> dict[str, Any]:
    return config_manager.get()
