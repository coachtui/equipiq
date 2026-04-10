"""
Learning system — adjustment engine (offline / controlled).

Converts hypothesis performance metrics into suggested weight adjustments for
admin review. Adjustments are NEVER applied automatically.

Admin must explicitly approve each adjustment via the admin API. Only then does
the multiplier become active at session creation time.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.learning.metrics import HypothesisMetrics

# ── Thresholds ────────────────────────────────────────────────────────────────

HIGH_RESOLUTION = 0.70   # resolution_rate >= this → boost weight
HIGH_REVERSAL   = 0.30   # reversal_rate   >= this → reduce weight
LOW_RATING      = 2.5    # avg_rating      <= this → penalise
MIN_SAMPLES     = 5      # fewer cases → low confidence signal
MIN_CHANGE      = 0.05   # ignore if suggested multiplier is within 5% of base

MULTIPLIER_MIN = 0.50
MULTIPLIER_MAX = 2.00


@dataclass
class WeightAdjustment:
    hypothesis_id: str
    base_weight: float           # current approved multiplier (1.0 = no adjustment)
    suggested_multiplier: float  # what this engine recommends
    confidence: float            # 0.0–1.0 based on sample size
    reason: str


def generate_adjustments(
    metrics: dict[str, HypothesisMetrics],
    current_multipliers: dict[str, float] | None = None,
) -> list[WeightAdjustment]:
    """
    Generate suggested weight adjustments from hypothesis performance metrics.

    Rules:
    - high resolution rate  → increase weight (system's top prediction kept being right)
    - high reversal rate    → decrease weight (system was wrong despite high confidence)
    - low avg rating        → penalise (users weren't satisfied with the diagnosis)
    - low sample size       → low confidence (don't act on thin data)

    Only returns adjustments that differ meaningfully (> MIN_CHANGE) from the
    current approved multiplier. Sorted by confidence descending.
    """
    _base = current_multipliers or {}
    adjustments: list[WeightAdjustment] = []

    for hyp_id, m in metrics.items():
        if m.total_cases < 2:
            continue  # not enough data to signal anything

        base = _base.get(hyp_id, 1.0)
        suggested = 1.0
        reasons: list[str] = []

        # Positive: consistent top-prediction resolution
        if m.resolution_rate >= HIGH_RESOLUTION:
            boost = 1.0 + (m.resolution_rate - 0.5) * 0.4  # +8% at 70%, +20% at 100%
            suggested *= boost
            reasons.append(f"high resolution rate ({m.resolution_rate:.0%})")

        # Negative: frequent wrong predictions
        if m.reversal_rate >= HIGH_REVERSAL:
            penalty = 1.0 - m.reversal_rate * 0.5  # −15% at 30%, −25% at 50%
            suggested *= penalty
            reasons.append(f"high reversal rate ({m.reversal_rate:.0%})")

        # Negative: poor user satisfaction
        if m.avg_rating > 0 and m.avg_rating <= LOW_RATING:
            suggested *= 0.85
            reasons.append(f"low avg rating ({m.avg_rating:.1f}/5)")

        suggested = round(max(MULTIPLIER_MIN, min(MULTIPLIER_MAX, suggested)), 3)

        if abs(suggested - base) < MIN_CHANGE:
            continue

        confidence = round(min(1.0, m.total_cases / MIN_SAMPLES), 3)

        adjustments.append(WeightAdjustment(
            hypothesis_id=hyp_id,
            base_weight=base,
            suggested_multiplier=suggested,
            confidence=confidence,
            reason="; ".join(reasons) if reasons else "statistical drift",
        ))

    return sorted(adjustments, key=lambda a: a.confidence, reverse=True)
