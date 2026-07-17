"""Fix Pro Bridge Flask application entry point."""

from __future__ import annotations

import sys

# Flask imports MarkupSafe through Jinja and Werkzeug. The official pure-Python
# implementation is bundled to guarantee that Termux never builds C extensions.
from app._vendor import markupsafe as _markupsafe
from app._vendor.markupsafe import _native as _markupsafe_native

sys.modules.setdefault("markupsafe", _markupsafe)
sys.modules.setdefault("markupsafe._native", _markupsafe_native)

from app.app import create_app  # noqa: E402


__version__ = "2.5.0"
app = create_app()

