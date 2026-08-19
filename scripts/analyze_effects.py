#!/usr/bin/env python
"""Controlled contrasts on the extended run: density, scale and source effects.

The correlation analysis is observational — many dataset properties move
together, so a high rho does not identify a cause. The OpenEA family however
allows genuinely controlled comparisons, because its variants differ in exactly
one dimension while everything else is held constant:

    V1 vs. V2     same entities, same source pair, same size — only density
    15K vs. 100K  same source pair, same density — only scale
    source pair   same size, same density — only schema heterogeneity

This script extracts those contrasts and writes them next to the extended run.

    python scripts/analyze_effects.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kg_quality_eval.utils.console import enable_utf8_output  # noqa: E402

enable_utf8_output()

sns.set_theme(style="whitegrid", context="talk")

NAME = re.compile(r"^(?P<pair>[A-Z_]+?)_(?P<scale>\d+K)_(?P<density>V\d)$")
MATCHER_ORDER = ["value_overlap", "pyjedai_ngram", "structural_propagation", "paris"]


def annotate(scores: pd.DataFrame) -> pd.DataFrame:
    """Split the dataset name into its three experimental factors."""
    parsed = scores["dataset"].str.extract(NAME)
    out = pd.concat([scores, parsed], axis=1)
    missing = out["pair"].isna().sum()
    if missing:
        print(f"⚠ {missing} Datensätze folgen nicht dem OpenEA-Namensschema und entfallen")
    return out.dropna(subset=["pair", "scale", "density"])


def contrast(data: pd.DataFrame, factor: str, low: str, high: str) -> pd.DataFrame:
    """Mean F1 at both factor levels, paired over everything else."""
    others = [c for c in ("pair", "scale", "density") if c != factor]
    wide = data.pivot_table(index=["matcher", *others], columns=factor, values="f1")
    if low not in wide.columns or high not in wide.columns:
        return pd.DataFrame()

    wide = wide.dropna(subset=[low, high])
    wide["delta"] = wide[high] - wide[low]

    summary = wide.groupby("matcher")[[low, high, "delta"]].mean()
    summary["n_pairs"] = wide.groupby("matcher").size()
    return summary.reindex([m for m in MATCHER_ORDER if m in summary.index]).round(3)


def plot_contrast(summary: pd.DataFrame, low: str, high: str, title: str, path: Path) -> None:
    if summary.empty:
        return

    long = (
        summary[[low, high]]
        .reset_index()
        .melt(id_vars="matcher", var_name="Variante", value_name="f1")
    )
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(data=long, x="matcher", y="f1", hue="Variante", ax=ax, palette="colorblind")

    for i, matcher in enumerate(summary.index):
        delta = summary.loc[matcher, "delta"]
        ax.text(
            i, max(summary.loc[matcher, low], summary.loc[matcher, high]) + 0.03,
            f"{delta:+.2f}", ha="center", fontsize=12,
            color="#2a7f3f" if delta > 0 else "#b3402f", fontweight="bold",
        )

    ax.set_ylim(0, 1.08)
    ax.set_ylabel("ø F1 (Test-Split)")
    ax.set_xlabel("")
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=15)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", default="results/reports_extended")
    parser.add_argument("--figures", default="results/figures_extended")
    args = parser.parse_args()

    reports, figures = Path(args.reports), Path(args.figures)
    figures.mkdir(parents=True, exist_ok=True)

    scores = pd.read_csv(reports / "matching_results.csv")
    data = annotate(scores)

    contrasts = {
        "density": (contrast(data, "density", "V1", "V2"), "V1", "V2",
                    "Dichte-Effekt: identische Entitäten, doppelt so viele Tripel"),
        "scale": (contrast(data, "scale", "15K", "100K"), "15K", "100K",
                  "Skalen-Effekt: 15 K → 100 K Entitäten"),
    }

    frames = []
    for name, (summary, low, high, title) in contrasts.items():
        if summary.empty:
            continue
        print(f"\n=== {title} ===")
        print(summary.to_string())

        out = summary.reset_index()
        out.insert(0, "contrast", name)
        out = out.rename(columns={low: "level_low", high: "level_high"})
        frames.append(out)

        plot_contrast(summary, low, high, title, figures / f"contrast_{name}.png")

    # Source-pair comparison: all four pairs side by side, densities pooled.
    by_pair = (
        data.pivot_table(index="matcher", columns="pair", values="f1")
        .reindex([m for m in MATCHER_ORDER if m in data["matcher"].unique()])
        .round(3)
    )
    print("\n=== Quellenpaar-Vergleich (ø F1 über Größen und Dichten) ===")
    print(by_pair.to_string())
    by_pair.to_csv(reports / "effect_by_source_pair.csv")

    if frames:
        pd.concat(frames, ignore_index=True).to_csv(reports / "controlled_contrasts.csv", index=False)
        print(f"\n✓ {reports / 'controlled_contrasts.csv'}")


if __name__ == "__main__":
    main()
