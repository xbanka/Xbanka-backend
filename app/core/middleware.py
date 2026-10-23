import logging
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_ctx

logger = logging.getLogger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestLoggingMiddleware:
    """Assigns a request ID and logs one line per HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = Headers(scope=scope).get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        # Unhandled exceptions are answered by ServerErrorMiddleware, outside
        # this middleware, after the contextvar is reset; keep the ID on state.
        scope.setdefault("state", {})["request_id"] = request_id
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            client = scope.get("client")
            level = logging.ERROR if status_code >= 500 else logging.INFO
            logger.log(
                level,
                "%s %s -> %s",
                scope["method"],
                scope["path"],
                status_code,
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client[0] if client else None,
                },
            )
            request_id_ctx.reset(token)
