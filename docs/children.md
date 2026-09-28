# Adding child MCPs

Edit `kit.yaml` (start from `kit.example.yaml`).

The hub keeps a **long-lived** session per enabled stdio/HTTP child: tools are listed at startup and proxied as `{group}__{child}__{tool}`.

## Stdio child

```yaml
groups:
  - id: media
    children:
      - id: montage
        transport: stdio
        enabled: true
        command: uvx
        args: ["some-ffmpeg-mcp"]
```

Tools appear as `media__montage__<tool>`.

Official starters often used under **`dev`**:

| id | Example |
|---|---|
| `fs` | `npx -y @modelcontextprotocol/server-filesystem ./workspace/projects` |
| `git` | `uvx mcp-server-git --repository ./workspace/projects` |

Enable them in `kit.yaml` (`enabled: true`) after `npx` / `uvx` work on your machine.

## HTTP child

If a server already speaks Streamable HTTP locally:

```yaml
- id: mobile
  transport: http
  url: http://127.0.0.1:3200/mcp
  token_env: CHILD_MOBILE_TOKEN   # optional; read from kit .env
```

## Builtin

| `module` | Role |
|---|---|
| `python_sandbox` | Sandboxed Python (see [python-sandbox.md](python-sandbox.md)) |
| `hub_run` | Allowlisted shell in workspace — **keep `enabled: false` unless you need it** |

## Failure behavior

If a child fails handshake at startup, the hub **stays up**. `hub_list_children` shows `status: error` and that child’s tools are omitted until restart.

## Ideas (not bundled)

Godot, Blender, Playwright, GitHub, Xcode/mobile — add as stdio/http children when installed on your machine. Do not commit secrets; use `*_TOKEN` env names in `.env` only.
