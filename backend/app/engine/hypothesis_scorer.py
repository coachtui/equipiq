# M4: thin re-export — implementation lives in fix_core
from fix_core.engine.hypothesis_scorer import Hypothesis, HypothesisScorer

__all__ = ["Hypothesis", "HypothesisScorer"]
