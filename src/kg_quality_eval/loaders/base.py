"""Abstract loader interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from kg_quality_eval.core import KGPair


class BaseLoader(ABC):
    """One implementation per data format (OpenEA, RDF, CSV, ...)."""

    name: str = "base"

    @abstractmethod
    def load(self, path: Path) -> KGPair:
        """Read the dataset at `path` and return a KGPair."""
        ...

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """E.g. ['.tsv', '.txt'] for OpenEA, ['.ttl', '.nt'] for RDF."""
        ...
