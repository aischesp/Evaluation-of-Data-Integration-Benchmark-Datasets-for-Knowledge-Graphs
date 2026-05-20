"""Unified Internal Representation of a Knowledge-Graph-Alignment-Benchmark.

Alle Loader müssen Output dieser Datenklassen liefern, damit Metriken loader-agnostisch
implementiert werden können.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class KnowledgeGraph:
    """Ein einzelner KG innerhalb eines Benchmark-Paars."""

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
    """Ein Benchmark-Paar: zwei KGs + Referenz-Alignment."""

    name: str
    kg1: KnowledgeGraph
    kg2: KnowledgeGraph
    alignments: "pd.DataFrame"   # columns: [e1, e2, split]  split ∈ {train, valid, test, all}
    meta: dict = field(default_factory=dict)

    def n_alignments(self) -> int:
        return len(self.alignments)
