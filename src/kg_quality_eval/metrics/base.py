"""Abstract Metric Interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from kg_quality_eval.core import KGPair


@dataclass
class MetricResult:
    """Einheitliches Output-Format aller Metriken.

    - `scalar_values`: einzelne Kennzahlen (für JSON-Output)
    - `tabular`: tabellarische Outputs (für CSV-Export, z. B. Histogramme)
    - `plot_spec`: optionale Plot-Anweisung für das Reporting-Modul
    """

    name: str
    scalar_values: dict[str, float] = field(default_factory=dict)
    tabular: dict[str, pd.DataFrame] = field(default_factory=dict)
    plot_spec: dict | None = None


class BaseMetric(ABC):
    """Abstract Metric. Eine Subklasse pro Metrik (Gruppe)."""

    name: str = "base"
    category: Literal["basic", "structural", "quality"] = "basic"

    @abstractmethod
    def compute(self, kg_pair: KGPair) -> MetricResult:
        """Berechnet die Metrik auf dem KG-Paar und liefert ein MetricResult."""
        ...
