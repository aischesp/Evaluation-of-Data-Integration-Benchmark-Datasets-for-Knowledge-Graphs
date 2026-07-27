"""Export a KnowledgeGraph to N-Triples so external tools can read it.

PARIS expects two RDF files, but the OpenEA dumps are tab-separated and not
valid RDF: YAGO subjects look like `YAGO/E473489`, YAGO predicates like
`isLocatedIn`, and literal datatypes are written inconsistently (`xsd:date`
vs. a full URI). We therefore rewrite every term into a well-formed N-Triples
term using rdflib's own term classes, which gives us correct IRI and literal
escaping without holding a full rdflib Graph in memory — important for the
100 K datasets.

*Every* term is mapped into a synthetic namespace in a reversible way. Doing
this for all terms rather than only for the malformed ones is deliberate: PARIS
abbreviates well-known namespaces in its output (`http://dbpedia.org/resource/X`
comes back as `dbp:resource/X`), which would break the mapping from its results
onto the original OpenEA identifiers. A namespace PARIS does not know is left
verbatim, so the round-trip stays exact.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote

from rdflib import Literal, URIRef

from kg_quality_eval.core import KnowledgeGraph
from kg_quality_eval.utils.literals import parse_literal

SYNTHETIC_NS = "http://openea.local/"


def to_uriref(term: str, kind: str) -> URIRef:
    """Reversible synthetic IRI for any OpenEA term."""
    return URIRef(f"{SYNTHETIC_NS}{kind}/{quote(term, safe='')}")


def from_uriref(uri: str) -> str:
    """Inverse of `to_uriref` — recover the original OpenEA identifier."""
    uri = uri.strip().strip("<>")
    if uri.startswith(SYNTHETIC_NS):
        _, _, encoded = uri[len(SYNTHETIC_NS) :].partition("/")
        return unquote(encoded)
    return uri


def write_ntriples(kg: KnowledgeGraph, target: Path, kind: str = "e") -> Path:
    """Serialise a KG to N-Triples. Returns the written path.

    Attribute values are written as plain (untyped) literals on purpose: the
    original datatype annotations in OpenEA are partly malformed, and PARIS
    compares literals as strings anyway.
    """
    target.parent.mkdir(parents=True, exist_ok=True)

    with open(target, "w", encoding="utf-8") as out:
        for head, rel, tail in zip(
            kg.rel_triples["head"], kg.rel_triples["relation"], kg.rel_triples["tail"], strict=False
        ):
            out.write(
                f"{to_uriref(head, kind).n3()} "
                f"{to_uriref(rel, 'p').n3()} "
                f"{to_uriref(tail, kind).n3()} .\n"
            )

        for head, attr, literal in zip(
            kg.attr_triples["head"], kg.attr_triples["attribute"], kg.attr_triples["literal"],
            strict=False,
        ):
            value = parse_literal(literal)[0]
            if not value:
                continue
            out.write(
                f"{to_uriref(head, kind).n3()} "
                f"{to_uriref(attr, 'p').n3()} "
                f"{Literal(value).n3()} .\n"
            )

    return target
