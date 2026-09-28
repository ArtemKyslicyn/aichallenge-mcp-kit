"""ASGI: Streamable HTTP MCP + /health + /artifacts + child proxy lifespan."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from aichallenge_mcp_kit.artifacts import ArtifactStore, mount_artifact_routes
from aichallenge_mcp_kit.auth import BearerAuthMiddleware
from aichallenge_mcp_kit.config import KitConfig
from aichallenge_mcp_kit.server import connect_proxies, mcp, shutdown_proxies


def build_app(config: KitConfig, artifacts: ArtifactStore):  # type: ignore[no-untyped-def]
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token_env=config.token_env)

    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "service": "aichallenge-mcp-kit"})

    app.add_route("/health", health, methods=["GET"])
    mount_artifact_routes(app, artifacts)

    _original = app.router.lifespan_context

    @asynccontextmanager
    async def _lifespan(instance: Starlette) -> AsyncIterator[None]:
        await connect_proxies()
        try:
            if _original is not None:
                async with _original(instance):
                    yield
            else:
                yield
        finally:
            await shutdown_proxies()

    app.router.lifespan_context = _lifespan
    return app
