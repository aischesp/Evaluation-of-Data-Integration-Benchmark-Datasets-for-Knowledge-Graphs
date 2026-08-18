"""Quality metrics: attribute completeness, types, consistency, schema heterogeneity.

Section 3 of docs/Metriken-Katalog.md (except the alignment group, which lives
in metrics/alignment.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from kg_quality_eval.core import KGPair
from kg_quality_eval.metrics.base import BaseMetric, MetricResult
from kg_quality_eval.utils.literals import namespace, normalize_value, parse_literal
from kg_quality_eval.utils.stats import normalized_entropy, summarize

TYPE_PREDICATES = (
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "http://www.wikidata.org/entity/P31",
    "rdf:type",
    "type",
)


def _iter_kgs(kg_pair: KGPair):
    yield "kg1", kg_pair.kg1
    yield "kg2", kg_pair.kg2


class AttributeCompleteness(BaseMetric):
    """How much literal information the entities actually carry.

    Textual/embedding matchers encode an entity from its literals, so coverage
    of attribute properties is a direct predictor of their performance. The
    per-property coverage table also exposes property-mapping gaps between the
    two KGs of a pair.
    """

    name = "attribute_completeness"
    category = "quality"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        scalars: dict[str, float] = {}
        cov_rows: list[pd.DataFrame] = []

        for label, kg in _iter_kgs(kg_pair):
            n_ent = max(kg.n_entities(), 1)
            attr = kg.attr_triples

            covered = attr["head"].nunique()
            scalars[f"{label}.share_entities_with_attribute"] = covered / n_ent
            scalars[f"{label}.mean_attr_per_entity"] = len(attr) / n_ent
            scalars[f"{label}.mean_distinct_attr_per_entity"] = (
                attr.groupby("head")["attribute"].nunique().sum() / n_ent
            )

            per_prop = attr.groupby("attribute")["head"].nunique() / n_ent
            scalars[f"{label}.property_coverage.mean"] = float(per_prop.mean()) if len(per_prop) else 0.0
            scalars[f"{label}.property_coverage.median"] = (
                float(per_prop.median()) if len(per_prop) else 0.0
            )
            scalars[f"{label}.property_coverage.max"] = float(per_prop.max()) if len(per_prop) else 0.0
            scalars[f"{label}.n_properties_cov_gt_10pct"] = float((per_prop > 0.10).sum())

            # Datatype mix — how much of the literal mass is actually text?
            dtypes = attr["datatype"].value_counts(normalize=True)
            scalars[f"{label}.share_literals_text"] = float(
                dtypes.get("string", 0.0) + dtypes.get("langString", 0.0)
            )
            scalars[f"{label}.share_literals_numeric"] = float(
                sum(v for k, v in dtypes.items() if k in ("numeric", "integer", "double", "float")
                    or "nonNegativeInteger" in str(k))
            )
            scalars[f"{label}.share_literals_date"] = float(
                sum(v for k, v in dtypes.items() if "date" in str(k).lower())
            )
            scalars[f"{label}.mean_literal_length"] = float(
                attr["literal"].str.len().mean() if len(attr) else 0.0
            )

            tab = per_prop.rename("coverage").reset_index()
            tab.insert(0, "kg", label)
            cov_rows.append(tab.sort_values("coverage", ascending=False))

        scalars["pair.min_share_entities_with_attribute"] = min(
            scalars["kg1.share_entities_with_attribute"], scalars["kg2.share_entities_with_attribute"]
        )
        scalars["pair.mean_attr_per_entity"] = float(
            np.mean([scalars["kg1.mean_attr_per_entity"], scalars["kg2.mean_attr_per_entity"]])
        )
        scalars["pair.mean_share_literals_text"] = float(
            np.mean([scalars["kg1.share_literals_text"], scalars["kg2.share_literals_text"]])
        )
        return MetricResult(
            name=self.name,
            scalar_values=scalars,
            tabular={"property_coverage": pd.concat(cov_rows, ignore_index=True)},
        )


class TypeDistribution(BaseMetric):
    """Class/type information available in the graphs.

    Type triples are searched in both relation triples (rdf:type, wdt:P31) and
    attribute triples. On the OpenEA benchmarks this is mostly empty — which is
    itself a finding, because type-aware matchers have nothing to work with.
    """

    name = "type_distribution"
    category = "quality"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        scalars: dict[str, float] = {}
        rows: list[pd.DataFrame] = []
        type_sets: dict[str, set[str]] = {}

        for label, kg in _iter_kgs(kg_pair):
            n_ent = max(kg.n_entities(), 1)
            rel = kg.rel_triples
            type_triples = rel[rel["relation"].isin(TYPE_PREDICATES)]

            counts = type_triples["tail"].value_counts()
            type_sets[label] = set(counts.index)

            scalars[f"{label}.n_type_triples"] = float(len(type_triples))
            scalars[f"{label}.n_distinct_types"] = float(len(counts))
            scalars[f"{label}.share_entities_typed"] = float(
                type_triples["head"].nunique() / n_ent
            )
            scalars[f"{label}.type_entropy_norm"] = normalized_entropy(counts.to_numpy())

            if len(counts):
                tab = counts.rename("count").reset_index()
                tab.columns = ["type", "count"]
                tab.insert(0, "kg", label)
                rows.append(tab.head(50))

        inter = len(type_sets["kg1"] & type_sets["kg2"])
        union = len(type_sets["kg1"] | type_sets["kg2"])
        scalars["pair.type_jaccard"] = float(inter / union) if union else 0.0

        table = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
            columns=["kg", "type", "count"]
        )
        return MetricResult(name=self.name, scalar_values=scalars, tabular={"types": table})


class SchemaHeterogeneity(BaseMetric):
    """How differently the two KGs of a pair describe the same world.

    High heterogeneity (disjoint vocabularies, disjoint namespaces) is the case
    schema-agnostic matchers are built for and where schema-reliant ones fail.
    """

    name = "schema_heterogeneity"
    category = "quality"

    def compute(self, kg_pair: KGPair) -> MetricResult:
        kg1, kg2 = kg_pair.kg1, kg_pair.kg2

        rel1, rel2 = set(kg1.rel_triples["relation"]), set(kg2.rel_triples["relation"])
        att1, att2 = set(kg1.attr_triples["attribute"]), set(kg2.attr_triples["attribute"])

        ns1 = {namespace(u) for u in rel1 | att1}
        ns2 = {namespace(u) for u in rel2 | att2}
        ens1 = {namespace(u) for u in kg1.entities["entity_uri"]}
        ens2 = {namespace(u) for u in kg2.entities["entity_uri"]}

        scalars = {
            "rel_property_jaccard": _jaccard(rel1, rel2),
            "attr_property_jaccard": _jaccard(att1, att2),
            "property_jaccard": _jaccard(rel1 | att1, rel2 | att2),
            "property_namespace_jaccard": _jaccard(ns1, ns2),
            "entity_namespace_jaccard": _jaccard(ens1, ens2),
            "n_shared_rel_properties": float(len(rel1 & rel2)),
            "n_shared_attr_properties": float(len(att1 & att2)),
            "vocab_size_ratio": float(
                min(len(rel1 | att1), len(rel2 | att2)) / max(len(rel1 | att1), len(rel2 | att2), 1)
            ),
        }

        shared = sorted(rel1 & rel2)[:50] + sorted(att1 & att2)[:50]
        table = pd.DataFrame({"shared_property": shared})
        return MetricResult(name=self.name, scalar_values=scalars, tabular={"shared_properties": table})


class AlignedEntityConsistency(BaseMetric):
    """Are the two sides of a gold pair actually described comparably?

    Measures degree correlation, attribute-property overlap and literal-value
    overlap over the reference alignment. Low values mean the gold standard
    links entities whose descriptions barely overlap — hard for every matcher
    and a genuine quality problem of the benchmark.
    """

    name = "aligned_consistency"
    category = "quality"

    def __init__(self, sample_pairs: int = 5000, seed: int = 42) -> None:
        self.sample_pairs = sample_pairs
        self.seed = seed

    def compute(self, kg_pair: KGPair) -> MetricResult:
        from scipy.stats import pearsonr, spearmanr

        # Konsistenz ist nur fuer echte Paare definiert.
        align = kg_pair.matched().drop_duplicates(subset=["e1", "e2"])
        if align.empty:
            return MetricResult(name=self.name, scalar_values={})

        d1 = kg_pair.kg1.degrees.set_index("entity_uri")["total_degree"]
        d2 = kg_pair.kg2.degrees.set_index("entity_uri")["total_degree"]

        deg1 = align["e1"].map(d1).fillna(0).to_numpy(dtype=float)
        deg2 = align["e2"].map(d2).fillna(0).to_numpy(dtype=float)

        scalars: dict[str, float] = {
            "n_pairs_evaluated": float(len(align)),
            "degree_pearson": _safe_corr(pearsonr, deg1, deg2),
            "degree_spearman": _safe_corr(spearmanr, deg1, deg2),
            "mean_abs_degree_diff": float(np.abs(deg1 - deg2).mean()),
            "share_pairs_one_side_isolated": float(((deg1 == 0) | (deg2 == 0)).mean()),
            "share_pairs_both_isolated": float(((deg1 == 0) & (deg2 == 0)).mean()),
        }
        scalars.update(summarize(np.abs(deg1 - deg2), "abs_degree_diff"))

        a1 = kg_pair.kg1.attr_count
        a2 = kg_pair.kg2.attr_count
        na1 = align["e1"].map(a1).fillna(0).to_numpy(dtype=float)
        na2 = align["e2"].map(a2).fillna(0).to_numpy(dtype=float)
        scalars["attr_count_spearman"] = _safe_corr(spearmanr, na1, na2)
        scalars["share_pairs_one_side_no_attr"] = float(((na1 == 0) | (na2 == 0)).mean())

        # Literal-value overlap on a sample (the expensive part).
        sample = align.sample(
            n=min(self.sample_pairs, len(align)), random_state=self.seed
        )
        vals1 = _value_sets(kg_pair.kg1.attr_triples, set(sample["e1"]))
        vals2 = _value_sets(kg_pair.kg2.attr_triples, set(sample["e2"]))

        jaccards, containments = [], []
        for e1, e2 in zip(sample["e1"], sample["e2"], strict=False):
            s1, s2 = vals1.get(e1, set()), vals2.get(e2, set())
            if not s1 or not s2:
                jaccards.append(0.0)
                containments.append(0.0)
                continue
            inter = len(s1 & s2)
            jaccards.append(inter / len(s1 | s2))
            containments.append(inter / min(len(s1), len(s2)))

        scalars["literal_value_jaccard.mean"] = float(np.mean(jaccards)) if jaccards else 0.0
        scalars["literal_value_containment.mean"] = (
            float(np.mean(containments)) if containments else 0.0
        )
        scalars["share_pairs_no_shared_literal"] = (
            float(np.mean([j == 0.0 for j in jaccards])) if jaccards else 1.0
        )

        table = pd.DataFrame(
            {
                "e1": sample["e1"].to_numpy(),
                "e2": sample["e2"].to_numpy(),
                "literal_jaccard": jaccards,
                "literal_containment": containments,
            }
        )
        return MetricResult(
            name=self.name, scalar_values=scalars, tabular={"pair_consistency_sample": table}
        )


def _value_sets(attr: pd.DataFrame, heads: set[str]) -> dict[str, set[str]]:
    sub = attr[attr["head"].isin(heads)]
    out: dict[str, set[str]] = {}
    for head, literal in zip(sub["head"], sub["literal"], strict=False):
        value = normalize_value(literal)
        if value:
            out.setdefault(head, set()).add(value)
    return out


def _jaccard(a: set, b: set) -> float:
    union = len(a | b)
    return float(len(a & b) / union) if union else 0.0


def _safe_corr(fn, x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    try:
        return float(fn(x, y)[0])
    except Exception:  # noqa: BLE001 - correlation is a reporting nicety, never fatal
        return float("nan")


def datatype_of(literal: str) -> str:
    """Re-exported for the loaders, which annotate the datatype column."""
    return parse_literal(literal)[1]
