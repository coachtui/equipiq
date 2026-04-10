# M4: thin re-export — implementation lives in fix_core
# The individual tree files in this directory are superseded; fix_core.trees is the
# single source of truth for all 91 trees.
from fix_core.trees import *  # noqa: F401, F403  (large re-export of ~400 tree constants)
from fix_core.trees import (
    TREES, HYPOTHESES, CONTEXT_PRIORS, POST_DIAGNOSIS, resolve_tree_key,
    _HE_SUBTYPES,  # underscore names are not exported by *; import explicitly
)

__all__ = ["TREES", "HYPOTHESES", "CONTEXT_PRIORS", "POST_DIAGNOSIS", "resolve_tree_key", "_HE_SUBTYPES"]
