"""Binary artifact store under workspace/artifacts."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response


class ArtifactStore:
    def __init__(self, workspace: Path) -> None:
        self._root = workspace / "artifacts"
        self._root.mkdir(parents=True, exist_ok=True)
        self._meta: dict[str, dict[str, float | str]] = {}

    @property
    def max_bytes(self) -> int:
        return int(os.environ.get("ARTIFACT_MAX_BYTES", str(500 * 1024 * 1024)))

    @property
    def ttl_sec(self) -> int:
        return int(os.environ.get("ARTIFACT_TTL_SEC", "86400"))

    def create(self) -> dict[str, str]:
        artifact_id = uuid.uuid4().hex
        self._meta[artifact_id] = {
            "created": time.time(),
            "path": str(self._root / artifact_id),
        }
        return {
            "id": artifact_id,
            "upload_url": f"/artifacts/{artifact_id}",
            "download_url": f"/artifacts/{artifact_id}",
            "expires_at": str(int(time.time()) + self.ttl_sec),
        }

    def path_for(self, artifact_id: str) -> Path:
        if not artifact_id.isalnum() or len(artifact_id) > 64:
            raise ValueError("invalid artifact id")
        return self._root / artifact_id

    async def put(self, artifact_id: str, body: bytes) -> None:
        if len(body) > self.max_bytes:
            raise ValueError("artifact too large")
        path = self.path_for(artifact_id)
        path.write_bytes(body)
        self._meta[artifact_id] = {"created": time.time(), "path": str(path)}

    def get_path(self, artifact_id: str) -> Path | None:
        path = self.path_for(artifact_id)
        if not path.is_file():
            return None
        meta = self._meta.get(artifact_id)
        created = float(meta["created"]) if meta else path.stat().st_mtime
        if time.time() - created > self.ttl_sec:
            path.unlink(missing_ok=True)
            self._meta.pop(artifact_id, None)
            return None
        return path


def mount_artifact_routes(app, store: ArtifactStore) -> None:  # type: ignore[no-untyped-def]
    async def create_artifact(_request: Request) -> JSONResponse:
        return JSONResponse(store.create())

    async def put_artifact(request: Request) -> Response:
        artifact_id = request.path_params["artifact_id"]
        body = await request.body()
        try:
            await store.put(artifact_id, body)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"ok": True, "id": artifact_id, "bytes": len(body)})

    async def get_artifact(request: Request) -> Response:
        artifact_id = request.path_params["artifact_id"]
        path = store.get_path(artifact_id)
        if path is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return FileResponse(path, filename=artifact_id)

    app.add_route("/artifacts", create_artifact, methods=["POST"])
    app.add_route("/artifacts/{artifact_id}", put_artifact, methods=["PUT"])
    app.add_route("/artifacts/{artifact_id}", get_artifact, methods=["GET"])
