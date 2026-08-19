#!/usr/bin/env python
"""Fehler-Taxonomie über alle Datensätze und Matcher.

Die Korrelationsanalyse zeigt, *dass* eine Datensatz-Eigenschaft mit der
Matching-Güte zusammenhängt. Dieses Skript geht eine Ebene tiefer und ordnet
jeden einzelnen Fehler einer Ursache zu — und trennt dabei die Fehler, die der
Benchmark verursacht (kein Verfahren kann sie lösen), von denen, die am
Verfahren liegen.

    python scripts/analyze_errors.py --config config/datasets.yaml

Setzt einen abgeschlossenen Pipeline-Lauf voraus, weil die vorhergesagten Paare
aus `results/reports/<dataset>/matching/<matcher>_pairs.csv` gelesen werden.

Ausgabe:
    error_taxonomy.csv          Verteilung der Fehlerklassen
    error_solvability.csv       benchmark- vs. verfahrensbedingte Fehler
    error_examples.csv          Stichprobe klassifizierter Einzelfaelle
    figures/error_taxonomy.png  gestapelte Anteile je Matcher
"""

from __future__ import annotations

import argparse
import logging
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kg_quality_eval.loaders import get_loader  # noqa: E402
from kg_quality_eval.matching import REGISTRY as MATCHERS  # noqa: E402
from kg_quality_eval.preprocessing.nonmatch import inject_non_matches  # noqa: E402
from kg_quality_eval.reporting import error_taxonomy as tax  # noqa: E402
from kg_quality_eval.utils.config import load_config  # noqa: E402

sns.set_theme(style="whitegrid", context="talk")
log = logging.getLogger("errors")

# Von "nicht lösbar" nach "lösbar, aber falsch gelöst".
PLOT_ORDER = [
    "correct", "wrong_candidate", "abstained", "no_shared_literal",
    "structurally_unreachable", "no_signal", "false_on_unmatched",
]
COLORS = {
    "correct": "#4c9f70",
    "wrong_candidate": "#d1615d",
    "abstained": "#e8a33d",
    "no_shared_literal": "#c47ec4",
    "structurally_unreachable": "#6a8fd1",
    "no_signal": "#8c8c8c",
    "false_on_unmatched": "#7d4a4a",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/datasets.yaml")
    parser.add_argument("--reports", default="results/reports")
    parser.add_argument("--figures", default="results/figures")
    parser.add_argument("--datasets", nargs="*")
    parser.add_argument("--examples-per-class", type=int, default=3)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    warnings.filterwarnings("ignore")

    cfg = load_config(args.config)
    reports = Path(args.reports)
    datasets = cfg.datasets
    if args.datasets:
        datasets = [d for d in datasets if d.name in args.datasets]

    summaries, examples = [], []
    for ds in datasets:
        pairs_dir = reports / ds.name / "matching"
        if not pairs_dir.is_dir():
            log.warning("%s: keine Vorhersagen unter %s — übersprungen", ds.name, pairs_dir)
            continue

        log.info("── %s ──", ds.name)
        kg_pair = get_loader(ds.loader, fold=ds.fold).load(Path(ds.path))
        kg_pair.name = ds.name
        if ds.match_ratio is not None:
            kg_pair = inject_non_matches(kg_pair, ds.match_ratio, seed=ds.non_match_seed)
            kg_pair.name = ds.name

        for mc in cfg.matchers:
            path = pairs_dir / f"{mc.name}_pairs.csv"
            if not path.exists():
                continue
            predictions = pd.read_csv(path, dtype={"e1": str, "e2": str}, na_filter=False)

            # Die Signalfamilie entscheidet, welches fehlende Signal als
            # unloesbar gilt — ein struktureller Matcher scheitert nicht an
            # fehlenden Literalen.
            family = getattr(MATCHERS.get(mc.name), "family", "holistic")
            classified = tax.classify(
                kg_pair, predictions, split=cfg.eval_split, family=family
            )
            summary = tax.summarize(classified, ds.name, mc.name)
            summaries.append(summary)

            sample = (
                classified[classified["error_class"] != "correct"]
                .groupby("error_class", group_keys=False)
                .head(args.examples_per_class)
                .assign(dataset=ds.name, matcher=mc.name)
            )
            examples.append(sample)

            shares = summary.set_index("error_class")["share"]
            log.info(
                "   %-24s [%-10s] korrekt %.2f | falscher Kandidat %.2f | "
                "enthalten %.2f | blockiert %.2f",
                mc.name, family, shares.get("correct", 0),
                shares.get("wrong_candidate", 0), shares.get("abstained", 0),
                sum(shares.get(c, 0) for c in tax.UNSOLVABLE),
            )

    if not summaries:
        raise SystemExit("Keine Vorhersagen gefunden — erst die Pipeline laufen lassen.")

    out = reports
    taxonomy = pd.concat(summaries, ignore_index=True)
    taxonomy.to_csv(out / "error_taxonomy.csv", index=False)

    solvability = tax.solvability(taxonomy)
    solvability.to_csv(out / "error_solvability.csv", index=False)

    pd.concat(examples, ignore_index=True).to_csv(out / "error_examples.csv", index=False)

    _plot(taxonomy, Path(args.figures))

    print("\n=== Fehlerklassen je Matcher (Mittel über die Datensätze) ===")
    pivot = (
        taxonomy.groupby(["matcher", "error_class"])["share"].mean()
        .unstack().reindex(columns=[c for c in PLOT_ORDER if c in taxonomy["error_class"].values])
    )
    print(pivot.round(3).to_string())

    print("\n=== Wie viel der Fehler geht auf den Benchmark, wie viel aufs Verfahren? ===")
    agg = solvability.groupby("matcher")[["unsolvable_share", "method_share"]].mean()
    print(agg.round(3).to_string())

    print(f"\n✓ {out / 'error_taxonomy.csv'}")


def _plot(taxonomy: pd.DataFrame, figures: Path) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    pivot = (
        taxonomy.groupby(["matcher", "error_class"])["share"].mean().unstack().fillna(0)
    )
    classes = [c for c in PLOT_ORDER if c in pivot.columns]
    pivot = pivot[classes]

    fig, ax = plt.subplots(figsize=(13, 6))
    bottom = [0.0] * len(pivot)
    for cls in classes:
        ax.bar(
            pivot.index, pivot[cls], bottom=bottom,
            label=cls, color=COLORS.get(cls), edgecolor="white", linewidth=0.6,
        )
        bottom = [b + v for b, v in zip(bottom, pivot[cls], strict=False)]

    ax.set_ylabel("Anteil der Test-Entitäten")
    ax.set_ylim(0, 1)
    ax.set_title("Woran scheitern die Matcher?")
    ax.tick_params(axis="x", rotation=15)
    ax.legend(fontsize=9, loc="center left", bbox_to_anchor=(1.01, 0.5),
              title="Fehlerklasse")
    fig.savefig(figures / "error_taxonomy.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ {figures / 'error_taxonomy.png'}")


if __name__ == "__main__":
    main()
