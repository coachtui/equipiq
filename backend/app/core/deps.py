from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token


@dataclass
class CurrentUser:
    id: str
    email: str
    partner_id:     Optional[str] = None
    partner_org_id: Optional[str] = None


async def _resolve_partner_user(request: Request) -> Optional[CurrentUser]:
    """If the request carries valid partner-auth headers, return the resolved
    CurrentUser, auto-creating the user record on first sight. Returns None if
    no partner key is present (caller should fall through to cookie auth).

    Headers:
      X-Partner-Key       — secret, must match settings.partner_api_keys
      X-Partner-User-Id   — required, the user's ID in the partner platform
      X-Partner-User-Email — optional display email
      X-Partner-Org-Id    — optional, partner's tenant scope
    """
    partner_key = request.headers.get("X-Partner-Key")
    if not partner_key:
        return None

    partner_id = settings.partner_keys_map.get(partner_key)
    if not partner_id:
        raise HTTPException(status_code=401, detail="Invalid partner key")

    external_user_id = request.headers.get("X-Partner-User-Id")
    if not external_user_id:
        raise HTTPException(status_code=400, detail="X-Partner-User-Id required")

    external_email = request.headers.get("X-Partner-User-Email")
    external_org_id = request.headers.get("X-Partner-Org-Id")

    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.partner_id == partner_id,
                User.partner_user_id == external_user_id,
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            synthetic_email = external_email or f"{external_user_id}@{partner_id}.partner.local"

            # If a native Fix user already exists with this email (e.g. they signed
            # up directly before partner integration was wired), link the partner
            # identity to that account instead of inserting a duplicate row —
            # otherwise the unique email constraint blows up with a 500.
            existing_by_email = await db.execute(
                select(User).where(User.email == synthetic_email)
            )
            existing = existing_by_email.scalar_one_or_none()

            if existing is not None:
                existing.partner_id = partner_id
                existing.partner_user_id = external_user_id
                if external_org_id:
                    existing.partner_org_id = external_org_id
                await db.commit()
                await db.refresh(existing)
                user = existing
            else:
                user = User(
                    email=synthetic_email,
                    password_hash=None,
                    partner_id=partner_id,
                    partner_user_id=external_user_id,
                    partner_org_id=external_org_id,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
        elif external_org_id and user.partner_org_id != external_org_id:
            # Org may have changed — keep it in sync
            user.partner_org_id = external_org_id
            await db.commit()

        return CurrentUser(
            id=user.id,
            email=user.email,
            partner_id=user.partner_id,
            partner_org_id=user.partner_org_id,
        )


async def get_current_user(request: Request) -> CurrentUser:
    # Partner auth first — trusted external platforms (BedrockOS, etc.)
    partner_user = await _resolve_partner_user(request)
    if partner_user is not None:
        return partner_user

    # Fall back to Fix's native cookie/JWT auth
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
