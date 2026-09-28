"""Child registry: builtins + stdio/HTTP proxy sessions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from aichallenge_mcp_kit.config import ChildSpec, KitConfig
from aichallenge_mcp_kit.proxy import ChildSession
from aichallenge_mcp_kit.sandbox import PythonSandbox

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Awaitable[str] | str]


@dataclass
class ChildRuntime:
    group_id: str
    spec: ChildSpec
    status: str = "ok"  # ok | disabled | error | pending
    detail: str = ""
    tool_count: int = 0
    tools: dict[str, ToolHandler] = field(default_factory=dict)
    session: ChildSession | None = None


class ChildRegistry:
    def __init__(self, config: KitConfig, sandbox: PythonSandbox) -> None:
        self.config = config
        self.sandbox = sandbox
        self.children: list[ChildRuntime] = []

    def bootstrap_sync(self) -> None:
        """Mount builtins and record disabled/pending rows. Proxies connect in bootstrap_async."""
        self.children.clear()
        for group in self.config.groups:
            for spec in group.children:
                rt = ChildRuntime(group_id=group.id, spec=spec)
                if not spec.enabled:
                    rt.status = "disabled"
                    self.children.append(rt)
                    continue
                if spec.transport == "builtin":
                    self._mount_builtin(rt)
                elif spec.transport in {"stdio", "http"}:
                    rt.status = "pending"
                    rt.detail = "connecting…"
                else:
                    rt.status = "error"
                    rt.detail = f"unknown transport {spec.transport}"
                self.children.append(rt)

    async def bootstrap_async(self) -> None:
        """Connect enabled stdio/HTTP children and attach proxied tools."""
        for rt in self.children:
            if not rt.spec.enabled or rt.spec.transport not in {"stdio", "http"}:
                continue
            session = ChildSession(rt.group_id, rt.spec)
            try:
                await session.connect()
            except Exception as exc:  # noqa: BLE001 — surface in hub_list_children
                logger.exception("child connect failed %s__%s", rt.group_id, rt.spec.id)
                rt.status = "error"
                rt.detail = str(exc)[:300]
                continue
            rt.session = session
            rt.tools = session.make_handlers()
            rt.tool_count = len(rt.tools)
            rt.status = "ok"
            rt.detail = ""

    async def aclose(self) -> None:
        for rt in self.children:
            if rt.session is not None:
                await rt.session.close()
                rt.session = None

    def _mount_builtin(self, rt: ChildRuntime) -> None:
        module = rt.spec.module or ""
        prefix = f"{rt.group_id}__{rt.spec.id}"
        if module == "python_sandbox":

            async def write(session_id: str = "default", path: str = "", content: str = "") -> str:
                return self.sandbox.write(session_id, path, content)

            async def read(session_id: str = "default", path: str = "") -> str:
                return self.sandbox.read(session_id, path or None)

            async def reset(session_id: str = "default") -> str:
                return self.sandbox.reset(session_id)

            async def exec_tool(
                session_id: str = "default",
                code: str = "",
                file: str = "",
            ) -> str:
                return await self.sandbox.exec(
                    session_id,
                    code=code or None,
                    file=file or None,
                )

            rt.tools = {
                f"{prefix}__write": write,
                f"{prefix}__read": read,
                f"{prefix}__reset": reset,
                f"{prefix}__exec": exec_tool,
            }
            rt.tool_count = len(rt.tools)
            rt.status = "ok"
        elif module == "hub_run":
            rt.status = "disabled"
            rt.detail = "hub_run disabled by default; enable only with an allowlist"
        else:
            rt.status = "error"
            rt.detail = f"unknown builtin module {module}"

    def list_payload(self) -> list[dict[str, Any]]:
        by_group: dict[str, list[dict[str, Any]]] = {}
        for rt in self.children:
            by_group.setdefault(rt.group_id, []).append(
                {
                    "id": rt.spec.id,
                    "transport": rt.spec.transport,
                    "status": rt.status,
                    "detail": rt.detail,
                    "tool_count": rt.tool_count,
                    "tools": sorted(rt.tools.keys()),
                }
            )
        return [{"id": gid, "children": kids} for gid, kids in by_group.items()]

    def all_tool_handlers(self) -> dict[str, ToolHandler]:
        merged: dict[str, ToolHandler] = {}
        for rt in self.children:
            merged.update(rt.tools)
        return merged
