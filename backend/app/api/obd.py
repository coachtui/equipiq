"""
OBD / DTC code lookup — stateless endpoint.

POST /api/obd/lookup  — look up a diagnostic trouble code
No session is created; no DB row is written.
"""
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings
from app.core.rate_limit import limiter
from app.llm.claude import lookup_obd_code

router = APIRouter(prefix="/api/obd", tags=["obd"])

_DTC_RE = re.compile(r"^[PBCU]\d{4}$")


class VehicleInput(BaseModel):
    year: int | None = None
    make: str | None = None
    model: str | None = None
    engine: str | None = None


class OBDLookupRequest(BaseModel):
    code: str
    vehicle: VehicleInput | None = None


class OBDLookupResponse(BaseModel):
    code: str
    description: str
    severity: str
    likely_causes: list[str]
    next_steps: list[str]
    diy_difficulty: str


@router.post("/lookup", response_model=OBDLookupResponse)
@limiter.limit(settings.rate_limit_obd_lookup)
async def lookup_obd(request: Request, req: OBDLookupRequest):
    """Look up a DTC/OBD-II fault code and return a plain-English explanation."""
    code = req.code.strip().upper()
    if not _DTC_RE.match(code):
        raise HTTPException(400, "Invalid DTC format. Expected a code like P0420, B1234, C0035, or U0100.")

    vehicle_parts = []
    if req.vehicle:
        for val in [req.vehicle.year, req.vehicle.make, req.vehicle.model, req.vehicle.engine]:
            if val:
                vehicle_parts.append(str(val))
    vehicle_context = " ".join(vehicle_parts) if vehicle_parts else "Unknown vehicle"

    result = lookup_obd_code(code, vehicle_context)
    return OBDLookupResponse(**result)
