"""Shared fixtures: a tiny synthetic OpenEA dataset with known ground truth.

The numbers in the tests are hand-derived from this fixture, so a metric that
silently changes its definition fails the suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_quality_eval.loaders import OpenEALoader

# KG1: a triangle a-b-c plus a pendant d, and an isolated e (alignment only).
REL_1 = """\
kg1:a\tknows\tkg1:b
kg1:b\tknows\tkg1:c
kg1:c\tknows\tkg1:a
kg1:a\tknows\tkg1:d
"""

# KG2 mirrors the structure with different property names.
REL_2 = """\
kg2:A\tconnait\tkg2:B
kg2:B\tconnait\tkg2:C
kg2:C\tconnait\tkg2:A
kg2:A\tconnait\tkg2:D
"""

ATTR_1 = """\
kg1:a\tname\t"Alice"
kg1:a\tborn\t"1990-01-01"^^<http://www.w3.org/2001/XMLSchema#date>
kg1:b\tname\t"Bob"
kg1:c\tname\t"Carol"
kg1:c\tage\t"31"
"""

ATTR_2 = """\
kg2:A\tnom\t"Alice"
kg2:A\tne\t"1990-01-01"^^xsd:date
kg2:B\tnom\t"Bob"
kg2:D\tnom\t"Dan"@fra
"""

# 5 gold pairs; e/E exist only here, so they have degree 0.
LINKS = [
    ("kg1:a", "kg2:A"),
    ("kg1:b", "kg2:B"),
    ("kg1:c", "kg2:C"),
    ("kg1:d", "kg2:D"),
    ("kg1:e", "kg2:E"),
]


@pytest.fixture
def openea_dir(tmp_path: Path) -> Path:
    root = tmp_path / "MINI_5"
    root.mkdir()

    (root / "rel_triples_1").write_text(REL_1, encoding="utf-8")
    (root / "rel_triples_2").write_text(REL_2, encoding="utf-8")
    (root / "attr_triples_1").write_text(ATTR_1, encoding="utf-8")
    (root / "attr_triples_2").write_text(ATTR_2, encoding="utf-8")

    all_links = "".join(f"{a}\t{b}\n" for a, b in LINKS)
    (root / "ent_links").write_text(all_links, encoding="utf-8")

    fold = root / "721_5fold" / "1"
    fold.mkdir(parents=True)
    (fold / "train_links").write_text("".join(f"{a}\t{b}\n" for a, b in LINKS[:2]), encoding="utf-8")
    (fold / "valid_links").write_text(f"{LINKS[2][0]}\t{LINKS[2][1]}\n", encoding="utf-8")
    (fold / "test_links").write_text("".join(f"{a}\t{b}\n" for a, b in LINKS[3:]), encoding="utf-8")

    return root


@pytest.fixture
def kg_pair(openea_dir: Path):
    return OpenEALoader().load(openea_dir)
