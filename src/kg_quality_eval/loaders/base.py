<<<<<<< HEAD
"""Abstract Loader Interface."""
=======
"""Abstract loader interface."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from kg_quality_eval.core import KGPair


class BaseLoader(ABC):
<<<<<<< HEAD
    """Abstract Loader. Eine Implementierung pro Datenformat (OpenEA, RDF, CSV, ...)."""
=======
    """One implementation per data format (OpenEA, RDF, CSV, ...)."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

    name: str = "base"

    @abstractmethod
    def load(self, path: Path) -> KGPair:
<<<<<<< HEAD
        """Liest den Datensatz unter `path` und liefert ein KGPair zurück."""
=======
        """Read the dataset at `path` and return a KGPair."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
        ...

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
<<<<<<< HEAD
        """Beispiel: ['.tsv', '.txt'] für OpenEA, ['.ttl', '.nt'] für RDF."""
=======
        """E.g. ['.tsv', '.txt'] for OpenEA, ['.ttl', '.nt'] for RDF."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
        ...
