<<<<<<< HEAD
"""Pipeline-Runner: liest Config, lädt Datensätze, berechnet Metriken, schreibt Outputs.

Aufruf:

    python -m kg_quality_eval.runner --config config/datasets.example.yaml

Stand: minimaler End-to-End-Pfad (Loader → Basis-Statistiken → JSON-Export).
Wird in Phase 2 erweitert.
=======
"""Pipeline runner. Loads config, runs loaders + metrics, writes outputs.

Usage:

    python -m kg_quality_eval.runner --config config/datasets.example.yaml
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from kg_quality_eval.loaders import get_loader
from kg_quality_eval.metrics import get_metric
from kg_quality_eval.utils.config import RunConfig, load_config

log = logging.getLogger("kg_quality_eval")


def run(config: RunConfig) -> None:
    out_root = Path(config.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, dict] = {}

    for ds in config.datasets:
        log.info("→ Dataset: %s", ds.name)
        loader = get_loader(ds.loader)
        kg_pair = loader.load(Path(ds.path))

        ds_out = out_root / ds.name
        ds_out.mkdir(parents=True, exist_ok=True)

        ds_summary: dict[str, dict] = {}
        for metric_name in config.metrics:
            metric = get_metric(metric_name)
            result = metric.compute(kg_pair)

            (ds_out / f"{metric.name}.json").write_text(
                json.dumps(result.scalar_values, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            for tab_name, df in result.tabular.items():
                df.to_csv(ds_out / f"{metric.name}.{tab_name}.csv", index=False)

            ds_summary[metric.name] = result.scalar_values

        summary[ds.name] = ds_summary
<<<<<<< HEAD
        log.info("   ✓ %d Metriken gespeichert nach %s", len(config.metrics), ds_out)
=======
        log.info("   %d metrics written to %s", len(config.metrics), ds_out)
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

    (out_root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
    )
<<<<<<< HEAD
    log.info("Pipeline abgeschlossen. Übersicht: %s", out_root / "summary.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="KG Quality Evaluation — Pipeline-Runner")
    parser.add_argument("--config", required=True, help="Pfad zur YAML-Konfiguration")
=======
    log.info("Done. Summary at %s", out_root / "summary.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="KG quality evaluation pipeline")
    parser.add_argument("--config", required=True, help="Path to YAML config")
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
<<<<<<< HEAD
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
=======
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
    )

    cfg = load_config(args.config)
    run(cfg)


if __name__ == "__main__":
    main()
