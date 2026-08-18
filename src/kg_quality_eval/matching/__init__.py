"""Entity-Alignment-Matcher.

Drei eigenständige Verfahren plus PARIS als Referenz. Die Auswahl folgt dem
Prinzip, dass jedes Verfahren *ein* Signal isoliert nutzt — nur so lässt sich
messen, welche Datensatz-Eigenschaft auf welche Verfahrensart wirkt:

| Matcher                  | Familie    | Signal                          | Seeds | Herkunft   |
| ------------------------ | ---------- | ------------------------------- | ----- | ---------- |
| `value_overlap`          | wertbasiert| exakte Literalwerte, IDF-gewichtet | nein | eigen      |
| `pyjedai_ngram`          | wertbasiert| Zeichen-n-Gramme, Blocking      | nein  | pyJedAI    |
| `structural_propagation` | strukturell| gerichtete, typisierte Nachbarschaft | ja | eigen      |
| `paris`                  | holistisch | Struktur + Literale, iterativ   | nein  | PARIS v0.3 |

PARIS ist selbst bereits ein hybrides Verfahren (es gleicht Entitäten,
Relationen und Klassen gemeinsam ab). Ein zusätzlicher eigener Hybrid-Matcher
wäre daher kein eigenständiger Ansatz, sondern nur eine Linearkombination der
beiden anderen — er wurde deshalb entfernt.
"""

from kg_quality_eval.matching.base import BaseMatcher, MatchResult, SparseScoreMatcher
from kg_quality_eval.matching.evaluate import EvalScores, evaluate, evaluation_frame
from kg_quality_eval.matching.lexical import ValueOverlapMatcher
from kg_quality_eval.matching.paris import ParisMatcher
from kg_quality_eval.matching.record_linkage import PyJedAIMatcher
from kg_quality_eval.matching.structural import StructuralPropagationMatcher

REGISTRY: dict[str, type[BaseMatcher]] = {
    "value_overlap": ValueOverlapMatcher,
    "pyjedai_ngram": PyJedAIMatcher,
    "structural_propagation": StructuralPropagationMatcher,
    "paris": ParisMatcher,
}

ALL_MATCHERS = list(REGISTRY)

__all__ = [
    "ALL_MATCHERS",
    "REGISTRY",
    "BaseMatcher",
    "EvalScores",
    "MatchResult",
    "ParisMatcher",
    "PyJedAIMatcher",
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
