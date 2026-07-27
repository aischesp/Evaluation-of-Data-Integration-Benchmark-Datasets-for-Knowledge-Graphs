"""Parsing and normalisation of the literal strings used in OpenEA files.

OpenEA stores object values of attribute triples verbatim in N-Triples-ish
notation, but not consistently: DBpedia uses full datatype URIs
(`"23"^^<http://www.w3.org/2001/XMLSchema#nonNegativeInteger>`), YAGO uses the
`xsd:` prefix (`"1946-06-04"^^xsd:date`), some values carry a language tag
(`"Titel"@ita`) and some are bare strings. Both the quality metrics and the
matchers need one canonical form, so the parsing lives here.
"""

from __future__ import annotations

import re
import unicodedata

_TYPED = re.compile(r'^"(?P<v>.*)"\^\^<?(?P<t>[^>]*)>?$', re.DOTALL)
_LANG = re.compile(r'^"(?P<v>.*)"@(?P<l>[A-Za-z-]+)$', re.DOTALL)
_QUOTED = re.compile(r'^"(?P<v>.*)"$', re.DOTALL)
_NUMERIC = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")
_TOKEN = re.compile(r"[0-9a-z]+")


def parse_literal(raw: str) -> tuple[str, str, str]:
    """Split a raw literal into (value, datatype, language).

    `datatype` is the local name of the XSD/DBpedia type or a coarse inferred
    label ('numeric', 'string', 'empty'); `language` is '' when untagged.
    """
    if not raw:
        return "", "empty", ""

    m = _TYPED.match(raw)
    if m:
        return m.group("v"), _local_name(m.group("t")), ""

    m = _LANG.match(raw)
    if m:
        return m.group("v"), "langString", m.group("l")

    m = _QUOTED.match(raw)
    value = m.group("v") if m else raw

    if _NUMERIC.match(value):
        return value, "numeric", ""
    return value, "string", ""


def literal_value(raw: str) -> str:
    """Just the value part of a literal."""
    return parse_literal(raw)[0]


def _local_name(datatype: str) -> str:
    """`http://www.w3.org/2001/XMLSchema#date` / `xsd:date` -> `date`."""
    for sep in ("#", "/", ":"):
        if sep in datatype:
            datatype = datatype.rsplit(sep, 1)[1]
    return datatype or "unknown"


def normalize_value(raw: str) -> str:
    """Lower-cased, accent-folded, whitespace-collapsed value for comparison."""
    value = literal_value(raw)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(value.lower().split())


def tokenize(raw: str) -> list[str]:
    """Alphanumeric tokens of a normalised literal, used by the lexical matchers."""
    return _TOKEN.findall(normalize_value(raw))


def local_name(uri: str) -> str:
    """Local name of a URI — the part after the last '/', '#' or ':'."""
    for sep in ("#", "/"):
        if sep in uri:
            uri = uri.rsplit(sep, 1)[1]
    return uri


def namespace(uri: str) -> str:
    """Namespace of a URI, i.e. everything up to and including the last separator."""
    for sep in ("#", "/"):
        if sep in uri:
            return uri.rsplit(sep, 1)[0] + sep
    return uri
