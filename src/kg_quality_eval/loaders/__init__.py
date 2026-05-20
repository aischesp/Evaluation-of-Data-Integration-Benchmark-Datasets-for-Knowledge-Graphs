"""Dataset Loaders — alle leiten von BaseLoader ab und liefern KGPair-Objekte."""

from kg_quality_eval.loaders.base import BaseLoader
from kg_quality_eval.loaders.openea import OpenEALoader

__all__ = ["BaseLoader", "OpenEALoader"]


def get_loader(name: str) -> BaseLoader:
    """Factory: liefert Loader-Instanz nach Konfigurationsname.

    Erweitern: einfach neue Subklasse importieren und hier registrieren.
    """
    registry: dict[str, type[BaseLoader]] = {
        "openea": OpenEALoader,
    }
    if name not in registry:
        raise ValueError(f"Unbekannter Loader: {name!r}. Bekannt: {list(registry)}")
    return registry[name]()
