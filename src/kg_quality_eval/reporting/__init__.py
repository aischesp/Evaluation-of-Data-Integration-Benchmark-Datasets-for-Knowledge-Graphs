"""Reporting: comparison tables, correlation analysis and figures."""

from kg_quality_eval.reporting.comparison import (
    HEADLINE_METRICS,
    build_comparison,
    headline_table,
    matching_table,
    merge_metrics_and_scores,
)
from kg_quality_eval.reporting.correlation import correlate, correlation_matrix, top_drivers

__all__ = [
    "HEADLINE_METRICS",
    "build_comparison",
    "correlate",
    "correlation_matrix",
    "headline_table",
    "matching_table",
    "merge_metrics_and_scores",
    "top_drivers",
]
