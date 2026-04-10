from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.rate_limit import limiter
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def _set_auth_cookies(response: JSONResponse, user_id: str, email: str) -> None:
    secure = settings.environment != "development"
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        path="/api/auth/refresh",
    )


def _clear_auth_cookies(response: JSONResponse) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth/refresh")


@router.post("/register")
@limiter.limit(settings.rate_limit_auth)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    result = await db.execute(
        insert(User)
        .values(email=body.email, password_hash=hash_password(body.password))
        .returning(User.id, User.email)
    )
    await db.commit()
    row = result.one()

    response = JSONResponse({"user": {"id": row.id, "email": row.email}})
    _set_auth_cookies(response, row.id, row.email)
    return response


@router.post("/login")
@limiter.limit(settings.rate_limit_auth)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response = JSONResponse({"user": {"id": user.id, "email": user.email, "is_admin": user.is_admin, "is_operator": user.is_operator}})
    _set_auth_cookies(response, user.id, user.email)
    return response


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    response = JSONResponse({"ok": True})
    _clear_auth_cookies(response)
    return response


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(request: Request) -> JSONResponse:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload["sub"]
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db_session:
        result = await db_session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token(user.id, user.email)
    secure = settings.environment != "development"
    response = JSONResponse({"ok": True})
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return response


@router.get("/me")
async def me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    is_admin = user.is_admin if user else False
    is_operator = user.is_operator if user else False
    return {"user": {"id": current_user.id, "email": current_user.email, "is_admin": is_admin, "is_operator": is_operator}}
