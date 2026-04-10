from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token


@dataclass
class CurrentUser:
    id: str
    email: str


async def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return CurrentUser(id=payload["sub"], email=payload["email"])


async def get_admin_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency that verifies the current user has is_admin=True in the DB."""
    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()

    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_fleet_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency that verifies the current user has is_operator=True OR is_admin=True."""
    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()

    if not user or (not user.is_operator and not user.is_admin):
        raise HTTPException(status_code=403, detail="Fleet operator access required")
    return current_user
