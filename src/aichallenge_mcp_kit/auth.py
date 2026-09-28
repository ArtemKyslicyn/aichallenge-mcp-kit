"""Bearer auth for /mcp and /artifacts."""

from __future__ import annotations

import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token_env: str = "KIT_SHARED_TOKEN") -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._token_env = token_env

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        if request.url.path in {"/health", "/"}:
            return await call_next(request)
        token = os.environ.get(self._token_env, "")
        if not token:
            return JSONResponse({"error": f"{self._token_env} unset"}, status_code=503)
        auth = request.headers.get("authorization", "")
        expected = f"Bearer {token}"
        if not hmac.compare_digest(auth, expected):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
