#!/usr/bin/env python
"""Fünf-Fold-Kreuzvalidierung: Streuung statt Punktschätzern.

Bisher stand jede Zahl im Projekt für genau einen Fold. Ein Unterschied von
+0,24 F1 ist ohne Streuungsangabe nicht einzuordnen — er könnte weit über oder
knapp innerhalb des Rauschens liegen.

OpenEA liefert fünf disjunkte 721-Splits je Datensatz. Dieses Skript rechnet
alle Matcher auf allen fünf Folds und aggregiert zu Mittelwert und
Standardabweichung. Das entspricht dem Protokoll, das Sun et al. (2020,
PVLDB 13(11)) für dieselben Datensätze verwenden: ein Fold (20 %) als Seeds,
10 % Validierung, 70 % Test.

Die Profiling-Metriken werden nicht je Fold neu gerechnet: die Folds
partitionieren dasselbe Referenz-Alignment, die Graphen und damit alle
Struktur- und Qualitätsmetriken sind identisch. Nur die Matcher hängen vom
Fold ab, weil sich ihre Seed-Menge ändert.

    python scripts/run_folds.py --config config/datasets.yaml

Ausgabe:
    results/reports/fold_scores.csv     eine Zeile je (Fold, Datensatz, Matcher)
    results/reports/fold_variance.csv   Mittel und Streuung je (Datensatz, Matcher)
    results/figures/fold_variance.png   F1 mit Fehlerbalken
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kg_quality_eval.loaders import get_loader  # noqa: E402
from kg_quality_eval.matching import evaluate, get_matcher  # noqa: E402
from kg_quality_eval.preprocessing.nonmatch import inject_non_matches  # noqa: E402
from kg_quality_eval.utils.config import load_config  # noqa: E402

sns.set_theme(style="whitegrid", context="talk")
log = logging.getLogger("folds")

MATCHER_ORDER = ["value_overlap", "pyjedai_ngram", "structural_propagation", "paris"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/datasets.yaml")
    parser.add_argument("--folds", type=int, nargs="*", default=[1, 2, 3, 4, 5])
    parser.add_argument(
        "--datasets", nargs="*",
        help="Standard: alle aus der Config ausser den 100K-Varianten (Laufzeit).",
    )
    parser.add_argument("--out", default="results/reports")
    parser.add_argument("--figures", default="results/figures")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    warnings.filterwarnings("ignore")

    cfg = load_config(args.config)
    datasets = cfg.datasets
    if args.datasets:
        datasets = [d for d in datasets if d.name in args.datasets]
    else:
        # Die 100K-Varianten kosten je Fold ein Vielfaches der 15K-Läufe und
        # tragen zur Streuungsschätzung nichts bei, was die fünf kleineren
        # nicht schon zeigen.
        datasets = [d for d in datasets if "100K" not in d.name]

    rows = []
    for fold in args.folds:
        log.info("═══ Fold %d ═══", fold)
        for ds in datasets:
            kg_pair = get_loader(ds.loader, fold=fold).load(Path(ds.path))
            kg_pair.name = ds.name
            if ds.match_ratio is not None:
                kg_pair = inject_non_matches(kg_pair, ds.match_ratio, seed=ds.non_match_seed)
                kg_pair.name = ds.name
            seeds = kg_pair.matched(cfg.seed_split)

            for mc in cfg.matchers:
                if mc.name in ds.skip_matchers:
                    continue
                try:
                    matcher = get_matcher(mc.name, **mc.params)
                    start = time.perf_counter()
                    result = matcher.match(kg_pair, seeds if matcher.requires_seeds else None)
                    runtime = time.perf_counter() - start
                except Exception as exc:  # noqa: BLE001 - ein Matcher darf den Lauf nicht kippen
                    log.error("   %-24s FEHLER: %s", mc.name, exc)
                    continue

                score = evaluate(result, kg_pair, split=cfg.eval_split)
                rows.append(
                    {
                        "fold": fold, "dataset": ds.name, "matcher": mc.name,
                        "precision": score.precision, "recall": score.recall,
                        "f1": score.f1, "abstain_rate": score.abstain_rate,
                        "n_false_on_unmatched": score.n_false_on_unmatched,
                        "runtime_s": runtime,
                    }
                )
                log.info(
                    "   %-14s %-24s F1=%.3f  P=%.3f  (%.0fs)",
                    ds.name, mc.name, score.f1, score.precision, runtime,
                )

    if not rows:
        raise SystemExit("Keine Ergebnisse.")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    scores = pd.DataFrame(rows)
    scores.to_csv(out / "fold_scores.csv", index=False)

    variance = (
        scores.groupby(["dataset", "matcher"])
        .agg(
            f1_mean=("f1", "mean"), f1_std=("f1", "std"),
            f1_min=("f1", "min"), f1_max=("f1", "max"),
            precision_mean=("precision", "mean"), precision_std=("precision", "std"),
            n_folds=("f1", "count"),
        )
        .reset_index()
    )
    variance.to_csv(out / "fold_variance.csv", index=False)

    per_matcher = (
        scores.groupby("matcher")
        .agg(f1_mean=("f1", "mean"), f1_std=("f1", "std"))
        .reindex([m for m in MATCHER_ORDER if m in scores["matcher"].unique()])
        .reset_index()
    )
    per_matcher.to_csv(out / "fold_variance_by_matcher.csv", index=False)

    _plot(variance, Path(args.figures))

    print("\n=== F1 je Datensatz und Matcher: Mittel ± Streuung über die Folds ===")
    table = variance.copy()
    table["f1"] = table.apply(lambda r: f"{r.f1_mean:.3f} ± {r.f1_std:.3f}", axis=1)
    print(table.pivot(index="dataset", columns="matcher", values="f1").to_string())

    print("\n=== Streuung je Matcher (über alle Datensätze und Folds) ===")
    print(per_matcher.round(4).to_string(index=False))

    print(f"\n✓ {out / 'fold_variance.csv'}")


def _plot(variance: pd.DataFrame, figures: Path) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    matchers = [m for m in MATCHER_ORDER if m in variance["matcher"].unique()]
    datasets = sorted(variance["dataset"].unique())

    fig, ax = plt.subplots(figsize=(12, 6))
    width = 0.8 / max(len(matchers), 1)
    palette = sns.color_palette("colorblind", len(matchers))

    for i, matcher in enumerate(matchers):
        sub = variance[variance["matcher"] == matcher].set_index("dataset").reindex(datasets)
        positions = [x + i * width - 0.4 + width / 2 for x in range(len(datasets))]
        ax.bar(
            positions, sub["f1_mean"], width=width, label=matcher,
            yerr=sub["f1_std"].fillna(0), capsize=3, color=palette[i],
        )

    ax.set_xticks(range(len(datasets)))
    ax.set_xticklabels(datasets, rotation=20, ha="right")
    ax.set_ylabel("F1 (Test-Split)")
    ax.set_ylim(0, 1)
    ax.set_title("F1 über fünf Folds — Mittel mit Standardabweichung")
    ax.legend(title="Matcher", fontsize=9, ncol=2)
    fig.savefig(figures / "fold_variance.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ {figures / 'fold_variance.png'}")


if __name__ == "__main__":
    main()
