# Security

## Threat model (short)

The kit turns your computer into a remote tool host. Anyone who learns **tunnel URL + Bearer** can call every enabled tool: read/write workspace files, run sandboxed Python, invoke child MCPs (montage, git, …).

Treat the token like a password. Rotate if the tunnel URL leaked in a screenshot or chat log.

## Hardening checklist

- [ ] `KIT_SHARED_TOKEN` is long and random (not `changeme`)
- [ ] Process binds `127.0.0.1` only (default)
- [ ] Tunnel is the only public surface
- [ ] `hub_run` / shell child stays disabled unless you accept command execution risk
- [ ] Python sandbox network stays off unless required
- [ ] Child tokens live in `.env`, never in `kit.yaml` committed to git
- [ ] Workspace does not symlink to `$HOME` or secrets dirs

## What is protected in v1

- Path checks under `KIT_WORKSPACE`
- Bearer on `/mcp` and `/artifacts` (except `/health`)
- Sandbox timeout and output size caps
- No real secrets in the public git tree (`.env.example` placeholders only)

## What is not a full VM

v1 Python isolation is subprocess-based unless you enable Docker/bwrap. Do not expose the kit on a shared host you do not trust. Prefer a dedicated workspace directory.

## Reporting

Prefer private disclosure to the repo owner for security issues in the hub itself.
