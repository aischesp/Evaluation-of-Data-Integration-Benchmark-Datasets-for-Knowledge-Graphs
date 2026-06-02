<<<<<<< HEAD
"""Abstract Metric Interface."""
=======
"""Abstract metric interface."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from kg_quality_eval.core import KGPair


@dataclass
class MetricResult:
<<<<<<< HEAD
    """Einheitliches Output-Format aller Metriken.

    - `scalar_values`: einzelne Kennzahlen (für JSON-Output)
    - `tabular`: tabellarische Outputs (für CSV-Export, z. B. Histogramme)
    - `plot_spec`: optionale Plot-Anweisung für das Reporting-Modul
=======
    """Unified output format for all metrics.

    scalar_values: single numbers (written to JSON)
    tabular:       tables (written to CSV, e.g. histograms)
    plot_spec:     optional plot description for the reporting module
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
    """

    name: str
    scalar_values: dict[str, float] = field(default_factory=dict)
    tabular: dict[str, pd.DataFrame] = field(default_factory=dict)
    plot_spec: dict | None = None


class BaseMetric(ABC):
<<<<<<< HEAD
    """Abstract Metric. Eine Subklasse pro Metrik (Gruppe)."""
=======
    """One subclass per metric (or metric group)."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

    name: str = "base"
    category: Literal["basic", "structural", "quality"] = "basic"

    @abstractmethod
    def compute(self, kg_pair: KGPair) -> MetricResult:
<<<<<<< HEAD
        """Berechnet die Metrik auf dem KG-Paar und liefert ein MetricResult."""
=======
        """Compute the metric on a KG pair and return a MetricResult."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
        ...
