"""
Framework detection and helpers for common Python web frameworks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .server import start_server_with_smart_networking

if TYPE_CHECKING:
    from .options import NetworkingOptions


def detect_framework() -> str:
    try:
        import flask  # noqa: F401

        return "flask"
    except ImportError:
        pass
    try:
        import fastapi  # noqa: F401

        return "fastapi"
    except ImportError:
        pass
    try:
        import django  # noqa: F401

        return "django"
    except ImportError:
        pass
    try:
        import tornado  # noqa: F401

        return "tornado"
    except ImportError:
        pass
    return "unknown"


async def start_flask_with_smart_networking(app, options: NetworkingOptions | None = None):
    result = await start_server_with_smart_networking(app, options)
    app.run(host="0.0.0.0", port=result.port, debug=False, use_reloader=False, threaded=True)
    return result


async def start_fastapi_with_smart_networking(app, options: NetworkingOptions | None = None):
    """Start FastAPI with smart networking using Granian (2-3x faster than uvicorn)."""
    result = await start_server_with_smart_networking(app, options)

    # Try Granian first (2-3x faster), fall back to uvicorn
    try:
        import granian
        from granian.asgi import Asgi

        asgi_handler = Asgi(app)
        server = granian.Granian(
            asgi_handler,
            host="0.0.0.0",
            port=result.port,
            workers=4,
            loop="auto",
            ssl=None,
        )
        await server.serve()
    except ImportError:
        # Fallback to uvicorn if granian not available
        import uvicorn
        config = uvicorn.Config(app, host="0.0.0.0", port=result.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    return result
