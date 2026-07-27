#!/usr/bin/env python
"""Generate config/datasets_extended.yaml from everything under data/raw/openea.

The extended configuration exists only to widen the sample of the correlation
analysis: with the six core datasets n = 6 is far too small to say anything
about which dataset properties drive matching quality. Running the identical
pipeline over all 16 OpenEA v2.0 variants gives n = 16.

    python scripts/download_data.py --all
    python scripts/make_extended_config.py
    python -m kg_quality_eval.runner --config config/datasets_extended.yaml
"""

from __future__ import annotations

from pathlib import Path

import yaml

BASE = Path("config/datasets.yaml")
TARGET = Path("config/datasets_extended.yaml")
RAW = Path("data/raw/openea")

HEADER = """# Erweiterte Konfiguration: alle OpenEA-v2.0-Varianten unter data/raw/openea.
#
# Zweck ist ausschliesslich die Korrelationsanalyse. Mit den sechs Kern-
# datensaetzen aus config/datasets.yaml ist n = 6 zu klein, um Zusammenhaenge
# zwischen Datensatz-Eigenschaften und Matching-Guete abzusichern; hier ist
# n = 16. Die Kernauswertung und alle Detailtabellen der Ausarbeitung stammen
# weiterhin aus config/datasets.yaml.
#
# Automatisch erzeugt von scripts/make_extended_config.py — nicht von Hand
# editieren.
"""


def main() -> None:
    config = yaml.safe_load(BASE.read_text(encoding="utf-8"))

    names = sorted(p.name for p in RAW.iterdir() if p.is_dir() and (p / "ent_links").exists())
    config["datasets"] = [
        {"name": n, "loader": "openea", "path": str(RAW / n), "fold": 1} for n in names
    ]
    config["output_dir"] = "results/reports_extended"
    config["figures_dir"] = "results/figures_extended"

    TARGET.write_text(
        HEADER + yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print(f"✓ {TARGET} mit {len(names)} Datensätzen geschrieben")


if __name__ == "__main__":
    main()
