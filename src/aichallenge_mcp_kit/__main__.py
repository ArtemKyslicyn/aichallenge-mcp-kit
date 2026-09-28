"""CLI entry: load env, bootstrap hub, serve HTTP."""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def main() -> None:
    _load_dotenv()
    import uvicorn

    from aichallenge_mcp_kit.config import load_kit_config
    from aichallenge_mcp_kit.http_app import build_app
    from aichallenge_mcp_kit.server import bootstrap

    config = load_kit_config()
    _registry, artifacts = bootstrap(config)
    app = build_app(config, artifacts)

    token = os.environ.get(config.token_env, "")
    if not token:
        raise SystemExit(f"Set {config.token_env} in .env before starting")

    print(
        f"aichallenge-mcp-kit on http://{config.bind_host}:{config.bind_port}/mcp "
        f"(workspace={config.workspace})"
    )
    uvicorn.run(app, host=config.bind_host, port=config.bind_port, log_level="info")


if __name__ == "__main__":
    main()
