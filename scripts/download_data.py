#!/usr/bin/env python
"""Fetch the benchmark data and the PARIS jar.

The OpenEA archive (~240 MB) and the extracted datasets are not versioned, so
this script reproduces `data/raw/` and `tools/` from scratch:

    python scripts/download_data.py

Only the six datasets used in the study are extracted; pass --all to unpack the
complete archive.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

OPENEA_URL = "https://ndownloader.figshare.com/files/34234391"  # figshare, OpenEA v2.0
OPENEA_ZIP = Path("data/raw/openea/OpenEA_dataset_v2.0.zip")
OPENEA_ROOT = Path("data/raw/openea")

PARIS_URL = "https://github.com/dig-team/PARIS/releases/download/v0.3/paris_0_3.jar"
PARIS_JAR = Path("tools/paris_0_3.jar")

DATASETS = [
    "EN_FR_15K_V1",
    "EN_FR_15K_V2",
    "EN_DE_15K_V1",
    "D_W_15K_V1",
    "D_Y_15K_V1",
    "EN_FR_100K_V1",
]


def download(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"✓ {target} liegt bereits vor ({target.stat().st_size / 1e6:.0f} MB)")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"→ Lade {url}\n  nach {target} ...")
    with urllib.request.urlopen(url) as response, open(target, "wb") as out:  # noqa: S310
        shutil.copyfileobj(response, out)
    print(f"✓ {target.stat().st_size / 1e6:.0f} MB geladen")


def extract(zip_path: Path, wanted: set[str] | None) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        members = [
            info
            for info in archive.infolist()
            if len(info.filename.split("/")) > 1
            and (wanted is None or info.filename.split("/")[1] in wanted)
        ]
        for info in members:
            parts = info.filename.split("/")[1:]
            target = OPENEA_ROOT.joinpath(*parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if target.exists() and target.stat().st_size == info.file_size:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    print(f"✓ {len(members)} Dateien entpackt nach {OPENEA_ROOT}")


def verify() -> int:
    missing = 0
    for name in DATASETS:
        root = OPENEA_ROOT / name
        files = ["rel_triples_1", "rel_triples_2", "attr_triples_1", "attr_triples_2", "ent_links"]
        absent = [f for f in files if not (root / f).exists()]
        if absent:
            print(f"✗ {name}: fehlt {absent}")
            missing += 1
        else:
            n = sum(1 for _ in open(root / "ent_links", encoding="utf-8"))
            print(f"✓ {name}: {n} Referenz-Alignments")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Alle 16 OpenEA-Varianten entpacken")
    parser.add_argument("--keep-zip", action="store_true", help="Archiv nach dem Entpacken behalten")
    args = parser.parse_args()

    download(OPENEA_URL, OPENEA_ZIP)
    extract(OPENEA_ZIP, None if args.all else set(DATASETS))
    if not args.keep_zip:
        OPENEA_ZIP.unlink(missing_ok=True)
        print(f"✓ {OPENEA_ZIP} gelöscht (--keep-zip zum Behalten)")

    download(PARIS_URL, PARIS_JAR)

    print("\nVerifikation:")
    missing = verify()
    if missing:
        print(f"\n{missing} Datensätze unvollständig.")
        return 1

    print("\nAlles bereit. Nächster Schritt:")
    print("  python -m kg_quality_eval.runner --config config/datasets.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
