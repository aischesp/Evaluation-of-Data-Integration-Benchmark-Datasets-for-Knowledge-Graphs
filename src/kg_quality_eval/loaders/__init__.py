"""Dataset loaders. All subclass BaseLoader and return KGPair objects."""

from kg_quality_eval.loaders.base import BaseLoader
from kg_quality_eval.loaders.openea import OpenEALoader

__all__ = ["BaseLoader", "OpenEALoader"]


def get_loader(name: str) -> BaseLoader:
    """Return a loader instance for a config name."""
    registry: dict[str, type[BaseLoader]] = {
        "openea": OpenEALoader,
    }
    if name not in registry:
        raise ValueError(f"Unknown loader: {name!r}. Available: {list(registry)}")
    return registry[name]()
