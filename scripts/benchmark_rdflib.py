#!/usr/bin/env python
"""Vergleich rdflib vs. Pandas als Datenhaltung für die Kernmetriken.

Hintergrund: Im Testat-1-Gespräch wurde vorgeschlagen, statt Pandas/PySpark
einfach durchgängig rdflib zu verwenden ("die API reicht für die meisten
Sachen"). Dieses Skript prüft das nach, statt die Entscheidung zu behaupten:
es lädt denselben KG einmal in einen rdflib-Graph und einmal in unsere
Pandas-Repräsentation und misst Laufzeit, Speicher und Ergebnisgleichheit für
Triple-Count und Degree-Verteilung.

    python scripts/benchmark_rdflib.py --dataset EN_FR_15K_V1

Ergebnis geht nach results/reports/rdflib_vs_pandas.csv.
"""

from __future__ import annotations

import argparse
import resource
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kg_quality_eval.loaders import get_loader  # noqa: E402
from kg_quality_eval.loaders.rdf_export import write_rdf  # noqa: E402


def peak_memory_mb() -> float:
    """Maximum resident set size so far. macOS reports bytes, Linux kilobytes."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024


def pandas_path(dataset_dir: Path) -> dict:
    from kg_quality_eval.utils.literals import parse_literal

    start = time.perf_counter()
    kg_pair = get_loader("openea").load(dataset_dir)
    kg = kg_pair.kg1
    load_s = time.perf_counter() - start

    start = time.perf_counter()
    n_triples = kg.n_rel_triples() + kg.n_attr_triples()
    degrees = kg.degrees["total_degree"]
    metric_s = time.perf_counter() - start

    # Attribut-Tripel ohne Wert kommen nicht in den N-Triples-Export (ein
    # Literal ohne Inhalt ist kein gültiges RDF-Objekt). Für den fairen
    # Vergleich mit rdflib zählen wir sie hier separat.
    n_empty = sum(1 for v in kg.attr_triples["literal"] if not parse_literal(v)[0])

    return {
        "n_triples_exportable": int(n_triples - n_empty),
        "n_empty_literals": int(n_empty),
        "backend": "pandas",
        "load_s": round(load_s, 2),
        "metric_s": round(metric_s, 3),
        "n_triples": int(n_triples),
        "n_entities": kg.n_entities(),
        "mean_degree": round(float(degrees.mean()), 4),
        "max_degree": int(degrees.max()),
        "peak_rss_mb": round(peak_memory_mb(), 1),
    }


def rdflib_path(nt_file: Path) -> dict:
    from rdflib import Graph, Literal

    start = time.perf_counter()
    graph = Graph()
    graph.parse(str(nt_file), format="nt")
    load_s = time.perf_counter() - start

    # Dieselben Kennzahlen, aber über die rdflib-Triple-Iteration statt über
    # DataFrame-Operationen.
    start = time.perf_counter()
    n_triples = len(graph)

    degree: Counter = Counter()
    entities = set()
    for subject, _predicate, obj in graph:
        entities.add(subject)
        if not isinstance(obj, Literal):       # nur Relations-Tripel zählen als Grad
            degree[subject] += 1
            degree[obj] += 1
            entities.add(obj)
    metric_s = time.perf_counter() - start

    degrees = [degree.get(e, 0) for e in entities]
    return {
        "backend": "rdflib",
        "load_s": round(load_s, 2),
        "metric_s": round(metric_s, 3),
        "n_triples": int(n_triples),
        "n_triples_exportable": int(n_triples),
        "n_empty_literals": 0,
        "n_entities": len(entities),
        "mean_degree": round(sum(degrees) / len(degrees), 4) if degrees else 0.0,
        "max_degree": max(degrees) if degrees else 0,
        "peak_rss_mb": round(peak_memory_mb(), 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="EN_FR_15K_V1")
    parser.add_argument("--data-root", default="data/raw/openea")
    parser.add_argument("--out", default="results/reports/rdflib_vs_pandas.csv")
    args = parser.parse_args()

    dataset_dir = Path(args.data_root) / args.dataset
    if not dataset_dir.is_dir():
        raise SystemExit(f"Datensatz nicht gefunden: {dataset_dir}")

    print(f"Datensatz: {args.dataset} (KG1)\n")

    pandas_result = pandas_path(dataset_dir)
    print(f"pandas  laden {pandas_result['load_s']:6.2f}s  "
          f"Metriken {pandas_result['metric_s']:6.3f}s  "
          f"Peak-RSS {pandas_result['peak_rss_mb']:7.1f} MB")

    # Für rdflib brauchen wir gültiges RDF — die OpenEA-TSV ist keines.
    kg = get_loader("openea").load(dataset_dir).kg1
    nt_file = Path("data/processed/rdflib_benchmark") / f"{args.dataset}_kg1.nt"
    start = time.perf_counter()
    write_rdf(kg, nt_file, kind="e1")
    export_s = time.perf_counter() - start
    size_mb = nt_file.stat().st_size / 1e6
    print(f"        (N-Triples-Export vorab: {export_s:.2f}s, {size_mb:.0f} MB)")
    del kg

    rdflib_result = rdflib_path(nt_file)
    print(f"rdflib  laden {rdflib_result['load_s']:6.2f}s  "
          f"Metriken {rdflib_result['metric_s']:6.3f}s  "
          f"Peak-RSS {rdflib_result['peak_rss_mb']:7.1f} MB")

    table = pd.DataFrame([pandas_result, rdflib_result])
    table.insert(0, "dataset", args.dataset)

    print("\n" + table.to_string(index=False))

    print(
        f"\nTriple-Count roh:  Pandas {pandas_result['n_triples']} vs. "
        f"rdflib {rdflib_result['n_triples']}  "
        f"(Differenz {pandas_result['n_triples'] - rdflib_result['n_triples']} = "
        f"{pandas_result['n_empty_literals']} Attribut-Tripel mit leerem Literalwert)"
    )
    agree = pandas_result["n_triples_exportable"] == rdflib_result["n_triples_exportable"]
    print(f"Triple-Count nach Abzug leerer Literale identisch: {agree}")

    same_degree = (
        pandas_result["mean_degree"] == rdflib_result["mean_degree"]
        and pandas_result["max_degree"] == rdflib_result["max_degree"]
        and pandas_result["n_entities"] == rdflib_result["n_entities"]
    )
    print(f"Grad-Verteilung und Entitätsmenge identisch:       {same_degree}")

    factor_time = rdflib_result["load_s"] / max(pandas_result["load_s"], 1e-9)
    factor_mem = rdflib_result["peak_rss_mb"] / max(pandas_result["peak_rss_mb"], 1e-9)
    print(
        f"\nrdflib braucht Faktor {factor_time:.1f} der Ladezeit und Faktor "
        f"{factor_mem:.1f} des Speichers von Pandas —\nund benötigt zusätzlich den "
        f"N-Triples-Export ({export_s:.1f}s), weil OpenEA kein RDF ausliefert."
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    print(f"\n✓ {out}")


if __name__ == "__main__":
    main()
