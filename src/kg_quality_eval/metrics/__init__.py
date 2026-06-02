<<<<<<< HEAD
"""Metric Plugins — alle leiten von BaseMetric ab."""
=======
"""Metric plugins. All subclass BaseMetric."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

from kg_quality_eval.metrics.base import BaseMetric, MetricResult
from kg_quality_eval.metrics.basic import BasicStatistics

__all__ = ["BaseMetric", "MetricResult", "BasicStatistics"]


def get_metric(name: str) -> BaseMetric:
    registry: dict[str, type[BaseMetric]] = {
        "basic_stats": BasicStatistics,
<<<<<<< HEAD
        # weitere folgen (degree_distribution, attribute_completeness, ...)
    }
    if name not in registry:
        raise ValueError(f"Unbekannte Metrik: {name!r}. Bekannt: {list(registry)}")
=======
        # to add: degree_distribution, attribute_completeness, ...
    }
    if name not in registry:
        raise ValueError(f"Unknown metric: {name!r}. Available: {list(registry)}")
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
    return registry[name]()
