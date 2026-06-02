<<<<<<< HEAD
"""Unified Internal Representation of a Knowledge-Graph-Alignment-Benchmark.

Alle Loader müssen Output dieser Datenklassen liefern, damit Metriken loader-agnostisch
implementiert werden können.
=======
"""Unified internal representation for a KG alignment benchmark.

Every loader returns these dataclasses, so metrics can stay loader-agnostic.
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class KnowledgeGraph:
<<<<<<< HEAD
    """Ein einzelner KG innerhalb eines Benchmark-Paars."""
=======
    """A single KG within a benchmark pair."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

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
<<<<<<< HEAD
    """Ein Benchmark-Paar: zwei KGs + Referenz-Alignment."""
=======
    """A benchmark pair: two KGs plus the reference alignment."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

    name: str
    kg1: KnowledgeGraph
    kg2: KnowledgeGraph
    alignments: "pd.DataFrame"   # columns: [e1, e2, split]  split ∈ {train, valid, test, all}
    meta: dict = field(default_factory=dict)

    def n_alignments(self) -> int:
        return len(self.alignments)
