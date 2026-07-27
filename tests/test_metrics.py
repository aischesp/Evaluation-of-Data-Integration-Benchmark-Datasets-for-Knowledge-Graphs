"""Metric tests. Expected values are derived by hand from tests/conftest.py."""

from __future__ import annotations

import numpy as np
import pytest

from kg_quality_eval.core import KGPair
from kg_quality_eval.metrics import ALL_METRICS, get_metric
from kg_quality_eval.utils.stats import gini, long_tail_share, normalized_entropy, top_k_concentration


@pytest.mark.parametrize("name", ALL_METRICS)
def test_every_metric_runs_and_is_serialisable(name: str, kg_pair: KGPair):
    """Smoke test: no metric may crash or emit non-finite garbage."""
    result = get_metric(name).compute(kg_pair)
    assert result.name == name

    for key, value in result.scalar_values.items():
        assert isinstance(value, int | float), f"{name}.{key} is {type(value)}"
        # NaN is allowed (e.g. undefined correlations), inf is not.
        assert not np.isinf(value), f"{name}.{key} is infinite"


def test_basic_stats(kg_pair: KGPair):
    s = get_metric("basic_stats").compute(kg_pair).scalar_values
    assert s["kg1.n_entities"] == 5
    assert s["kg1.n_rel_triples"] == 4
    assert s["kg1.n_attr_triples"] == 5
    assert s["kg1.n_relations"] == 1          # only 'knows'
    assert s["kg1.n_attributes"] == 3         # name, born, age
    assert s["alignments.n"] == 5
    assert s["alignments.ratio"] == 1.0       # 5 pairs / min(5, 5) entities
    assert s["kg1.attr_to_rel_ratio"] == pytest.approx(5 / 4)


def test_degree_distribution(kg_pair: KGPair):
    s = get_metric("degree_distribution").compute(kg_pair).scalar_values
    # Degrees in KG1: a=3, b=2, c=2, d=1, e=0  -> sum 8 = 2 * 4 edges, mean 1.6
    assert s["kg1.total_degree.mean"] == pytest.approx(1.6)
    assert s["kg1.total_degree.max"] == 3
    assert s["kg1.total_degree.median"] == 2
    assert s["kg1.share_isolated"] == pytest.approx(0.2)   # only 'e'
    assert s["kg1.share_deg_le_2"] == pytest.approx(0.8)   # all but 'a'


def test_connectivity(kg_pair: KGPair):
    s = get_metric("connectivity").compute(kg_pair).scalar_values
    # a-b-c-d form one component, e is isolated.
    assert s["kg1.n_connected_components"] == 2
    assert s["kg1.size_largest_cc"] == 4
    assert s["kg1.share_largest_cc"] == pytest.approx(0.8)


def test_attribute_completeness(kg_pair: KGPair):
    s = get_metric("attribute_completeness").compute(kg_pair).scalar_values
    # a, b, c carry attributes; d and e do not.
    assert s["kg1.share_entities_with_attribute"] == pytest.approx(0.6)
    assert s["kg1.mean_attr_per_entity"] == pytest.approx(1.0)  # 5 triples / 5 entities


def test_schema_heterogeneity_is_total_here(kg_pair: KGPair):
    """KG1 and KG2 share no property name at all -> Jaccard 0."""
    s = get_metric("schema_heterogeneity").compute(kg_pair).scalar_values
    assert s["property_jaccard"] == 0.0
    assert s["n_shared_rel_properties"] == 0


def test_alignment_metrics(kg_pair: KGPair):
    s = get_metric("alignment_metrics").compute(kg_pair).scalar_values
    assert s["n_alignments"] == 5
    assert s["alignment_coverage"] == 1.0
    assert s["bijective_share"] == 1.0        # the fixture alignment is strictly 1:1
    assert s["ambiguity_1_to_n"] == 0.0


def test_alignment_reachability(kg_pair: KGPair):
    s = get_metric("alignment_reachability").compute(kg_pair).scalar_values
    # 4 of 5 gold pairs have an edge on the KG1 side (kg1:e has none).
    assert s["kg1.share_aligned_with_edge"] == pytest.approx(0.8)
    assert s["share_pairs_both_with_edge"] == pytest.approx(0.8)


def test_type_distribution_empty_without_type_triples(kg_pair: KGPair):
    s = get_metric("type_distribution").compute(kg_pair).scalar_values
    assert s["kg1.n_type_triples"] == 0
    assert s["pair.type_jaccard"] == 0.0


def test_unknown_metric_raises():
    with pytest.raises(ValueError, match="Unknown metric"):
        get_metric("nope")


# -- statistics helpers ----------------------------------------------------


def test_gini_bounds():
    assert gini(np.array([5.0, 5.0, 5.0, 5.0])) == pytest.approx(0.0)
    assert gini(np.array([0.0, 0.0, 0.0, 100.0])) > 0.7
    assert gini(np.array([])) == 0.0
    assert gini(np.zeros(5)) == 0.0


def test_normalized_entropy_bounds():
    assert normalized_entropy(np.array([1.0, 1.0, 1.0, 1.0])) == pytest.approx(1.0)
    assert normalized_entropy(np.array([100.0, 1.0])) < 0.2
    assert normalized_entropy(np.array([7.0])) == 0.0


def test_top_k_concentration_and_long_tail():
    counts = np.array([90.0, 5.0, 3.0, 1.0, 1.0])
    assert top_k_concentration(counts, 1) == pytest.approx(0.9)
    assert top_k_concentration(counts, 5) == pytest.approx(1.0)
    # 1/100 = 1 % is not < 1 %, so only nothing falls below the threshold here.
    assert long_tail_share(counts, 0.01) == pytest.approx(0.0)
    assert long_tail_share(counts, 0.05) == pytest.approx(0.6)  # 3, 1, 1
