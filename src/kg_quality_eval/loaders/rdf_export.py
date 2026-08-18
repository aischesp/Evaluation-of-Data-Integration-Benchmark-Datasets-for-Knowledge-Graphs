"""Export eines KnowledgeGraph nach RDF über rdflib.

PARIS erwartet zwei RDF-Dateien. Der Export baut dafür einen echten
`rdflib.Graph` auf und lässt ihn von rdflib serialisieren — die Formatierung,
das IRI- und Literal-Escaping und die Gültigkeit der Ausgabe verantwortet damit
die Bibliothek, nicht wir.

Die Gegenrichtung ist über `parse_ntriples` verfügbar und wird in den Tests als
Round-Trip geprüft: was wir schreiben, muss rdflib auch wieder einlesen können.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal

from kg_quality_eval.core import KnowledgeGraph
from kg_quality_eval.utils.literals import from_uriref, to_literal, to_uriref

__all__ = ["build_graph", "from_uriref", "parse_ntriples", "to_uriref", "write_rdf"]


def build_graph(kg: KnowledgeGraph, kind: str = "e") -> Graph:
    """Baut einen rdflib-Graph aus der internen Repräsentation.

    Attributwerte werden als einfache Literale ohne Datentyp geschrieben: die
    Datentyp-Annotationen in OpenEA sind teils fehlerhaft (siehe
    `utils.literals.is_ill_typed`), und PARIS vergleicht Literale ohnehin als
    Zeichenketten.
    """
    graph = Graph()

    for head, relation, tail in zip(
        kg.rel_triples["head"], kg.rel_triples["relation"], kg.rel_triples["tail"],
        strict=False,
    ):
        graph.add((to_uriref(head, kind), to_uriref(relation, "p"), to_uriref(tail, kind)))

    for head, attribute, raw in zip(
        kg.attr_triples["head"], kg.attr_triples["attribute"], kg.attr_triples["literal"],
        strict=False,
    ):
        term = to_literal(raw)
        if term is None:
            continue
        graph.add((to_uriref(head, kind), to_uriref(attribute, "p"), Literal(str(term))))

    return graph


def write_rdf(
    kg: KnowledgeGraph, target: Path, kind: str = "e", fmt: str = "nt"
) -> tuple[Path, int]:
    """Serialisiert einen KG nach RDF. Gibt (Pfad, Anzahl Tripel) zurück."""
    target.parent.mkdir(parents=True, exist_ok=True)
    graph = build_graph(kg, kind=kind)
    graph.serialize(destination=str(target), format=fmt, encoding="utf-8")
    return target, len(graph)


def parse_ntriples(path: Path) -> Graph:
    """Liest eine RDF-Datei wieder ein — Gegenstück zu `write_rdf`."""
    graph = Graph()
    graph.parse(str(path), format="nt")
    return graph
