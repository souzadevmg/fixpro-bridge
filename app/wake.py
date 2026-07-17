"""Manual Wake request validation and Magic Packet delivery."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from wakeonlan import wake


MAC_PATTERN = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
REQUIRED_FIELDS = ("mac_address", "broadcast", "port", "computer_id", "hostname")


class WakeError(RuntimeError):
    pass


def validate_wake_payload(data: object) -> tuple[dict[str, Any] | None, dict[str, str]]:
    errors: dict[str, str] = {}
    if not isinstance(data, dict):
        return None, {"json": "O corpo deve ser um objeto JSON."}

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors[field] = "Campo obrigatório."

    mac = data.get("mac_address")
    broadcast = data.get("broadcast")
    port = data.get("port")
    computer_id = data.get("computer_id")
    hostname = data.get("hostname")

    if mac is not None:
        if not isinstance(mac, str):
            errors["mac_address"] = "Deve ser texto."
        else:
            mac = mac.strip().upper().replace("-", ":")
            if not MAC_PATTERN.fullmatch(mac):
                errors["mac_address"] = "Endereço MAC inválido."

    if broadcast is not None:
        if not isinstance(broadcast, str):
            errors["broadcast"] = "Deve ser texto."
        else:
            try:
                address = ipaddress.ip_address(broadcast.strip())
                if address.version != 4:
                    raise ValueError
                broadcast = str(address)
            except ValueError:
                errors["broadcast"] = "Broadcast IPv4 inválido."

    if port is not None and (
        isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535
    ):
        errors["port"] = "Deve ser um inteiro entre 1 e 65535."

    if computer_id is not None and (
        isinstance(computer_id, bool) or not isinstance(computer_id, int) or computer_id < 1
    ):
        errors["computer_id"] = "Deve ser um inteiro positivo."

    if hostname is not None:
        if not isinstance(hostname, str) or not hostname.strip():
            errors["hostname"] = "Deve ser um texto não vazio."
        elif len(hostname.strip()) > 190:
            errors["hostname"] = "Deve possuir no máximo 190 caracteres."
        else:
            hostname = hostname.strip()

    if errors:
        return None, errors

    return {
        "mac_address": mac,
        "broadcast": broadcast,
        "port": port,
        "computer_id": computer_id,
        "hostname": hostname,
    }, {}


def send_wake(payload: dict[str, Any]) -> None:
    try:
        wake(
            payload["mac_address"],
            host=payload["broadcast"],
            port=payload["port"],
        )
    except (OSError, ValueError) as error:
        raise WakeError(str(error)) from error
