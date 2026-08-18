"""Dataset loaders. All subclass BaseLoader and return KGPair objects."""

from kg_quality_eval.loaders.base import BaseLoader
from kg_quality_eval.loaders.openea import OpenEALoader
from kg_quality_eval.loaders.rdf_export import parse_ntriples, write_rdf

REGISTRY: dict[str, type[BaseLoader]] = {
    "openea": OpenEALoader,
}

__all__ = ["REGISTRY", "BaseLoader", "OpenEALoader", "get_loader", "parse_ntriples", "write_rdf"]


def get_loader(name: str, **kwargs) -> BaseLoader:
    """Return a loader instance for a config name."""
    if name not in REGISTRY:
        raise ValueError(f"Unknown loader: {name!r}. Available: {list(REGISTRY)}")
    return REGISTRY[name](**kwargs)
