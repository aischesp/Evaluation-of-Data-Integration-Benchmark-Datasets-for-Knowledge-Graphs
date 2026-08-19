"""Correlation between dataset characteristics and matcher quality.

This is the step the profiling exists for: it answers "which structural or
semantic property of a benchmark actually predicts how well entity alignment
works on it?".

Caveat that is stated with every result: with a handful of benchmark datasets
the sample size per matcher is tiny, so these correlations are **descriptive
indicators of a trend, not significance tests**.

Zwei Gründe, warum die p-Werte nicht als Signifikanztest gelesen werden dürfen:

1. **Multiples Testen.** Über alle Matcher und Metriken werden Dutzende
   Korrelationen gerechnet. Bei 48 Tests und α = 0,05 wäre schon zufällig mit
   rund zwei "signifikanten" Ergebnissen zu rechnen. Die Ausgabe enthält
   deshalb `p_bonferroni` und `p_fdr` (Benjamini-Hochberg) neben dem rohen
   Wert — und die Spalte `survives_bonferroni`, die auf unseren Daten für
   genau einen der 48 Tests wahr ist.
2. **Abhängige Stichprobe.** Die 16 OpenEA-Varianten sind 4 Quellenpaare × 2
   Grössen × 2 Dichtestufen, also keine unabhängigen Ziehungen. Die effektive
   Stichprobe ist kleiner als n = 16.

Das tragende Argument des Projekts sind deshalb die kontrollierten Vergleiche
(V1 gegen V2 bei identischer Entitätsmenge) und das *Vorzeichenmuster* über die
Matcher-Familien hinweg — nicht einzelne p-Werte.
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

    out = pd.DataFrame(frames)
    return (
        adjust_p_values(out)
        .sort_values(["matcher", "abs_rho"], ascending=[True, False])
        .reset_index(drop=True)
    )


def adjust_p_values(frame: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    """Ergänzt Bonferroni- und Benjamini-Hochberg-korrigierte p-Werte.

    Die Korrektur läuft über *alle* Tests der Tabelle, also über Matcher und
    Metriken hinweg — das ist die Familie, aus der die berichteten Ergebnisse
    ausgewählt werden.
    """
    if frame.empty:
        return frame

    out = frame.copy()
    n = len(out)
    out["n_tests"] = n
    out["p_bonferroni"] = (out["p_value"] * n).clip(upper=1.0)
    out["survives_bonferroni"] = out["p_value"] < (alpha / n)

    # Benjamini-Hochberg: p-Werte aufsteigend, p * n / Rang, dann monoton machen.
    order = out["p_value"].rank(method="first").astype(int)
    scaled = (out["p_value"] * n / order).clip(upper=1.0)
    ranked = scaled.sort_values(ascending=False)
    out["p_fdr"] = ranked.cummin().reindex(out.index)
    out["survives_fdr"] = out["p_fdr"] < alpha
    return out


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
