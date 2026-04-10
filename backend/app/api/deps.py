"""
FastAPI dependency providers for M6 adapters.

Usage in route functions:
    repo: PostgresSessionRepository = Depends(get_session_repo)
    llm:  ClaudeProvider            = Depends(get_llm)
    storage: LocalStorageProvider   = Depends(get_storage)
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.session_repository import PostgresSessionRepository
from app.llm.claude_provider import ClaudeProvider
from app.storage.local_provider import LocalStorageProvider

# Module-level singletons for stateless providers
_llm = ClaudeProvider()
_storage = LocalStorageProvider()


def get_session_repo(db: AsyncSession = Depends(get_db)) -> PostgresSessionRepository:
    """Per-request session repository bound to the current DB session."""
    return PostgresSessionRepository(db)


def get_llm() -> ClaudeProvider:
    """Shared ClaudeProvider instance (stateless — safe as singleton)."""
    return _llm


def get_storage() -> LocalStorageProvider:
    """Shared LocalStorageProvider instance (stateless — safe as singleton)."""
    return _storage
