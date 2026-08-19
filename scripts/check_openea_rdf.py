#!/usr/bin/env python
"""Prüft, ob die OpenEA-Dateien als RDF geparst werden können.

Hintergrund: Im Testat 2 kam die Frage auf, warum wir die OpenEA-Dateien nicht
einfach mit `rdflib.Graph().parse(pfad)` einlesen — OpenEA gilt als bekannter
RDF-Datensatz. Dieses Skript beantwortet das messbar statt per Behauptung.

Ergebnis (siehe docs/Ergebnisse.md): Die Dateien sind tab-separierte Tripel,
aber kein gültiges RDF-Serialisierungsformat. Die Subjekt- und Prädikatspalten
enthalten nackte URIs ohne spitze Klammern, es fehlen die abschliessenden
Punkte, und ein Teil der Objektspalte besteht aus unquotierten Rohstrings.

    python scripts/check_openea_rdf.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kg_quality_eval.utils.console import enable_utf8_output  # noqa: E402

enable_utf8_output()

# rdflib meldet jede ungueltige Lexikalform einzeln; wir zaehlen sie stattdessen.
logging.getLogger("rdflib.term").setLevel(logging.ERROR)

from rdflib import Graph, Literal  # noqa: E402
from rdflib.util import from_n3  # noqa: E402

from kg_quality_eval.utils.literals import NSM  # noqa: E402

FORMATS = ("nt", "turtle")
FILES = ("rel_triples_1", "rel_triples_2", "attr_triples_1", "attr_triples_2")


def try_parse(path: Path) -> dict[str, str]:
    """Versucht, eine Datei in jedem RDF-Format zu parsen."""
    out = {}
    for fmt in FORMATS:
        graph = Graph()
        try:
            graph.parse(str(path), format=fmt)
            out[fmt] = f"OK ({len(graph)} Tripel)"
        except Exception as exc:  # noqa: BLE001 - genau das wollen wir zeigen
            out[fmt] = f"{type(exc).__name__}"
    return out


def classify_objects(path: Path) -> dict[str, int]:
    """Zählt, wie viele Objektwerte gültige RDF-Terme sind."""
    df = pd.read_csv(
        path, sep="\t", header=None, names=["s", "p", "o"],
        dtype=str, na_filter=False, quoting=3,
    )
    counts = {"gueltiger_term": 0, "kein_gueltiger_term": 0, "leer": 0, "ill_typed": 0}
    for value in df["o"]:
        if not value:
            counts["leer"] += 1
            continue
        try:
            term = from_n3(value, nsm=NSM)
        except Exception:  # noqa: BLE001
            counts["kein_gueltiger_term"] += 1
            continue
        if isinstance(term, Literal) and (str(term) != "" or value.strip() == '""'):
            counts["gueltiger_term"] += 1
            if getattr(term, "ill_typed", False):
                counts["ill_typed"] += 1
        else:
            counts["kein_gueltiger_term"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="*",
                        default=["EN_FR_15K_V1", "D_W_15K_V1", "D_Y_15K_V1"])
    parser.add_argument("--data-root", default="data/raw/openea")
    parser.add_argument("--out", default="results/reports/openea_rdf_check.csv")
    args = parser.parse_args()

    root = Path(args.data_root)
    rows = []

    print("=== 1. Können die Rohdateien als RDF geparst werden? ===\n")
    for name in args.datasets:
        for filename in FILES:
            path = root / name / filename
            if not path.exists():
                continue
            result = try_parse(path)
            print(f"{name:14} {filename:16} " +
                  "  ".join(f"{fmt}: {res}" for fmt, res in result.items()))
            rows.append({"dataset": name, "file": filename, "check": "parse", **result})

    print("\n=== 2. Wie viele Objektwerte sind gültige RDF-Terme? ===\n")
    for name in args.datasets:
        for filename in ("attr_triples_1", "attr_triples_2"):
            path = root / name / filename
            if not path.exists():
                continue
            counts = classify_objects(path)
            total = sum(counts[k] for k in ("gueltiger_term", "kein_gueltiger_term", "leer"))
            invalid_share = 100 * counts["kein_gueltiger_term"] / max(total, 1)
            print(f"{name:14} {filename:16} "
                  f"{total:>8,} Objekte | "
                  f"kein gültiger Term: {counts['kein_gueltiger_term']:>7,} ({invalid_share:5.1f}%) | "
                  f"ill-typed: {counts['ill_typed']:>5,}")
            rows.append({
                "dataset": name, "file": filename, "check": "objects",
                "n_objects": total, **counts,
                "share_invalid_term": round(invalid_share / 100, 4),
            })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n✓ {out}")
    print("\nFazit: Die OpenEA-Dateien sind TSV, kein RDF-Serialisierungsformat.")
    print("Ein direktes Graph().parse(pfad) ist daher nicht möglich; die Terme")
    print("werden stattdessen spaltenweise über rdflib konstruiert.")


if __name__ == "__main__":
    main()
