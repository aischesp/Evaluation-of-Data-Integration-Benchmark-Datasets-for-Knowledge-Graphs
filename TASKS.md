# Offene Aufgaben — Aufteilung Aische ↔ Berkay

> Living Document. Status: `[ ]` offen · `[~]` in Arbeit · `[x]` erledigt.
> Bei jeder Änderung kurz in [`WORKLOG.md`](WORKLOG.md) notieren.

---

## 🔥 Sprint 1 — Testat 1 abschließen (bis 30.05.2026)

### Gemeinsam
- [ ] `docs/Entwurfsdokument.md` gemeinsam querlesen, Korrekturen einarbeiten
- [ ] Offene Fragen in `docs/Offene_Fragen.md` prüfen — was streichen, was ergänzen?
- [ ] Finalen Dateinamen festlegen: `Entwurfsdokument_KG-Quality_Spieker-Oezcekic.pdf`

### Berkay
- [ ] Pandoc installieren (s. `docs/PDF-Konvertierung.md` §A)
- [ ] PDF-Build durchführen, Seitenzahl prüfen (4–5 Seiten!)
- [ ] Falls Mermaid-Diagramme schöner gerendert werden sollen → `mermaid-cli` einsetzen
- [ ] Hofer als GitHub-Collaborator einladen (`hofer@informatik.uni-leipzig.de` → seinen GH-Handle erfragen)
- [ ] PDF an Hofer mailen + Repo-Link

### Aische
- [ ] Lokale Python-Umgebung aufsetzen: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- [ ] `pytest tests/test_smoke.py` laufen lassen — sollen alle 5 Tests grün sein
- [ ] OpenEA-Zip von <https://github.com/nju-websoft/OpenEA> herunterladen, `EN_FR_15K_V1` nach `data/raw/openea/EN_FR_15K_V1/` entpacken
- [ ] Smoke-Run: `python -m kg_quality_eval.runner --config config/datasets.example.yaml --verbose` und prüfen, dass `results/reports/openea_en_fr_15k_v1/basic_stats.json` plausible Zahlen enthält

---

## 📦 Sprint 2 — Datenbeschaffung + Loader-Vervollständigung (KW 21–22)

### Aische
- [ ] Alle 6 OpenEA-Varianten herunterladen (EN_FR_15K_V1+V2, EN_DE_15K_V1, D_W_15K_V1, D_Y_15K_V1, EN_FR_100K_V1)
- [ ] `OpenEALoader` ggf. anpassen, falls Pfad-Struktur abweicht
- [ ] Unit-Tests pro Datensatz: Lädt `kg_pair.kg1.n_entities()` ≈ 15 000?

### Berkay
- [ ] `RDFLoader` für OAEI Conference implementieren (`src/kg_quality_eval/loaders/rdf.py`)
  - Eingabe: `.owl` / `.rdf` / `.ttl` über `rdflib`
  - Output: dieselbe `KGPair`-Struktur
- [ ] OAEI Conference Track herunterladen: <https://oaei.ontologymatching.org/2023/conference/>
- [ ] Loader im `loaders/__init__.py`-Registry eintragen
- [ ] Smoke-Test analog zu OpenEA

---

## 📊 Sprint 3 — Strukturelle Metriken (KW 23–24)

### Aische
- [ ] `src/kg_quality_eval/metrics/structural.py` anlegen
- [ ] Klassen `DegreeDistribution` (in/out/total) mit Kennzahlen + Histogramm
- [ ] Tests + Beispiel-Notebook `notebooks/01_degree_analysis.ipynb`

### Berkay
- [ ] `PropertyDistribution` (Häufigkeiten, Top-k-Konzentration)
- [ ] `Connectivity` (NetworkX) — vorsichtshalber Sampling-Pfad bei >100K Knoten
- [ ] `PowerLawFit` via `powerlaw`-Bibliothek oder eigene MLE-Impl. nach Clauset

---

## 🎯 Sprint 4 — Qualitätsmetriken (KW 25–26)

### Aische
- [ ] `AttributeCompleteness` — Coverage pro Property, aggregiert
- [ ] `TypeDistribution` — falls Typen extrahierbar (rdf:type, URI-Heuristik)
- [ ] `LongTailAnalysis` — Gini, P_k

### Berkay
- [ ] `AlignmentMetrics` — Coverage, Ambiguität, bijektiver Anteil
- [ ] `AlignedConsistency` — Degree-Korrelation, Typ-Jaccard
- [ ] `SchemaHeterogeneity` — Property-Jaccard, Entropy (optional)

---

## 🚀 Sprint 5 — Skalierung (KW 27–28)

### Gemeinsam
- [ ] PySpark-Backend (`src/kg_quality_eval/backend/spark_backend.py`)
- [ ] Backend-Abstraktion verfeinern (Protocol oder duck-typing genügt)
- [ ] 100K-Variante (`EN_FR_100K_V1`) end-to-end

### Berkay (Vor­arbeit)
- [ ] Custom DBpedia↔Wikidata-Sampling-Skript (`src/kg_quality_eval/loaders/custom.py`)
- [ ] Dump-Download dokumentieren in `docs/Datenbeschaffung.md`

---

## 📑 Sprint 6 — Reporting & Testat 2 (KW 29)

### Gemeinsam
- [ ] `reporting/comparison.py` — sammelt alle `summary.json`-Daten in eine zentrale Tabelle
- [ ] `reporting/exporters.py` — Plot-Funktionen (Degree-Histogramm, Coverage-Heatmap)
- [ ] `notebooks/02_results_overview.ipynb` — alle Plots aus Comparison-Table
- [ ] Testat-2-Bericht schreiben (Methodik, Ergebnisse, Diskussion)

---

## 🎤 Sprint 7+8 — Auswertung & Präsentation

- [ ] Folien
- [ ] Generalprobe
- [ ] **Testat 3** 07.08. oder 18.09. (mit Hofer abstimmen)

---

## 🧹 Continuous / Querschnitt

- [ ] Bei jedem Push: WORKLOG-Eintrag ergänzen
- [ ] Bei jeder Architektur-Änderung: `docs/Architektur.md` synchron halten
- [ ] Bei neuer Metrik: `docs/Metriken-Katalog.md` + `metrics/__init__.py`-Registry pflegen
