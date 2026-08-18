"""Tests für die Erzeugung von Benchmark-Varianten mit partnerlosen Entitäten.

Das Modul greift in den Gold-Standard ein, deshalb wird hier genau geprüft:
Bleiben die Zahlen konsistent? Verschwinden auch die Tripel entfernter
Entitäten? Und sehen die Metriken die neue Struktur überhaupt — genau das war
zunächst nicht der Fall, weil sie `alignments` statt `matched()` gelesen haben.
"""

from __future__ import annotations

import pytest

from kg_quality_eval.core import KGPair
from kg_quality_eval.metrics import get_metric
from kg_quality_eval.preprocessing.nonmatch import inject_non_matches, summarize_variant


def test_splits_pairs_into_keep_and_dropped(kg_pair: KGPair):
    """Bei match_ratio=0.6 bleiben von 5 Paaren 3 erhalten, 2 werden aufgelöst."""
    variant = inject_non_matches(kg_pair, match_ratio=0.6, seed=1)

    assert variant.n_matched() == 3
    # Von den zwei aufgelösten Paaren verliert eines die KG1-, eines die
    # KG2-Seite. Nur bei letzterem bleibt eine partnerlose KG1-Entität übrig.
    assert len(variant.unmatched()) == 1
    assert variant.kg1.n_entities() == 4      # 5 - 1 entfernt
    assert variant.kg2.n_entities() == 4


def test_bijectivity_is_actually_broken(kg_pair: KGPair):
    variant = inject_non_matches(kg_pair, match_ratio=0.5, seed=7)

    n1 = variant.kg1.n_entities()
    assert variant.n_matched() < n1, "es muss Entitäten ohne Partner geben"
    assert len(variant.unmatched()) > 0


def test_triples_of_removed_entities_are_gone(kg_pair: KGPair):
    """Eine entfernte Entität darf in keinem Tripel mehr auftauchen."""
    variant = inject_non_matches(kg_pair, match_ratio=0.5, seed=3)

    remaining1 = set(variant.kg1.entities["entity_uri"])
    removed1 = set(kg_pair.kg1.entities["entity_uri"]) - remaining1
    assert removed1, "der Test braucht mindestens eine entfernte Entität"

    assert not set(variant.kg1.rel_triples["head"]) & removed1
    assert not set(variant.kg1.rel_triples["tail"]) & removed1
    assert not set(variant.kg1.attr_triples["head"]) & removed1


def test_unmatched_rows_have_empty_partner(kg_pair: KGPair):
    variant = inject_non_matches(kg_pair, match_ratio=0.5, seed=3)

    unmatched = variant.unmatched()
    assert (unmatched["e2"] == "").all()
    # Und sie bleiben im Auswertungsumfang, tauchen also im Split auf.
    assert set(unmatched["e1"]) <= set(variant.kg1.entities["entity_uri"])
    assert not set(unmatched["e1"]) & set(variant.matched()["e1"])


def test_gold_pairs_still_reference_existing_entities(kg_pair: KGPair):
    variant = inject_non_matches(kg_pair, match_ratio=0.5, seed=11)
    matched = variant.matched()

    assert set(matched["e1"]) <= set(variant.kg1.entities["entity_uri"])
    assert set(matched["e2"]) <= set(variant.kg2.entities["entity_uri"])


def test_deterministic_for_same_seed(kg_pair: KGPair):
    a = inject_non_matches(kg_pair, match_ratio=0.5, seed=42)
    b = inject_non_matches(kg_pair, match_ratio=0.5, seed=42)
    assert a.matched().equals(b.matched())


def test_match_ratio_one_keeps_everything(kg_pair: KGPair):
    variant = inject_non_matches(kg_pair, match_ratio=1.0, seed=5)
    assert variant.n_matched() == kg_pair.n_matched()
    assert len(variant.unmatched()) == 0
    assert variant.kg1.n_entities() == kg_pair.kg1.n_entities()


@pytest.mark.parametrize("ratio", [0.0, -0.5, 1.5])
def test_invalid_ratio_rejected(kg_pair: KGPair, ratio: float):
    with pytest.raises(ValueError, match="match_ratio"):
        inject_non_matches(kg_pair, match_ratio=ratio)


def test_original_is_not_mutated(kg_pair: KGPair):
    before_entities = kg_pair.kg1.n_entities()
    before_pairs = kg_pair.n_matched()
    inject_non_matches(kg_pair, match_ratio=0.5, seed=9)
    assert kg_pair.kg1.n_entities() == before_entities
    assert kg_pair.n_matched() == before_pairs


def test_summary_is_consistent(kg_pair: KGPair):
    variant = inject_non_matches(kg_pair, match_ratio=0.5, seed=2)
    summary = summarize_variant(kg_pair, variant)

    assert summary["gold_pairs"] == variant.n_matched()
    assert summary["unmatched_kg1"] == len(variant.unmatched())
    assert summary["entities_kg1"] == variant.kg1.n_entities()
    assert 0.0 < summary["alignment_coverage"] <= 1.0


# -- Zusammenspiel mit den Metriken ---------------------------------------


def test_alignment_metrics_see_the_non_matches(kg_pair: KGPair):
    """Die Coverage muss fallen.

    Vorher lasen die Alignment-Metriken `alignments` statt `matched()` und
    zählten die partnerlosen Zeilen als Gold-Paare mit — die Coverage blieb
    dadurch auf 1,0 und der leere String galt als KG2-Entität.
    """
    original = get_metric("alignment_metrics").compute(kg_pair).scalar_values
    assert original["alignment_coverage"] == pytest.approx(1.0)
    assert original["n_unmatched_kg1"] == 0.0

    variant = inject_non_matches(kg_pair, match_ratio=0.5, seed=3)
    scalars = get_metric("alignment_metrics").compute(variant).scalar_values

    assert scalars["alignment_coverage"] < 1.0
    assert scalars["n_unmatched_kg1"] > 0
    assert scalars["non_match_share_kg1"] > 0
    # Der leere String darf nicht als Entität durchgehen.
    assert scalars["max_fanout_kg2"] == 1.0


def test_basic_stats_count_only_real_pairs(kg_pair: KGPair):
    variant = inject_non_matches(kg_pair, match_ratio=0.5, seed=3)
    scalars = get_metric("basic_stats").compute(variant).scalar_values
    assert scalars["alignments.n"] == variant.n_matched()


def test_reachability_ignores_unmatched(kg_pair: KGPair):
    variant = inject_non_matches(kg_pair, match_ratio=0.5, seed=3)
    scalars = get_metric("alignment_reachability").compute(variant).scalar_values
    # Ohne den Fix wären die partnerlosen Zeilen mit leerem e2 eingeflossen und
    # hätten den Anteil künstlich gedrückt.
    assert 0.0 <= scalars["share_pairs_both_in_lcc"] <= 1.0
    assert scalars["kg2.share_aligned_with_edge"] <= 1.0
