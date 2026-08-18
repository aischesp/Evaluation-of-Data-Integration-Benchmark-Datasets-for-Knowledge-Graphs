"""Pipeline runner: profile datasets, run matchers, evaluate, report.

    python -m kg_quality_eval.runner --config config/datasets.yaml

Stages (each can be skipped from the command line, so the pipeline can be
re-run incrementally while working on one of them):

    profile   loaders + metric plugins   -> results/reports/<dataset>/*.json|csv
    match     matchers + evaluation      -> results/reports/matching_results.csv
    report    comparison + correlation   -> results/reports/*.csv, results/figures/*.png
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import pandas as pd

from kg_quality_eval.core import KGPair
from kg_quality_eval.loaders import get_loader
from kg_quality_eval.matching import evaluate, evaluation_frame, get_matcher
from kg_quality_eval.metrics import get_metric
from kg_quality_eval.preprocessing.nonmatch import inject_non_matches
from kg_quality_eval.reporting import comparison as cmp_mod
from kg_quality_eval.reporting import correlation as corr_mod
from kg_quality_eval.reporting import plots
from kg_quality_eval.utils.config import DatasetConfig, RunConfig, load_config

log = logging.getLogger("kg_quality_eval")


class Pipeline:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.out_root = Path(config.output_dir)
        self.fig_dir = Path(config.figures_dir)
        self.out_root.mkdir(parents=True, exist_ok=True)
        self.fig_dir.mkdir(parents=True, exist_ok=True)

        self.profiles: dict[str, dict[str, dict[str, float]]] = {}
        self.tables: dict[str, dict[str, pd.DataFrame]] = {}
        self.scores: list = []
        self.runtimes: list[dict] = []

    # -- stages -------------------------------------------------------------

    def run(self, do_profile: bool = True, do_match: bool = True, do_report: bool = True) -> None:
        for ds in self.config.datasets:
            # A dataset that blows up (typically the large one running out of
            # memory) must not cost us the results of all the others.
            try:
                kg_pair = self._load(ds)
                if do_profile:
                    self._profile(ds, kg_pair)
                if do_match:
                    self._match(ds, kg_pair)
                del kg_pair  # free memory before the next dataset
            except Exception:
                log.exception("   Datensatz %s abgebrochen", ds.name)

        if do_report:
            self._report()

    def _load(self, ds: DatasetConfig) -> KGPair:
        log.info("── %s ──", ds.name)
        start = time.perf_counter()
        loader = get_loader(ds.loader, fold=ds.fold)
        kg_pair = loader.load(Path(ds.path))
        kg_pair.name = ds.name

        if ds.match_ratio is not None:
            kg_pair = inject_non_matches(kg_pair, ds.match_ratio, seed=ds.non_match_seed)
            kg_pair.name = ds.name
            log.info(
                "   Non-Match-Variante: %d Gold-Paare, %d Entitaeten in KG1 ohne Partner",
                kg_pair.n_matched(), len(kg_pair.unmatched()),
            )
        log.info(
            "   geladen in %.1fs: |E1|=%d |E2|=%d |M|=%d",
            time.perf_counter() - start,
            kg_pair.kg1.n_entities(),
            kg_pair.kg2.n_entities(),
            kg_pair.n_matched(),
        )
        return kg_pair

    def _profile(self, ds: DatasetConfig, kg_pair: KGPair) -> None:
        ds_out = self.out_root / ds.name
        ds_out.mkdir(parents=True, exist_ok=True)

        metrics: dict[str, dict[str, float]] = {}
        tables: dict[str, pd.DataFrame] = {}

        for metric_name in self.config.metrics:
            metric = get_metric(metric_name)
            start = time.perf_counter()
            try:
                result = metric.compute(kg_pair)
            except Exception as exc:  # noqa: BLE001 - keep the remaining metrics
                log.error("   metric %-24s FEHLER: %s", metric_name, exc)
                continue
            elapsed = time.perf_counter() - start

            (ds_out / f"{result.name}.json").write_text(
                json.dumps(result.scalar_values, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            for tab_name, df in result.tabular.items():
                df.to_csv(ds_out / f"{result.name}.{tab_name}.csv", index=False)
                tables[tab_name] = df

            metrics[result.name] = result.scalar_values
            self.runtimes.append(
                {
                    "dataset": ds.name,
                    "stage": "metric",
                    "component": metric_name,
                    "backend": "pandas",
                    "runtime_s": elapsed,
                }
            )
            log.info("   metric %-24s %6.2fs", metric_name, elapsed)

        self.profiles[ds.name] = metrics
        self.tables[ds.name] = tables

    def _match(self, ds: DatasetConfig, kg_pair: KGPair) -> None:
        if not self.config.matchers:
            return

        ds_out = self.out_root / ds.name / "matching"
        ds_out.mkdir(parents=True, exist_ok=True)
        seeds = kg_pair.matched(self.config.seed_split)

        for mc in self.config.matchers:
            if mc.name in ds.skip_matchers:
                log.info("   matcher %-24s übersprungen (config)", mc.name)
                continue
            try:
                matcher = get_matcher(mc.name, **mc.params)
                result = matcher.match(kg_pair, seeds if matcher.requires_seeds else None)
            except Exception as exc:  # noqa: BLE001 - one broken matcher must not kill the run
                log.error("   matcher %-24s FEHLER: %s", mc.name, exc)
                continue

            result.pairs.to_csv(ds_out / f"{mc.name}_pairs.csv", index=False)

            score = evaluate(result, kg_pair, split=self.config.eval_split)
            score_all = evaluate(result, kg_pair, split="all")
            self.scores.append(score)
            self.runtimes.append(
                {
                    "dataset": ds.name,
                    "stage": "matcher",
                    "component": mc.name,
                    "backend": "pandas",
                    "runtime_s": result.runtime_s,
                }
            )
            log.info(
                "   matcher %-24s %6.1fs  P=%.3f R=%.3f F1=%.3f (all-F1=%.3f)",
                mc.name, result.runtime_s, score.precision, score.recall, score.f1, score_all.f1,
            )

    def _report(self) -> None:
        comparison = cmp_mod.build_comparison(self.profiles)
        if not comparison.empty:
            comparison.to_csv(self.out_root / "comparison.csv", index=False)
            cmp_mod.headline_table(comparison).to_csv(
                self.out_root / "comparison_headline.csv", index=False
            )
            log.info(
                "comparison.csv: %d Datensätze x %d Metriken",
                len(comparison), comparison.shape[1] - 1,
            )

        scores_df = evaluation_frame(self.scores)
        if not scores_df.empty:
            scores_df.to_csv(self.out_root / "matching_results.csv", index=False)
            cmp_mod.matching_table(scores_df).to_csv(
                self.out_root / "matching_f1_matrix.csv", index=False
            )

        if not comparison.empty and not scores_df.empty:
            merged = cmp_mod.merge_metrics_and_scores(comparison, scores_df)
            merged.to_csv(self.out_root / "merged_metrics_scores.csv", index=False)

            metric_cols = [c for c in cmp_mod.HEADLINE_METRICS if c in merged.columns]
            correlations = corr_mod.correlate(merged, metric_cols)
            if not correlations.empty:
                correlations.to_csv(self.out_root / "correlation.csv", index=False)
                corr_mod.top_drivers(correlations).to_csv(
                    self.out_root / "correlation_top.csv", index=False
                )
                plots.correlation_heatmap(
                    corr_mod.correlation_matrix(merged, metric_cols), self.fig_dir
                )
            self._scatter_plots(merged)

        if self.runtimes:
            pd.DataFrame(self.runtimes).to_csv(self.out_root / "runtimes.csv", index=False)

        self._figures(scores_df)
        (self.out_root / "summary.json").write_text(
            json.dumps(
                {
                    "project": self.config.project,
                    "datasets": list(self.profiles),
                    "metrics": self.config.metrics,
                    "matchers": [m.name for m in self.config.matchers],
                    "eval_split": self.config.eval_split,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        log.info("Fertig. Reports in %s, Figures in %s", self.out_root, self.fig_dir)

    # -- figures ------------------------------------------------------------

    def _figures(self, scores_df: pd.DataFrame) -> None:
        hists = {d: t["degree_histogram"] for d, t in self.tables.items() if "degree_histogram" in t}
        if hists:
            plots.degree_distributions(hists, self.fig_dir)

        curves = {d: t["long_tail_curve"] for d, t in self.tables.items() if "long_tail_curve" in t}
        if curves:
            plots.long_tail_curves(curves, self.fig_dir)

        props = {d: t["property_counts"] for d, t in self.tables.items() if "property_counts" in t}
        if props:
            plots.property_long_tail(props, self.fig_dir)

        cov = {d: t["property_coverage"] for d, t in self.tables.items() if "property_coverage" in t}
        if cov:
            plots.attribute_coverage(cov, self.fig_dir)

        if not scores_df.empty:
            plots.matcher_scores(scores_df, self.fig_dir)
            plots.precision_recall(scores_df, self.fig_dir)

        runtimes = pd.DataFrame(self.runtimes)
        if not runtimes.empty and runtimes["backend"].nunique() > 1:
            agg = (
                runtimes[runtimes["stage"] == "metric"]
                .groupby(["dataset", "backend"], as_index=False)["runtime_s"]
                .sum()
            )
            plots.backend_runtime(agg, self.fig_dir)

    def _scatter_plots(self, merged: pd.DataFrame) -> None:
        for metric in (
            "attribute_completeness.pair.mean_attr_per_entity",
            "degree_distribution.pair.mean_total_degree",
            "schema_heterogeneity.property_jaccard",
            "aligned_consistency.literal_value_jaccard.mean",
        ):
            plots.metric_vs_f1(merged, metric, self.fig_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="KG quality evaluation pipeline")
    parser.add_argument("--config", required=True, help="Pfad zur YAML-Konfiguration")
    parser.add_argument("--no-profile", action="store_true", help="Metrik-Stufe überspringen")
    parser.add_argument("--no-match", action="store_true", help="Matcher-Stufe überspringen")
    parser.add_argument("--no-report", action="store_true", help="Report-Stufe überspringen")
    parser.add_argument("--datasets", nargs="*", help="Nur diese Datensätze (Namen aus der Config)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = load_config(args.config)
    if args.datasets:
        cfg.datasets = [d for d in cfg.datasets if d.name in args.datasets]
        if not cfg.datasets:
            raise SystemExit(f"Kein Datensatz passt zu {args.datasets}")

    Pipeline(cfg).run(
        do_profile=not args.no_profile,
        do_match=not args.no_match,
        do_report=not args.no_report,
    )


if __name__ == "__main__":
    main()
