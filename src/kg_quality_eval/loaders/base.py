"""Abstract Loader Interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from kg_quality_eval.core import KGPair


class BaseLoader(ABC):
    """Abstract Loader. Eine Implementierung pro Datenformat (OpenEA, RDF, CSV, ...)."""

    name: str = "base"

    @abstractmethod
    def load(self, path: Path) -> KGPair:
        """Liest den Datensatz unter `path` und liefert ein KGPair zurück."""
        ...

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Beispiel: ['.tsv', '.txt'] für OpenEA, ['.ttl', '.nt'] für RDF."""
        ...
