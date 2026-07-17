"""Flask application factory."""

from __future__ import annotations

import atexit

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from app.routes import routes
from app.utils import configure_logging


logger = configure_logging()


def create_app() -> Flask:
    application = Flask(__name__)
    application.config.update(
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    application.register_blueprint(routes)

    @application.errorhandler(413)
    def too_large(_: object):
        return jsonify(success=False, message="Corpo JSON muito grande."), 413

    @application.errorhandler(Exception)
    def internal_error(error: Exception):
        if isinstance(error, HTTPException):
            return jsonify(success=False, message=error.description), error.code
        logger.exception(
            "internal_error client_ip=%s path=%s error=%s",
            request.remote_addr or "unknown",
            request.path,
            error,
        )
        return jsonify(success=False, message="Erro interno do Bridge."), 500

    logger.info("bridge_started version=2.4")
    return application


@atexit.register
def log_shutdown() -> None:
    logger.info("bridge_stopped")

