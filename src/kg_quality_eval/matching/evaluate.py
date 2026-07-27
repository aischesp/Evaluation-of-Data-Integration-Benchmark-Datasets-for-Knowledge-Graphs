"""Evaluation of matcher predictions against the reference alignment.

All matchers are scored on the *test* split of fold 1, for two reasons:

* it is the split the OpenEA authors themselves report on, so our numbers stay
  comparable to the published ones, and
* the semi-supervised matchers see the train split as seeds, so evaluating on
  the full reference alignment would reward them for reproducing their input.

Predictions about entities outside the evaluation universe (the left-hand
entities of the test split) are ignored rather than counted as false positives
— otherwise an unsupervised matcher would be punished for also producing
correct predictions on the training entities.
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
    n_predicted: int
    n_correct: int
    precision: float
    recall: float
    f1: float
    hits_at_1: float
    coverage: float
    runtime_s: float

    def as_dict(self) -> dict:
        return asdict(self)


def evaluate(
    result: MatchResult, kg_pair: KGPair, split: str = "test"
) -> EvalScores:
    """Precision / recall / F1 of one matcher on one split."""
    gold_df = kg_pair.split(split) if split != "all" else kg_pair.alignments
    gold = set(zip(gold_df["e1"], gold_df["e2"], strict=False))
    universe = set(gold_df["e1"])

    pred_df = result.pairs
    if not pred_df.empty:
        pred_df = pred_df[pred_df["e1"].isin(universe)]
        pred_df = (
            pred_df.sort_values("score", ascending=False)
            .drop_duplicates(subset=["e1"])
        )
    predicted = set(zip(pred_df["e1"], pred_df["e2"], strict=False))

    n_correct = len(predicted & gold)
    n_pred = len(predicted)
    n_gold = len(gold)

    precision = n_correct / n_pred if n_pred else 0.0
    recall = n_correct / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return EvalScores(
        matcher=result.matcher,
        dataset=result.dataset,
        split=split,
        n_gold=n_gold,
        n_predicted=n_pred,
        n_correct=n_correct,
        precision=precision,
        recall=recall,
        f1=f1,
        hits_at_1=n_correct / len(universe) if universe else 0.0,
        coverage=n_pred / len(universe) if universe else 0.0,
        runtime_s=result.runtime_s,
    )


def evaluation_frame(scores: list[EvalScores]) -> pd.DataFrame:
    return pd.DataFrame([s.as_dict() for s in scores])
