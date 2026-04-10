"""
Heavy equipment DTC / fault code lookup — stateless endpoint.

POST /api/dtc/lookup  — look up a manufacturer fault code
No session is created; no DB row is written.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings
from app.core.rate_limit import limiter
from app.llm.claude import lookup_he_dtc

router = APIRouter(prefix="/api/dtc", tags=["dtc"])

_SUPPORTED_MANUFACTURERS = {
    "cat", "caterpillar",
    "deere", "john deere", "johndeere",
    "komatsu",
    "kubota",
    "volvo", "volvo ce",
    "case", "cnh",
    "doosan", "bobcat",
    "liebherr",
    "hitachi",
    "other",
}


class HEEquipmentInput(BaseModel):
    model: str | None = None
    hours: int | None = None
    engine: str | None = None


class HEDTCLookupRequest(BaseModel):
    code: str
    manufacturer: str
    equipment: HEEquipmentInput | None = None


class HEDTCLookupResponse(BaseModel):
    code: str
    manufacturer: str
    description: str
    severity: str
    likely_causes: list[str]
    isolation_steps: list[str]
    part_numbers: list[str]
    service_reference: str | None


@router.post("/lookup", response_model=HEDTCLookupResponse)
@limiter.limit(settings.rate_limit_dtc_lookup)
async def lookup_dtc(request: Request, req: HEDTCLookupRequest):
    """Look up a heavy equipment manufacturer fault code and return professional technical guidance."""
    code = req.code.strip().upper()
    if not code:
        raise HTTPException(400, "Fault code cannot be empty.")

    manufacturer = req.manufacturer.strip()
    if not manufacturer:
        raise HTTPException(400, "Manufacturer is required.")
    if manufacturer.lower() not in _SUPPORTED_MANUFACTURERS:
        # Accept unknown manufacturers — LLM handles best-effort; just sanitize
        manufacturer = manufacturer[:60]

    equipment_parts = []
    if req.equipment:
        if req.equipment.model:
            equipment_parts.append(req.equipment.model)
        if req.equipment.hours is not None:
            equipment_parts.append(f"{req.equipment.hours} hours")
        if req.equipment.engine:
            equipment_parts.append(req.equipment.engine)
    equipment_context = ", ".join(equipment_parts) if equipment_parts else "Unknown model"

    result = lookup_he_dtc(code, manufacturer, equipment_context)
    return HEDTCLookupResponse(**result)
