# Detaillierter Arbeitsplan bis Testat 3

> Stand: 2026-05-20 · KW 20

## Übersicht (Phasen)

| Phase | Zeitraum                | Ergebnis                                                   |
| ----- | ----------------------- | ---------------------------------------------------------- |
| 0     | KW 18 (04.05.)          | Kick-off mit Hofer ✅                                       |
| 1     | KW 19 – 20 (jetzt)      | Repo + Entwurfsdokument                                    |
| 2     | KW 21 – 22              | Datenbeschaffung + OpenEA-Loader + Basis-Statistiken       |
| 3     | KW 23 – 24              | Strukturelle Metriken                                      |
| 4     | KW 25 – 26              | Qualitätsmetriken                                          |
| 5     | KW 27 – 28              | PySpark-Backend + Custom-Subset + 100 K                    |
| 6     | KW 29                   | Reporting + Comparison-Table + **Testat 2**                |
| 7     | KW 30 – 35              | Evaluation, Optimierung, schriftliche Ausarbeitung         |
| 8     | KW 36 oder KW 38        | **Testat 3** (Abschlusspräsentation)                       |

## Meilensteine

| MS | Datum (Soll) | Inhalt                                                  |
| -- | ------------ | ------------------------------------------------------- |
| M1 | 30.05.2026   | **Testat 1**: Entwurfsdokument abgegeben                |
| M2 | 14.06.2026   | OpenEA-Loader steht, Basis-Statistiken laufen           |
| M3 | 30.06.2026   | Strukturelle Metriken komplett, Histogramme exportiert  |
| M4 | 14.07.2026   | Qualitätsmetriken komplett (mind. Attr-Coverage + Align)|
| M5 | 22.07.2026   | PySpark-Backend lauffähig auf 100K-Variante             |
| M6 | 28.07.2026   | **Testat 2**: lauffähiges Framework + Bericht           |
| M7 | 31.08.2026   | Folien + Generalprobe                                   |
| M8 | 18.09.2026   | **Testat 3**: Abschlusspräsentation                     |

## Phase 1 (laufend) — Repo & Konzept

- [x] Repo-Struktur (`docs/`, `src/`, ...)
- [x] README mit Projektbeschreibung
- [x] Datensatzauswahl + Begründung
- [x] Metriken-Katalog
- [x] Architektur-Dokument
- [x] Entwurfsdokument (Markdown)
- [ ] Entwurfsdokument → PDF (Pandoc)
- [ ] PDF an Hofer senden
- [ ] Hofer ins Repo einladen (GitHub Collaborator)

## Phase 2 — Loader & Basis

**Aische:**
- [ ] OpenEA-Zip lokal herunterladen, nach `data/raw/openea/` entpacken
- [ ] `OpenEALoader` implementieren + Unit-Tests
- [ ] Basis-Statistiken (`metrics/basic.py`) implementieren

**Berkay:**
- [ ] `BaseLoader`-Interface und Pandas-Backend gerüst
- [ ] `RDFLoader` für OAEI Conference
- [ ] Konfigurations-Loader (`utils/config.py`)
- [ ] CLI-Runner (`python -m kg_quality_eval run --config ...`)

## Phase 3 — Strukturelle Metriken

**Aische:**
- [ ] Degree-Berechnung (in/out/total) auf Pandas
- [ ] Kennzahlen-Aggregation
- [ ] Histogramm-Export (CSV + Plot)

**Berkay:**
- [ ] Property-Frequenz-Analyse
- [ ] Connectivity (NetworkX-Backend)
- [ ] Power-Law-Fit (Clauset-MLE)

## Phase 4 — Qualitätsmetriken

**Aische:**
- [ ] Attribut-Vollständigkeit + Coverage-Tabelle
- [ ] Type-Distribution (sofern Typen extrahierbar)
- [ ] Long-Tail-Analyse (Gini, $P_k$)

**Berkay:**
- [ ] Alignment-Metriken (Coverage, Ambiguität, bijektiver Anteil)
- [ ] Konsistenz aligned Entitäten (Degree-Korrelation)
- [ ] Schema-Heterogenität (Jaccard, Entropy)

## Phase 5 — Skalierung

Gemeinsam: PySpark-Backend, identische API zum Pandas-Backend. Custom-DBpedia-Wikidata-Sampling.

## Phase 6 — Reporting & Testat 2

- [ ] `comparison.csv` Generator
- [ ] Plots-Modul (Matplotlib)
- [ ] Notebook `notebooks/02_results_overview.ipynb`
- [ ] Berichtsteil: Methodik, Ergebnisse, Diskussion
- [ ] **Testat 2** mit Hofer

## Phase 7 — Auswertung & Schreiben

- [ ] Vergleichende Analyse: was unterscheidet die Datensätze?
- [ ] Plots für Folien
- [ ] Slides (Google Slides / PPTX)
- [ ] Generalprobe

## Phase 8 — Präsentation

- [ ] **Testat 3** am 07.08. oder 18.09. (mit Hofer abstimmen)
