---
title: "Quality Evaluation of Data Integration Benchmark Datasets for Knowledge Graphs"
subtitle: "Entwurfsdokument zum Big-Data-Praktikum (Testat 1)"
author: "Aische Vera Spieker · Berkay Ethem Özcekic"
date: "Mai 2026"
abstract: |
  Wir entwerfen ein modulares Python-Framework, das die Qualität von Knowledge-Graph-Benchmark-Datensätzen quantitativ bewertet. Die Anwendung kombiniert Pandas und PySpark, vereinheitlicht Datensätze unterschiedlicher Herkunft in einer internen Repräsentation und berechnet darauf eine Auswahl von Basis-, Struktur- und Qualitätsmetriken. Ziel sind systematische Vergleichswerte über 8 Benchmark-Datensätze (OpenEA-Familie, OAEI Conference, ein eigener DBpedia-Wikidata-Subset), die in einem Comparison-Report konsolidiert werden.
betreuer: "Marvin Hofer (Lehrstuhl Datenbanken, Universität Leipzig)"
---

# 1. Einleitung und Motivation

Beim Aufbau integrierter Knowledge Graphs (KGs) ist Entity Alignment — das Erkennen, dass Entitäten in unterschiedlichen Datenquellen denselben Realweltobjekten entsprechen — ein zentraler Schritt. Zur Evaluation entsprechender Verfahren existiert eine wachsende Zahl von **Benchmark-Datensätzen**: zwei oder mehr KGs, ergänzt um ein Referenz-Alignment $M$, das die "richtigen" Entitäts-Paare definiert. Standardbenchmarks sind die OpenEA-Suite [1, 2], OAEI-Tracks [3] sowie kuratierte Subsets aus DBpedia, Wikidata und YAGO.

Die **Aussagekraft** eines Benchmarks hängt jedoch von seinen Eigenschaften ab: Ist der Graph dicht oder fragmentiert? Wie groß ist der Long-Tail an Entitäten mit nur 1-2 Tripeln? Sind die zwei verglichenen KGs schematisch ähnlich, oder weichen ihre Properties stark voneinander ab? Wie viele Alignments sind injektiv (1:1), wie viele mehrdeutig? Diese Größen bestimmen, ob ein Verfahren auf dem Benchmark erfolgreich sein *kann*, und ob die Ergebnisse über Benchmarks hinweg vergleichbar sind. Trotz ihrer Relevanz werden sie selten dokumentiert.

**Problem.** Es fehlt ein systematisches, einheitlich messendes Werkzeug, das diese Qualitäts-Indikatoren *über mehrere Benchmark-Datensätze hinweg* berechnet und vergleichbar macht. Genau diese Lücke wollen wir schließen.

# 2. Zielstellung

Wir entwerfen und implementieren ein Python-Framework, das:

1. **heterogene Benchmark-Datensätze** (OpenEA-Triples, RDF/OWL, CSV, eigene Custom-Subsets) in eine **einheitliche interne Repräsentation** überführt;
2. darauf einen **Katalog von Metriken** dreier Gruppen berechnet — Basis-Statistiken, strukturelle Eigenschaften, Qualitätsmetriken;
3. die Berechnung **skalierbar** macht: Pandas für kleine Datensätze, PySpark für die 100 K-Variante;
4. **vergleichende Reports** über alle Datensätze erstellt (JSON, CSV, Plots, eine zentrale Comparison-Table) und
5. **modular** ist, sodass neue Datensätze, Metriken oder Backends ohne Eingriff in den Pipeline-Kern integriert werden können.

Erfolgskriterium für Testat 1 ist dieses Entwurfsdokument; für Testat 2 ein lauffähiges Framework, das die 8 ausgewählten Datensätze analysiert.

# 3. Auswahl der Benchmark-Datensätze

Wir analysieren 8 Datensätze, die wir entlang von **Skala, Sprache, Schema-Heterogenität, Dichte und Alignment-Eigenschaften** so wählen, dass das Framework auf der gesamten realistischen Bandbreite getestet ist. Details siehe `docs/Datensaetze.md`.

| #  | Datensatz                | # Ent.  | # Tripel | Charakter                                          |
| -- | ------------------------ | ------- | -------- | -------------------------------------------------- |
| 1  | OpenEA `EN_FR_15K_V1`    | 30 K    | ~96 K    | cross-lingual EN-FR, sparse                        |
| 2  | OpenEA `EN_FR_15K_V2`    | 30 K    | ~177 K   | cross-lingual EN-FR, dense — Vergleich V1/V2       |
| 3  | OpenEA `EN_DE_15K_V1`    | 30 K    | ~96 K    | cross-lingual EN-DE                                |
| 4  | OpenEA `D_W_15K_V1`      | 30 K    | ~78 K    | DBpedia ↔ Wikidata, heterogenes Schema             |
| 5  | OpenEA `D_Y_15K_V1`      | 30 K    | ~91 K    | DBpedia ↔ YAGO, reichere Typ-Hierarchie            |
| 6  | OpenEA `EN_FR_100K_V1`   | 200 K   | ~650 K   | Skalierungs­vergleich, Spark-Pfad                  |
| 7  | OAEI Conference          | ~150    | ~600     | OWL-Format, Sanity-Check + Edge-Case               |
| 8  | Custom DBp ↔ Wiki Subset | ~10 K   | TBD      | aktueller Dump, eigenes Sampling                   |

Die Auswahl ist bewusst von OpenEA geprägt, weil OpenEA als De-facto-Standard ein einheitliches Format und Train/Valid/Test-Splits bereitstellt; wir ergänzen mit OAEI (anderes Format, sehr kleiner Graph) und einem **selbst generierten Custom-Subset**, um auch die End-to-End-Sampling-Pipeline zu demonstrieren. Innerhalb von OpenEA wählen wir Varianten, die *paarweise eine Variable isolieren*: V1 ↔ V2 (Dichte), EN-FR ↔ EN-DE (Sprache), D-W ↔ D-Y (Schema), 15K ↔ 100K (Skala).

# 4. Metriken-Konzept

Der vollständige Katalog mit Formeln steht in `docs/Metriken-Katalog.md`. Im Folgenden die drei Gruppen.

## 4.1 Basis-Statistiken

Pro KG werden $|E|$, $|R|$ (Relations-Properties), $|A|$ (Attribut-Properties), $|L|$ (Literale), $|T^R|$, $|T^A|$ sowie das Attribut-Relations-Verhältnis $|T^A|/|T^R|$ berechnet. Pro Paar zusätzlich $|M|$ und das **Alignment Ratio** $|M|/\min(|E_1|,|E_2|)$. Diese Statistiken sind die Größenordnungs-Basis, die jeder weitere Vergleich braucht.

## 4.2 Strukturelle Metriken

Für jede Entität berechnen wir **in-degree**, **out-degree** und **total-degree** auf den Relations-Tripeln. Aus der Degree-Sequenz extrahieren wir (i) ein log-skaliertes **Histogramm**, (ii) **Kennzahlen** (Mean, Median, Std, Min, Max, 25/75/95/99-%-Quartile), (iii) Anteil **isolierter** Entitäten (deg = 0) und **strukturell schwacher** Entitäten (deg ≤ 2) und (iv) eine **Power-Law-Schätzung** des Exponenten $\alpha$ über die Maximum-Likelihood-Methode nach Clauset et al. [5]. Der mittlere Grad ist hier besonders relevant: laut unserem Betreuer Hofer ist ein niedriger Median ein Indikator für einen **strukturell schwachen Benchmark** — Embedding-Verfahren brauchen genug Tripel pro Entität für stabile Vektoren.

Parallel berechnen wir die **Property-Frequenz-Verteilung** (welche Relationen dominieren?), eine **Top-k-Konzentrationsmetrik** (Anteil der Tripel in den 10 häufigsten Properties) und Connectivity-Größen (`n_connected_components`, Größe der LCC, Density). Letztere werden bei großen Graphen auf Stichproben berechnet, um Compute-Kosten zu beherrschen.

## 4.3 Qualitätsmetriken

Diese Gruppe ist der Kern unseres Beitrags und gliedert sich in fünf Unterbereiche:

- **Attribut-Vollständigkeit (Coverage):** pro Attribut-Property der Anteil der Entitäten, die diesen Wert haben. Aggregiert: Mean/Median Coverage. Zusätzlich: **Attribut-Overlap** zwischen aligned Entitäten — wie oft tragen $(e_1, e_2) \in M$ Werte für *vergleichbare* Properties? Diese Größe macht Property-Mapping-Lücken sichtbar.
- **Typen-Verteilung:** Histogramm der `rdf:type`-Klassen, Skewness, Jaccard zwischen $G_1$- und $G_2$-Typen, sowie eine **Type-Consistency-Rate**, die misst, wie oft aligned Entitäten denselben Typ besitzen.
- **Long-Tail-Analyse:** kumulative Verteilung der Entity-Frequenzen, **Gini-Koeffizient** auf der Degree-Verteilung und Anteil $P_k$ Entitäten mit Total-Degree $\leq k$. Ein hoher Long-Tail-Anteil verzerrt die Test-Genauigkeit von Embedding-Verfahren systematisch.
- **Alignment-Metriken:** Coverage, Ambiguität (1:n und n:1), Anteil bijektiver Mappings, sowie der Anteil aligned Entitäten innerhalb der größten verbundenen Komponente. Letzteres erkennt isolierte Cluster, die für Alignment-Lernen wertlos sind.
- **Konsistenz aligned Entitäten:** Spearman-Korrelation der Degrees zwischen $(e_1, e_2) \in M$, Jaccard auf Typ-Mengen und auf Sub-Sample-Basis ein Vergleich von Attribut-Werten (numerische Distanz / Levenshtein).

Optional erweitern wir um eine **Schema-Heterogenitäts**-Gruppe: Property-Jaccard, Klass-Jaccard, Namespace-Overlap, Entropy der Property-Verteilung. Diese Metriken werden ergänzend berechnet, sofern Zeit bleibt (MoSCoW: *Could*).

# 5. Architektur

## 5.1 Pipeline-Übersicht

Das Framework folgt einer klassischen ETL-Struktur mit klar getrennten Verantwortlichkeiten:

```
config.yaml
   │
   ▼
┌───────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│  Loader   │ →  │ Preprocessor │ →  │ Backend Sel. │ →  │ Metric Plug. │ →  │  Reporting  │
│ (4 Impls) │    │ (clean/norm) │    │ (Pd | Spark) │    │  (3 Gruppen) │    │ (JSON/CSV)  │
└───────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └─────────────┘
                                                                                    │
                                                                                    ▼
                                                                          comparison.csv
                                                                          summary plots
```

## 5.2 Unified Internal Representation

Loader-Output ist ein `KGPair`-Datentyp mit zwei `KnowledgeGraph`-Instanzen (Entitäten, Relations-Tripel, Attribut-Tripel) und einem DataFrame $M$ der Alignments mit Train/Valid/Test-Spalten. Auf Pandas-Seite sind das `pd.DataFrame`-Objekte; auf Spark-Seite Spark-DataFrames mit identischem Schema. Sämtliche Metriken werden gegen diese Schnittstelle implementiert ⇒ identische Logik für beide Backends.

## 5.3 Modul-Struktur

```
src/kg_quality_eval/
├── core.py              # Datenklassen KGPair, KnowledgeGraph
├── loaders/             # BaseLoader + 4 Implementierungen
├── preprocessing/       # Cleaning, URI-Normalisierung, Validierung
├── metrics/             # BaseMetric + basic.py, structural.py, quality.py
├── reporting/           # JSON/CSV/Plot-Exporter + comparison.py
├── backend/             # pandas_backend.py, spark_backend.py
└── utils/               # config.py (YAML), logging.py
```

Neue Metriken oder Loader werden durch Subclassing eingebracht — der Pipeline-Kern (`runner.py`) bleibt unverändert.

## 5.4 Skalierbarkeitsstrategie

Die Backend-Auswahl ist datenabhängig. Heuristisch:

- **Pandas** bei $|T| < 10^6$ — schneller, einfacher zu debuggen, ausreichend für 7 unserer 8 Datensätze;
- **PySpark** bei $|T| \geq 10^6$ — für die 100 K-OpenEA-Variante und das Custom-Sampling. Hier nutzen wir Spark im Local-Mode (`local[*]`).

Die teuersten Metriken sind Power-Law-Fit (skaliert linear, unkritisch) sowie Connectivity und Clustering — letztere berechnen wir bei großen Graphen auf einer **Stichprobe** ($n=10^4$ Knoten), eine in der Graph-Analytics-Literatur etablierte Approximation.

## 5.5 Reproduzierbarkeit & Outputs

Alle Inputs sind in `config/datasets.yaml` deklarativ beschrieben. Pro Datensatz erzeugt das Framework deterministische Outputs unter `results/reports/<dataset>/`: einzeln JSON/CSV pro Metrik plus eine `summary.json`. Eine zentrale `comparison.csv` aggregiert alle Metriken über alle Datensätze und ist die Basis der Endpräsentation.

# 6. Tech-Stack

| Komponente             | Begründung                                                                 |
| ---------------------- | -------------------------------------------------------------------------- |
| **Python 3.11**        | breite Library-Unterstützung, Standard im Lehrstuhl                       |
| **Pandas 2.x**         | schnelle Tabellenoperationen für < 1 M Tripel                             |
| **PySpark 3.5**        | skalierbares ETL für 100 K-Variante; Big-Data-Aspekt des Praktikums       |
| **rdflib**             | robustes RDF/Turtle/N-Triples/OWL-Parsing                                  |
| **NetworkX**           | etablierte Graph-Analytics-Bibliothek für Connectivity-Metriken           |
| **Matplotlib + Seaborn** | Standard für statische Plots in Reports                                  |
| **PyYAML**             | deklarative, versionierbare Konfiguration                                  |
| **pytest**             | Tests für Loader und kritische Metrik-Implementierungen                    |
| **Jupyter**            | explorative Analyse, Reproduktion der Endergebnisse                       |

# 7. Arbeits- und Zeitplan

| Phase | Zeitraum            | Inhalt                                                                          |
| ----- | ------------------- | ------------------------------------------------------------------------------- |
| 1     | KW 20 (jetzt)       | Repo + Konzeptdokumente (dieses Dokument)                                       |
| 2     | KW 21 – 22          | Loader für OpenEA & RDF + Pandas-Backend + Basis-Statistiken                    |
| 3     | KW 23 – 24          | Strukturelle Metriken inkl. Degree-Analyse + erste Plots                        |
| 4     | KW 25 – 26          | Qualitätsmetriken (Attribut-Coverage, Alignment-Metriken)                       |
| 5     | KW 27 – 28          | PySpark-Backend + 100K-Datensatz; Custom-DBp-Wiki-Sampling                      |
| 6     | KW 29               | Reporting-Modul + Comparison-Table; **Testat 2** Ende KW 29                     |
| 7     | KW 30 – 35          | Evaluierung, Optimierung, schriftliche Auswertung                               |
| 8     | KW 36 / KW 38       | **Testat 3** (Präsentation)                                                     |

Die Aufgabenverteilung innerhalb des Teams konkretisieren wir beim Übergang in Phase 2.

# 8. Risiken

| Risiko                                              | Maßnahme                                                                   |
| --------------------------------------------------- | -------------------------------------------------------------------------- |
| OpenEA-Download (~1 GB) zu groß für Repo            | nicht versioniert; Setup-Skript lädt nach `data/raw/openea/`               |
| PySpark-Setup unter macOS                           | Docker-Fallback dokumentieren                                              |
| OAEI-OWL-Parsing instabil                           | Pre-Konvertierung zu N-Triples; OAEI-Loader optional                       |
| Aufwand Custom-Sampling                             | als optional eingestuft; bei Zeitdruck weglassen                           |

# 9. Quellen

- [1] Sun, Hu, Li (2017): *Cross-lingual Entity Alignment via Joint Attribute-Preserving Embedding*. arXiv:1708.05045.
- [2] Sun et al. (2020): *A Benchmarking Study of Embedding-based Entity Alignment for Knowledge Graphs*. PVLDB 13(11), 2326–2340.
- [3] OAEI: <https://oaei.ontologymatching.org/>
- [4] Zhang et al. (2022): *An Experimental Study of State-of-the-Art Entity Alignment Approaches*. IEEE TKDE.
- [5] Clauset, Shalizi, Newman (2009): *Power-Law Distributions in Empirical Data*. SIAM Review 51(4), 661–703.
- [6] OpenEA Repository: <https://github.com/nju-websoft/OpenEA>
