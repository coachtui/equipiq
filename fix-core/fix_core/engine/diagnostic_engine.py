"""
Diagnostic engine — manages tree traversal and session state.

Responsibilities:
- Given a session, determine the next question node.
- Given a user answer, classify it to an option and apply score deltas.
- Determine when to exit early or when the tree is exhausted.
- Does NOT call the LLM — LLM is handled in the API layer.
"""
from __future__ import annotations

from fix_core.engine.hypothesis_scorer import HypothesisScorer
from fix_core.trees import TREES, HYPOTHESES


class DiagnosticEngine:
    def __init__(self, tree_key: str) -> None:
        if tree_key not in TREES:
            raise ValueError(f"No diagnostic tree for key: {tree_key}")
        self.tree_key = tree_key
        self.tree = TREES[tree_key]
        self.hypotheses_def = HYPOTHESES[tree_key]

    # ─────────────────────────────────────────────────────────────────────────
    # State helpers
    # ─────────────────────────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> dict | None:
        return self.tree.get(node_id)

    def first_node(self) -> str:
        return "start"

    def option_labels(self, node_id: str) -> list[str]:
        """Return user-facing option labels for a node."""
        node = self.get_node(node_id)
        if not node:
            return []
        return [opt["label"] for opt in node["options"]]

    # ─────────────────────────────────────────────────────────────────────────
    # Answer classification — match user free-text to closest option
    # This is a simple keyword/fuzzy match; LLM-based classification is done
    # at the API layer for the natural-language intake.
    # ─────────────────────────────────────────────────────────────────────────

    def classify_answer(self, node_id: str, answer_text: str, matched_option_key: str | None = None) -> dict | None:
        """
        Return the matching option dict for the given answer.
        matched_option_key: if the LLM already resolved this, use it directly.
        Otherwise fall back to index-based matching.
        """
        node = self.get_node(node_id)
        if not node:
            return None

        options = node["options"]

        # Direct key match (LLM provides this)
        if matched_option_key:
            for opt in options:
                if opt["match"] == matched_option_key:
                    return opt

        # Fallback: try to match by index if answer_text is a digit
        answer_stripped = answer_text.strip()
        if answer_stripped.isdigit():
            idx = int(answer_stripped) - 1
            if 0 <= idx < len(options):
                return options[idx]

        # Last resort: return first option (should not normally happen)
        return options[0] if options else None

    # ─────────────────────────────────────────────────────────────────────────
    # Progress
    # ─────────────────────────────────────────────────────────────────────────

    def advance(
        self,
        current_node_id: str,
        matched_option_key: str,
        answer_text: str,
        scorer: HypothesisScorer,
    ) -> tuple[str | None, bool]:
        """
        Apply the answer, update scores, and return (next_node_id, should_stop).
        should_stop is True if the tree is exhausted or early-exit triggered.
        """
        node = self.get_node(current_node_id)
        if not node:
            return None, True

        option = self.classify_answer(current_node_id, answer_text, matched_option_key)
        if not option:
            return None, True

        scorer.apply_option(option, node["question"], option["label"])

        next_node = option.get("next_node")
        if next_node is None:
            return None, True

        # Check early exit after applying scores
        if scorer.should_exit_early():
            return None, True

        # Check if next node exists
        if next_node not in self.tree:
            return None, True

        return next_node, False
