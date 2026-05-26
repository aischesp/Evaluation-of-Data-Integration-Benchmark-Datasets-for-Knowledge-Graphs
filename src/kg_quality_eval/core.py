"""Unified internal representation for a KG alignment benchmark.

Every loader returns these dataclasses, so metrics can stay loader-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class KnowledgeGraph:
    """A single KG within a benchmark pair."""

    name: str
    entities: "pd.DataFrame"      # columns: [entity_uri]
    rel_triples: "pd.DataFrame"   # columns: [head, relation, tail]
    attr_triples: "pd.DataFrame"  # columns: [head, attribute, literal, datatype]

    def n_entities(self) -> int:
        return len(self.entities)

    def n_rel_triples(self) -> int:
        return len(self.rel_triples)

    def n_attr_triples(self) -> int:
        return len(self.attr_triples)

    def n_relations(self) -> int:
        return self.rel_triples["relation"].nunique()

    def n_attributes(self) -> int:
        return self.attr_triples["attribute"].nunique()


@dataclass
class KGPair:
    """A benchmark pair: two KGs plus the reference alignment."""

    name: str
    kg1: KnowledgeGraph
    kg2: KnowledgeGraph
    alignments: "pd.DataFrame"   # columns: [e1, e2, split]  split ∈ {train, valid, test, all}
    meta: dict = field(default_factory=dict)

    def n_alignments(self) -> int:
        return len(self.alignments)
