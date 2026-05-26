# Auswahl der Benchmark-Datensätze

## 1. Auswahlkriterien

Wir wählen 8 Datensätze entlang folgender Dimensionen, damit unser Framework auf der gesamten Bandbreite realistischer Benchmarks evaluiert werden kann:

| Dimension                  | Spannweite, die wir abdecken                    |
| -------------------------- | ----------------------------------------------- |
| **Skala**                  | ~150 (OAEI) … 100 K Entitäten (OpenEA-large)    |
| **Sprache**                | mono-lingual und cross-lingual (EN-FR, EN-DE)   |
| **Quelle**                 | DBpedia, Wikidata, YAGO, OAEI, kuratiert        |
| **Dichte (V1 vs. V2)**     | sparse (V1) und dense (V2) zum direkten Vergleich |
| **Schema-Heterogenität**   | homogen (DBpedia↔DBpedia) bis heterogen (D-W, D-Y) |
| **Alignment-Eigenschaften**| Anteil aligned Entitäten, 1:1 vs. 1:n          |

## 2. Endgültige Auswahl (8 Datensätze)

### 2.1 OpenEA-Familie (6 Datensätze)

OpenEA [1] ist der **De-facto-Standard** für Entity-Alignment-Benchmarks. Vorteile:

- einheitliches **Format** (Tab-separierte Triples: `rel_triples_1`, `rel_triples_2`, `attr_triples_1`, `attr_triples_2`, `ent_links`)
- **Seed-Splits** (train/valid/test) bereits vorbereitet
- zwei Dichte-Stufen (V1: sparse, V2: dense — durch iteratives Degree-Bias-Sampling)
- vier Sprach-/Quellen-Paare und zwei Größen (15 K / 100 K) ⇒ insgesamt 16 Varianten

| # | Datensatz            | Beschreibung                                                                                    |
| - | -------------------- | ----------------------------------------------------------------------------------------------- |
| 1 | `EN_FR_15K_V1`       | DBpedia EN ↔ DBpedia FR, sparse (mittlerer Grad ≈ 4)                                            |
| 2 | `EN_FR_15K_V2`       | DBpedia EN ↔ DBpedia FR, dense (mittlerer Grad ≈ 8). **Direkter Vergleich V1/V2.**              |
| 3 | `EN_DE_15K_V1`       | DBpedia EN ↔ DBpedia DE — andere Zielsprache, eigene Property-Verteilung                        |
| 4 | `D_W_15K_V1`         | DBpedia ↔ Wikidata, mono-lingual. **Stark heterogene Schemata.**                                |
| 5 | `D_Y_15K_V1`         | DBpedia ↔ YAGO, mono-lingual. YAGO hat reichere Typ-Hierarchie ⇒ Typ-Verteilung interessant.    |
| 6 | `EN_FR_100K_V1`      | 100 K-Variante. **Wichtig für Skalierungs-Demo (Spark-Pfad).**                                  |

### 2.2 OAEI Conference Track (1 Datensatz)

- **Größe**: ~150 Entitäten (sehr klein!)
- **Zweck**: Sanity-Check + Edge-Case (kleiner Graph, OWL-Ontologie statt RDF-Tripel)
- **Format-Vielfalt**: OWL/XML — fordert unseren RDF-Loader heraus

### 2.3 Eigener DBpedia ↔ Wikidata-Subset (1 Datensatz)

- **Größe**: ~10 K Entitäten
- **Generierung**: Sampling aus aktuellen DBpedia- und Wikidata-Dumps (Frühjahr 2026) über `sameAs`-Links
- **Zweck**: 
  - aktuelle Daten (OpenEA basiert auf 2016er DBpedia-Dump!)
  - **eigener** Daten­erzeugungs­prozess als Methodik-Demo
  - Test der **End-to-End-Pipeline**, inkl. Custom-Loader

## 3. Diversität der Auswahl (Tabellarische Übersicht)

| #  | Datensatz                | # Ent.  | # Tripel | # Align. | Sprache    | Quellen          | Dichte |
| -- | ------------------------ | ------- | -------- | -------- | ---------- | ---------------- | ------ |
| 1  | OpenEA `EN_FR_15K_V1`    | 30 K    | ~96 K    | 15 K     | EN ↔ FR    | DBpedia          | sparse |
| 2  | OpenEA `EN_FR_15K_V2`    | 30 K    | ~177 K   | 15 K     | EN ↔ FR    | DBpedia          | dense  |
| 3  | OpenEA `EN_DE_15K_V1`    | 30 K    | ~96 K    | 15 K     | EN ↔ DE    | DBpedia          | sparse |
| 4  | OpenEA `D_W_15K_V1`      | 30 K    | ~78 K    | 15 K     | mono       | DBpedia, Wikidata| sparse |
| 5  | OpenEA `D_Y_15K_V1`      | 30 K    | ~91 K    | 15 K     | mono       | DBpedia, YAGO    | sparse |
| 6  | OpenEA `EN_FR_100K_V1`   | 200 K   | ~650 K   | 100 K    | EN ↔ FR    | DBpedia          | sparse |
| 7  | OAEI Conference          | ~150    | ~600     | ~50      | EN         | mehrere Onto.    | n/a    |
| 8  | Custom DBp↔Wiki Subset   | ~10 K   | TBD      | ~5 K     | mono       | DBpedia, Wikidata| TBD    |

(Werte für OpenEA aus Sun et al. 2020 [2]; Werte für #7/#8 nach erster Generierung verifizieren.)

## 4. Erwarteter Mehrwert der Diversität

- **#1 vs. #2** (V1 vs. V2): zeigt **Effekt der Dichte** auf alle Metriken (Degree-Verteilung wird kompakter, Long-Tail kürzer)
- **#1 vs. #3**: **Sprach-Effekt** bei identischer Quelle (DBpedia)
- **#4 vs. #5**: **Schema-Heterogenität** Wikidata (flach, viele Properties) vs. YAGO (tiefe Typ-Hierarchie)
- **#1 vs. #6**: **Skalierungs­vergleich** 15 K → 100 K (Pandas → PySpark)
- **#7** als Sonderfall: testet Loader-Robustheit bei OWL-Format
- **#8**: aktuelle Daten, demonstriert komplette Pipeline incl. Sampling

## 5. Bezug der Daten

| #     | Quelle / URL                                                                  |
| ----- | ------------------------------------------------------------------------------ |
| 1-6   | <https://github.com/nju-websoft/OpenEA> → `OpenEA_dataset_v2.0.zip` (~1.1 GB) |
| 7     | <https://oaei.ontologymatching.org/2023/conference/index.html>                |
| 8     | DBpedia Snapshot 2026, Wikidata Truthy-Dump → eigenes Sampling-Skript         |

## 6. Quellen

- [1] Sun, Hu, Li (2017): *Cross-lingual Entity Alignment via Joint Attribute-Preserving Embedding*. arXiv:1708.05045.
- [2] Sun et al. (2020): *A Benchmarking Study of Embedding-based Entity Alignment for KGs*. PVLDB 13(11).
- [3] Zhang et al. (2022): *An Experimental Study of State-of-the-Art Entity Alignment Approaches*. TKDE.
- [4] OAEI: <https://oaei.ontologymatching.org/>
