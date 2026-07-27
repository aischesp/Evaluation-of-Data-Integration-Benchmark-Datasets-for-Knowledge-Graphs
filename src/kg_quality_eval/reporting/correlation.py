"""Correlation between dataset characteristics and matcher quality.

This is the step the profiling exists for: it answers "which structural or
semantic property of a benchmark actually predicts how well entity alignment
works on it?".

Caveat that is stated with every result: with a handful of benchmark datasets
the sample size per matcher is tiny, so these correlations are descriptive
indicators of a trend, not significance tests. p-values are reported so the
reader can see exactly how weak the evidence is.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

MIN_DATASETS = 4


def correlate(
    merged: pd.DataFrame,
    metric_columns: list[str],
    target: str = "f1",
    per_matcher: bool = True,
) -> pd.DataFrame:
    """Spearman correlation of every metric column with the matcher target.

    Returns a long frame with one row per (matcher, metric).
    """
    if merged.empty:
        return pd.DataFrame()

    frames = []
    groups = merged.groupby("matcher") if per_matcher else [("__all__", merged)]

    for matcher, group in groups:
        for column in metric_columns:
            if column not in group.columns:
                continue
            x = pd.to_numeric(group[column], errors="coerce").to_numpy(dtype=float)
            y = pd.to_numeric(group[target], errors="coerce").to_numpy(dtype=float)

            mask = np.isfinite(x) & np.isfinite(y)
            if mask.sum() < MIN_DATASETS or np.unique(x[mask]).size < 3:
                continue

            rho, p = spearmanr(x[mask], y[mask])
            if not np.isfinite(rho):
                continue

            frames.append(
                {
                    "matcher": matcher,
                    "metric": column,
                    "spearman_rho": float(rho),
                    "p_value": float(p),
                    "n_datasets": int(mask.sum()),
                    "abs_rho": abs(float(rho)),
                }
            )

    if not frames:
        return pd.DataFrame()

    return (
        pd.DataFrame(frames)
        .sort_values(["matcher", "abs_rho"], ascending=[True, False])
        .reset_index(drop=True)
    )


def top_drivers(correlations: pd.DataFrame, k: int = 8) -> pd.DataFrame:
    """The k strongest correlations per matcher — the table for the slides."""
    if correlations.empty:
        return pd.DataFrame()
    return (
        correlations.groupby("matcher", group_keys=False)
        .head(k)
        .reset_index(drop=True)
    )


def correlation_matrix(
    merged: pd.DataFrame, metric_columns: list[str], target: str = "f1"
) -> pd.DataFrame:
    """Matchers x metrics matrix of Spearman rho, ready for a heatmap."""
    long = correlate(merged, metric_columns, target=target)
    if long.empty:
        return pd.DataFrame()
    return long.pivot(index="matcher", columns="metric", values="spearman_rho")
