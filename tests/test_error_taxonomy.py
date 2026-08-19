"""Tests der Fehler-Taxonomie.

Der Kern ist die familienabhängige Kaskade: dasselbe fehlgeschlagene Gold-Paar
muss je nach Matcher-Familie einer anderen Ursache zugeordnet werden. Ein rein
struktureller Matcher scheitert nicht an fehlenden Literalen, ein wertbasierter
nicht an fehlender Konnektivität.
"""

from __future__ import annotations

import pandas as pd
import pytest

from kg_quality_eval.core import KGPair
from kg_quality_eval.reporting import error_taxonomy as tax


def _pred(pairs: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        {"e1": [p[0] for p in pairs], "e2": [p[1] for p in pairs], "score": 1.0}
    )


def _classes(kg_pair: KGPair, predictions, family: str) -> dict[str, str]:
    frame = tax.classify(kg_pair, predictions, split="test", family=family)
    return dict(zip(frame["e1"], frame["error_class"], strict=False))


def test_correct_prediction(kg_pair: KGPair):
    classes = _classes(kg_pair, _pred([("kg1:d", "kg2:D")]), "holistic")
    assert classes["kg1:d"] == "correct"


def test_no_signal_beats_everything(kg_pair: KGPair):
    """kg1:e hat weder Relations- noch Attribut-Tripel — für kein Verfahren lösbar."""
    for family in ("structural", "value", "holistic"):
        classes = _classes(kg_pair, _pred([]), family)
        assert classes["kg1:e"] == "no_signal", family


def test_family_decides_the_blocker(kg_pair: KGPair):
    """Dasselbe Paar, drei Familien, drei Zuordnungen.

    kg1:d hat eine Kante (Grad 1) und keine Attribute; sein Gold-Partner kg2:D
    hat ebenfalls eine Kante und ein Attribut. Es gibt also Struktur, aber
    keinen gemeinsamen Literalwert.
    """
    predictions = _pred([])   # niemand sagt etwas vorher

    value = _classes(kg_pair, predictions, "value")
    assert value["kg1:d"] == "no_shared_literal"

    structural = _classes(kg_pair, predictions, "structural")
    # Struktur ist vorhanden, also ist es kein Blocker, sondern Enthaltung.
    assert structural["kg1:d"] == "abstained"


def test_abstention_is_distinguished_from_wrong_candidate(kg_pair: KGPair):
    """Nichts sagen und etwas Falsches sagen sind verschiedene Fehler."""
    silent = _classes(kg_pair, _pred([]), "structural")
    wrong = _classes(kg_pair, _pred([("kg1:d", "kg2:B")]), "structural")

    assert silent["kg1:d"] == "abstained"
    assert wrong["kg1:d"] == "wrong_candidate"


def _with_orphan(kg_pair: KGPair) -> KGPair:
    rows = kg_pair.alignments.copy()
    rows.loc[len(rows)] = {"e1": "kg1:c", "e2": "", "split": "test"}
    return KGPair(name=kg_pair.name, kg1=kg_pair.kg1, kg2=kg_pair.kg2, alignments=rows)


def test_false_prediction_on_unmatched_entity(kg_pair: KGPair):
    """Eine Vorhersage für eine partnerlose Entität ist eine eigene Fehlerklasse."""
    pair = _with_orphan(kg_pair)
    predicted = _classes(pair, _pred([("kg1:c", "kg2:A")]), "holistic")
    assert predicted["kg1:c"] == "false_on_unmatched"


def test_correct_abstention_is_a_true_negative_not_a_hit(kg_pair: KGPair):
    """Enthaltung bei einer partnerlosen Entität ist richtig — aber kein Treffer.

    Beides in `correct` zu zählen würde den Anteil auf den Non-Match-Varianten
    stark überhöhen, weil dort ein Drittel der Entitäten partnerlos ist.
    """
    pair = _with_orphan(kg_pair)
    classes = _classes(pair, _pred([("kg1:d", "kg2:D")]), "holistic")

    assert classes["kg1:c"] == "true_negative"
    assert classes["kg1:d"] == "correct"

    frame = tax.classify(pair, _pred([("kg1:d", "kg2:D")]), family="holistic")
    n_correct = (frame["error_class"] == "correct").sum()
    n_true_negative = (frame["error_class"] == "true_negative").sum()
    assert n_correct == 1, "nur der echte Treffer"
    assert n_true_negative == 1


def test_true_negative_is_not_counted_as_error(kg_pair: KGPair):
    pair = _with_orphan(kg_pair)
    frame = tax.classify(pair, _pred([("kg1:d", "kg2:D")]), family="holistic")
    summary = tax.summarize(frame, "MINI_5", "dummy")
    solv = tax.solvability(summary)

    n_errors = int(solv.iloc[0]["n_errors"])
    assert n_errors == len(frame) - 2   # ein Treffer, ein True Negative


def test_components_can_be_passed_in(kg_pair: KGPair):
    """Vorberechnete Komponenten müssen dasselbe Ergebnis liefern."""
    components = tax.largest_components(kg_pair)
    without = tax.classify(kg_pair, _pred([]), family="structural")
    with_cached = tax.classify(kg_pair, _pred([]), family="structural", components=components)
    pd.testing.assert_frame_equal(without, with_cached)


def test_every_entity_gets_exactly_one_class(kg_pair: KGPair):
    frame = tax.classify(kg_pair, _pred([("kg1:d", "kg2:D")]), family="holistic")
    assert len(frame) == len(kg_pair.split("test"))
    assert frame["e1"].is_unique
    assert set(frame["error_class"]) <= set(tax.CLASSES)


def test_summary_shares_sum_to_one(kg_pair: KGPair):
    frame = tax.classify(kg_pair, _pred([("kg1:d", "kg2:D")]), family="holistic")
    summary = tax.summarize(frame, "MINI_5", "dummy")
    assert summary["share"].sum() == pytest.approx(1.0)
    assert list(summary["error_class"]) == list(tax.CLASSES)


def test_solvability_splits_benchmark_from_method(kg_pair: KGPair):
    frame = tax.classify(kg_pair, _pred([]), family="value")
    summary = tax.summarize(frame, "MINI_5", "dummy")
    solv = tax.solvability(summary)

    assert len(solv) == 1
    row = solv.iloc[0]
    assert row["unsolvable_share"] + row["method_share"] == pytest.approx(1.0)
    assert 0.0 <= row["unsolvable_share"] <= 1.0


def test_empty_predictions_are_handled(kg_pair: KGPair):
    frame = tax.classify(kg_pair, pd.DataFrame(columns=["e1", "e2", "score"]), family="value")
    assert len(frame) == len(kg_pair.split("test"))
    assert "correct" not in set(frame["error_class"])
