"""Authenticated HTTP routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.config import ConfigurationError, config_manager
from app.security import require_bearer
from app.terminal import command_catalog, diagnostics, run_bridge_command
from app.utils import configure_logging, health_data, last_log_lines, system_info
from app.wake import WakeError, send_wake, validate_wake_payload


routes = Blueprint("routes", __name__)
logger = configure_logging()


@routes.get("/")
@require_bearer
def root():
    return jsonify(service="Fix Pro Bridge", version="2.4", status="online")


@routes.get("/health")
@require_bearer
def health():
    return jsonify(health_data())


@routes.post("/api/wake")
@require_bearer
def wake_computer():
    data = request.get_json(silent=True)
    payload, errors = validate_wake_payload(data)
    if errors:
        logger.warning(
            "invalid_json client_ip=%s errors=%s",
            request.remote_addr or "unknown",
            len(errors),
        )
        return jsonify(success=False, message="JSON inválido.", errors=errors), 400

    try:
        send_wake(payload or {})
    except WakeError as error:
        logger.error(
            "wake_error client_ip=%s hostname=%s error=%s",
            request.remote_addr or "unknown",
            (payload or {}).get("hostname"),
            error,
        )
        return jsonify(success=False, message="Falha ao enviar Wake."), 500

    logger.info(
        "wake_sent client_ip=%s computer_id=%s hostname=%s mac=%s broadcast=%s port=%s",
        request.remote_addr or "unknown",
        payload["computer_id"],
        payload["hostname"],
        payload["mac_address"],
        payload["broadcast"],
        payload["port"],
    )
    return jsonify(success=True, message="Wake enviado.")


@routes.get("/api/info")
@require_bearer
def info():
    return jsonify(system_info())


@routes.get("/api/diagnostics")
@require_bearer
def bridge_diagnostics():
    return jsonify(success=True, **diagnostics())


@routes.post("/api/terminal/run")
@require_bearer
def bridge_terminal():
    data = request.get_json(silent=True) or {}
    command = str(data.get("command") or "").strip().lower()
    try:
        result = run_bridge_command(command)
    except ValueError as error:
        return jsonify(success=False, message=str(error), commands=command_catalog()), 400
    logger.info(
        "terminal_command client_ip=%s command=%s exit_code=%s",
        request.remote_addr or "unknown",
        command,
        result["exit_code"],
    )
    return jsonify(success=True, result=result)


@routes.post("/api/test")
@require_bearer
def test():
    logger.info("bridge_test client_ip=%s", request.remote_addr or "unknown")
    return jsonify(success=True)


@routes.get("/api/logs")
@require_bearer
def logs():
    lines = last_log_lines(100)
    return jsonify(success=True, count=len(lines), lines=lines)


@routes.post("/api/reload")
@require_bearer
def reload_config():
    try:
        config_manager.reload()
    except ConfigurationError as error:
        logger.error(
            "config_reload_error client_ip=%s error=%s",
            request.remote_addr or "unknown",
            error,
        )
        return jsonify(success=False, message=str(error)), 400
    logger.info("config_reloaded client_ip=%s", request.remote_addr or "unknown")
    return jsonify(success=True, message="Configuração recarregada.")

