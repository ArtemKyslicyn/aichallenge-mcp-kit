"""Load kit.yaml and resolve workspace paths."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ChildSpec:
    id: str
    transport: str
    enabled: bool = True
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    token_env: str | None = None
    module: str | None = None


@dataclass
class GroupSpec:
    id: str
    children: list[ChildSpec]


@dataclass
class KitConfig:
    workspace: Path
    bind_host: str
    bind_port: int
    token_env: str
    groups: list[GroupSpec]

    def enabled_children(self) -> list[tuple[str, ChildSpec]]:
        out: list[tuple[str, ChildSpec]] = []
        for group in self.groups:
            for child in group.children:
                if child.enabled:
                    out.append((group.id, child))
        return out


def _parse_bind(raw: str, default_host: str, default_port: int) -> tuple[str, int]:
    raw = (raw or "").strip()
    if not raw:
        return default_host, default_port
    if ":" in raw:
        host, _, port_s = raw.rpartition(":")
        return host or default_host, int(port_s)
    return raw, default_port


def load_kit_config(path: Path | None = None) -> KitConfig:
    config_path = path or Path(os.environ.get("KIT_CONFIG", "kit.yaml"))
    if not config_path.is_file():
        example = Path("kit.example.yaml")
        if example.is_file():
            config_path = example
        else:
            raise FileNotFoundError(f"kit config not found: {config_path}")

    data: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    default_host = os.environ.get("KIT_BIND", "127.0.0.1")
    default_port = int(os.environ.get("KIT_PORT", "3100"))
    host, port = _parse_bind(str(data.get("bind", "")), default_host, default_port)

    workspace = Path(os.environ.get("KIT_WORKSPACE") or data.get("workspace") or "./workspace")
    workspace = workspace.resolve()

    groups: list[GroupSpec] = []
    for g in data.get("groups") or []:
        children: list[ChildSpec] = []
        for c in g.get("children") or []:
            children.append(
                ChildSpec(
                    id=str(c["id"]),
                    transport=str(c.get("transport", "stdio")),
                    enabled=bool(c.get("enabled", True)),
                    command=c.get("command"),
                    args=list(c.get("args") or []),
                    url=c.get("url"),
                    token_env=c.get("token_env"),
                    module=c.get("module"),
                )
            )
        groups.append(GroupSpec(id=str(g["id"]), children=children))

    return KitConfig(
        workspace=workspace,
        bind_host=host,
        bind_port=port,
        token_env=str(data.get("token_env") or "KIT_SHARED_TOKEN"),
        groups=groups,
    )


def ensure_workspace(root: Path) -> None:
    for sub in ("projects", "sandboxes", "artifacts", "in", "out"):
        (root / sub).mkdir(parents=True, exist_ok=True)


def safe_join(root: Path, relative: str) -> Path:
    """Resolve relative path under root; raise ValueError on escape."""
    rel = relative.replace("\\", "/").lstrip("/")
    if ".." in Path(rel).parts:
        raise ValueError("path escapes workspace")
    target = (root / rel).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ValueError("path escapes workspace")
    return target
