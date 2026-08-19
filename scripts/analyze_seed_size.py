#!/usr/bin/env python
"""Einfluss der Seed-Größe auf die Matching-Güte.

Die semi-supervised Matcher bekommen ein Referenz-Alignment als Startpunkt.
Wie viel davon nötig ist, war bisher nicht untersucht — wir hatten schlicht den
Train-Split von OpenEA (20 %) genommen. Das ist eine Hyperparameter-Entscheidung
und gehört gemessen, nicht geerbt.

Das Skript variiert den Anteil des Train-Splits, der tatsächlich als Seed
verwendet wird, und misst die Güte auf dem Test-Split.

    python scripts/analyze_seed_size.py --config config/datasets.yaml

Ausgabe: results/reports/seed_size_sweep.csv und results/figures/seed_size.png
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

from kg_quality_eval.utils.console import enable_utf8_output  # noqa: E402

enable_utf8_output()

from kg_quality_eval.loaders import get_loader  # noqa: E402
from kg_quality_eval.matching import evaluate, get_matcher  # noqa: E402
from kg_quality_eval.preprocessing.nonmatch import inject_non_matches  # noqa: E402
from kg_quality_eval.utils.config import load_config  # noqa: E402

sns.set_theme(style="whitegrid", context="talk")
log = logging.getLogger("seed-size")

FRACTIONS = [0.05, 0.10, 0.25, 0.50, 0.75, 1.00]
SEEDED_MATCHERS = ("structural_propagation",)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/datasets.yaml")
    parser.add_argument("--datasets", nargs="*")
    parser.add_argument("--matchers", nargs="*", default=list(SEEDED_MATCHERS))
    parser.add_argument("--out", default="results/reports")
    parser.add_argument("--figures", default="results/figures")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    warnings.filterwarnings("ignore")

    cfg = load_config(args.config)
    datasets = cfg.datasets
    if args.datasets:
        datasets = [d for d in datasets if d.name in args.datasets]

    rows = []
    for ds in datasets:
        log.info("── %s ──", ds.name)
        kg_pair = get_loader(ds.loader, fold=ds.fold).load(Path(ds.path))
        kg_pair.name = ds.name
        if ds.match_ratio is not None:
            kg_pair = inject_non_matches(kg_pair, ds.match_ratio, seed=ds.non_match_seed)
            kg_pair.name = ds.name

        full_seeds = kg_pair.matched(cfg.seed_split)
        for fraction in FRACTIONS:
            n = max(int(round(len(full_seeds) * fraction)), 1)
            seeds = full_seeds.sample(n=n, random_state=args.seed)

            for name in args.matchers:
                matcher = get_matcher(name)
                try:
                    result = matcher.match(kg_pair, seeds)
                except Exception as exc:  # noqa: BLE001
                    log.error("   %s @ %.0f%% FEHLER: %s", name, 100 * fraction, exc)
                    continue
                score = evaluate(result, kg_pair, split=cfg.eval_split)
                rows.append(
                    {
                        "dataset": ds.name, "matcher": name,
                        "seed_fraction": fraction, "n_seeds": n,
                        "seed_share_of_entities": n / max(kg_pair.kg1.n_entities(), 1),
                        "precision": score.precision, "recall": score.recall,
                        "f1": score.f1, "runtime_s": result.runtime_s,
                    }
                )
                log.info(
                    "   %-24s Seeds %5d (%3.0f%%)  F1=%.3f",
                    name, n, 100 * fraction, score.f1,
                )

    if not rows:
        raise SystemExit("Keine Ergebnisse.")

    frame = pd.DataFrame(rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out / "seed_size_sweep.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    for (dataset, matcher), group in frame.groupby(["dataset", "matcher"]):
        label = dataset if len(args.matchers) == 1 else f"{dataset} / {matcher}"
        ax.plot(
            100 * group["seed_fraction"], group["f1"],
            marker="o", lw=1.8, label=label,
        )
    ax.set_xlabel("Anteil des Train-Splits als Seed [%]")
    ax.set_ylabel("F1 (Test-Split)")
    ax.set_title("Wie viele Seeds braucht der strukturelle Matcher?")
    ax.legend(fontsize=9)
    figures = Path(args.figures)
    figures.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures / "seed_size.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("\n=== F1 nach Seed-Anteil ===")
    print(
        frame.pivot_table(index="dataset", columns="seed_fraction", values="f1")
        .round(3).to_string()
    )
    print(f"\n✓ {out / 'seed_size_sweep.csv'}")
    print(f"✓ {figures / 'seed_size.png'}")


if __name__ == "__main__":
    main()
