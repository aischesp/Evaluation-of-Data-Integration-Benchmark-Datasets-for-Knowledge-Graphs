"""Metric plugins. All subclass BaseMetric."""

from kg_quality_eval.metrics.base import BaseMetric, MetricResult
from kg_quality_eval.metrics.basic import BasicStatistics

__all__ = ["BaseMetric", "MetricResult", "BasicStatistics"]


def get_metric(name: str) -> BaseMetric:
    registry: dict[str, type[BaseMetric]] = {
        "basic_stats": BasicStatistics,
        # to add: degree_distribution, attribute_completeness, ...
    }
    if name not in registry:
        raise ValueError(f"Unknown metric: {name!r}. Available: {list(registry)}")
    return registry[name]()
