<<<<<<< HEAD
"""Dataset Loaders — alle leiten von BaseLoader ab und liefern KGPair-Objekte."""
=======
"""Dataset loaders. All subclass BaseLoader and return KGPair objects."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

from kg_quality_eval.loaders.base import BaseLoader
from kg_quality_eval.loaders.openea import OpenEALoader

__all__ = ["BaseLoader", "OpenEALoader"]


def get_loader(name: str) -> BaseLoader:
<<<<<<< HEAD
    """Factory: liefert Loader-Instanz nach Konfigurationsname.

    Erweitern: einfach neue Subklasse importieren und hier registrieren.
    """
=======
    """Return a loader instance for a config name."""
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
    registry: dict[str, type[BaseLoader]] = {
        "openea": OpenEALoader,
    }
    if name not in registry:
<<<<<<< HEAD
        raise ValueError(f"Unbekannter Loader: {name!r}. Bekannt: {list(registry)}")
=======
        raise ValueError(f"Unknown loader: {name!r}. Available: {list(registry)}")
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
    return registry[name]()
