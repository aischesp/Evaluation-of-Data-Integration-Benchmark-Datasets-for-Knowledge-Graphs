"""Smoke-Test: prüft, dass das Package importierbar ist und der OpenEA-Loader
auf einer Mini-Dummy-Datenstruktur funktioniert."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.loaders import OpenEALoader, get_loader
from kg_quality_eval.metrics import BasicStatistics, get_metric


@pytest.fixture
def dummy_openea_dir(tmp_path: Path) -> Path:
    """Erzeugt ein minimales OpenEA-Verzeichnis im pytest-tmp_path."""
    root = tmp_path / "dummy"
    root.mkdir()

    (root / "rel_triples_1").write_text(
        "e1_a\thas_friend\te1_b\ne1_a\tworks_at\te1_c\n", encoding="utf-8"
    )
    (root / "rel_triples_2").write_text(
        "e2_a\tha_un_ami\te2_b\n", encoding="utf-8"
    )
    (root / "attr_triples_1").write_text(
        'e1_a\tname\t"Alice"\ne1_a\tage\t"30"^^<int>\n', encoding="utf-8"
    )
    (root / "attr_triples_2").write_text(
        'e2_a\tnom\t"Alice"\n', encoding="utf-8"
    )
    (root / "ent_links").write_text("e1_a\te2_a\n", encoding="utf-8")

    fold = root / "721_5fold" / "1"
    fold.mkdir(parents=True)
    (fold / "train_links").write_text("e1_a\te2_a\n", encoding="utf-8")
    (fold / "valid_links").write_text("", encoding="utf-8")
    (fold / "test_links").write_text("", encoding="utf-8")

    return root


def test_loader_factory_known():
    loader = get_loader("openea")
    assert isinstance(loader, OpenEALoader)


def test_loader_factory_unknown():
    with pytest.raises(ValueError):
        get_loader("does_not_exist")


def test_openea_loader_produces_kgpair(dummy_openea_dir: Path):
    kg_pair = OpenEALoader().load(dummy_openea_dir)

    assert isinstance(kg_pair, KGPair)
    assert isinstance(kg_pair.kg1, KnowledgeGraph)
    assert kg_pair.kg1.n_rel_triples() == 2
    assert kg_pair.kg2.n_rel_triples() == 1
    assert kg_pair.kg1.n_attr_triples() == 2
    assert kg_pair.n_alignments() == 1


def test_basic_stats_metric(dummy_openea_dir: Path):
    kg_pair = OpenEALoader().load(dummy_openea_dir)
    result = BasicStatistics().compute(kg_pair)

    assert result.name == "basic_stats"
    assert result.scalar_values["kg1.n_rel_triples"] == 2.0
    assert result.scalar_values["kg2.n_rel_triples"] == 1.0
    assert result.scalar_values["alignments.n"] == 1.0
    # alignment_ratio = 1 / min(|E1|, |E2|) — kg2 hat 2 Entitäten (e2_a, e2_b)
    assert 0.0 < result.scalar_values["alignments.ratio"] <= 1.0


def test_metric_factory():
    assert isinstance(get_metric("basic_stats"), BasicStatistics)
