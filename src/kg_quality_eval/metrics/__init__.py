"""Metric plugins. All subclass BaseMetric and are addressed by name from the config."""

from kg_quality_eval.metrics.alignment import AlignmentMetrics, AlignmentReachability
from kg_quality_eval.metrics.base import BaseMetric, MetricResult
from kg_quality_eval.metrics.basic import BasicStatistics
from kg_quality_eval.metrics.quality import (
    AlignedEntityConsistency,
    AttributeCompleteness,
    SchemaHeterogeneity,
    TypeDistribution,
)
from kg_quality_eval.metrics.structural import (
    Connectivity,
    DegreeDistribution,
    LongTail,
    PropertyDistribution,
)

REGISTRY: dict[str, type[BaseMetric]] = {
    # Core (Katalog Abschnitt 1)
    "basic_stats": BasicStatistics,
    # Strukturell (Abschnitt 2)
    "degree_distribution": DegreeDistribution,
    "property_distribution": PropertyDistribution,
    "connectivity": Connectivity,
    "long_tail": LongTail,
    # Qualität (Abschnitt 3)
    "attribute_completeness": AttributeCompleteness,
    "type_distribution": TypeDistribution,
    "schema_heterogeneity": SchemaHeterogeneity,
    "aligned_consistency": AlignedEntityConsistency,
    "alignment_metrics": AlignmentMetrics,
    "alignment_reachability": AlignmentReachability,
}

ALL_METRICS = list(REGISTRY)

__all__ = [
    "ALL_METRICS",
    "REGISTRY",
    "AlignedEntityConsistency",
    "AlignmentMetrics",
    "AlignmentReachability",
    "AttributeCompleteness",
    "BaseMetric",
    "BasicStatistics",
    "Connectivity",
    "DegreeDistribution",
    "LongTail",
    "MetricResult",
    "PropertyDistribution",
    "SchemaHeterogeneity",
    "TypeDistribution",
    "get_metric",
]


def get_metric(name: str) -> BaseMetric:
    if name not in REGISTRY:
        raise ValueError(f"Unknown metric: {name!r}. Available: {ALL_METRICS}")
    return REGISTRY[name]()
