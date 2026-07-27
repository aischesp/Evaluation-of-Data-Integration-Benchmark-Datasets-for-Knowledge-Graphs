"""Loader and literal-parsing tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.loaders import OpenEALoader, get_loader
from kg_quality_eval.loaders.rdf_export import from_uriref, to_uriref, write_ntriples
from kg_quality_eval.utils.literals import namespace, normalize_value, parse_literal, tokenize


def test_loader_factory():
    assert isinstance(get_loader("openea"), OpenEALoader)
    with pytest.raises(ValueError, match="Unknown loader"):
        get_loader("does_not_exist")


def test_loads_triples_and_splits(kg_pair: KGPair):
    assert isinstance(kg_pair.kg1, KnowledgeGraph)
    assert kg_pair.kg1.n_rel_triples() == 4
    assert kg_pair.kg2.n_rel_triples() == 4
    assert kg_pair.kg1.n_attr_triples() == 5
    assert kg_pair.n_alignments() == 5

    counts = kg_pair.alignments["split"].value_counts().to_dict()
    assert counts == {"train": 2, "valid": 1, "test": 2}


def test_entity_set_includes_alignment_only_entities(kg_pair: KGPair):
    """kg1:e appears in no triple — it must still count as an entity (degree 0)."""
    assert kg_pair.kg1.n_entities() == 5  # a, b, c, d, e
    assert "kg1:e" in set(kg_pair.kg1.entities["entity_uri"])

    degrees = kg_pair.kg1.degrees.set_index("entity_uri")["total_degree"]
    assert degrees["kg1:e"] == 0
    assert degrees["kg1:a"] == 3  # out: ->b, ->d;  in: c->
    assert degrees["kg1:d"] == 1
    assert degrees.sum() == 8     # every edge contributes twice


def test_degrees_split_in_and_out(kg_pair: KGPair):
    deg = kg_pair.kg1.degrees.set_index("entity_uri")
    assert deg.loc["kg1:a", "out_degree"] == 2   # -> b, -> d
    assert deg.loc["kg1:a", "in_degree"] == 1    # c ->
    assert deg.loc["kg1:d", "out_degree"] == 0


@pytest.mark.parametrize(
    ("raw", "value", "datatype", "lang"),
    [
        ('"Alice"', "Alice", "string", ""),
        ('"31"', "31", "numeric", ""),
        ('"1990-01-01"^^<http://www.w3.org/2001/XMLSchema#date>', "1990-01-01", "date", ""),
        ('"1946-06-04"^^xsd:date', "1946-06-04", "date", ""),
        ('"Titel"@ita', "Titel", "langString", "ita"),
        ("", "", "empty", ""),
        ('"3.451E8"^^<http://dbpedia.org/datatype/usDollar>', "3.451E8", "usDollar", ""),
    ],
)
def test_parse_literal(raw, value, datatype, lang):
    assert parse_literal(raw) == (value, datatype, lang)


def test_normalize_and_tokenize():
    assert normalize_value('"Café  Münster"@de') == "cafe munster"
    assert tokenize('"Star Wars: Episode IV"') == ["star", "wars", "episode", "iv"]


def test_namespace():
    assert namespace("http://dbpedia.org/resource/E1") == "http://dbpedia.org/resource/"
    assert namespace("YAGO/E1") == "YAGO/"


def test_ntriples_export_roundtrip(kg_pair: KGPair, tmp_path: Path):
    """Every term must survive the export/parse round-trip unchanged."""
    for term in ("kg1:a", "YAGO/E473489", "http://dbpedia.org/resource/E1", "isLocatedIn"):
        assert from_uriref(str(to_uriref(term, "e1"))) == term

    target = write_ntriples(kg_pair.kg1, tmp_path / "kg1.nt", kind="e1")
    lines = target.read_text(encoding="utf-8").strip().splitlines()

    # 4 relation triples + 5 attribute triples, all well-formed.
    assert len(lines) == 9
    assert all(line.endswith(" .") for line in lines)

    # rdflib must be able to parse what we wrote.
    from rdflib import Graph

    graph = Graph()
    graph.parse(data=target.read_text(encoding="utf-8"), format="nt")
    assert len(graph) == 9
