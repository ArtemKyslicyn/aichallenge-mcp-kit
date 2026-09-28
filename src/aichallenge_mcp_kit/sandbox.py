"""In-process Python sandbox under workspace/sandboxes/{session}/."""

from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from pathlib import Path

from aichallenge_mcp_kit.config import safe_join


class PythonSandbox:
    def __init__(self, workspace: Path) -> None:
        self._root = workspace / "sandboxes"
        self._root.mkdir(parents=True, exist_ok=True)
        self._last_output: dict[str, str] = {}

    def _session_dir(self, session_id: str) -> Path:
        sid = session_id.strip() or "default"
        if "/" in sid or ".." in sid or "\\" in sid:
            raise ValueError("invalid session_id")
        path = self._root / sid
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write(self, session_id: str, relative_path: str, content: str) -> str:
        base = self._session_dir(session_id)
        target = safe_join(base, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {target.relative_to(base)}"

    def read(self, session_id: str, relative_path: str | None = None) -> str:
        if relative_path:
            base = self._session_dir(session_id)
            target = safe_join(base, relative_path)
            return target.read_text(encoding="utf-8")
        return self._last_output.get(session_id or "default", "")

    def reset(self, session_id: str) -> str:
        base = self._session_dir(session_id)
        shutil.rmtree(base, ignore_errors=True)
        self._last_output.pop(session_id or "default", None)
        self._session_dir(session_id)
        return "reset ok"

    async def exec(
        self,
        session_id: str,
        *,
        code: str | None = None,
        file: str | None = None,
    ) -> str:
        base = self._session_dir(session_id)
        timeout = float(os.environ.get("SANDBOX_TIMEOUT_SEC", "30"))
        max_out = int(os.environ.get("SANDBOX_MAX_OUTPUT_BYTES", "1048576"))
        network = os.environ.get("SANDBOX_NETWORK", "false").lower() in {"1", "true", "yes"}

        if code and file:
            raise ValueError("pass code or file, not both")
        if not code and not file:
            raise ValueError("pass code or file")

        if file:
            script = safe_join(base, file)
            argv = ["python", str(script)]
        else:
            name = f"_snippet_{uuid.uuid4().hex[:8]}.py"
            script = base / name
            script.write_text(code or "", encoding="utf-8")
            argv = ["python", str(script)]

        env = os.environ.copy()
        # Scrub kit secrets from child env
        for key in list(env):
            if key.endswith("_TOKEN") or key.endswith("_KEY") or "SECRET" in key:
                env.pop(key, None)
        if not network:
            env["PYTHONNOUSERSITE"] = "1"

        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(base),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            msg = f"timeout after {timeout}s"
            self._last_output[session_id or "default"] = msg
            return msg

        out = (stdout_b or b"").decode("utf-8", errors="replace")
        err = (stderr_b or b"").decode("utf-8", errors="replace")
        combined = f"exit={proc.returncode}\n--- stdout ---\n{out}\n--- stderr ---\n{err}"
        if len(combined.encode("utf-8")) > max_out:
            combined = combined.encode("utf-8")[:max_out].decode("utf-8", errors="replace") + "\n…truncated"
        self._last_output[session_id or "default"] = combined
        return combined
