"""YAML configuration for the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DatasetConfig:
    name: str
    loader: str
    path: str
    fold: int = 1
    skip_matchers: list[str] = field(default_factory=list)
    # Anteil der Gold-Paare, der intakt bleibt. None = Datensatz unveraendert
    # (strikt bijektiv). Werte < 1 erzeugen Entitaeten ohne Gegenstueck,
    # siehe preprocessing/nonmatch.py.
    match_ratio: float | None = None
    non_match_seed: int = 42


@dataclass
class MatcherConfig:
    name: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendConfig:
    mode: str = "pandas"          # pandas | spark | both
    spark_master: str = "local[*]"
    spark_memory: str = "4g"
    spark_metrics: list[str] = field(
        default_factory=lambda: ["basic_stats", "degree_distribution", "property_distribution"]
    )


@dataclass
class RunConfig:
    project: str
    output_dir: str
    datasets: list[DatasetConfig]
    metrics: list[str]
    matchers: list[MatcherConfig] = field(default_factory=list)
    eval_split: str = "test"
    seed_split: str = "train"
    figures_dir: str = "results/figures"
    backend: BackendConfig = field(default_factory=BackendConfig)


def load_config(path: str | Path) -> RunConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    return RunConfig(
        project=raw["project"],
        output_dir=raw["output_dir"],
        datasets=[DatasetConfig(**d) for d in raw["datasets"]],
        metrics=raw["metrics"],
        matchers=[_matcher(m) for m in raw.get("matchers", []) or []],
        eval_split=raw.get("eval_split", "test"),
        seed_split=raw.get("seed_split", "train"),
        figures_dir=raw.get("figures_dir", "results/figures"),
        backend=BackendConfig(**raw.get("backend", {})),
    )


def _matcher(entry: str | dict) -> MatcherConfig:
    """Matchers may be given as a bare name or as `{name: ..., params: {...}}`."""
    if isinstance(entry, str):
        return MatcherConfig(name=entry)
    return MatcherConfig(name=entry["name"], params=entry.get("params", {}) or {})
