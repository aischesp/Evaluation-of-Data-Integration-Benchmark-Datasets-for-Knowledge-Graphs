# Quality Evaluation of Data Integration Benchmark Datasets for Knowledge Graphs

<<<<<<< HEAD
> Big-Data-Praktikum SoSe 2026 · Universität Leipzig · Lehrstuhl Datenbanken (Prof. Rahm)
> Thema 11 · Betreuer: Marvin Hofer
> Teammitglieder: **Aische Vera Spieker**, **Berkay Ethem Özcekic**

---

## 1. Projektüberblick

Ziel des Projektes ist der **Entwurf und die Realisierung eines Frameworks in Python** (Pandas + PySpark), das die **Qualität von Knowledge-Graph-Benchmark-Datensätzen** systematisch analysiert. Im Fokus stehen Datensätze, die für **Entity Alignment** bzw. Daten­integrations­aufgaben verwendet werden (OpenEA, DBpedia, Wikidata, YAGO, OAEI).

Die Motivation: Eigenschaften wie Graphgröße, Struktur, Attribut-Vollständigkeit und Alignment-Dichte beeinflussen Modellgüte und Vergleichbarkeit massiv, werden in den Benchmarks aber selten dokumentiert. Wir wollen diese Eigenschaften **quantifizieren** und Benchmark-Datensätze vergleichbar machen.

---

## 2. Teilziele

1. **Konzeptioneller Entwurf** (Testat 1, Ende Mai 2026) — Entwurfsdokument, das Architektur, Daten und Metriken motiviert.
2. **Implementierung** (Testat 2, Mitte/Ende Juli 2026) — modulares Python-Framework, das auf 8 Benchmark-Datensätzen läuft.
3. **Abschlusspräsentation** (Testat 3, Aug./Sept. 2026) — 10 + 5 min Präsentation der Ergebnisse.

---

## 3. Repository-Struktur

```
.
├── README.md                    ← Dieses Dokument
├── WORKLOG.md                   ← Chronologisches Änderungsprotokoll (async Arbeit)
├── TASKS.md                     ← Offene Aufgaben & Aufteilung Aische/Berkay
├── requirements.txt             ← Python-Abhängigkeiten
├── .gitignore
│
├── docs/                        ← Konzeptionelle Dokumente
│   ├── Entwurfsdokument.md      ← Hauptdokument für Testat 1 (4-5 Seiten)
│   ├── Datensaetze.md           ← Auswahl + Begründung der 8 Benchmark-Datensätze
│   ├── Metriken-Katalog.md      ← Vollständiger Metriken-Katalog mit Formeln
│   ├── Architektur.md           ← Detaillierte Architekturbeschreibung
│   ├── Offene_Fragen.md         ← Fragen an den Betreuer
│   └── Arbeitsplan.md           ← Meilensteinplan bis Testat 3
│
├── material/                    ← Originalmaterial (Aufgaben­stellung, Notizen, Paper)
│   ├── topic_description.md
│   ├── meeting_notes_2026-05-04.md
│   ├── general_info.rtf
│   └── references/
│       └── JAPE_Sun_2017.pdf
│
├── src/kg_quality_eval/         ← Python-Package (Skelett für Testat 2)
│   ├── loaders/                 ← Dataset-spezifische Loader (OpenEA, RDF, CSV)
│   ├── preprocessing/           ← Cleaning & Normalisierung
│   ├── metrics/                 ← Metric-Plugins (basic, structural, quality)
│   ├── reporting/               ← Export & Plots
│   └── utils/
│
├── config/                      ← YAML-Konfigurationen
├── notebooks/                   ← Explorations-Notebooks
├── data/
│   ├── raw/                     ← Original-Datensätze (nicht in Git)
│   └── processed/               ← vorverarbeitete Daten
├── results/
│   ├── figures/                 ← Plots
│   └── reports/                 ← JSON/CSV-Reports
└── tests/                       ← Unit-Tests
```

---

## 4. Geplante Benchmark-Datensätze

Wir wählen 8 Datensätze mit hoher Diversität in Größe, Sprache, Schema-Heterogenität und Alignment-Dichte. Die finale Auswahl mit Begründung steht in [`docs/Datensaetze.md`](docs/Datensaetze.md).

| #  | Datensatz                | Quelle  | Skala  | Charakter                                       |
| -- | ------------------------ | ------- | ------ | ----------------------------------------------- |
| 1  | OpenEA `EN_FR_15K_V1`    | OpenEA  | 15 K   | cross-lingual, sparse (V1)                      |
| 2  | OpenEA `EN_FR_15K_V2`    | OpenEA  | 15 K   | cross-lingual, dense (V2) — Vergleich zu #1     |
| 3  | OpenEA `EN_DE_15K_V1`    | OpenEA  | 15 K   | cross-lingual                                   |
| 4  | OpenEA `D_W_15K_V1`      | OpenEA  | 15 K   | DBpedia ↔ Wikidata (mono-lingual, heterogen)    |
| 5  | OpenEA `D_Y_15K_V1`      | OpenEA  | 15 K   | DBpedia ↔ YAGO                                  |
| 6  | OpenEA `EN_FR_100K_V1`   | OpenEA  | 100 K  | Skalierungs­vergleich (Spark-Pfad)              |
| 7  | OAEI Conference          | OAEI    | ~150   | Ontologie-Matching, sehr klein                  |
| 8  | Eigener DBpedia↔Wikidata | Custom  | ~10 K  | aus aktuellen Dumps generiert                   |

---

## 5. Geplante Metriken (Kurzfassung)

Vollständiger Katalog mit Formeln in [`docs/Metriken-Katalog.md`](docs/Metriken-Katalog.md).

- **Basis-Statistiken**: # Entitäten, # Relationen, # Attribute, # Tripel, # Alignments
- **Strukturelle Metriken**: in/out/total-degree-Verteilung (Histogramme + Mean/Median/Std/Quartile), Dichte, Connected Components
- **Qualitätsmetriken**: Attribut-Vollständigkeit, Typen-Verteilung, Long-Tail-Analyse, Alignment-Coverage, Alignment-Ambiguität, Konsistenz aligned Entitäten

---

## 6. Tech-Stack

- **Python 3.11+**
- **Pandas** für Datasets < 1 M Tripel (schnelle Iteration)
- **PySpark 3.5** für skalierbare Verarbeitung großer Graphen (100 K+ Variante)
- **rdflib** für RDF/Turtle/N-Triples-Parsing
- **NetworkX** für Graph-Analysen auf Sub-Graphen
- **Matplotlib / Seaborn / Plotly** für Visualisierung
- **Jupyter** für explorative Analyse

---

## 7. Setup

```bash
# Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Test
python -c "import pandas, pyspark, rdflib, networkx; print('OK')"
```

---

## 8. Aktueller Stand

- [x] Kick-off mit Betreuer (04.05.2026)
- [x] Repository-Struktur angelegt
- [x] Datensatzauswahl + Begründung dokumentiert
- [x] Metriken-Katalog konzipiert
- [x] Architektur entworfen
- [x] Entwurfsdokument (Testat 1) erstellt
- [ ] Betreuer ins Repo eingeladen
- [ ] Entwurfsdokument als PDF an Hofer senden

Detaillierte Änderungs­chronik: [`WORKLOG.md`](WORKLOG.md)
Offene Aufgaben: [`TASKS.md`](TASKS.md)

---

## 9. Quellen

- [1] Sun, Hu, Li (2017): *Cross-lingual Entity Alignment via Joint Attribute-Preserving Embedding*. [arXiv:1708.05045](https://arxiv.org/pdf/1708.05045)
- [2] OpenEA: <https://github.com/nju-websoft/openea>
- [3] OAEI: <https://oaei.ontologymatching.org/>
- [4] Sun et al. (2020): *A Benchmarking Study of Embedding-based Entity Alignment for Knowledge Graphs*. VLDB.
- [5] Zhang et al. (2022): *An Experimental Study of State-of-the-Art Entity Alignment Approaches*. TKDE.
=======
Big-Data-Praktikum SoSe 2026, Universität Leipzig (Lehrstuhl Datenbanken, Prof. Rahm).
Thema 11, Betreuer Marvin Hofer.
Bearbeitet von Aische Vera Spieker und Berkay Ethem Özcekic.

## Idee

Wir bauen ein Python-Framework, das die Qualität von Knowledge-Graph-Benchmark-Datensätzen für Entity Alignment systematisch analysiert. Quellen sind unter anderem OpenEA, OAEI sowie eigene Subsets aus DBpedia und Wikidata. Eigenschaften wie Graphgröße, Degree-Verteilung, Attribut-Vollständigkeit oder Alignment-Dichte werden in den Benchmarks selten dokumentiert, beeinflussen Modellgüte und Vergleichbarkeit aber stark. Ziel ist, diese Größen reproduzierbar zu berechnen und Benchmarks gegenüberstellen zu können.

## Ergebnis pro Praktikumsphase

1. Konzeptioneller Entwurf (Testat 1, Ende Mai) — `docs/Entwurfsdokument.md`.
2. Implementierung (Testat 2, Mitte/Ende Juli) — lauffähiges Framework auf 8 Datensätzen.
3. Abschlusspräsentation (Testat 3, August/September).

## Repository

```
docs/                Konzeptdokumente, Hauptdeliverable für Testat 1
material/            Aufgabenstellung und Literatur
src/kg_quality_eval/ Python-Package
config/              YAML-Konfigurationen
data/                Datasets (nicht versioniert)
results/             Outputs (nicht versioniert)
notebooks/           Explorations-Notebooks
tests/               Unit-Tests
```

## Datensätze

Wir planen acht Benchmarks mit unterschiedlicher Größe, Sprache und Schema-Heterogenität. Begründung der Auswahl in `docs/Datensaetze.md`.

| Datensatz                | Quelle  | Skala  | Charakter                                    |
| ------------------------ | ------- | ------ | -------------------------------------------- |
| OpenEA EN_FR_15K V1      | OpenEA  | 15K    | cross-lingual, sparse                        |
| OpenEA EN_FR_15K V2      | OpenEA  | 15K    | cross-lingual, dense (Vergleich zu V1)       |
| OpenEA EN_DE_15K V1      | OpenEA  | 15K    | cross-lingual                                |
| OpenEA D_W_15K V1        | OpenEA  | 15K    | DBpedia, Wikidata (heterogene Schemata)      |
| OpenEA D_Y_15K V1        | OpenEA  | 15K    | DBpedia, YAGO                                |
| OpenEA EN_FR_100K V1     | OpenEA  | 100K   | Skalierungsvergleich, Spark                  |
| OAEI Conference          | OAEI    | ~150   | Ontologie-Matching, sehr klein               |
| Custom DBpedia, Wikidata | eigen   | ~10K   | aktueller Dump                               |

## Metriken (Kurzform)

- Basis-Statistiken: Entitäten, Relations- und Attribut-Properties, Tripel, Alignments.
- Strukturelle Metriken: in/out/total-Degree mit Histogrammen und Kennzahlen, Property-Häufigkeit, Connectivity, Power-Law-Fit.
- Qualitätsmetriken: Attribut-Vollständigkeit, Typen-Verteilung, Long-Tail-Analyse (Gini), Alignment-Coverage und Ambiguität, Konsistenz aligned Entitäten, Schema-Heterogenität.

Vollständige Beschreibung in `docs/Metriken-Katalog.md`.

## Tech-Stack

Python 3.11, Pandas, PySpark 3.5 für die 100K-Variante, rdflib für RDF-/OWL-Parsing, NetworkX für Graph-Analytics, Matplotlib/Seaborn für Plots, PyYAML, pytest.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Eine Beispielausführung der Pipeline (sobald ein OpenEA-Datensatz unter `data/raw/openea/EN_FR_15K_V1` liegt):

```bash
python -m kg_quality_eval.runner --config config/datasets.example.yaml --verbose
```

## Quellen

- Sun, Hu, Li: Cross-lingual Entity Alignment via Joint Attribute-Preserving Embedding. arXiv:1708.05045.
- Sun et al.: A Benchmarking Study of Embedding-based Entity Alignment for KGs. PVLDB 13(11), 2020.
- Zhang et al.: An Experimental Study of State-of-the-Art Entity Alignment Approaches. TKDE 2022.
- Clauset, Shalizi, Newman: Power-Law Distributions in Empirical Data. SIAM Review 51(4), 2009.
- OpenEA: github.com/nju-websoft/OpenEA. OAEI: oaei.ontologymatching.org.
>>>>>>> 3a734701cb91d3adf12ec1c972eb9a4496fe7468
