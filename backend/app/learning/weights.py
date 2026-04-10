"""
Learning system — approved weight multiplier store.

Loads admin-approved multipliers from approved_weight_adjustments.
Applied to hypothesis priors at session creation time only.
Default multiplier = 1.0 (no effect).

RULES:
- Never apply unapproved adjustments.
- Scoring remains deterministic — same session always produces same result.
- Multipliers are applied to the prior at session init, then baked into DB scores.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import ApprovedWeightAdjustment


async def get_approved_multipliers(db: AsyncSession) -> dict[str, float]:
    """
    Returns {hypothesis_id: multiplier} for all admin-approved adjustments.
    If no adjustment exists for a hypothesis, it defaults to 1.0 at call sites.
    """
    result = await db.execute(select(ApprovedWeightAdjustment))
    return {row.hypothesis_id: row.multiplier for row in result.scalars().all()}
