"""Basis-Statistiken (Section 1 des Metriken-Katalogs).

Implementiert die einfachsten Größen — eine vollständig funktionsfähige Demo der Pipeline.
"""

from __future__ import annotations

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.metrics.base import BaseMetric, MetricResult


class BasicStatistics(BaseMetric):
    name = "basic_stats"
    category = "basic"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        s = {}
        for kg_label, kg in [("kg1", kg_pair.kg1), ("kg2", kg_pair.kg2)]:
            for k, v in _kg_stats(kg).items():
                s[f"{kg_label}.{k}"] = v

        n_align = kg_pair.n_alignments()
        s["alignments.n"] = n_align
        min_ent = min(kg_pair.kg1.n_entities(), kg_pair.kg2.n_entities())
        s["alignments.ratio"] = n_align / min_ent if min_ent else 0.0

        return MetricResult(name=self.name, scalar_values=s)


def _kg_stats(kg: KnowledgeGraph) -> dict[str, float]:
    n_rel = kg.n_rel_triples()
    n_attr = kg.n_attr_triples()
    return {
        "n_entities":     float(kg.n_entities()),
        "n_relations":    float(kg.n_relations()),
        "n_attributes":   float(kg.n_attributes()),
        "n_rel_triples":  float(n_rel),
        "n_attr_triples": float(n_attr),
        "attr_to_rel_ratio": (n_attr / n_rel) if n_rel else 0.0,
    }
