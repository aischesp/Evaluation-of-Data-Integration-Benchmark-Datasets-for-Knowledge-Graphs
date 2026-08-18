"""Überführung der OpenEA-Spalten in rdflib-Terme.

Warum nicht einfach `Graph().parse(pfad)`? Weil die OpenEA-Dateien kein
RDF-Serialisierungsformat sind, auch wenn OpenEA ein RDF-Datensatz ist. Sie sind
tab-separiert, die URIs stehen ohne spitze Klammern da, die abschliessenden
Punkte fehlen, und YAGO-Terme wie `YAGO/E473489` oder `isLocatedIn` sind gar
keine IRIs. `scripts/check_openea_rdf.py` weist das nach: der Parser scheitert
auf jeder Datei in jedem Format.

Deshalb wird hier spaltenweise gearbeitet — aber die Termkonstruktion selbst
übernimmt rdflib (`rdflib.util.from_n3`), nicht eigene reguläre Ausdrücke. Das
deckt Datentypen (`"23"^^<...>`), Präfixnotation (`"1946-06-04"^^xsd:date`) und
Sprach-Tags (`"Titel"@ita`) korrekt ab.

Ein Teil der Objektspalte (je nach Datensatz 8–43 %) besteht aus unquotierten
Rohstrings, die kein gültiger RDF-Term sind. Diese werden dokumentiert als
einfaches Literal behandelt — die Alternative wäre, ein Drittel der
Attributwerte zu verwerfen.
"""

from __future__ import annotations

import logging
import unicodedata
from functools import lru_cache
from urllib.parse import quote, unquote

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.util import from_n3

# rdflib protokolliert jede ungültige Lexikalform einzeln (OpenEA enthält z. B.
# das Datum "-0070-10-15"). Wir zählen sie stattdessen über `is_ill_typed` als
# Qualitätsmetrik, deshalb hier keine Log-Flut.
logging.getLogger("rdflib.term").setLevel(logging.ERROR)

# Namespace-Manager, damit Präfixnotation wie `xsd:date` aufgelöst werden kann.
_NS_GRAPH = Graph()
_NS_GRAPH.bind("xsd", XSD)
NSM = _NS_GRAPH.namespace_manager

# Terme, die keine absoluten IRIs sind (YAGO), werden reversibel in diesen
# Namespace abgebildet. Das ist auch für PARIS nötig, das bekannte Namespaces
# in seiner Ausgabe abkürzt und den Rückweg sonst unmöglich macht.
SYNTHETIC_NS = "http://openea.local/"

_TOKEN_CHARS = set("0123456789abcdefghijklmnopqrstuvwxyz")


@lru_cache(maxsize=200_000)
def to_literal(raw: str) -> Literal | None:
    """Objektwert -> rdflib-Literal. `None` bei leerem Wert.

    Gecacht, weil Werte wie Jahreszahlen tausendfach vorkommen.
    """
    if not raw:
        return None
    try:
        term = from_n3(raw, nsm=NSM)
    except Exception:  # noqa: BLE001 - defekte Lexikalform, siehe Modul-Docstring
        return Literal(raw)

    # from_n3 liefert für unquotierte Strings einen BNode statt eines Literals.
    if not isinstance(term, Literal):
        return Literal(raw)
    # Ein leeres Ergebnis bei nicht-leerer Eingabe heisst: nicht parsebar.
    if str(term) == "" and raw.strip() != '""':
        return Literal(raw)
    return term


def parse_literal(raw: str) -> tuple[str, str, str]:
    """(Wert, Datentyp-Lokalname, Sprache) — die Form, die die Metriken nutzen."""
    term = to_literal(raw)
    if term is None:
        return "", "empty", ""

    value = str(term)
    if term.language:
        return value, "langString", term.language
    if term.datatype:
        return value, local_name(str(term.datatype)), ""
    return value, "numeric" if _looks_numeric(value) else "string", ""


def is_ill_typed(raw: str) -> bool:
    """Hat der Wert einen Datentyp, passt aber nicht dazu?

    rdflib prüft die Lexikalform gegen den angegebenen XSD-Typ. OpenEA enthält
    z. B. `"3.6e"^^xsd:double` und `"-0070-10-15"^^xsd:date`. Wir nutzen das als
    Datenqualitätsmetrik des Benchmarks.
    """
    term = to_literal(raw)
    return bool(term is not None and getattr(term, "ill_typed", False))


def literal_value(raw: str) -> str:
    """Nur der Wertanteil."""
    return parse_literal(raw)[0]


def _looks_numeric(value: str) -> bool:
    stripped = value.lstrip("+-")
    return stripped.replace(".", "", 1).isdigit() and stripped != ""


def to_uriref(term: str, kind: str) -> URIRef:
    """Reversible IRI für einen OpenEA-Term.

    Auch absolute URIs werden abgebildet: PARIS kürzt bekannte Namespaces in
    seiner Ausgabe ab (`http://dbpedia.org/resource/X` -> `dbp:resource/X`),
    wodurch der Rückweg auf die Originalkennung verlorenginge.
    """
    return URIRef(f"{SYNTHETIC_NS}{kind}/{quote(term, safe='')}")


def from_uriref(uri: str) -> str:
    """Umkehrung von `to_uriref`."""
    uri = uri.strip().strip("<>")
    if uri.startswith(SYNTHETIC_NS):
        _, _, encoded = uri[len(SYNTHETIC_NS) :].partition("/")
        return unquote(encoded)
    return uri


def normalize_value(raw: str) -> str:
    """Kleingeschrieben, akzentfrei, Leerraum normalisiert — für Vergleiche."""
    value = literal_value(raw)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(value.lower().split())


def tokenize(raw: str) -> list[str]:
    """Alphanumerische Tokens eines normalisierten Werts."""
    text = normalize_value(raw)
    tokens, current = [], []
    for char in text:
        if char in _TOKEN_CHARS:
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def char_ngrams(raw: str, n: int = 3) -> list[str]:
    """Zeichen-n-Gramme eines normalisierten Werts.

    Robuster gegen Schreibvarianten als Wort-Tokens und damit die übliche Wahl
    für Record Linkage über Namen und kurze Werte.
    """
    text = normalize_value(raw)
    if len(text) < n:
        return [text] if text else []
    return [text[i : i + n] for i in range(len(text) - n + 1)]


def local_name(uri: str) -> str:
    """Lokalname einer URI — der Teil nach dem letzten '/', '#' oder ':'."""
    for sep in ("#", "/"):
        if sep in uri:
            uri = uri.rsplit(sep, 1)[1]
    return uri


def namespace(uri: str) -> str:
    """Namespace einer URI, inklusive des letzten Trennzeichens."""
    for sep in ("#", "/"):
        if sep in uri:
            return uri.rsplit(sep, 1)[0] + sep
    return uri
