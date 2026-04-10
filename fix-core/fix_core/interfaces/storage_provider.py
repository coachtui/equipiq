from __future__ import annotations

from typing import Protocol, runtime_checkable

from fix_core.models.context import OwnerContext


@runtime_checkable
class StorageProvider(Protocol):
    """
    Contract for file storage.

    Core never calls StorageProvider directly. Adapters call it to resolve bytes
    before passing them to LLMProvider.analyze_image(), and to obtain URLs for
    client-facing responses. The resulting storage_path is persisted in
    MediaReference.storage_path inside the DiagnosticSession aggregate.

    StorageProvider has no knowledge of sessions or hypotheses — it stores and
    retrieves bytes only. The adapter wires the storage_path into a MediaReference
    and includes it in the session aggregate passed to SessionRepository.save().

    Implementations may be backed by local filesystem, object storage (S3, GCS),
    Supabase Storage, or any other mechanism. The interface is identical.
    """

    async def store(
        self,
        file_bytes: bytes,
        filename: str,
        context: OwnerContext,
    ) -> str:
        """
        Store file_bytes and return an opaque storage_path string.
        The path is meaningful only to this StorageProvider implementation.
        """
        ...

    async def retrieve(self, storage_path: str) -> bytes:
        """Return the raw bytes for a previously stored file."""
        ...

    async def get_url(self, storage_path: str) -> str:
        """
        Return a URL (public or signed/time-limited) for client access.
        The URL lifetime is implementation-defined.
        """
        ...
