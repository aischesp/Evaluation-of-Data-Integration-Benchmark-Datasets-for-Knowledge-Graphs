<<<<<<< HEAD
"""Loader für das OpenEA-Dateiformat.

Erwartete Verzeichnis-Layout (siehe github.com/nju-websoft/OpenEA):

    <root>/
    ├── rel_triples_1        head \\t relation \\t tail
    ├── rel_triples_2
    ├── attr_triples_1       head \\t attribute \\t literal
    ├── attr_triples_2
    ├── ent_links            e1 \\t e2
    └── 721_5fold/
        └── 1/
            ├── train_links
            ├── valid_links
            └── test_links
=======
"""OpenEA dataset loader.

Expected directory layout (see github.com/nju-websoft/OpenEA):

    <root>/
        rel_triples_1     - head TAB relation TAB tail
        rel_triples_2
        attr_triples_1    - head TAB attribute TAB literal
        attr_triples_2
        ent_links         - e1 TAB e2
        721_5fold/1/{train,valid,test}_links
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.loaders.base import BaseLoader


class OpenEALoader(BaseLoader):
    name = "openea"

    @property
    def supported_formats(self) -> list[str]:
        return [".tsv", ".txt", ""]

    def load(self, path: Path) -> KGPair:
        path = Path(path)
        if not path.is_dir():
<<<<<<< HEAD
            raise FileNotFoundError(f"Kein OpenEA-Verzeichnis: {path}")
=======
            raise FileNotFoundError(f"Not an OpenEA directory: {path}")
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468

        kg1 = self._load_kg(name=f"{path.name}__kg1", rel_file=path / "rel_triples_1", attr_file=path / "attr_triples_1")
        kg2 = self._load_kg(name=f"{path.name}__kg2", rel_file=path / "rel_triples_2", attr_file=path / "attr_triples_2")
        alignments = self._load_alignments(path)

        return KGPair(name=path.name, kg1=kg1, kg2=kg2, alignments=alignments, meta={"format": "openea"})

    @staticmethod
    def _load_kg(name: str, rel_file: Path, attr_file: Path) -> KnowledgeGraph:
        rel = pd.read_csv(rel_file, sep="\t", header=None, names=["head", "relation", "tail"], dtype=str, na_filter=False)

        if attr_file.exists():
            attr = pd.read_csv(
                attr_file, sep="\t", header=None,
                names=["head", "attribute", "literal"], dtype=str, na_filter=False,
            )
            attr["datatype"] = attr["literal"].apply(_infer_datatype)
        else:
            attr = pd.DataFrame(columns=["head", "attribute", "literal", "datatype"])

        entities = pd.DataFrame({
            "entity_uri": pd.concat([rel["head"], rel["tail"], attr["head"]]).drop_duplicates().reset_index(drop=True)
        })

        return KnowledgeGraph(name=name, entities=entities, rel_triples=rel, attr_triples=attr)

    @staticmethod
    def _load_alignments(path: Path) -> pd.DataFrame:
        fold_dir = path / "721_5fold" / "1"
        if fold_dir.is_dir():
            train = _read_align(fold_dir / "train_links", "train")
            valid = _read_align(fold_dir / "valid_links", "valid")
            test = _read_align(fold_dir / "test_links", "test")
            return pd.concat([train, valid, test], ignore_index=True)

<<<<<<< HEAD
        # Fallback: nur ent_links vorhanden (kein Split)
=======
        # fall back to ent_links (no split available)
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
        return _read_align(path / "ent_links", "all")


def _read_align(file: Path, split: str) -> pd.DataFrame:
    if not file.exists():
        return pd.DataFrame(columns=["e1", "e2", "split"])
    df = pd.read_csv(file, sep="\t", header=None, names=["e1", "e2"], dtype=str, na_filter=False)
    df["split"] = split
    return df


def _infer_datatype(literal: str) -> str:
<<<<<<< HEAD
    """Sehr leichte Datentyp-Inferenz aus dem Literal-String.

    Für vollständige Inferenz wäre rdflib nötig — hier reicht eine Heuristik für die
    Coverage-Metrik.
=======
    """Light-weight datatype inference from the literal string.

    Good enough for coverage metrics; for full RDF semantics use rdflib.
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
    """
    if not literal:
        return "empty"
    if literal.startswith('"') and "^^" in literal:
        return literal.rsplit("^^", 1)[1].strip("<>")
    if literal.startswith('"') and "@" in literal[1:]:
        return "lang_string"
    if literal.lstrip("-").replace(".", "", 1).isdigit():
        return "numeric"
    return "string"
