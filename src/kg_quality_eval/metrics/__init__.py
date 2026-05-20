"""Metric Plugins — alle leiten von BaseMetric ab."""

from kg_quality_eval.metrics.base import BaseMetric, MetricResult
from kg_quality_eval.metrics.basic import BasicStatistics

__all__ = ["BaseMetric", "MetricResult", "BasicStatistics"]


def get_metric(name: str) -> BaseMetric:
    registry: dict[str, type[BaseMetric]] = {
        "basic_stats": BasicStatistics,
        # weitere folgen (degree_distribution, attribute_completeness, ...)
    }
    if name not in registry:
        raise ValueError(f"Unbekannte Metrik: {name!r}. Bekannt: {list(registry)}")
    return registry[name]()
