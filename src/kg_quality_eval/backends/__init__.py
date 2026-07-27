"""Processing backends.

`pandas` is the default in-memory path used by all metric plugins. `spark` is a
second implementation of the core metrics for the scalability part of the
project; it is imported lazily because it pulls in a JVM.
"""

__all__ = ["get_spark_backend"]


def get_spark_backend():
    """Import the Spark backend on demand (starting a JVM is expensive)."""
    from kg_quality_eval.backends import spark

    return spark
