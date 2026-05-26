"""Abstract metric interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from kg_quality_eval.core import KGPair


@dataclass
class MetricResult:
    """Unified output format for all metrics.

    scalar_values: single numbers (written to JSON)
    tabular:       tables (written to CSV, e.g. histograms)
    plot_spec:     optional plot description for the reporting module
    """

    name: str
    scalar_values: dict[str, float] = field(default_factory=dict)
    tabular: dict[str, pd.DataFrame] = field(default_factory=dict)
    plot_spec: dict | None = None


class BaseMetric(ABC):
    """One subclass per metric (or metric group)."""

    name: str = "base"
    category: Literal["basic", "structural", "quality"] = "basic"

    @abstractmethod
    def compute(self, kg_pair: KGPair) -> MetricResult:
        """Compute the metric on a KG pair and return a MetricResult."""
        ...
