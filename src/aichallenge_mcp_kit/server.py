"""FastMCP hub tools + dynamic child tool registration."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from aichallenge_mcp_kit.artifacts import ArtifactStore
from aichallenge_mcp_kit.children import ChildRegistry
from aichallenge_mcp_kit.config import KitConfig, ensure_workspace, safe_join
from aichallenge_mcp_kit.sandbox import PythonSandbox

SERVER_NAME = "aichallenge-mcp-kit"

mcp = FastMCP(
    SERVER_NAME,
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# Filled by bootstrap()
_config: KitConfig | None = None
_registry: ChildRegistry | None = None
_artifacts: ArtifactStore | None = None
_workspace: Path | None = None


def bootstrap(config: KitConfig) -> tuple[ChildRegistry, ArtifactStore]:
    global _config, _registry, _artifacts, _workspace
    _config = config
    ensure_workspace(config.workspace)
    _workspace = config.workspace
    sandbox = PythonSandbox(config.workspace)
    _registry = ChildRegistry(config, sandbox)
    _registry.bootstrap()
    _artifacts = ArtifactStore(config.workspace)

    # Register builtin child tools on the FastMCP instance
    for name, handler in _registry.all_tool_handlers().items():
        _register_dynamic_tool(name, handler)

    return _registry, _artifacts


def _register_dynamic_tool(name: str, handler: Any) -> None:
    # FastMCP tool names must be valid; our prefixes use __ which is fine.
    async def _tool(**kwargs: Any) -> str:
        result = handler(**kwargs)
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[misc]
        return str(result)

    _tool.__name__ = name
    _tool.__doc__ = f"Kit child tool {name}"
    mcp.tool(name=name)(_tool)


def _require() -> tuple[KitConfig, ChildRegistry, ArtifactStore, Path]:
    if not _config or not _registry or not _artifacts or not _workspace:
        raise RuntimeError("kit not bootstrapped")
    return _config, _registry, _artifacts, _workspace


@mcp.tool()
def hub_list_children() -> str:
    """List configured groups/children and their status."""
    _, registry, _, _ = _require()
    return json.dumps(registry.list_payload(), ensure_ascii=False, indent=2)


@mcp.tool()
def hub_workspace_list(relative: str = ".") -> str:
    """List files under KIT_WORKSPACE (relative path)."""
    _, _, _, workspace = _require()
    base = safe_join(workspace, relative) if relative not in {".", ""} else workspace
    if not base.is_dir():
        return f"not a directory: {relative}"
    lines: list[str] = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            rel = path.relative_to(workspace).as_posix()
            lines.append(f"{rel}\t{path.stat().st_size}")
    return "\n".join(lines) if lines else "(empty)"


@mcp.tool()
def hub_workspace_put(relative_path: str, content_b64: str = "", text: str = "") -> str:
    """Write a small file into the workspace (text or base64)."""
    _, _, _, workspace = _require()
    target = safe_join(workspace, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if text:
        target.write_text(text, encoding="utf-8")
    elif content_b64:
        target.write_bytes(base64.b64decode(content_b64))
    else:
        raise ValueError("pass text or content_b64")
    return f"wrote {relative_path}"


@mcp.tool()
def hub_workspace_get(relative_path: str, as_artifact: bool = False) -> str:
    """Read a small text file, or copy into /artifacts and return artifact id."""
    _, _, artifacts, workspace = _require()
    target = safe_join(workspace, relative_path)
    if not target.is_file():
        raise FileNotFoundError(relative_path)
    if as_artifact or target.stat().st_size > 64_000:
        meta = artifacts.create()
        artifacts.path_for(meta["id"]).write_bytes(target.read_bytes())
        return json.dumps(
            {
                "path": relative_path,
                "artifact_id": meta["id"],
                "download_url": meta["download_url"],
                "bytes": target.stat().st_size,
                "hint": "GET {tunnel}{download_url} with Authorization: Bearer <token>",
            },
            ensure_ascii=False,
        )
    return target.read_text(encoding="utf-8", errors="replace")
