"""Cross-dataset comparison tables.

`comparison.csv` is the central artefact of the profiling stage: one row per
dataset, one column per scalar metric. `matching_results.csv` is its counterpart
for the matching stage, and `correlation.csv` joins the two.
"""

from __future__ import annotations

import pandas as pd

# The columns that go into the compact table shown in the report and the slides.
HEADLINE_METRICS = [
    "basic_stats.kg1.n_entities",
    "basic_stats.pair.n_triples_total",
    "basic_stats.kg1.attr_to_rel_ratio",
    "basic_stats.kg2.attr_to_rel_ratio",
    "degree_distribution.pair.mean_total_degree",
    "degree_distribution.pair.min_median_total_degree",
    "degree_distribution.pair.mean_degree_gini",
    "degree_distribution.kg1.powerlaw_alpha",
    "connectivity.pair.min_share_largest_cc",
    "property_distribution.pair.mean_rel_entropy_norm",
    "attribute_completeness.pair.min_share_entities_with_attribute",
    "attribute_completeness.pair.mean_attr_per_entity",
    "attribute_completeness.pair.mean_share_literals_text",
    "schema_heterogeneity.property_jaccard",
    "type_distribution.kg1.share_entities_typed",
    "alignment_metrics.alignment_coverage",
    "alignment_metrics.bijective_share",
    "aligned_consistency.degree_spearman",
    "aligned_consistency.literal_value_jaccard.mean",
    "alignment_reachability.share_pairs_both_in_lcc",
]


def build_comparison(profiles: dict[str, dict[str, dict[str, float]]]) -> pd.DataFrame:
    """Wide table: datasets x flattened `<metric>.<key>` columns."""
    rows = {}
    for dataset, metrics in profiles.items():
        flat: dict[str, float] = {}
        for metric_name, scalars in metrics.items():
            for key, value in scalars.items():
                flat[f"{metric_name}.{key}"] = value
        rows[dataset] = flat

    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = "dataset"
    return df.sort_index(axis=1).reset_index()


def headline_table(comparison: pd.DataFrame) -> pd.DataFrame:
    """The subset of columns that is small enough to print in the report."""
    cols = ["dataset"] + [c for c in HEADLINE_METRICS if c in comparison.columns]
    return comparison[cols]


def matching_table(scores: pd.DataFrame) -> pd.DataFrame:
    """Long matcher results -> matchers as columns, datasets as rows (F1)."""
    if scores.empty:
        return pd.DataFrame()
    return (
        scores.pivot_table(index="dataset", columns="matcher", values="f1")
        .round(4)
        .reset_index()
    )


def merge_metrics_and_scores(comparison: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    """One row per (dataset, matcher) with all dataset metrics attached.

    This is the frame the correlation analysis runs on.
    """
    if scores.empty:
        return pd.DataFrame()
    return scores.merge(comparison, on="dataset", how="left")
