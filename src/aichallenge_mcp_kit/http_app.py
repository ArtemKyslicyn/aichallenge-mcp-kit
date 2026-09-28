"""ASGI: Streamable HTTP MCP + /health + /artifacts."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from aichallenge_mcp_kit.artifacts import ArtifactStore, mount_artifact_routes
from aichallenge_mcp_kit.auth import BearerAuthMiddleware
from aichallenge_mcp_kit.config import KitConfig
from aichallenge_mcp_kit.server import mcp


def build_app(config: KitConfig, artifacts: ArtifactStore):  # type: ignore[no-untyped-def]
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token_env=config.token_env)

    @app.route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "service": "aichallenge-mcp-kit"})

    mount_artifact_routes(app, artifacts)
    return app
