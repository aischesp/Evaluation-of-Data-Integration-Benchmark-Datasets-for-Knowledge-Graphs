# Quality Evaluation of Data Integration Benchmark Datasets for Knowledge Graphs

Big-Data-Praktikum SoSe 2026, Universität Leipzig (Lehrstuhl Datenbanken, Prof. Rahm).
Thema 11, Betreuer Marvin Hofer.
Bearbeitet von Aische Vera Spieker und Berkay Ethem Özcekic.

## Idee

Wir bauen ein Python-Framework, das die Qualität von Knowledge-Graph-Benchmark-Datensätzen für Entity Alignment systematisch analysiert. Quellen sind unter anderem OpenEA und OAEI. Eigenschaften wie Graphgröße, Degree-Verteilung, Attribut-Vollständigkeit oder Alignment-Dichte werden in den Benchmarks selten dokumentiert, beeinflussen Modellgüte und Vergleichbarkeit aber stark. Ziel ist, diese Größen reproduzierbar zu berechnen und Benchmarks gegenüberstellen zu können.

## Ergebnis pro Praktikumsphase

1. Konzeptioneller Entwurf (Testat 1, Ende Mai) — `docs/Entwurfsdokument.md`.
2. Implementierung (Testat 2, Mitte/Ende Juli) — lauffähiges Framework auf 7 Datensätzen.
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

Wir planen sieben Benchmarks mit unterschiedlicher Größe, Sprache und Schema-Heterogenität. Begründung der Auswahl in `docs/Datensaetze.md`.

| Datensatz                | Quelle  | Skala  | Charakter                                    |
| ------------------------ | ------- | ------ | -------------------------------------------- |
| OpenEA EN_FR_15K V1      | OpenEA  | 15K    | cross-lingual, sparse                        |
| OpenEA EN_FR_15K V2      | OpenEA  | 15K    | cross-lingual, dense (Vergleich zu V1)       |
| OpenEA EN_DE_15K V1      | OpenEA  | 15K    | cross-lingual                                |
| OpenEA D_W_15K V1        | OpenEA  | 15K    | DBpedia, Wikidata (heterogene Schemata)      |
| OpenEA D_Y_15K V1        | OpenEA  | 15K    | DBpedia, YAGO                                |
| OpenEA EN_FR_100K V1     | OpenEA  | 100K   | Skalierungsvergleich, Spark                  |
| OAEI Conference          | OAEI    | ~150   | Ontologie-Matching, sehr klein               |

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
