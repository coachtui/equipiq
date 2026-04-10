"""
Prior calibration script.

Reads completed sessions with feedback rating >= 4, aggregates final hypothesis
scores per tree, and diffs them against current tree priors.

Output flags hypotheses where |observed_avg - current_prior| > 0.08
and session count >= 20.

Run from inside the backend container:
  docker compose run --rm backend python scripts/calibrate_priors.py

Or directly with DB access:
  DATABASE_URL=postgresql://... python scripts/calibrate_priors.py
"""
import asyncio
import collections
import os
import sys

# Allow imports from the app package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engine.trees import HYPOTHESES

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fix:fix@db:5432/fixdb")
# SQLAlchemy requires async driver
ASYNC_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

DELTA_THRESHOLD = 0.08
MIN_SESSIONS = 20


async def fetch_data(db: AsyncSession) -> list[dict]:
    """Return rows of (tree_key, hypothesis_key, final_score) for high-rated sessions."""
    rows = await db.execute(text("""
        SELECT
            ds.context->>'tree_key'   AS tree_key,
            sh.hypothesis_key,
            sh.score                  AS final_score
        FROM session_hypotheses sh
        JOIN diagnostic_sessions ds ON ds.id = sh.session_id
        JOIN session_feedback sf ON sf.session_id = sh.session_id
        WHERE sf.rating >= 4
          AND ds.status IN ('awaiting_followup', 'complete')
          AND ds.context->>'tree_key' IS NOT NULL
          AND sh.eliminated = FALSE
    """))
    return [{"tree_key": r[0], "hypothesis_key": r[1], "final_score": float(r[2])} for r in rows.fetchall()]


def aggregate(rows: list[dict]) -> dict[str, dict[str, dict]]:
    """
    Aggregate by (tree_key, hypothesis_key).
    Returns: { tree_key: { hypothesis_key: { sum, count } } }
    """
    agg: dict = collections.defaultdict(lambda: collections.defaultdict(lambda: {"sum": 0.0, "count": 0}))
    for row in rows:
        bucket = agg[row["tree_key"]][row["hypothesis_key"]]
        bucket["sum"] += row["final_score"]
        bucket["count"] += 1
    return agg


def report(agg: dict) -> None:
    printed_any = False
    for tree_key in sorted(agg.keys()):
        if tree_key not in HYPOTHESES:
            continue
        tree_hyps = HYPOTHESES[tree_key]
        tree_agg = agg[tree_key]

        # Session count = max count across hypotheses in this tree (all share same sessions)
        session_count = max((v["count"] for v in tree_agg.values()), default=0)

        rows = []
        for hyp_key, hyp_def in tree_hyps.items():
            if hyp_key not in tree_agg:
                continue
            bucket = tree_agg[hyp_key]
            observed_avg = bucket["sum"] / bucket["count"]
            current_prior = hyp_def["prior"]
            delta = observed_avg - current_prior
            flag = ""
            if abs(delta) > DELTA_THRESHOLD and bucket["count"] >= MIN_SESSIONS:
                flag = "  ← review"
            elif abs(delta) > DELTA_THRESHOLD:
                flag = f"  (only {bucket['count']} sessions)"
            rows.append((hyp_key, current_prior, observed_avg, bucket["count"], delta, flag))

        if not rows:
            continue

        flagged = [r for r in rows if "← review" in r[5]]
        if not flagged and not any(abs(r[4]) > DELTA_THRESHOLD for r in rows):
            continue

        printed_any = True
        print(f"\nTree: {tree_key}  |  sessions with rating ≥ 4: {session_count}")
        print(f"  {'hypothesis':<35} {'current_prior':>13} {'observed_avg':>12} {'sessions':>9} {'delta':>8}")
        print(f"  {'-'*35} {'-'*13} {'-'*12} {'-'*9} {'-'*8}")
        for hyp_key, current_prior, observed_avg, count, delta, flag in sorted(rows, key=lambda r: abs(r[4]), reverse=True):
            print(f"  {hyp_key:<35} {current_prior:>13.2f} {observed_avg:>12.2f} {count:>9} {delta:>+8.2f}{flag}")

    if not printed_any:
        print("\nNo hypotheses exceed the review threshold. Priors look well-calibrated.")
    else:
        print(f"\nThreshold: |delta| > {DELTA_THRESHOLD}, session count >= {MIN_SESSIONS}")
        print("'← review' flags are suggestions only. Review and adjust tree priors manually.")


async def main() -> None:
    engine = create_async_engine(ASYNC_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        rows = await fetch_data(db)

    await engine.dispose()

    if not rows:
        print("No qualifying sessions found (need completed sessions with rating >= 4).")
        return

    agg = aggregate(rows)
    report(agg)


if __name__ == "__main__":
    asyncio.run(main())
