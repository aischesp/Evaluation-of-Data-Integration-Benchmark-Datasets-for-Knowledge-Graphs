#!/usr/bin/env python
"""Pandas vs. PySpark: equivalence check and runtime comparison.

Runs the core metrics of every configured dataset through both backends,
verifies that the numbers agree, and records how long each backend needed.

    python scripts/run_backend_benchmark.py --config config/datasets.yaml

Outputs
    results/reports/backend_equivalence.csv   metric-by-metric comparison
    results/reports/backend_runtimes.csv      runtime per dataset and backend
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kg_quality_eval.loaders import get_loader  # noqa: E402
from kg_quality_eval.metrics import get_metric  # noqa: E402
from kg_quality_eval.utils.config import load_config  # noqa: E402

log = logging.getLogger("backend-benchmark")

# The Pandas-side metrics whose scalars cover the Spark core metrics.
CORE_METRICS = ["basic_stats", "degree_distribution", "property_distribution"]


def pandas_core(path: str, fold: int) -> tuple[dict, float]:
    start = time.perf_counter()
    kg_pair = get_loader("openea", fold=fold).load(Path(path))

    scalars: dict[str, float] = {}
    for name in CORE_METRICS:
        scalars.update(get_metric(name).compute(kg_pair).scalar_values)
    return scalars, time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/datasets.yaml")
    parser.add_argument("--datasets", nargs="*")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )

    cfg = load_config(args.config)
    datasets = cfg.datasets
    if args.datasets:
        datasets = [d for d in datasets if d.name in args.datasets]

    from kg_quality_eval.backends import spark as spark_backend

    session = spark_backend.get_session(cfg.backend.spark_master, cfg.backend.spark_memory)

    equivalence, runtimes = [], []
    try:
        for ds in datasets:
            log.info("── %s ──", ds.name)

            pandas_scalars, t_pandas = pandas_core(ds.path, ds.fold)
            log.info("   pandas  %6.1fs", t_pandas)

            spark_scalars, t_spark = spark_backend.timed_compute(session, ds.path, ds.fold)
            log.info("   spark   %6.1fs", t_spark)

            table = spark_backend.compare_backends(pandas_scalars, spark_scalars)
            table.insert(0, "dataset", ds.name)
            equivalence.append(table)

            n_mismatch = int((~table["match"]).sum())
            log.info(
                "   Äquivalenz: %d/%d Metriken identisch%s",
                len(table) - n_mismatch, len(table),
                "" if n_mismatch == 0 else f"  ⚠ {n_mismatch} Abweichungen",
            )
            if n_mismatch:
                log.warning("\n%s", table[~table["match"]].to_string(index=False))

            runtimes += [
                {"dataset": ds.name, "backend": "pandas", "runtime_s": t_pandas},
                {"dataset": ds.name, "backend": "spark", "runtime_s": t_spark},
            ]
    finally:
        session.stop()

    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(equivalence, ignore_index=True).to_csv(out / "backend_equivalence.csv", index=False)

    runtime_df = pd.DataFrame(runtimes)
    runtime_df.to_csv(out / "backend_runtimes.csv", index=False)

    from kg_quality_eval.reporting import plots

    plots.backend_runtime(runtime_df, Path(cfg.figures_dir))
    log.info("Geschrieben: %s", out / "backend_equivalence.csv")


if __name__ == "__main__":
    main()
