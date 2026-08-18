"""Alignment metrics — properties of the reference alignment M itself.

Section 3.4 of docs/Metriken-Katalog.md. These describe the gold standard: how
much of each KG it covers, whether it is a clean 1:1 mapping, and whether the
aligned entities are structurally reachable at all.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from kg_quality_eval.core import KGPair
from kg_quality_eval.metrics.base import BaseMetric, MetricResult


class AlignmentMetrics(BaseMetric):
    name = "alignment_metrics"
    category = "quality"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        # Nur echte Gold-Paare. Zeilen mit leerem `e2` sind Entitäten, die
        # bewusst keinen Partner haben (preprocessing/nonmatch.py); sie als
        # Alignment mitzuzählen würde die Coverage künstlich auf 1,0 heben und
        # den leeren String als KG2-Entität behandeln.
        align = kg_pair.matched().drop_duplicates(subset=["e1", "e2"])
        n = len(align)
        n1 = max(kg_pair.kg1.n_entities(), 1)
        n2 = max(kg_pair.kg2.n_entities(), 1)

        if n == 0:
            return MetricResult(name=self.name, scalar_values={"n_alignments": 0.0})

        left_counts = align["e1"].value_counts()
        right_counts = align["e2"].value_counts()

        scalars: dict[str, float] = {
            "n_alignments": float(n),
            "alignment_coverage": float(n / min(n1, n2)),
            "entity_coverage_kg1": float(left_counts.size / n1),
            "entity_coverage_kg2": float(right_counts.size / n2),
            "ambiguity_1_to_n": float((left_counts > 1).sum() / left_counts.size),
            "ambiguity_n_to_1": float((right_counts > 1).sum() / right_counts.size),
            "max_fanout_kg1": float(left_counts.max()),
            "max_fanout_kg2": float(right_counts.max()),
        }

        bijective = align[
            align["e1"].map(left_counts).eq(1) & align["e2"].map(right_counts).eq(1)
        ]
        scalars["bijective_share"] = float(len(bijective) / n)

        # Search-space size: how many candidates a matcher has to rank per entity.
        scalars["candidate_space_log10"] = float(np.log10(n1 * n2))
        scalars["unaligned_share_kg1"] = float(1.0 - left_counts.size / n1)
        scalars["unaligned_share_kg2"] = float(1.0 - right_counts.size / n2)

        # Are the aligned entities structurally informative?
        d1 = kg_pair.kg1.degrees.set_index("entity_uri")["total_degree"]
        d2 = kg_pair.kg2.degrees.set_index("entity_uri")["total_degree"]
        deg1 = align["e1"].map(d1).fillna(0)
        deg2 = align["e2"].map(d2).fillna(0)
        scalars["aligned_mean_degree_kg1"] = float(deg1.mean())
        scalars["aligned_mean_degree_kg2"] = float(deg2.mean())
        scalars["aligned_degree_bias_kg1"] = float(
            deg1.mean() / max(kg_pair.kg1.degrees["total_degree"].mean(), 1e-9)
        )
        scalars["aligned_degree_bias_kg2"] = float(
            deg2.mean() / max(kg_pair.kg2.degrees["total_degree"].mean(), 1e-9)
        )

        # Wie viele Entitäten haben korrekterweise keinen Partner? Auf den
        # unveränderten OpenEA-Benchmarks ist das null; erst die
        # Non-Match-Varianten machen daraus eine relevante Größe.
        n_unmatched = len(kg_pair.unmatched())
        scalars["n_unmatched_kg1"] = float(n_unmatched)
        scalars["non_match_share_kg1"] = float(n_unmatched / n1)

        split_rows = (
            kg_pair.matched().groupby("split").size().rename("n_pairs").reset_index()
        )
        for _, row in split_rows.iterrows():
            scalars[f"split.{row['split']}"] = float(row["n_pairs"])

        return MetricResult(
            name=self.name, scalar_values=scalars, tabular={"splits": split_rows}
        )


class AlignmentReachability(BaseMetric):
    """Can a structural matcher reach the gold pairs at all?

    For every gold pair we check whether both entities have at least one
    relation triple and whether they sit in the largest connected component.
    This is an upper bound for purely structural approaches.
    """

    name = "alignment_reachability"
    category = "quality"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        import networkx as nx

        align = kg_pair.matched().drop_duplicates(subset=["e1", "e2"])
        if align.empty:
            return MetricResult(name=self.name, scalar_values={})

        scalars: dict[str, float] = {}
        in_lcc: dict[str, set[str]] = {}

        for label, kg, col in (("kg1", kg_pair.kg1, "e1"), ("kg2", kg_pair.kg2, "e2")):
            g = nx.Graph()
            g.add_nodes_from(kg.entities["entity_uri"])
            g.add_edges_from(zip(kg.rel_triples["head"], kg.rel_triples["tail"], strict=False))
            components = list(nx.connected_components(g))
            largest = max(components, key=len) if components else set()
            in_lcc[label] = largest

            deg = kg.degrees.set_index("entity_uri")["total_degree"]
            has_edge = align[col].map(deg).fillna(0) > 0
            scalars[f"{label}.share_aligned_with_edge"] = float(has_edge.mean())
            scalars[f"{label}.share_aligned_in_lcc"] = float(align[col].isin(largest).mean())

        both = align["e1"].isin(in_lcc["kg1"]) & align["e2"].isin(in_lcc["kg2"])
        scalars["share_pairs_both_in_lcc"] = float(both.mean())

        d1 = kg_pair.kg1.degrees.set_index("entity_uri")["total_degree"]
        d2 = kg_pair.kg2.degrees.set_index("entity_uri")["total_degree"]
        both_edges = (align["e1"].map(d1).fillna(0) > 0) & (align["e2"].map(d2).fillna(0) > 0)
        scalars["share_pairs_both_with_edge"] = float(both_edges.mean())

        table = pd.DataFrame(
            {
                "criterion": ["both_with_edge", "both_in_lcc"],
                "share": [scalars["share_pairs_both_with_edge"], scalars["share_pairs_both_in_lcc"]],
            }
        )
        return MetricResult(name=self.name, scalar_values=scalars, tabular={"reachability": table})
