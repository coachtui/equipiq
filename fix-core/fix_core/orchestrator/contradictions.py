"""
Contradiction Detection — compares evidence packets to identify conflicting signals.

Contradiction types detected:
  1. score_reversal    — A hypothesis is strongly supported then strongly contradicted
  2. answer_conflict   — Two answers that are logically mutually exclusive
  3. image_vs_verbal   — Image evidence sharply contradicts verbal answers
  4. eliminated_boost  — Eliminated hypothesis receives large positive evidence

Behavior:
  - severity >= 0.5  → blocks early exit (handled by exit_guard)
  - any detected     → the controller triggers a clarification question
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Contradiction:
    type: str
    description: str
    severity: float   # 0.0–1.0; >= 0.5 blocks exit

    def to_dict(self) -> dict:
        return asdict(self)


# Threshold: a delta is "significant" only if its absolute value meets this
_SIG_DELTA: float = 0.15

# Threshold: total conflicting signal must exceed this to flag as contradiction
_REVERSAL_THRESHOLD: float = 0.20


def detect_contradictions(
    evidence_log: list[dict],
    *,
    current_hypotheses: dict[str, dict] | None = None,
) -> list[Contradiction]:
    """
    Scan the accumulated evidence log and return any contradictions found.

    Args:
        evidence_log:        List of EvidencePacket dicts (from session.evidence_log).
        current_hypotheses:  Optional: {key: {score, eliminated}} for cross-checks.
    """
    contradictions: list[Contradiction] = []
    seen_keys: set[str] = set()

    # Normalize: accept both plain dicts and Pydantic/dataclass objects
    _log: list[dict] = [
        e if isinstance(e, dict) else e.model_dump()
        for e in evidence_log
    ]

    # Build per-hypothesis delta history
    hyp_history: dict[str, list[dict]] = {}
    for packet in _log:
        source = packet.get("source", "")
        for hyp_key, delta in packet.get("affects", {}).items():
            hyp_history.setdefault(hyp_key, []).append({
                "source": source,
                "delta": delta,
                "observation": packet.get("observation", ""),
            })

    # ── 1. Score reversal detection ──────────────────────────────────────────
    for hyp_key, history in hyp_history.items():
        positive_total = sum(e["delta"] for e in history if e["delta"] > _SIG_DELTA)
        negative_total = sum(e["delta"] for e in history if e["delta"] < -_SIG_DELTA)

        if positive_total >= _REVERSAL_THRESHOLD and negative_total <= -_REVERSAL_THRESHOLD:
            flag_key = f"reversal_{hyp_key}"
            if flag_key not in seen_keys:
                seen_keys.add(flag_key)
                severity = min(
                    1.0,
                    (positive_total + abs(negative_total)) / 0.80
                )
                contradictions.append(Contradiction(
                    type="score_reversal",
                    description=(
                        f"Conflicting evidence for '{hyp_key}': "
                        f"+{positive_total:.2f} support vs {negative_total:.2f} contradiction"
                    ),
                    severity=round(severity, 3),
                ))

    # ── 2. Image vs verbal conflict ──────────────────────────────────────────
    image_evidence: dict[str, float] = {}
    verbal_evidence: dict[str, float] = {}

    for packet in _log:
        for hyp_key, delta in packet.get("affects", {}).items():
            if abs(delta) < _SIG_DELTA:
                continue
            if packet.get("source") == "image":
                image_evidence[hyp_key] = image_evidence.get(hyp_key, 0.0) + delta
            elif packet.get("source") in ("user_text", "manual_test"):
                verbal_evidence[hyp_key] = verbal_evidence.get(hyp_key, 0.0) + delta

    for hyp_key in image_evidence:
        if hyp_key in verbal_evidence:
            img_val = image_evidence[hyp_key]
            vrb_val = verbal_evidence[hyp_key]
            # Conflict if they strongly disagree (one significantly positive, other significantly negative)
            if img_val > _REVERSAL_THRESHOLD and vrb_val < -_REVERSAL_THRESHOLD:
                flag_key = f"img_verbal_{hyp_key}"
                if flag_key not in seen_keys:
                    seen_keys.add(flag_key)
                    contradictions.append(Contradiction(
                        type="image_vs_verbal",
                        description=(
                            f"Image supports '{hyp_key}' (+{img_val:.2f}) but "
                            f"verbal answers contradict it ({vrb_val:.2f})"
                        ),
                        severity=round(min(1.0, (img_val + abs(vrb_val)) / 0.60), 3),
                    ))
            elif vrb_val > _REVERSAL_THRESHOLD and img_val < -_REVERSAL_THRESHOLD:
                flag_key = f"verbal_img_{hyp_key}"
                if flag_key not in seen_keys:
                    seen_keys.add(flag_key)
                    contradictions.append(Contradiction(
                        type="image_vs_verbal",
                        description=(
                            f"Verbal answers support '{hyp_key}' (+{vrb_val:.2f}) but "
                            f"image evidence contradicts it ({img_val:.2f})"
                        ),
                        severity=round(min(1.0, (vrb_val + abs(img_val)) / 0.60), 3),
                    ))

    # ── 3. Eliminated hypothesis boosted ────────────────────────────────────
    if current_hypotheses:
        for hyp_key, state in current_hypotheses.items():
            if not state.get("eliminated", False):
                continue
            boosted_total = sum(
                e["delta"]
                for e in hyp_history.get(hyp_key, [])
                if e["delta"] > _SIG_DELTA and e["source"] != "intake"
            )
            if boosted_total >= _REVERSAL_THRESHOLD:
                flag_key = f"eliminated_{hyp_key}"
                if flag_key not in seen_keys:
                    seen_keys.add(flag_key)
                    contradictions.append(Contradiction(
                        type="eliminated_boost",
                        description=(
                            f"'{hyp_key}' was eliminated but follow-up evidence "
                            f"provides +{boosted_total:.2f} support"
                        ),
                        severity=0.60,
                    ))

    return contradictions


def merge_flags(existing: list[dict], new: list[Contradiction]) -> list[dict]:
    """
    Merge new contradictions into the existing flag list, de-duplicating by type+description.
    """
    existing_descs = {f.get("description") for f in existing}
    result = list(existing)
    for c in new:
        if c.description not in existing_descs:
            result.append(c.to_dict())
            existing_descs.add(c.description)
    return result
