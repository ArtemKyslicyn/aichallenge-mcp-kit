"""Persistent stdio / Streamable HTTP child MCP sessions."""

from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

from aichallenge_mcp_kit.config import ChildSpec

logger = logging.getLogger(__name__)


def _format_tool_result(result: Any) -> str:
    parts: list[str] = []
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(str(text))
        else:
            parts.append(str(block))
    if getattr(result, "isError", False):
        return "error: " + ("\n".join(parts) if parts else "tool failed")
    return "\n".join(parts) if parts else str(result)


class ChildSession:
    """One long-lived MCP client session to a child process or HTTP endpoint."""

    def __init__(self, group_id: str, spec: ChildSpec) -> None:
        self.group_id = group_id
        self.spec = spec
        self.prefix = f"{group_id}__{spec.id}"
        self.tool_names: list[str] = []
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def connect(self) -> None:
        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            if self.spec.transport == "stdio":
                if not self.spec.command:
                    raise ValueError("stdio child requires command")
                params = StdioServerParameters(
                    command=self.spec.command,
                    args=list(self.spec.args),
                    env=None,
                )
                read, write = await stack.enter_async_context(stdio_client(params))
            elif self.spec.transport == "http":
                if not self.spec.url:
                    raise ValueError("http child requires url")
                headers: dict[str, str] = {}
                if self.spec.token_env:
                    token = os.environ.get(self.spec.token_env, "")
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                read, write, _sid = await stack.enter_async_context(
                    streamablehttp_client(self.spec.url, headers=headers or None)
                )
            else:
                raise ValueError(f"unsupported transport {self.spec.transport}")

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            listed = await session.list_tools()
            self._session = session
            self._stack = stack
            self.tool_names = [t.name for t in listed.tools]
            logger.info(
                "child connected %s transport=%s tools=%s",
                self.prefix,
                self.spec.transport,
                len(self.tool_names),
            )
        except Exception:
            await stack.__aexit__(None, None, None)
            raise

    async def close(self) -> None:
        if self._stack is not None:
            await self._stack.__aexit__(None, None, None)
        self._stack = None
        self._session = None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> str:
        if self._session is None:
            raise RuntimeError(f"child {self.prefix} not connected")
        result = await self._session.call_tool(tool_name, arguments or {})
        return _format_tool_result(result)

    def make_handlers(self) -> dict[str, Any]:
        handlers: dict[str, Any] = {}
        for tool_name in self.tool_names:
            prefixed = f"{self.prefix}__{tool_name}"

            async def _handler(_tn: str = tool_name, **kwargs: Any) -> str:
                return await self.call_tool(_tn, kwargs)

            _handler.__name__ = prefixed
            _handler.__doc__ = f"Proxied {self.prefix} → {tool_name}"
            handlers[prefixed] = _handler
        return handlers
