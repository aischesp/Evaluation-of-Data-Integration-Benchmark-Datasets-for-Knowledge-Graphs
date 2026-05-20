"""YAML-Konfigurations-Loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DatasetConfig:
    name: str
    loader: str
    path: str


@dataclass
class BackendConfig:
    mode: str = "auto"        # auto | pandas | spark
    spark_master: str = "local[*]"
    spark_memory: str = "4g"


@dataclass
class RunConfig:
    project: str
    output_dir: str
    datasets: list[DatasetConfig]
    metrics: list[str]
    backend: BackendConfig = field(default_factory=BackendConfig)


def load_config(path: str | Path) -> RunConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    datasets = [DatasetConfig(**d) for d in raw["datasets"]]
    backend = BackendConfig(**raw.get("backend", {}))

    return RunConfig(
        project=raw["project"],
        output_dir=raw["output_dir"],
        datasets=datasets,
        metrics=raw["metrics"],
        backend=backend,
    )
