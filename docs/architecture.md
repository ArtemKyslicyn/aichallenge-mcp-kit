# Architecture

## Roles

| Component | Responsibility |
|---|---|
| **Hub** | Single Streamable HTTP `/mcp`, Bearer auth, aggregates tools |
| **Groups** | Namespaces in `kit.yaml` (`dev`, `media`, …) |
| **Children** | stdio MCP, remote HTTP MCP, or **builtin** modules |
| **Artifacts** | `POST/PUT/GET /artifacts` for binary in/out |
| **AIChallenge** | Guest MCP client only — one connection to this hub |

## Tool naming

```text
hub_*                          → hub built-ins
{group}__{child}__{tool}       → proxied or builtin child
```

Examples:

- `hub_list_children`
- `dev__fs__read_file`
- `dev__python__exec`
- `media__montage__cut`

## Request path

1. Client `tools/list` → hub merges hub tools + every healthy child’s tools (prefixed).
2. Client `tools/call` on `dev__git__git_status` → hub strips prefix → child’s `git_status`.
3. Child writes `workspace/out/clip.mp4` → `hub_workspace_get` or artifact API returns a downloadable id.

## Transports

| `transport` | Meaning |
|---|---|
| `stdio` | Spawn `command` + `args`; MCP over stdio |
| `http` | Forward to `url` (+ optional `token_env`) |
| `builtin` | In-process module (`python_sandbox`, `hub_run`) |

## Workspace layout

```text
workspace/
  projects/          # default filesystem / git root
  sandboxes/{id}/    # Python sandbox sessions
  artifacts/         # binary store for /artifacts
  in/ out/           # optional drop folders for media
```

All paths are resolved under `KIT_WORKSPACE` (default `./workspace`). Traversal outside that root is rejected.
