"""Matcher and evaluation tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

from kg_quality_eval.core import KGPair
from kg_quality_eval.matching import ALL_MATCHERS, evaluate, get_matcher
from kg_quality_eval.matching.base import MatchResult, seeds_to_matrix, topk_per_row
from kg_quality_eval.matching.structural import adjacency

PYTHON_MATCHERS = [m for m in ALL_MATCHERS if m != "paris"]  # PARIS needs a JVM


@pytest.mark.parametrize("name", PYTHON_MATCHERS)
def test_matcher_contract(name: str, kg_pair: KGPair):
    """Every matcher returns unique, well-formed, in-vocabulary predictions."""
    matcher = get_matcher(name)
    result = matcher.match(kg_pair, kg_pair.split("train"))

    assert isinstance(result, MatchResult)
    assert list(result.pairs.columns) == ["e1", "e2", "score"]
    assert result.pairs["e1"].is_unique, "a matcher must predict at most one partner per entity"
    assert result.runtime_s >= 0

    known1 = set(kg_pair.kg1.entities["entity_uri"])
    known2 = set(kg_pair.kg2.entities["entity_uri"])
    assert set(result.pairs["e1"]) <= known1
    assert set(result.pairs["e2"]) <= known2


def test_literal_tfidf_finds_the_obvious_pair(kg_pair: KGPair):
    """kg1:a and kg2:A share 'Alice' and a birth date — that must be found."""
    result = get_matcher("literal_tfidf").match(kg_pair)
    predicted = dict(zip(result.pairs["e1"], result.pairs["e2"], strict=False))
    assert predicted.get("kg1:a") == "kg2:A"


def test_value_overlap_matches_exact_values(kg_pair: KGPair):
    result = get_matcher("value_overlap").match(kg_pair)
    predicted = dict(zip(result.pairs["e1"], result.pairs["e2"], strict=False))
    assert predicted.get("kg1:a") == "kg2:A"


def test_structural_matcher_ignores_literals(kg_pair: KGPair):
    """Blanking all literals must not change a purely structural matcher."""
    matcher = get_matcher("structural_propagation")
    before = matcher.match(kg_pair, kg_pair.split("train")).pairs

    stripped = KGPair(
        name=kg_pair.name,
        kg1=kg_pair.kg1,
        kg2=kg_pair.kg2,
        alignments=kg_pair.alignments,
    )
    stripped.kg1.attr_triples = stripped.kg1.attr_triples.iloc[0:0]
    after = matcher.match(stripped, stripped.split("train")).pairs

    pd.testing.assert_frame_equal(before, after)


def test_adjacency_is_symmetric_and_binary(kg_pair: KGPair):
    a = adjacency(kg_pair.kg1)
    assert a.shape == (5, 5)
    assert (a != a.T).nnz == 0
    assert set(np.unique(a.data)) <= {1.0}


def test_seeds_to_matrix(kg_pair: KGPair):
    seeds = seeds_to_matrix(kg_pair.split("train"), kg_pair)
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


def test_unknown_matcher_raises():
    with pytest.raises(ValueError, match="Unknown matcher"):
        get_matcher("nope")


# -- evaluation ------------------------------------------------------------


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
    """Test split is {(d, D), (e, E)} — predicting both exactly gives F1 = 1."""
    scores = evaluate(_result([("kg1:d", "kg2:D"), ("kg1:e", "kg2:E")]), kg_pair, "test")
    assert scores.n_gold == 2
    assert scores.precision == 1.0
    assert scores.recall == 1.0
    assert scores.f1 == 1.0
    assert scores.hits_at_1 == 1.0


def test_evaluate_half_correct(kg_pair: KGPair):
    scores = evaluate(_result([("kg1:d", "kg2:D"), ("kg1:e", "kg2:A")]), kg_pair, "test")
    assert scores.n_correct == 1
    assert scores.precision == pytest.approx(0.5)
    assert scores.recall == pytest.approx(0.5)


def test_evaluate_ignores_predictions_outside_the_split(kg_pair: KGPair):
    """Predictions about training entities must neither help nor hurt.

    This is what makes unsupervised and seed-based matchers comparable.
    """
    with_extra = _result(
        [("kg1:d", "kg2:D"), ("kg1:e", "kg2:E"), ("kg1:a", "kg2:A"), ("kg1:b", "kg2:X")]
    )
    scores = evaluate(with_extra, kg_pair, "test")
    assert scores.n_predicted == 2
    assert scores.precision == 1.0
    assert scores.f1 == 1.0


def test_evaluate_partial_coverage(kg_pair: KGPair):
    """A matcher that abstains keeps precision but loses recall."""
    scores = evaluate(_result([("kg1:d", "kg2:D")]), kg_pair, "test")
    assert scores.precision == 1.0
    assert scores.recall == pytest.approx(0.5)
    assert scores.coverage == pytest.approx(0.5)


def test_evaluate_empty_prediction(kg_pair: KGPair):
    scores = evaluate(_result([]), kg_pair, "test")
    assert scores.precision == 0.0
    assert scores.f1 == 0.0
