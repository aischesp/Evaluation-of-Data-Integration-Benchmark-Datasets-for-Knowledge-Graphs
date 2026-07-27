"""PySpark backend for the core metrics.

Why a second backend at all: the Pandas path keeps every triple in memory, which
is fine for the 15 K and 100 K OpenEA benchmarks but does not generalise to the
graph sizes the topic description is aimed at. The Spark path computes the same
core metrics as relational operations (group-by, join, window) that spill to
disk and parallelise, so the same metric definitions scale beyond main memory.

The two backends are kept honest by `compare_backends`, which recomputes the
metrics both ways and asserts that the numbers agree.

Only the core metrics are ported. Connectivity and the sampled consistency
metrics stay in the Pandas/NetworkX path — porting connected components to
Spark (GraphFrames) would add a dependency without adding insight, and both are
explicitly out of scope in the metric catalogue.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# The workers must run the same interpreter as the driver.
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

from pyspark.sql import DataFrame, SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.window import Window  # noqa: E402

# Keys that both backends must agree on exactly (up to float tolerance).
COMPARABLE_KEYS = [
    "kg1.n_entities", "kg2.n_entities",
    "kg1.n_relations", "kg2.n_relations",
    "kg1.n_attributes", "kg2.n_attributes",
    "kg1.n_literals", "kg2.n_literals",
    "kg1.n_rel_triples", "kg2.n_rel_triples",
    "kg1.n_attr_triples", "kg2.n_attr_triples",
    "kg1.attr_to_rel_ratio", "kg2.attr_to_rel_ratio",
    "alignments.n",
    "kg1.total_degree.mean", "kg2.total_degree.mean",
    "kg1.total_degree.median", "kg2.total_degree.median",
    "kg1.total_degree.max", "kg2.total_degree.max",
    "kg1.total_degree.gini", "kg2.total_degree.gini",
    "kg1.share_isolated", "kg2.share_isolated",
    "kg1.rel.n_properties", "kg2.rel.n_properties",
    "kg1.rel.top10_concentration", "kg2.rel.top10_concentration",
]


def get_session(master: str = "local[*]", memory: str = "4g") -> SparkSession:
    """Reuse one local SparkSession for the whole run."""
    session = (
        SparkSession.builder.appName("kg-quality-eval")
        .master(master)
        .config("spark.driver.memory", memory)
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    return session


class SparkCoreMetrics:
    """Core metrics (basic stats, degree, property distribution) on Spark.

    Reads the OpenEA files directly — the whole point is that no Pandas frame is
    ever created, so nothing has to fit into the driver's memory.
    """

    def __init__(self, session: SparkSession) -> None:
        self.spark = session

    # -- IO -----------------------------------------------------------------

    def _split_text(self, paths: Path | list[Path], columns: list[str]) -> DataFrame:
        """Read tab-separated OpenEA files as text and split them explicitly.

        The CSV reader is deliberately not used: OpenEA literals contain
        unbalanced double quotes (`"Titel"@ita`), which the CSV parser would
        try to interpret. Reading raw lines and splitting on the tab is both
        simpler and exactly what the format specifies. Several files can be read
        in one go — Spark treats them as partitions of the same relation.
        """
        if isinstance(paths, Path):
            paths = [paths]
        parts = F.split(F.col("value"), "\t", len(columns))
        return (
            self.spark.read.text([str(p) for p in paths])
            .where(F.length(F.col("value")) > 0)
            .select(*[parts.getItem(i).alias(name) for i, name in enumerate(columns)])
        )

    def _read_triples(self, path: Path) -> DataFrame:
        return self._split_text(path, ["head", "predicate", "tail"])

    def _read_links(self, paths: Path | list[Path]) -> DataFrame:
        return self._split_text(paths, ["e1", "e2"])

    # -- public API ---------------------------------------------------------

    def compute(self, dataset_path: str | Path, fold: int = 1) -> dict[str, float]:
        root = Path(dataset_path)
        links = self._alignments(root, fold).cache()

        scalars: dict[str, float] = {}
        for label, suffix, link_col in (("kg1", "1", "e1"), ("kg2", "2", "e2")):
            rel = self._read_triples(root / f"rel_triples_{suffix}").cache()
            attr = self._read_triples(root / f"attr_triples_{suffix}").cache()
            entities = self._entities(rel, attr, links.select(F.col(link_col).alias("e"))).cache()

            scalars.update(self._basic(label, rel, attr, entities))
            scalars.update(self._degree(label, rel, entities))
            scalars.update(self._properties(label, rel, attr))

            for df in (rel, attr, entities):
                df.unpersist()

        n_align = links.distinct().count()
        scalars["alignments.n"] = float(n_align)
        min_ent = min(scalars["kg1.n_entities"], scalars["kg2.n_entities"])
        scalars["alignments.ratio"] = float(n_align / min_ent) if min_ent else 0.0
        links.unpersist()

        return scalars

    # -- metric groups ------------------------------------------------------

    @staticmethod
    def _entities(rel: DataFrame, attr: DataFrame, linked: DataFrame) -> DataFrame:
        """Entity set = union of relation endpoints, attribute subjects and links."""
        return (
            rel.select(F.col("head").alias("e"))
            .union(rel.select(F.col("tail").alias("e")))
            .union(attr.select(F.col("head").alias("e")))
            .union(linked)
            .where(F.col("e").isNotNull())
            .distinct()
        )

    def _alignments(self, root: Path, fold: int) -> DataFrame:
        fold_dir = root / "721_5fold" / str(fold)
        files = [fold_dir / n for n in ("train_links", "valid_links", "test_links")]
        existing = [f for f in files if f.exists() and f.stat().st_size > 0]
        return self._read_links(existing or [root / "ent_links"])

    @staticmethod
    def _basic(label: str, rel: DataFrame, attr: DataFrame, entities: DataFrame) -> dict[str, float]:
        n_rel = rel.count()
        n_attr = attr.count()
        n_ent = entities.count()

        agg = rel.agg(F.countDistinct("predicate").alias("n_rel_props")).collect()[0]
        agg_attr = attr.agg(
            F.countDistinct("predicate").alias("n_attr_props"),
            F.countDistinct("tail").alias("n_literals"),
        ).collect()[0]

        return {
            f"{label}.n_entities": float(n_ent),
            f"{label}.n_relations": float(agg["n_rel_props"]),
            f"{label}.n_attributes": float(agg_attr["n_attr_props"]),
            f"{label}.n_literals": float(agg_attr["n_literals"]),
            f"{label}.n_rel_triples": float(n_rel),
            f"{label}.n_attr_triples": float(n_attr),
            f"{label}.attr_to_rel_ratio": float(n_attr / n_rel) if n_rel else 0.0,
            f"{label}.rel_triples_per_entity": float(n_rel / n_ent) if n_ent else 0.0,
            f"{label}.attr_triples_per_entity": float(n_attr / n_ent) if n_ent else 0.0,
        }

    @staticmethod
    def _degree(label: str, rel: DataFrame, entities: DataFrame) -> dict[str, float]:
        """Degrees via two group-bys and a left join — the relational formulation."""
        out_deg = rel.groupBy("head").count().withColumnRenamed("count", "out_degree")
        in_deg = rel.groupBy("tail").count().withColumnRenamed("count", "in_degree")

        degrees = (
            entities.join(out_deg, entities["e"] == out_deg["head"], "left")
            .join(in_deg, entities["e"] == in_deg["tail"], "left")
            .select(
                F.col("e"),
                F.coalesce(F.col("out_degree"), F.lit(0)).alias("out_degree"),
                F.coalesce(F.col("in_degree"), F.lit(0)).alias("in_degree"),
            )
            .withColumn("total_degree", F.col("out_degree") + F.col("in_degree"))
            .cache()
        )

        stats: dict[str, float] = {}
        for col in ("in_degree", "out_degree", "total_degree"):
            row = degrees.agg(
                F.mean(col).alias("mean"),
                F.stddev_pop(col).alias("std"),
                F.min(col).alias("min"),
                F.max(col).alias("max"),
                F.skewness(col).alias("skew"),
                F.kurtosis(col).alias("kurt"),
            ).collect()[0]

            quantiles = degrees.approxQuantile(col, [0.25, 0.5, 0.75, 0.95, 0.99], 0.0)
            stats.update(
                {
                    f"{label}.{col}.mean": float(row["mean"] or 0.0),
                    f"{label}.{col}.std": float(row["std"] or 0.0),
                    f"{label}.{col}.min": float(row["min"] or 0.0),
                    f"{label}.{col}.max": float(row["max"] or 0.0),
                    f"{label}.{col}.p25": float(quantiles[0]),
                    f"{label}.{col}.median": float(quantiles[1]),
                    f"{label}.{col}.p75": float(quantiles[2]),
                    f"{label}.{col}.p95": float(quantiles[3]),
                    f"{label}.{col}.p99": float(quantiles[4]),
                    f"{label}.{col}.skewness": float(row["skew"] or 0.0),
                    f"{label}.{col}.kurtosis": float(row["kurt"] or 0.0),
                }
            )

        stats[f"{label}.total_degree.gini"] = _gini_spark(degrees, "total_degree")

        n = degrees.count()
        for k in (0, 2, 5):
            share = degrees.where(F.col("total_degree") <= k).count() / n if n else 0.0
            key = "share_isolated" if k == 0 else f"share_deg_le_{k}"
            stats[f"{label}.{key}"] = float(share)

        degrees.unpersist()
        return stats

    @staticmethod
    def _properties(label: str, rel: DataFrame, attr: DataFrame) -> dict[str, float]:
        stats: dict[str, float] = {}
        for kind, df in (("rel", rel), ("attr", attr)):
            counts = df.groupBy("predicate").count().cache()
            total = df.count()
            n_props = counts.count()

            top10 = (
                counts.orderBy(F.col("count").desc()).limit(10)
                .agg(F.sum("count").alias("s")).collect()[0]["s"] or 0
            )
            long_tail = (
                counts.where(F.col("count") < F.lit(0.01 * total)).count() if total else 0
            )
            entropy_row = (
                counts.withColumn("p", F.col("count") / F.lit(max(total, 1)))
                .agg(F.sum(-F.col("p") * (F.log2(F.col("p")))).alias("h"))
                .collect()[0]
            )

            stats[f"{label}.{kind}.n_properties"] = float(n_props)
            stats[f"{label}.{kind}.top10_concentration"] = float(top10 / total) if total else 0.0
            stats[f"{label}.{kind}.long_tail_share"] = (
                float(long_tail / n_props) if n_props else 0.0
            )
            stats[f"{label}.{kind}.entropy_norm"] = (
                float((entropy_row["h"] or 0.0) / np.log2(n_props)) if n_props > 1 else 0.0
            )
            counts.unpersist()
        return stats


def _gini_spark(degrees: DataFrame, col: str) -> float:
    """Gini coefficient using a window over the sorted values.

    Same formula as utils.stats.gini, expressed relationally:
        G = 2 * sum(i * x_i) / (n * sum(x)) - (n + 1) / n
    """
    ranked = degrees.select(F.col(col).cast("double").alias("v")).withColumn(
        "i", F.row_number().over(Window.orderBy(F.col("v").asc()))
    )
    row = ranked.agg(
        F.sum(F.col("i") * F.col("v")).alias("weighted"),
        F.sum("v").alias("total"),
        F.count("*").alias("n"),
    ).collect()[0]

    n, total = row["n"], row["total"]
    if not n or not total:
        return 0.0
    return float(2.0 * row["weighted"] / (n * total) - (n + 1.0) / n)


def compare_backends(
    pandas_scalars: dict[str, float], spark_scalars: dict[str, float], tolerance: float = 1e-6
) -> pd.DataFrame:
    """Row-by-row comparison of the two backends on the comparable core metrics."""
    rows = []
    for key in COMPARABLE_KEYS:
        a, b = pandas_scalars.get(key), spark_scalars.get(key)
        if a is None or b is None:
            rows.append({"metric": key, "pandas": a, "spark": b, "abs_diff": None, "match": False})
            continue
        diff = abs(float(a) - float(b))
        rows.append(
            {
                "metric": key,
                "pandas": float(a),
                "spark": float(b),
                "abs_diff": diff,
                "match": diff <= tolerance * max(1.0, abs(float(a))),
            }
        )
    return pd.DataFrame(rows)


def timed_compute(session: SparkSession, path: str | Path, fold: int = 1) -> tuple[dict, float]:
    start = time.perf_counter()
    scalars = SparkCoreMetrics(session).compute(path, fold=fold)
    return scalars, time.perf_counter() - start
