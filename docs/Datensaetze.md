# Auswahl der Benchmark-Datensätze

## 1. Eingrenzung nach Testat 1

Der Entwurf für Testat 1 enthielt neben OpenEA auch den **OAEI Conference
Track**. Dieser ist nach Rücksprache mit dem Betreuer **gestrichen**: OAEI ist
ein *Ontology*-Alignment-Problem — dort werden Klassen und Properties
aufeinander abgebildet (`Person` ↔ `Human`) — während dieses Projekt
ausschließlich *Entity* Alignment untersucht, also die Identifikation derselben
realen Entität in zwei Graphen. Die beiden Probleme haben unterschiedliche
Gold-Standards und unterschiedliche Metriken; sie zu vermischen hätte die
Vergleichbarkeit zerstört.

Ebenfalls gestrichen wurde der ursprünglich geplante eigene
DBpedia↔Wikidata-Subset (schon vor Testat 1, siehe Commit-Historie): der
Aufwand für Dump-Verarbeitung und Sampling stand in keinem Verhältnis zum
Erkenntnisgewinn, weil D\_W\_15K genau dieses Quellenpaar bereits abdeckt.

Damit bleibt **OpenEA v2.0** als einzige Quelle — für die Fragestellung kein
Nachteil, sondern eine Voraussetzung: nur weil alle Datensätze demselben
Erzeugungsprozess folgen und dasselbe Format haben, lassen sich Unterschiede in
den Metriken kausal auf Sprache, Quelle und Dichte zurückführen statt auf
Formatartefakte.

## 2. Auswahlkriterien

Wir wählen sechs Kern-Datensätze so, dass sie die relevanten Dimensionen
aufspannen und sich paarweise nur in *einer* Dimension unterscheiden:

| Dimension | Abgedeckte Spannweite | Isolierender Vergleich |
| --------- | --------------------- | ---------------------- |
| **Dichte** | sparse (V1) vs. dense (V2) | EN\_FR\_15K V1 ↔ V2 |
| **Sprache** | EN–FR vs. EN–DE | EN\_FR\_15K\_V1 ↔ EN\_DE\_15K\_V1 |
| **Quelle / Schema** | DBpedia↔DBpedia, DBpedia↔Wikidata, DBpedia↔YAGO | EN\_FR ↔ D\_W ↔ D\_Y |
| **Skala** | 15 K vs. 100 K Entitäten | EN\_FR\_15K\_V1 ↔ EN\_FR\_100K\_V1 |

## 3. Kern-Auswahl (6 Datensätze)

| # | Datensatz | Quellen | Sprache | Skala | Rolle im Vergleich |
| - | --------- | ------- | ------- | ----- | ------------------ |
| 1 | `EN_FR_15K_V1` | DBpedia EN ↔ DBpedia FR | cross-lingual | 15 K | Referenzpunkt |
| 2 | `EN_FR_15K_V2` | DBpedia EN ↔ DBpedia FR | cross-lingual | 15 K | **Dichte-Effekt** gegenüber #1 |
| 3 | `EN_DE_15K_V1` | DBpedia EN ↔ DBpedia DE | cross-lingual | 15 K | **Sprach-Effekt** gegenüber #1 |
| 4 | `D_W_15K_V1` | DBpedia ↔ Wikidata | mono-lingual | 15 K | **maximale Schema-Heterogenität** |
| 5 | `D_Y_15K_V1` | DBpedia ↔ YAGO | mono-lingual | 15 K | heterogenes Schema, sehr schmales YAGO-Vokabular |
| 6 | `EN_FR_100K_V1` | DBpedia EN ↔ DBpedia FR | cross-lingual | 100 K | **Skalierung** gegenüber #1, PySpark-Pfad |

Ist-Werte nach dem Laden (aus `results/reports/comparison.csv`, nicht aus der
Literatur übernommen):

| Datensatz | \|E₁\| | \|E₂\| | Rel-Tripel | Attr-Tripel | \|M\| | ø Grad |
| --------- | ------ | ------ | ---------- | ----------- | ----- | ------ |
| `EN_FR_15K_V1` | 15 000 | 15 000 | 47 334 / 40 864 | 57 164 / 54 401 | 15 000 | 5,88 |
| `EN_FR_15K_V2` | 15 000 | 15 000 | 96 318 / 80 112 | 52 396 / 56 114 | 15 000 | 11,76 |
| `EN_DE_15K_V1` | 15 000 | 15 000 | 47 676 / 50 419 | 62 403 / 133 776 | 15 000 | 6,54 |
| `D_W_15K_V1` | 15 000 | 15 000 | 38 265 / 42 746 | 52 134 / 138 246 | 15 000 | 5,40 |
| `D_Y_15K_V1` | 15 000 | 15 000 | 30 291 / 26 638 | 52 093 / 117 114 | 15 000 | 3,80 |
| `EN_FR_100K_V1` | 100 000 | 100 000 | 309 607 / 258 285 | 384 248 / 340 725 | 100 000 | 5,68 |

## 4. Erweiterte Auswahl (16 Datensätze) — nur für die Korrelationsanalyse

Die zentrale Frage des Projekts ist, **welche Datensatz-Eigenschaft die
Matching-Güte erklärt**. Mit sechs Datensätzen ist die Stichprobe für eine
Korrelation zu klein (n = 6, jede Rangkorrelation ist praktisch beliebig).
Deshalb läuft dieselbe Pipeline zusätzlich über **alle 16 Varianten** des
OpenEA-v2.0-Archivs (4 Quellenpaare × 2 Größen × 2 Dichtestufen), siehe
`config/datasets_extended.yaml`.

Berichtet werden beide Läufe: die Detailtabellen der Ausarbeitung stammen aus
der Kern-Auswahl, die Korrelationsaussagen aus dem erweiterten Lauf.

## 5. Warum OpenEA v2.0 und nicht v1.1

v2.0 kodiert die Entitäts-URIs (`http://dbpedia.org/resource/E399772` statt des
Klarnamens) und entfernt so den **Name Bias**: in v1.1 lässt sich ein großer
Teil des Alignments allein durch Vergleich der URI-Strings lösen, was jede
Evaluierung attributbasierter Verfahren wertlos macht (Zhang et al. 2022). Für
unsere Fragestellung ist das entscheidend — wir wollen messen, welche
*inhaltlichen* Eigenschaften das Matching tragen, nicht wie gut ein Matcher
URIs vergleicht. Unsere Matcher lesen die URI konsequent nie.

Als Nebeneffekt liegen die absoluten F1-Werte deutlich unter den in älteren
Papern für v1.1 berichteten — ein Vergleich über Datensatz-Versionen hinweg
wäre also unzulässig.

## 6. Bezug der Daten

| Was | Woher | Größe |
| --- | ----- | ----- |
| OpenEA v2.0 (alle 16 Varianten) | figshare, Artikel 19258760 v3 — `scripts/download_data.py` | 237 MB gepackt, ~2 GB entpackt |
| PARIS v0.3 (Jar) | `github.com/dig-team/PARIS`, Release v0.3 | 3,5 MB |

Beides ist nicht im Repository versioniert; `scripts/download_data.py` stellt
`data/raw/` und `tools/` reproduzierbar wieder her.

## 7. Quellen

- [1] Sun, Hu, Li (2017): *Cross-lingual Entity Alignment via Joint Attribute-Preserving Embedding*. arXiv:1708.05045.
- [2] Sun et al. (2020): *A Benchmarking Study of Embedding-based Entity Alignment for KGs*. PVLDB 13(11).
- [3] Zhang et al. (2022): *An Experimental Study of State-of-the-Art Entity Alignment Approaches*. TKDE.
- [4] OpenEA-Repository: <https://github.com/nju-websoft/OpenEA>
