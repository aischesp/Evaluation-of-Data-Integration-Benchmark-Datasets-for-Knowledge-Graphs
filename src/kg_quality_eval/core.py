"""Unified internal representation for a KG alignment benchmark.

Every loader returns these dataclasses, so metrics and matchers can stay
loader-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class KnowledgeGraph:
    """A single KG within a benchmark pair."""

    name: str
    entities: pd.DataFrame      # columns: [entity_uri]
    rel_triples: pd.DataFrame   # columns: [head, relation, tail]
    attr_triples: pd.DataFrame  # columns: [head, attribute, literal, datatype]

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

    def n_literals(self) -> int:
        return self.attr_triples["literal"].nunique()

    @cached_property
    def entity_index(self) -> dict[str, int]:
        """Stable entity-URI -> row-position mapping, used by the sparse matchers."""
        return {uri: i for i, uri in enumerate(self.entities["entity_uri"])}

    @cached_property
    def degrees(self) -> pd.DataFrame:
        """Per-entity in/out/total degree over relation triples.

        Cached because several metrics and matchers need it. Entities that occur
        only in attribute triples get degree 0 (they are structurally isolated).
        """
        import pandas as pd

        out_deg = self.rel_triples["head"].value_counts()
        in_deg = self.rel_triples["tail"].value_counts()

        df = pd.DataFrame({"entity_uri": self.entities["entity_uri"]})
        df["out_degree"] = df["entity_uri"].map(out_deg).fillna(0).astype("int64")
        df["in_degree"] = df["entity_uri"].map(in_deg).fillna(0).astype("int64")
        df["total_degree"] = df["out_degree"] + df["in_degree"]
        return df

    @cached_property
    def attr_count(self) -> pd.Series:
        """Per-entity number of attribute triples, indexed by entity URI."""
        return self.attr_triples["head"].value_counts()


@dataclass
class KGPair:
    """A benchmark pair: two KGs plus the reference alignment."""

    name: str
    kg1: KnowledgeGraph
    kg2: KnowledgeGraph
    alignments: pd.DataFrame   # columns: [e1, e2, split]  split ∈ {train, valid, test, all}
    meta: dict = field(default_factory=dict)

    def n_alignments(self) -> int:
        return len(self.alignments)

    def split(self, name: str) -> pd.DataFrame:
        """Alignment rows of one split ('train' / 'valid' / 'test')."""
        return self.alignments[self.alignments["split"] == name]

    def gold_pairs(self, split: str | None = None) -> set[tuple[str, str]]:
        df = self.alignments if split is None else self.split(split)
        return set(zip(df["e1"], df["e2"], strict=False))
