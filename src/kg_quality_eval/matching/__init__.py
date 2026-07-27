"""Entity-alignment matchers.

Five approaches spanning the signal types that a benchmark can (or cannot)
provide, so that the profiling metrics have something to correlate with:

| Matcher                  | Family     | Signal used            | Seeds |
| ------------------------ | ---------- | ---------------------- | ----- |
| `literal_tfidf`          | textual    | literal tokens         | no    |
| `value_overlap`          | textual    | whole literal values   | no    |
| `structural_propagation` | structural | relation neighbourhood | yes   |
| `hybrid`                 | hybrid     | both                   | yes   |
| `paris`                  | holistic   | both (external tool)   | no    |
"""

from kg_quality_eval.matching.base import BaseMatcher, MatchResult, SparseScoreMatcher
from kg_quality_eval.matching.evaluate import EvalScores, evaluate, evaluation_frame
from kg_quality_eval.matching.lexical import LiteralTFIDFMatcher, ValueOverlapMatcher
from kg_quality_eval.matching.paris import ParisMatcher
from kg_quality_eval.matching.structural import HybridMatcher, StructuralPropagationMatcher

REGISTRY: dict[str, type[BaseMatcher]] = {
    "literal_tfidf": LiteralTFIDFMatcher,
    "value_overlap": ValueOverlapMatcher,
    "structural_propagation": StructuralPropagationMatcher,
    "hybrid": HybridMatcher,
    "paris": ParisMatcher,
}

ALL_MATCHERS = list(REGISTRY)

__all__ = [
    "ALL_MATCHERS",
    "REGISTRY",
    "BaseMatcher",
    "EvalScores",
    "HybridMatcher",
    "LiteralTFIDFMatcher",
    "MatchResult",
    "ParisMatcher",
    "SparseScoreMatcher",
    "StructuralPropagationMatcher",
    "ValueOverlapMatcher",
    "evaluate",
    "evaluation_frame",
    "get_matcher",
]


def get_matcher(name: str, **kwargs) -> BaseMatcher:
    if name not in REGISTRY:
        raise ValueError(f"Unknown matcher: {name!r}. Available: {ALL_MATCHERS}")
    return REGISTRY[name](**kwargs)
