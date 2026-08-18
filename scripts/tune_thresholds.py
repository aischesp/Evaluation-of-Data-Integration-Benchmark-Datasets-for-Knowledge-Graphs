#!/usr/bin/env python
"""Bestimmt die Schwellenwerte der Matcher auf dem Valid-Split.

In der ersten Fassung stand `min_score` auf 0,0. Damit wurde für jede Entität
der bestbewertete Kandidat als Match ausgegeben, auch bei einem Score von 0,01.
Auf einem strikt bijektiven Benchmark fällt das kaum auf — dort gibt es für
jede Entität tatsächlich einen Partner. Sobald Entitäten ohne Gegenstück
existieren, ist jede solche Vorhersage ein False Positive.

Dieses Skript tastet den Schwellenwert je Matcher ab und wählt den besten Wert
**auf dem Valid-Split**. Der Test-Split wird dabei nicht angefasst.

    python scripts/tune_thresholds.py --config config/datasets.yaml

Ausgabe: results/reports/threshold_sweep.csv und threshold_choice.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
import warnings
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kg_quality_eval.loaders import get_loader  # noqa: E402
from kg_quality_eval.matching import evaluate, get_matcher  # noqa: E402
from kg_quality_eval.matching.base import SparseScoreMatcher  # noqa: E402
from kg_quality_eval.preprocessing.nonmatch import inject_non_matches  # noqa: E402
from kg_quality_eval.utils.config import load_config  # noqa: E402

log = logging.getLogger("tune")

GRID = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
SWEEPABLE = ("value_overlap", "structural_propagation")


def sweep_sparse(matcher_name: str, kg_pair, seeds, grid: list[float]) -> list[dict]:
    """Score-Matrix einmal berechnen, dann nur den Schwellenwert variieren.

    Das ist der Grund, warum hier nicht einfach `matcher.match()` in einer
    Schleife steht: die teure Ähnlichkeitsberechnung hängt nicht vom
    Schwellenwert ab.
    """
    matcher: SparseScoreMatcher = get_matcher(matcher_name)
    scores = matcher.score_matrix(kg_pair, seeds if matcher.requires_seeds else None)

    rows = []
    for threshold in grid:
        matcher.min_score = threshold
        pairs = matcher._reduce(scores, kg_pair)  # noqa: SLF001 - bewusst, s. o.
        from kg_quality_eval.matching.base import MatchResult

        result = MatchResult(matcher_name, kg_pair.name, pairs, 0.0)
        s = evaluate(result, kg_pair, split="valid")
        rows.append(
            {
                "dataset": kg_pair.name, "matcher": matcher_name, "threshold": threshold,
                "precision": s.precision, "recall": s.recall, "f1": s.f1,
                "coverage": s.coverage, "abstain_rate": s.abstain_rate,
                "n_predicted": s.n_predicted, "n_gold": s.n_gold,
                "n_false_on_unmatched": s.n_false_on_unmatched,
            }
        )
    return rows


def sweep_pyjedai(kg_pair, grid: list[float]) -> list[dict]:
    """pyJedAI: Kandidatengraph einmal bauen, dann nur das Clustering variieren."""
    from kg_quality_eval.matching.base import MatchResult

    matcher = get_matcher("pyjedai_ngram")
    graph, data, left, right = matcher.build_candidate_graph(kg_pair)

    rows = []
    for threshold in grid:
        pairs = matcher.cluster(graph, data, left, right, threshold)
        result = MatchResult("pyjedai_ngram", kg_pair.name, pairs, 0.0)
        s = evaluate(result, kg_pair, split="valid")
        rows.append(
            {
                "dataset": kg_pair.name, "matcher": "pyjedai_ngram", "threshold": threshold,
                "precision": s.precision, "recall": s.recall, "f1": s.f1,
                "coverage": s.coverage, "abstain_rate": s.abstain_rate,
                "n_predicted": s.n_predicted, "n_gold": s.n_gold,
                "n_false_on_unmatched": s.n_false_on_unmatched,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/datasets.yaml")
    parser.add_argument("--datasets", nargs="*")
    parser.add_argument("--matchers", nargs="*", default=[*SWEEPABLE, "pyjedai_ngram"])
    parser.add_argument("--out", default="results/reports")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    warnings.filterwarnings("ignore")

    cfg = load_config(args.config)
    datasets = cfg.datasets
    if args.datasets:
        datasets = [d for d in datasets if d.name in args.datasets]

    rows: list[dict] = []
    for ds in datasets:
        log.info("── %s ──", ds.name)
        kg_pair = get_loader(ds.loader, fold=ds.fold).load(Path(ds.path))
        kg_pair.name = ds.name
        if ds.match_ratio is not None:
            kg_pair = inject_non_matches(kg_pair, ds.match_ratio, seed=ds.non_match_seed)
            kg_pair.name = ds.name
        seeds = kg_pair.matched(cfg.seed_split)

        for name in args.matchers:
            try:
                if name == "pyjedai_ngram":
                    new = sweep_pyjedai(kg_pair, GRID)
                else:
                    new = sweep_sparse(name, kg_pair, seeds, GRID)
            except Exception as exc:  # noqa: BLE001
                log.error("   %s FEHLER: %s", name, exc)
                continue
            rows += new
            best = max(new, key=lambda r: r["f1"]) if new else None
            if best:
                log.info(
                    "   %-24s bester Threshold %.1f -> valid-F1 %.3f "
                    "(P=%.3f R=%.3f, Enthaltung %.0f%%)",
                    name, best["threshold"], best["f1"],
                    best["precision"], best["recall"], 100 * best["abstain_rate"],
                )

    if not rows:
        raise SystemExit("Keine Ergebnisse.")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sweep = pd.DataFrame(rows)
    sweep.to_csv(out / "threshold_sweep.csv", index=False)

    # Ein Schwellenwert je Matcher, gemittelt über die Datensätze — wir wollen
    # keinen datensatzspezifisch überangepassten Wert.
    mean_f1 = sweep.groupby(["matcher", "threshold"])["f1"].mean().reset_index()
    choice = mean_f1.loc[mean_f1.groupby("matcher")["f1"].idxmax()]
    choice.to_csv(out / "threshold_choice.csv", index=False)

    print("\n=== Gewählte Schwellenwerte (Mittel über Datensätze, Valid-Split) ===")
    print(choice.round(4).to_string(index=False))
    print(f"\n✓ {out / 'threshold_sweep.csv'}")


if __name__ == "__main__":
    main()
