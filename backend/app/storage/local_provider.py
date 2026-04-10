"""
LocalStorageProvider — implements fix_core.interfaces.StorageProvider using
the local filesystem (settings.upload_dir).

storage_path format: "{user_id}/{uuid_hex}_{filename}"
This is an opaque string from core's perspective; only this provider resolves it.

Served via FastAPI StaticFiles mount at /uploads/ in app/main.py.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fix_core.models.context import OwnerContext

from app.core.config import settings


class LocalStorageProvider:
    """
    Stores files under settings.upload_dir/{user_id}/{uuid}_{filename}.

    get_url() returns a relative /uploads/... path served by the StaticFiles
    mount. In production, swap for SupabaseStorageProvider or S3Provider
    at the dependency injection layer without changing any call sites.
    """

    def __init__(self) -> None:
        self._base = Path(settings.upload_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _full_path(self, storage_path: str) -> Path:
        return self._base / storage_path

    async def store(
        self,
        file_bytes: bytes,
        filename: str,
        context: OwnerContext,
    ) -> str:
        """Store bytes and return an opaque storage_path."""
        user_dir = self._base / str(context.user_id)
        user_dir.mkdir(exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        rel_path = f"{context.user_id}/{unique_name}"
        (self._base / rel_path).write_bytes(file_bytes)
        return rel_path

    async def retrieve(self, storage_path: str) -> bytes:
        """Return raw bytes for a previously stored file."""
        p = self._full_path(storage_path)
        if not p.exists():
            raise FileNotFoundError(f"Storage path not found: {storage_path}")
        return p.read_bytes()

    async def get_url(self, storage_path: str) -> str:
        """Return a URL path for client access (served by StaticFiles)."""
        return f"/uploads/{storage_path}"
