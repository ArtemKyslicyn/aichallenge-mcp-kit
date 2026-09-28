"""Proxy error handling when a child command is missing."""

from __future__ import annotations

from pathlib import Path

import pytest

from aichallenge_mcp_kit.children import ChildRegistry
from aichallenge_mcp_kit.config import ChildSpec, GroupSpec, KitConfig
from aichallenge_mcp_kit.sandbox import PythonSandbox


@pytest.mark.asyncio
async def test_stdio_missing_command_marks_error(tmp_path: Path) -> None:
    cfg = KitConfig(
        workspace=tmp_path,
        bind_host="127.0.0.1",
        bind_port=3100,
        token_env="KIT_SHARED_TOKEN",
        groups=[
            GroupSpec(
                id="dev",
                children=[
                    ChildSpec(
                        id="ghost",
                        transport="stdio",
                        enabled=True,
                        command="aichallenge-mcp-kit-no-such-binary",
                        args=[],
                    )
                ],
            )
        ],
    )
    reg = ChildRegistry(cfg, PythonSandbox(tmp_path))
    reg.bootstrap_sync()
    await reg.bootstrap_async()
    row = reg.list_payload()[0]["children"][0]
    assert row["status"] == "error"
    assert row["tool_count"] == 0
    await reg.aclose()
