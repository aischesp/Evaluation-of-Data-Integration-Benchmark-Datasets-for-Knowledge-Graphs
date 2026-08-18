"""Bewertung der Matcher-Vorhersagen gegen das Referenz-Alignment.

Alle Matcher werden auf dem *Test*-Split von Fold 1 bewertet, aus zwei Gründen:
die OpenEA-Autoren berichten auf demselben Split, und die semi-supervised
Matcher sehen den Train-Split als Seeds — auf dem gesamten Alignment zu
bewerten würde sie dafür belohnen, ihre Eingabe zu reproduzieren.

**Auswertungsumfang.** Bewertet werden alle Entitäten, die im Split stehen.
Dazu gehören auch Entitäten *ohne* Partner in KG2 (Alignment-Zeile mit leerem
`e2`, siehe preprocessing/nonmatch.py). Für sie ist jede Vorhersage falsch.
Genau das macht Schwellenwerte messbar: ein Matcher, der immer den besten
Kandidaten ausgibt, sammelt hier False Positives ein, während ein Matcher mit
sinnvollem Threshold sich enthält.

Vorhersagen zu Entitäten *ausserhalb* des Splits werden ignoriert statt als
False Positive gezählt — sonst würde ein unüberwachter Matcher dafür bestraft,
dass er auch auf den Trainingsentitäten richtig liegt.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from kg_quality_eval.core import KGPair
from kg_quality_eval.matching.base import MatchResult


@dataclass
class EvalScores:
    matcher: str
    dataset: str
    split: str
    n_gold: int
    n_unmatched: int
    n_predicted: int
    n_correct: int
    n_false_on_unmatched: int
    precision: float
    recall: float
    f1: float
    hits_at_1: float
    coverage: float
    abstain_rate: float
    runtime_s: float

    def as_dict(self) -> dict:
        return asdict(self)


def evaluate(result: MatchResult, kg_pair: KGPair, split: str = "test") -> EvalScores:
    """Precision / Recall / F1 eines Matchers auf einem Split."""
    scope = kg_pair.alignments if split == "all" else kg_pair.split(split)

    gold_df = scope[scope["e2"].astype(str) != ""]
    gold = set(zip(gold_df["e1"], gold_df["e2"], strict=False))

    universe = set(scope["e1"])                      # inkl. partnerloser Entitäten
    unmatched = set(scope[scope["e2"].astype(str) == ""]["e1"])

    pred_df = result.pairs
    if not pred_df.empty:
        pred_df = pred_df[pred_df["e1"].isin(universe)]
        pred_df = pred_df.sort_values("score", ascending=False).drop_duplicates(subset=["e1"])
    predicted = set(zip(pred_df["e1"], pred_df["e2"], strict=False))

    n_correct = len(predicted & gold)
    n_pred = len(predicted)
    n_gold = len(gold)

    # Vorhersagen für Entitäten, die korrekterweise keinen Partner haben.
    n_false_on_unmatched = sum(1 for e1, _ in predicted if e1 in unmatched)

    precision = n_correct / n_pred if n_pred else 0.0
    recall = n_correct / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return EvalScores(
        matcher=result.matcher,
        dataset=result.dataset,
        split=split,
        n_gold=n_gold,
        n_unmatched=len(unmatched),
        n_predicted=n_pred,
        n_correct=n_correct,
        n_false_on_unmatched=n_false_on_unmatched,
        precision=precision,
        recall=recall,
        f1=f1,
        hits_at_1=n_correct / n_gold if n_gold else 0.0,
        coverage=n_pred / len(universe) if universe else 0.0,
        abstain_rate=1.0 - (n_pred / len(universe)) if universe else 0.0,
        runtime_s=result.runtime_s,
    )


def evaluation_frame(scores: list[EvalScores]) -> pd.DataFrame:
    return pd.DataFrame([s.as_dict() for s in scores])
