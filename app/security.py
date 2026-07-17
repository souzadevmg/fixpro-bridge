"""Bearer authentication decorator for every route."""

from __future__ import annotations

import hmac
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import Response, jsonify, request

from app.config import get_config
from app.utils import configure_logging


logger = configure_logging()
F = TypeVar("F", bound=Callable[..., Any])


def require_bearer(function: F) -> F:
    @wraps(function)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        header = request.headers.get("Authorization", "")
        scheme, separator, token = header.partition(" ")
        valid = (
            separator == " "
            and scheme.lower() == "bearer"
            and hmac.compare_digest(token, get_config()["token"])
        )
        if not valid:
            logger.warning(
                "invalid_token client_ip=%s path=%s",
                request.remote_addr or "unknown",
                request.path,
            )
            response: Response = jsonify(
                success=False,
                message="Token Bearer ausente ou inválido.",
            )
            response.status_code = 401
            response.headers["WWW-Authenticate"] = "Bearer"
            return response
        return function(*args, **kwargs)

    return cast(F, decorated)
