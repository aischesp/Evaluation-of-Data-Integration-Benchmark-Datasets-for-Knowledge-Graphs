"""Tests für Matcher, Schwellenwerte und Bewertung."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

from kg_quality_eval.core import KGPair
from kg_quality_eval.matching import ALL_MATCHERS, evaluate, get_matcher
from kg_quality_eval.matching.base import (
    MatchResult,
    seeds_to_matrix,
    top1_margin_per_row,
    topk_per_row,
)
from kg_quality_eval.matching.structural import adjacency, align_relations

# PARIS braucht eine JVM, pyJedAI ist für ein 5-Entitäten-Fixture überdimensioniert.
LOCAL_MATCHERS = [m for m in ALL_MATCHERS if m not in ("paris", "pyjedai_ngram")]


@pytest.mark.parametrize("name", LOCAL_MATCHERS)
def test_matcher_contract(name: str, kg_pair: KGPair):
    """Jeder Matcher liefert eindeutige, wohlgeformte Vorhersagen."""
    matcher = get_matcher(name)
    result = matcher.match(kg_pair, kg_pair.matched("train"))

    assert isinstance(result, MatchResult)
    assert list(result.pairs.columns) == ["e1", "e2", "score"]
    assert result.pairs["e1"].is_unique, "höchstens ein Partner je Entität"
    assert result.runtime_s >= 0

    assert set(result.pairs["e1"]) <= set(kg_pair.kg1.entities["entity_uri"])
    assert set(result.pairs["e2"]) <= set(kg_pair.kg2.entities["entity_uri"])


@pytest.mark.parametrize("name", LOCAL_MATCHERS)
def test_threshold_is_effective(name: str, kg_pair: KGPair):
    """Ein hoher Schwellenwert muss Vorhersagen unterdrücken, nicht nur umsortieren.

    Genau das war vorher nicht der Fall: `min_score` stand auf 0,0, also wurde
    immer der beste Kandidat ausgegeben.
    """
    seeds = kg_pair.matched("train")
    permissive = get_matcher(name, min_score=0.0).match(kg_pair, seeds)
    strict = get_matcher(name, min_score=0.99).match(kg_pair, seeds)

    assert len(strict.pairs) <= len(permissive.pairs)


def test_value_overlap_finds_the_obvious_pair(kg_pair: KGPair):
    """kg1:a und kg2:A teilen 'Alice' und ein Geburtsdatum."""
    result = get_matcher("value_overlap", min_score=0.0).match(kg_pair)
    predicted = dict(zip(result.pairs["e1"], result.pairs["e2"], strict=False))
    assert predicted.get("kg1:a") == "kg2:A"


def test_structural_matcher_ignores_literals(kg_pair: KGPair):
    """Literale zu löschen darf einen rein strukturellen Matcher nicht ändern."""
    matcher = get_matcher("structural_propagation")
    before = matcher.match(kg_pair, kg_pair.matched("train")).pairs

    stripped = KGPair(
        name=kg_pair.name, kg1=kg_pair.kg1, kg2=kg_pair.kg2, alignments=kg_pair.alignments
    )
    stripped.kg1.attr_triples = stripped.kg1.attr_triples.iloc[0:0]
    after = matcher.match(stripped, stripped.matched("train")).pairs

    pd.testing.assert_frame_equal(before, after)


def test_align_relations_uses_seed_evidence(kg_pair: KGPair):
    """Relationen werden ohne gemeinsames Vokabular über die Seeds zugeordnet.

    Im Fixture heisst die Relation in KG1 'knows' und in KG2 'connait' — die
    Zuordnung darf sich also nicht auf Namensgleichheit stützen.
    """
    seeds = kg_pair.matched()          # alle Paare, damit genug Belege da sind
    aligned = align_relations(kg_pair, seeds, min_evidence=1)

    assert aligned, "es sollte mindestens eine Zuordnung gefunden werden"
    r1, r2, weight, _inverted = aligned[0]
    assert r1 == "knows"
    assert r2 == "connait"
    assert 0.0 < weight <= 1.0


def test_align_relations_without_seeds_is_empty(kg_pair: KGPair):
    assert align_relations(kg_pair, pd.DataFrame(columns=["e1", "e2"])) == []


def test_adjacency_is_symmetric_and_binary(kg_pair: KGPair):
    a = adjacency(kg_pair.kg1)
    assert a.shape == (5, 5)
    assert (a != a.T).nnz == 0
    assert set(np.unique(a.data)) <= {1.0}


def test_seeds_to_matrix(kg_pair: KGPair):
    seeds = seeds_to_matrix(kg_pair.matched("train"), kg_pair)
    assert seeds.shape == (5, 5)
    assert seeds.nnz == 2
    assert seeds_to_matrix(None, kg_pair).nnz == 0
    assert seeds_to_matrix(pd.DataFrame(columns=["e1", "e2"]), kg_pair).nnz == 0


def test_topk_per_row_prunes():
    dense = np.array([[0.1, 0.9, 0.5, 0.3], [0.0, 0.0, 0.0, 0.0]])
    pruned = topk_per_row(sp.csr_matrix(dense), k=2)
    assert pruned.getrow(0).nnz == 2
    assert sorted(pruned.getrow(0).data, reverse=True) == pytest.approx([0.9, 0.5])
    assert pruned.getrow(1).nnz == 0


def test_top1_margin_per_row():
    dense = np.array([
        [0.1, 0.9, 0.5],      # klarer Sieger, Abstand 0.4
        [0.6, 0.6, 0.0],      # Gleichstand, Abstand 0.0
        [0.0, 0.0, 0.0],      # leer
    ])
    rows, cols, margins = top1_margin_per_row(sp.csr_matrix(dense))
    assert list(rows) == [0, 1]
    assert cols[0] == 1
    assert margins[0] == pytest.approx(0.4)
    assert margins[1] == pytest.approx(0.0)


def test_unknown_matcher_raises():
    with pytest.raises(ValueError, match="Unknown matcher"):
        get_matcher("nope")


# -- Bewertung -------------------------------------------------------------


def _result(pairs: list[tuple[str, str]], dataset: str = "MINI_5") -> MatchResult:
    return MatchResult(
        matcher="dummy",
        dataset=dataset,
        pairs=pd.DataFrame(
            {"e1": [p[0] for p in pairs], "e2": [p[1] for p in pairs], "score": 1.0}
        ),
        runtime_s=0.0,
    )


def test_evaluate_perfect(kg_pair: KGPair):
    scores = evaluate(_result([("kg1:d", "kg2:D"), ("kg1:e", "kg2:E")]), kg_pair, "test")
    assert scores.n_gold == 2
    assert scores.precision == 1.0
    assert scores.recall == 1.0
    assert scores.f1 == 1.0


def test_evaluate_half_correct(kg_pair: KGPair):
    scores = evaluate(_result([("kg1:d", "kg2:D"), ("kg1:e", "kg2:A")]), kg_pair, "test")
    assert scores.n_correct == 1
    assert scores.precision == pytest.approx(0.5)


def test_evaluate_ignores_predictions_outside_the_split(kg_pair: KGPair):
    with_extra = _result(
        [("kg1:d", "kg2:D"), ("kg1:e", "kg2:E"), ("kg1:a", "kg2:A"), ("kg1:b", "kg2:X")]
    )
    scores = evaluate(with_extra, kg_pair, "test")
    assert scores.n_predicted == 2
    assert scores.precision == 1.0


def test_evaluate_counts_predictions_on_unmatched_entities(kg_pair: KGPair):
    """Eine Vorhersage für eine partnerlose Entität ist ein False Positive.

    Ohne diese Zählung wäre ein fehlender Schwellenwert nicht messbar — genau
    das war die Schwäche der bijektiven Originaldatensätze.
    """
    with_orphan = kg_pair.alignments.copy()
    with_orphan.loc[len(with_orphan)] = {"e1": "kg1:c", "e2": "", "split": "test"}
    pair = KGPair(
        name=kg_pair.name, kg1=kg_pair.kg1, kg2=kg_pair.kg2, alignments=with_orphan
    )

    scores = evaluate(_result([("kg1:d", "kg2:D"), ("kg1:c", "kg2:A")]), pair, "test")
    assert scores.n_unmatched == 1
    assert scores.n_false_on_unmatched == 1
    assert scores.n_correct == 1
    assert scores.precision == pytest.approx(0.5)   # 1 von 2 Vorhersagen richtig

    # Enthaltung auf der partnerlosen Entität ist die richtige Antwort.
    abstained = evaluate(_result([("kg1:d", "kg2:D")]), pair, "test")
    assert abstained.n_false_on_unmatched == 0
    assert abstained.precision == 1.0


def test_evaluate_empty_prediction(kg_pair: KGPair):
    scores = evaluate(_result([]), kg_pair, "test")
    assert scores.precision == 0.0
    assert scores.f1 == 0.0
    assert scores.abstain_rate == 1.0
