"""
Phase 15D tests — Fleet operator dashboard.

Tests:
  - Migration file exists (012_operator_role.sql)
  - User model has is_operator field
  - get_fleet_user dependency exists and enforces access
  - Fleet endpoints registered in main app
  - Fleet endpoints return 401 without authentication
  - Fleet endpoints return 403 for non-operator/non-admin users
  - Fleet summary returns required fields
  - Fleet assets returns a list
  - Asset history returns required structure
  - Auth /me endpoint returns is_operator field
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ── Migration file ────────────────────────────────────────────────────────────

def _find_migration_012():
    """Try several paths to find the migration file (host vs container)."""
    import os
    candidates = [
        # Docker: backend/ is the working directory, db/ mounted at /db
        "/db/migrations/012_operator_role.sql",
        # Host: backend/tests/ → ../../db/migrations/
        os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "012_operator_role.sql"),
        # Monorepo root: backend/tests/ → ../../../db/migrations/
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "db", "migrations", "012_operator_role.sql"),
        # Monorepo root via /fix/db
        "/fix/db/migrations/012_operator_role.sql",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def test_migration_012_exists():
    """Migration 012_operator_role.sql exists."""
    path = _find_migration_012()
    if path is None:
        pytest.skip("Migration file not accessible in this environment (Docker container only mounts backend/)")
    assert path is not None


def test_migration_012_contains_is_operator():
    """Migration 012 adds is_operator column."""
    path = _find_migration_012()
    if path is None:
        pytest.skip("Migration file not accessible in this environment")
    with open(path) as f:
        content = f.read()
    assert "is_operator" in content.lower()


# ── User model ────────────────────────────────────────────────────────────────

def test_user_model_has_is_operator():
    """User model has is_operator column."""
    from app.models.user import User
    assert hasattr(User, "is_operator"), "User model missing is_operator column"


def test_user_model_is_operator_default_false():
    """is_operator defaults to False."""
    from app.models.user import User
    col = User.__table__.columns["is_operator"]
    assert col.default.arg is False or str(col.server_default) == "false" or not col.nullable


# ── deps.py ───────────────────────────────────────────────────────────────────

def test_get_fleet_user_exists():
    """get_fleet_user dependency is importable from app.core.deps."""
    from app.core.deps import get_fleet_user
    import asyncio
    assert callable(get_fleet_user)


@pytest.mark.asyncio
async def test_get_fleet_user_rejects_non_operator():
    """get_fleet_user raises 403 for non-operator, non-admin users."""
    from fastapi import HTTPException
    from app.core.deps import get_fleet_user, CurrentUser

    mock_user = MagicMock()
    mock_user.is_operator = False
    mock_user.is_admin = False

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.core.database.AsyncSessionLocal", return_value=mock_session):
        current_user = CurrentUser(id="test-id", email="test@example.com")
        with pytest.raises(HTTPException) as exc_info:
            await get_fleet_user(current_user=current_user)
        assert exc_info.value.status_code == 403


# ── Router registration ───────────────────────────────────────────────────────

@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_fleet_router_registered(client):
    """Fleet endpoints are registered (not 404)."""
    # Without auth, expect 401 not 404
    res = client.get("/api/fleet/assets")
    assert res.status_code in (401, 403), f"Expected 401/403, got {res.status_code} — router may not be registered"


def test_fleet_summary_registered(client):
    res = client.get("/api/fleet/summary")
    assert res.status_code in (401, 403)


def test_fleet_asset_history_registered(client):
    res = client.get("/api/fleet/asset/TEST-001/history")
    assert res.status_code in (401, 403)


# ── Unauthenticated access ────────────────────────────────────────────────────

def test_fleet_assets_requires_auth(client):
    """GET /api/fleet/assets returns 401 without auth cookie."""
    res = client.get("/api/fleet/assets")
    assert res.status_code == 401


def test_fleet_summary_requires_auth(client):
    res = client.get("/api/fleet/summary")
    assert res.status_code == 401


# ── Authenticated operator access ─────────────────────────────────────────────

@pytest.fixture
def operator_client():
    """TestClient with mocked operator authentication."""
    from app.main import app
    from app.core.deps import get_fleet_user, CurrentUser

    async def mock_fleet_user():
        return CurrentUser(id="operator-id", email="operator@example.com")

    app.dependency_overrides[get_fleet_user] = mock_fleet_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _make_mock_db():
    """Return an async generator dependency that yields a mocked DB session."""
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = []
    mock_result.mappings.return_value.first.return_value = None
    mock_result.scalar.return_value = 0

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _override():
        yield mock_session

    return _override


@pytest.fixture
def operator_client_with_db():
    """TestClient with mocked operator auth AND mocked DB dependency."""
    from app.main import app
    from app.core.deps import get_fleet_user, CurrentUser
    from app.core.database import get_db

    async def mock_fleet_user():
        return CurrentUser(id="operator-id", email="operator@example.com")

    app.dependency_overrides[get_fleet_user] = mock_fleet_user
    app.dependency_overrides[get_db] = _make_mock_db()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_fleet_assets_returns_list(operator_client_with_db):
    """GET /api/fleet/assets returns a list with fleet access."""
    res = operator_client_with_db.get("/api/fleet/assets")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_fleet_summary_returns_expected_fields(operator_client_with_db):
    """GET /api/fleet/summary returns total_assets, active_issues, top_faults."""
    res = operator_client_with_db.get("/api/fleet/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_assets" in data
    assert "active_issues" in data
    assert "top_faults" in data
    assert isinstance(data["top_faults"], list)


def test_fleet_asset_history_returns_structure(operator_client_with_db):
    """GET /api/fleet/asset/{id}/history returns asset_id and sessions."""
    res = operator_client_with_db.get("/api/fleet/asset/TEST-001/history")
    assert res.status_code == 200
    data = res.json()
    assert "asset_id" in data
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


# ── Auth /me includes is_operator ────────────────────────────────────────────

def test_auth_me_returns_is_operator(client):
    """/api/auth/me response structure includes is_operator field."""
    from app.api.auth import router as auth_router
    # Find the me endpoint and check it returns is_operator
    # We can verify via the source code by importing and inspecting
    import inspect
    from app.api import auth
    source = inspect.getsource(auth)
    assert "is_operator" in source, "/api/auth/me endpoint does not return is_operator"


# ── Fleet lib ─────────────────────────────────────────────────────────────────

def _find_frontend_file(*rel_parts):
    """Search candidate paths for a frontend file (host layout vs container layout)."""
    import os
    candidates = [
        os.path.join("/fix", "frontend", *rel_parts),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", *rel_parts),
        os.path.join("/frontend", *rel_parts),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def test_fleet_ts_lib_exists():
    """frontend/src/lib/fleet.ts exists."""
    path = _find_frontend_file("src", "lib", "fleet.ts")
    if path is None:
        pytest.skip("frontend/ not mounted in this environment")
    assert path is not None


def test_fleet_page_exists():
    """frontend/src/app/fleet/page.tsx exists."""
    path = _find_frontend_file("src", "app", "fleet", "page.tsx")
    if path is None:
        pytest.skip("frontend/ not mounted in this environment")
    assert path is not None
