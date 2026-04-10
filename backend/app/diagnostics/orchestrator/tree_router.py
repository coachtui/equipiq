# M4: thin re-export — implementation lives in fix_core
from fix_core.orchestrator.tree_router import (
    TreeCandidate,
    rank_candidate_trees,
    should_use_discriminator,
    combine_candidates,
)

__all__ = ["TreeCandidate", "rank_candidate_trees", "should_use_discriminator", "combine_candidates"]
