# Adding child MCPs

Edit `kit.yaml` (start from `kit.example.yaml`).

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
| `python_sandbox` | Sandboxed Python (see python-sandbox.md) |
| `hub_run` | Allowlisted shell in workspace — **keep `enabled: false` unless you need it** |

## v0.1 note

Builtin `python_sandbox` tools are live. Stdio/HTTP entries appear in `hub_list_children` with `status: pending` when enabled; full tool proxy is the next release. Prefer HTTP children that already expose `/mcp` if you need them today.

## Failure behavior

If a child fails handshake at startup, the hub **stays up**. `hub_list_children` shows `status: error` and that child’s tools are omitted until restart (or reload, when implemented).

## Ideas (not bundled)

Godot, Blender, Playwright, GitHub, Xcode/mobile — add as stdio/http children when installed on your machine. Do not commit secrets for those children; use `*_TOKEN` env names in `.env` only.
