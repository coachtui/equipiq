import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.dtc import router as dtc_router
from app.api.fleet import router as fleet_router
from app.api.obd import router as obd_router
from app.api.sessions import router as sessions_router
from app.api.telematics import router as telematics_router
from app.core.config import settings
from app.core.database import get_db
from app.core.logging_config import RequestLoggingMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.llm.claude import LLMServiceError

configure_logging()

app = FastAPI(
    title="Fix — AI Engine Diagnostic",
    description="Chat-first AI diagnostic system for engine and drivetrain issues",
    version="0.1.0",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ─────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(LLMServiceError)
async def llm_error_handler(request: Request, exc: LLMServiceError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from app.core.logging_config import get_logger
    get_logger("fix.error").exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(obd_router)
app.include_router(dtc_router)
app.include_router(fleet_router)
app.include_router(admin_router)
app.include_router(telematics_router)

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health(request: Request):
    db_status = "error"
    async for db in get_db():
        try:
            await db.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"
        break

    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "db": db_status, "version": "0.1.0"}
