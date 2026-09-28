"""Smoke tests for config + sandbox path safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from aichallenge_mcp_kit.config import load_kit_config, safe_join
from aichallenge_mcp_kit.sandbox import PythonSandbox


def test_safe_join_blocks_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        safe_join(tmp_path, "../outside")


def test_load_example_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    cfg = load_kit_config(root / "kit.example.yaml")
    assert cfg.groups
    assert any(c.id == "python" for g in cfg.groups for c in g.children)


@pytest.mark.asyncio
async def test_python_exec(tmp_path: Path) -> None:
    sb = PythonSandbox(tmp_path)
    sb.write("default", "hi.py", "print(40+2)\n")
    out = await sb.exec("default", file="hi.py")
    assert "42" in out
