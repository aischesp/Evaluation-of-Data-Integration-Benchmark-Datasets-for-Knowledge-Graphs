"""Basic statistics: entity, relation, attribute, triple and alignment counts.

Section 1 of docs/Metriken-Katalog.md — cheap to compute, but they set the scale
for everything that follows.
"""

from __future__ import annotations

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.metrics.base import BaseMetric, MetricResult


class BasicStatistics(BaseMetric):
    name = "basic_stats"
    category = "basic"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        s: dict[str, float] = {}
        for kg_label, kg in [("kg1", kg_pair.kg1), ("kg2", kg_pair.kg2)]:
            for k, v in _kg_stats(kg).items():
                s[f"{kg_label}.{k}"] = v

        # Nur echte Gold-Paare, keine partnerlosen Entitaeten (leeres e2).
        n_align = len(kg_pair.matched().drop_duplicates(subset=["e1", "e2"]))
        s["alignments.n"] = float(n_align)
        min_ent = min(kg_pair.kg1.n_entities(), kg_pair.kg2.n_entities())
        s["alignments.ratio"] = n_align / min_ent if min_ent else 0.0

        s["pair.n_entities_total"] = float(
            kg_pair.kg1.n_entities() + kg_pair.kg2.n_entities()
        )
        s["pair.n_triples_total"] = float(
            kg_pair.kg1.n_rel_triples()
            + kg_pair.kg1.n_attr_triples()
            + kg_pair.kg2.n_rel_triples()
            + kg_pair.kg2.n_attr_triples()
        )
        s["pair.size_asymmetry"] = float(
            abs(kg_pair.kg1.n_rel_triples() - kg_pair.kg2.n_rel_triples())
            / max(kg_pair.kg1.n_rel_triples(), kg_pair.kg2.n_rel_triples(), 1)
        )

        return MetricResult(name=self.name, scalar_values=s)


def _kg_stats(kg: KnowledgeGraph) -> dict[str, float]:
    n_rel = kg.n_rel_triples()
    n_attr = kg.n_attr_triples()
    n_ent = max(kg.n_entities(), 1)
    return {
        "n_entities":        float(kg.n_entities()),
        "n_relations":       float(kg.n_relations()),
        "n_attributes":      float(kg.n_attributes()),
        "n_literals":        float(kg.n_literals()),
        "n_rel_triples":     float(n_rel),
        "n_attr_triples":    float(n_attr),
        "attr_to_rel_ratio": (n_attr / n_rel) if n_rel else 0.0,
        "rel_triples_per_entity":  n_rel / n_ent,
        "attr_triples_per_entity": n_attr / n_ent,
    }
