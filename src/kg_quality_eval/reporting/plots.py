"""Figure generation. Every figure is written as PNG into `results/figures/`."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

sns.set_theme(style="whitegrid", context="talk")
PALETTE = "colorblind"


def _save(fig: plt.Figure, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def degree_distributions(
    histograms: dict[str, pd.DataFrame], out_dir: Path, name: str = "degree_distributions"
) -> Path:
    """Log-log degree distribution of every dataset (KG1 and KG2 overlaid)."""
    n = len(histograms)
    ncols = min(3, max(n, 1))
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.5 * ncols, 4.2 * nrows), squeeze=False)

    for ax, (dataset, hist) in zip(axes.ravel(), sorted(histograms.items()), strict=False):
        for kg, sub in hist.groupby("kg"):
            sub = sub[sub["bin_lower"] > 0]
            if sub.empty:
                continue
            ax.plot(sub["bin_lower"], sub["count"], marker="o", ms=4, lw=1.4, label=kg)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(dataset, fontsize=12)
        ax.set_xlabel("total degree")
        ax.set_ylabel("# entities")
        ax.legend(fontsize=9)

    for ax in axes.ravel()[n:]:
        ax.axis("off")

    fig.suptitle("Degree-Verteilung (log-log)", fontsize=16)
    fig.tight_layout()
    return _save(fig, out_dir, name)


def long_tail_curves(curves: dict[str, pd.DataFrame], out_dir: Path) -> Path:
    """Share of entities with total degree <= k, per dataset."""
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for dataset, curve in sorted(curves.items()):
        agg = curve.groupby("k")["share_le_k"].mean()
        ax.plot(agg.index, agg.to_numpy(), marker="o", lw=1.8, label=dataset)
    ax.set_xlabel("k (total degree)")
    ax.set_ylabel("Anteil Entitäten mit deg ≤ k")
    ax.set_title("Long-Tail-Profil der Entitäten")
    ax.legend(fontsize=9)
    return _save(fig, out_dir, "long_tail")


def property_long_tail(counts: dict[str, pd.DataFrame], out_dir: Path) -> Path:
    """Rank-frequency curve of relation properties (Zipf plot)."""
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for dataset, table in sorted(counts.items()):
        sub = table[(table["kind"] == "rel") & (table["kg"] == "kg1")]
        if sub.empty:
            continue
        freq = np.sort(sub["count"].to_numpy())[::-1]
        ax.plot(np.arange(1, freq.size + 1), freq, lw=1.8, label=dataset)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Property-Rang")
    ax.set_ylabel("# Tripel")
    ax.set_title("Property-Häufigkeit (KG1, Relationen)")
    ax.legend(fontsize=9)
    return _save(fig, out_dir, "property_long_tail")


def matcher_scores(scores: pd.DataFrame, out_dir: Path) -> Path:
    """Grouped bar chart of F1 per dataset and matcher."""
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(
        data=scores, x="dataset", y="f1", hue="matcher", ax=ax, palette=PALETTE, edgecolor="none"
    )
    ax.set_ylabel("F1 (Test-Split)")
    ax.set_xlabel("")
    ax.set_ylim(0, 1)
    ax.set_title("Entity-Alignment-Güte je Benchmark und Matcher")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(title="Matcher", fontsize=9, ncol=2)
    return _save(fig, out_dir, "matcher_f1")


def precision_recall(scores: pd.DataFrame, out_dir: Path) -> Path:
    """Precision vs. recall scatter — shows the different operating points."""
    fig, ax = plt.subplots(figsize=(8, 6.5))
    sns.scatterplot(
        data=scores, x="recall", y="precision", hue="matcher", style="dataset",
        s=140, ax=ax, palette=PALETTE,
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_title("Precision vs. Recall")
    ax.legend(fontsize=8, ncol=2, loc="lower left")
    return _save(fig, out_dir, "precision_recall")


def correlation_heatmap(matrix: pd.DataFrame, out_dir: Path) -> Path | None:
    """Matcher x metric heatmap of Spearman correlations with F1."""
    if matrix.empty:
        return None

    short = matrix.copy()
    short.columns = [_short_label(c) for c in short.columns]

    fig, ax = plt.subplots(figsize=(max(10, 0.55 * short.shape[1]), 1.1 * short.shape[0] + 3))
    sns.heatmap(
        short, cmap="vlag", center=0, vmin=-1, vmax=1, annot=True, fmt=".2f",
        annot_kws={"size": 8}, cbar_kws={"label": "Spearman ρ mit F1"}, ax=ax,
    )
    ax.set_title("Welche Datensatz-Eigenschaften erklären die Matching-Güte?")
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    return _save(fig, out_dir, "correlation_heatmap")


def metric_vs_f1(
    merged: pd.DataFrame, metric: str, out_dir: Path, name: str | None = None
) -> Path | None:
    """Scatter of one dataset metric against F1, one series per matcher."""
    if merged.empty or metric not in merged.columns:
        return None

    fig, ax = plt.subplots(figsize=(9, 6))
    sns.scatterplot(data=merged, x=metric, y="f1", hue="matcher", s=140, ax=ax, palette=PALETTE)
    for _matcher, group in merged.groupby("matcher"):
        g = group.dropna(subset=[metric, "f1"]).sort_values(metric)
        if len(g) >= 3:
            ax.plot(g[metric], g["f1"], lw=1.0, alpha=0.45)
    ax.set_xlabel(_short_label(metric))
    ax.set_ylabel("F1 (Test-Split)")
    ax.set_title(f"F1 vs. {_short_label(metric)}")
    ax.legend(fontsize=9)
    return _save(fig, out_dir, name or f"f1_vs_{_short_label(metric).replace('.', '_')}")


def attribute_coverage(coverages: dict[str, pd.DataFrame], out_dir: Path, top_n: int = 15) -> Path:
    """Coverage of the most frequent attribute properties per dataset (KG1)."""
    n = len(coverages)
    ncols = min(3, max(n, 1))
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.2 * ncols, 4.6 * nrows), squeeze=False)

    for ax, (dataset, table) in zip(axes.ravel(), sorted(coverages.items()), strict=False):
        sub = table[table["kg"] == "kg1"].nlargest(top_n, "coverage").copy()
        sub["label"] = [_short_label(p) for p in sub["attribute"]]
        sns.barplot(data=sub, y="label", x="coverage", ax=ax, color="#4c72b0")
        ax.set_title(dataset, fontsize=11)
        ax.set_xlabel("Anteil Entitäten mit Property")
        ax.set_ylabel("")
        ax.tick_params(axis="y", labelsize=8)

    for ax in axes.ravel()[n:]:
        ax.axis("off")

    fig.suptitle("Attribut-Vollständigkeit: Top-Properties (KG1)", fontsize=15)
    fig.tight_layout()
    return _save(fig, out_dir, "attribute_coverage")


def backend_runtime(runtimes: pd.DataFrame, out_dir: Path) -> Path | None:
    """Pandas vs. PySpark runtime per dataset."""
    if runtimes.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.barplot(data=runtimes, x="dataset", y="runtime_s", hue="backend", ax=ax, palette=PALETTE)
    ax.set_ylabel("Laufzeit [s]")
    ax.set_xlabel("")
    ax.set_yscale("log")
    ax.set_title("Kernmetriken: Pandas vs. PySpark")
    ax.tick_params(axis="x", rotation=20)
    return _save(fig, out_dir, "backend_runtime")


def _short_label(text: str) -> str:
    """Shorten metric keys and property URIs for axis labels."""
    for sep in ("#", "/"):
        if text.startswith("http") and sep in text:
            text = text.rsplit(sep, 1)[1]
    parts = text.split(".")
    return ".".join(parts[-3:]) if len(parts) > 3 else text
