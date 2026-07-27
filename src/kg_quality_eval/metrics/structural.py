"""Structural metrics: degree distributions, property distributions, connectivity.

Section 2 of docs/Metriken-Katalog.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.metrics.base import BaseMetric, MetricResult
from kg_quality_eval.utils.stats import (
    log_histogram,
    long_tail_share,
    normalized_entropy,
    powerlaw_alpha,
    summarize,
    top_k_concentration,
)

KG_LABELS = ("kg1", "kg2")


def _iter_kgs(kg_pair: KGPair):
    yield "kg1", kg_pair.kg1
    yield "kg2", kg_pair.kg2


class DegreeDistribution(BaseMetric):
    """In/out/total degree distribution, tail shape and long-tail indicators.

    Rationale: embedding- and structure-based matchers need a minimum number of
    relation triples per entity to place it meaningfully in the vector space.
    A low median degree or a high share of isolated entities therefore predicts
    a structurally hard benchmark.
    """

    name = "degree_distribution"
    category = "structural"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        scalars: dict[str, float] = {}
        tables: dict[str, pd.DataFrame] = {}

        for label, kg in _iter_kgs(kg_pair):
            deg = kg.degrees
            n = max(len(deg), 1)

            for col in ("in_degree", "out_degree", "total_degree"):
                scalars.update(summarize(deg[col].to_numpy(), f"{label}.{col}"))

            total = deg["total_degree"].to_numpy()
            alpha, xmin = powerlaw_alpha(total, xmin=1.0)
            scalars[f"{label}.powerlaw_alpha"] = alpha
            scalars[f"{label}.powerlaw_xmin"] = xmin
            scalars[f"{label}.share_isolated"] = float((total == 0).sum() / n)
            scalars[f"{label}.share_deg_le_2"] = float((total <= 2).sum() / n)
            scalars[f"{label}.share_deg_le_5"] = float((total <= 5).sum() / n)

            hist = log_histogram(total)
            hist.insert(0, "kg", label)
            tables.setdefault("degree_histogram", pd.DataFrame())
            tables["degree_histogram"] = pd.concat(
                [tables["degree_histogram"], hist], ignore_index=True
            )

            deg_out = deg.copy()
            deg_out.insert(0, "kg", label)
            tables.setdefault("entity_degrees", pd.DataFrame())
            tables["entity_degrees"] = pd.concat(
                [tables["entity_degrees"], deg_out], ignore_index=True
            )

        # Pair-level aggregate: the harder of the two KGs dominates matching difficulty.
        scalars["pair.min_median_total_degree"] = min(
            scalars["kg1.total_degree.median"], scalars["kg2.total_degree.median"]
        )
        scalars["pair.max_share_isolated"] = max(
            scalars["kg1.share_isolated"], scalars["kg2.share_isolated"]
        )
        scalars["pair.mean_total_degree"] = float(
            np.mean([scalars["kg1.total_degree.mean"], scalars["kg2.total_degree.mean"]])
        )
        scalars["pair.mean_degree_gini"] = float(
            np.mean([scalars["kg1.total_degree.gini"], scalars["kg2.total_degree.gini"]])
        )
        return MetricResult(name=self.name, scalar_values=scalars, tabular=tables)


class PropertyDistribution(BaseMetric):
    """How triples are spread over relation and attribute properties.

    A schema in which a handful of properties carry almost all triples offers
    little discriminative signal; a very long tail of rare properties makes
    schema-level alignment hard.
    """

    name = "property_distribution"
    category = "structural"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        scalars: dict[str, float] = {}
        rows: list[pd.DataFrame] = []

        for label, kg in _iter_kgs(kg_pair):
            for kind, df, col in (
                ("rel", kg.rel_triples, "relation"),
                ("attr", kg.attr_triples, "attribute"),
            ):
                counts = df[col].value_counts()
                arr = counts.to_numpy()

                scalars[f"{label}.{kind}.n_properties"] = float(len(counts))
                scalars[f"{label}.{kind}.top10_concentration"] = top_k_concentration(arr, 10)
                scalars[f"{label}.{kind}.long_tail_share"] = long_tail_share(arr, 0.01)
                scalars[f"{label}.{kind}.entropy_norm"] = normalized_entropy(arr)
                scalars.update(summarize(arr, f"{label}.{kind}.freq"))

                tab = counts.rename("count").reset_index()
                tab.columns = ["property", "count"]
                tab.insert(0, "kind", kind)
                tab.insert(0, "kg", label)
                tab["share"] = tab["count"] / max(arr.sum(), 1)
                rows.append(tab)

        scalars["pair.mean_rel_entropy_norm"] = float(
            np.mean([scalars["kg1.rel.entropy_norm"], scalars["kg2.rel.entropy_norm"]])
        )
        return MetricResult(
            name=self.name,
            scalar_values=scalars,
            tabular={"property_counts": pd.concat(rows, ignore_index=True)},
        )


class Connectivity(BaseMetric):
    """Connected components, density and clustering of the relation graph.

    Entities in small disconnected components cannot be reached by structural
    propagation, so this bounds what a purely structural matcher can achieve.
    Clustering is estimated on a sample for large graphs (see `sample_nodes`).
    """

    name = "connectivity"
    category = "structural"

    def __init__(self, sample_nodes: int = 5000, seed: int = 42) -> None:
        self.sample_nodes = sample_nodes
        self.seed = seed

    def compute(self, kg_pair: KGPair) -> MetricResult:
        import networkx as nx

        scalars: dict[str, float] = {}
        comp_rows: list[pd.DataFrame] = []

        for label, kg in _iter_kgs(kg_pair):
            g = nx.Graph()
            g.add_nodes_from(kg.entities["entity_uri"])
            g.add_edges_from(zip(kg.rel_triples["head"], kg.rel_triples["tail"], strict=False))
            g.remove_edges_from(nx.selfloop_edges(g))

            n = max(g.number_of_nodes(), 1)
            components = sorted((len(c) for c in nx.connected_components(g)), reverse=True)

            scalars[f"{label}.n_connected_components"] = float(len(components))
            scalars[f"{label}.size_largest_cc"] = float(components[0]) if components else 0.0
            scalars[f"{label}.share_largest_cc"] = float(components[0] / n) if components else 0.0
            scalars[f"{label}.share_singleton_cc"] = float(
                sum(1 for c in components if c == 1) / max(len(components), 1)
            )
            scalars[f"{label}.density"] = float(nx.density(g))
            scalars[f"{label}.avg_clustering"] = self._clustering(g, nx)

            comp_rows.append(
                pd.DataFrame(
                    {
                        "kg": label,
                        "rank": range(1, min(len(components), 20) + 1),
                        "component_size": components[:20],
                    }
                )
            )

        scalars["pair.min_share_largest_cc"] = min(
            scalars["kg1.share_largest_cc"], scalars["kg2.share_largest_cc"]
        )
        return MetricResult(
            name=self.name,
            scalar_values=scalars,
            tabular={"components": pd.concat(comp_rows, ignore_index=True)},
        )

    def _clustering(self, g, nx) -> float:
        """Average clustering coefficient, sampled on graphs above the threshold."""
        if g.number_of_nodes() <= self.sample_nodes:
            return float(nx.average_clustering(g))
        rng = np.random.default_rng(self.seed)
        nodes = list(g.nodes())
        sample = [nodes[i] for i in rng.choice(len(nodes), self.sample_nodes, replace=False)]
        return float(nx.average_clustering(g, nodes=sample))


class LongTail(BaseMetric):
    """Long-tail profile of entity frequency: P(total_degree <= k) for small k.

    Complements the degree summary with the curve that is plotted in the report.
    """

    name = "long_tail"
    category = "structural"

    K_VALUES = (0, 1, 2, 3, 5, 10, 20, 50)

    def compute(self, kg_pair: KGPair) -> MetricResult:
        scalars: dict[str, float] = {}
        rows: list[pd.DataFrame] = []

        for label, kg in _iter_kgs(kg_pair):
            total = kg.degrees["total_degree"].to_numpy()
            n = max(total.size, 1)

            # Combined frequency = structural degree + number of attribute triples.
            attr = kg.entities["entity_uri"].map(kg.attr_count).fillna(0).to_numpy()
            combined = total + attr

            for k in self.K_VALUES:
                scalars[f"{label}.share_total_degree_le_{k}"] = float((total <= k).sum() / n)
            scalars[f"{label}.share_no_information"] = float((combined == 0).sum() / n)
            scalars[f"{label}.mean_facts_per_entity"] = float(combined.mean())

            rows.append(
                pd.DataFrame(
                    {
                        "kg": label,
                        "k": list(self.K_VALUES),
                        "share_le_k": [float((total <= k).sum() / n) for k in self.K_VALUES],
                    }
                )
            )

        return MetricResult(
            name=self.name,
            scalar_values=scalars,
            tabular={"long_tail_curve": pd.concat(rows, ignore_index=True)},
        )


def kg_degree_frame(kg: KnowledgeGraph) -> pd.DataFrame:
    """Public helper so matchers can reuse the cached degree frame."""
    return kg.degrees
