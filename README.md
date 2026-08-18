# Quality Evaluation of Data Integration Benchmark Datasets for Knowledge Graphs

Big-Data-Praktikum SoSe 2026, Universität Leipzig (Lehrstuhl Datenbanken, Prof. Rahm).
Thema 11, Betreuer Marvin Hofer.
Bearbeitet von Aische Vera Spieker und Berkay Ethem Özcekic.

## Forschungsfrage

> **Welche strukturellen und semantischen Eigenschaften von
> Entity-Alignment-Benchmarks bestimmen, wie gut ein Matching-Verfahren auf
> ihnen abschneidet — und hängt das davon ab, welche Art von Verfahren man
> einsetzt?**

Zwei Teilfragen:

1. **Deskriptiv:** Wie unterscheiden sich gängige Benchmarks in Größe,
   Struktur, Vollständigkeit, Schema und Gold-Standard? (→ Profiling)
2. **Erklärend:** Welche dieser Unterschiede schlagen messbar auf die
   Matching-Güte durch, und tun sie das für textuelle und strukturelle
   Verfahren gleichermaßen? (→ Matching + Korrelation)

**Warum das relevant ist:** Wer ein neues Verfahren auf einem einzelnen
Benchmark evaluiert, misst unvermeidlich die Eigenschaften dieses Benchmarks
mit. Zwei Belege dafür: Verdopplung der Graphdichte bei identischer
Entitätsmenge bringt dem strukturellen Verfahren 0,24 F1 und dem wertbasierten
null. Und sobald der Benchmark Entitäten ohne Gegenstück enthält, verlieren
alle Verfahren 14–46 Precision-Punkte — auch PARIS.

## Worum es geht

Entity-Alignment-Verfahren werden auf Benchmark-Datensätzen verglichen, deren
eigene Eigenschaften kaum dokumentiert sind — Graphgröße, Grad-Verteilung,
Attribut-Vollständigkeit, Schema-Heterogenität, Beschaffenheit des
Gold-Standards. Diese Eigenschaften beeinflussen die Ergebnisse aber massiv.

Dieses Projekt baut ein Framework, das

1. Benchmark-Datensätze systematisch **profiliert** (Metriken-Katalog, 11 Metrik-Gruppen),
2. auf denselben Datensätzen vier **Entity-Alignment-Matcher** ausführt und bewertet,
3. beides **korreliert** und in kontrollierten Vergleichen prüft.

Schritt 3 ist der eigentliche Beitrag — Profiling allein sagt noch nicht, ob
ein Benchmark für seine Aufgabe taugt.

## Ergebnis pro Praktikumsphase

| Phase | Deliverable | Stand |
| ----- | ----------- | ----- |
| Testat 1 — Konzeptioneller Entwurf | `docs/Entwurfsdokument.md` | abgeschlossen |
| Testat 2 — Implementierung | lauffähige Pipeline, `docs/Ergebnisse.md` | abgeschlossen, nach Feedback überarbeitet |
| Testat 3 — Abschlusspräsentation | Drehbuch und Folien (nicht im Repository) | in Arbeit |

Feedback und Umsetzung: `docs/Testat1-Feedback.md`, `docs/Testat2-Feedback.md`.

## Schnellstart

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .            # macht `python -m kg_quality_eval.runner` verfügbar
```

PARIS und das PySpark-Backend brauchen eine JVM (Java 17):

```bash
brew install openjdk@17 && export JAVA_HOME=/opt/homebrew/opt/openjdk@17
```

Daten und PARIS-Jar beschaffen (~240 MB Download, ~700 MB entpackt):

```bash
python scripts/download_data.py
```

Vollständiger Lauf über die sechs Kern-Datensätze (~3 Minuten):

```bash
python -m kg_quality_eval.runner --config config/datasets.yaml
```

Variante mit partnerlosen Entitäten, Schwellenwert-Bestimmung, Seed-Analyse:

```bash
python -m kg_quality_eval.runner --config config/datasets_nonmatch.yaml
python scripts/tune_thresholds.py --config config/datasets_nonmatch.yaml
python scripts/analyze_seed_size.py --config config/datasets.yaml
```

Pandas gegen PySpark verifizieren und die Laufzeiten vergleichen:

```bash
python scripts/run_backend_benchmark.py --config config/datasets.yaml
```

Tests:

```bash
pytest
```

## Datensätze

Sechs OpenEA-v2.0-Benchmarks, ausgewählt so, dass sich benachbarte Paare in
genau einer Dimension unterscheiden (Dichte, Sprache, Quelle, Skala).
Begründung und Ist-Werte in `docs/Datensaetze.md`.

| Datensatz | Quellen | Skala | Rolle |
| --------- | ------- | ----- | ----- |
| `EN_FR_15K_V1` | DBpedia EN ↔ FR | 15 K | Referenzpunkt |
| `EN_FR_15K_V2` | DBpedia EN ↔ FR | 15 K | Dichte-Effekt (V1 vs. V2) |
| `EN_DE_15K_V1` | DBpedia EN ↔ DE | 15 K | Sprach-Effekt |
| `D_W_15K_V1` | DBpedia ↔ Wikidata | 15 K | maximale Schema-Heterogenität |
| `D_Y_15K_V1` | DBpedia ↔ YAGO | 15 K | schmales Ziel-Vokabular |
| `EN_FR_100K_V1` | DBpedia EN ↔ FR | 100 K | Skalierung |

Für die Korrelationsanalyse läuft dieselbe Pipeline zusätzlich über alle 16
OpenEA-Varianten (`config/datasets_extended.yaml`), damit die Stichprobe nicht
bei n = 6 bleibt.

Der ursprünglich geplante OAEI-Conference-Track ist nach dem Testat-1-Feedback
gestrichen: das ist Ontology- und nicht Entity-Alignment.

## Metriken

11 Metrik-Gruppen, vollständig definiert in `docs/Metriken-Katalog.md`:

- **Basis** — Entitäten, Properties, Tripel, Alignments, Verhältnisse
- **Strukturell** — Grad-Verteilung inkl. Gini/Power-Law, Property-Verteilung
  und -Entropie, Connectivity, Long-Tail-Profil
- **Qualität** — Attribut-Vollständigkeit, Typ-Verteilung,
  Schema-Heterogenität, Alignment-Eigenschaften, Erreichbarkeit der Gold-Paare,
  Konsistenz aligned Entitäten

## Matcher

Zwei eigene Verfahren, eine Standard-Bibliothek, ein Referenzsystem. Die
eigenen sind bewusst so gebaut, dass jedes *ein* Signal isoliert nutzt — nur so
lässt sich messen, welche Datensatz-Eigenschaft auf welche Verfahrensart wirkt.

| Matcher | Familie | Signal | Seeds | Schwelle | Herkunft |
| ------- | ------- | ------ | ----- | -------- | -------- |
| `value_overlap` | wertbasiert | exakte Literalwerte, IDF-gewichtet | nein | 0,4 | eigen |
| `pyjedai_ngram` | wertbasiert | Zeichen-3-Gramme + Blocking | nein | 0,2 | pyJedAI |
| `structural_propagation` | strukturell | gerichtete, typisierte Nachbarschaft | ja | 0,1 | eigen |
| `paris` | holistisch | Struktur + Literale, iterativ | nein | — | PARIS v0.3 |

PARIS ist selbst bereits ein hybrides Verfahren; ein zusätzlicher eigener
Hybrid-Matcher wäre keine eigenständige Methode, sondern nur eine
Linearkombination der anderen. Alle Schwellenwerte sind auf dem Valid-Split
abgetastet, nicht gesetzt (`scripts/tune_thresholds.py`).

Bewertet wird auf dem Test-Split (70 %) von Fold 1; Seeds kommen nur aus dem
Train-Split.

### Benchmark-Varianten

Die OpenEA-Benchmarks sind strikt bijektiv — jede Entität hat genau einen
Partner. `preprocessing/nonmatch.py` bricht das auf und erzeugt Entitäten ohne
Gegenstück (`config/datasets_nonmatch.yaml`). Erst dort wird messbar, was ein
fehlender Schwellenwert kostet.

## Ergebnisse

Kernaussagen in `docs/Ergebnisse.md`, Rohdaten in `results/reports/`, Figures
in `results/figures/`.

## Tech-Stack

Python 3.11 · pandas · NumPy/SciPy · rdflib (Termkonstruktion und RDF-Export) ·
pyJedAI (Record Linkage) ·
NetworkX (Connectivity) · PySpark 4 (zweites Backend für die Kernmetriken) ·
Matplotlib/Seaborn · PyYAML · pytest/ruff · Java 17 (PARIS, Spark).

## Repository

```
config/              YAML-Konfigurationen (Kern + erweitert)
data/                Datensätze (nicht versioniert, via scripts/download_data.py)
docs/                Entwurf, Metriken-Katalog, Architektur, Ergebnisse, Feedback
material/            Aufgabenstellung und Literatur
results/             Reports und Figures (nicht versioniert)
scripts/             Datenbeschaffung, Benchmarks, Schwellenwert- und Seed-Analyse
src/kg_quality_eval/ Python-Package
tests/               Unit-Tests (pytest)
tools/               PARIS-Jar (nicht versioniert)
```

## Quellen

- Sun, Hu, Li: *Cross-lingual Entity Alignment via Joint Attribute-Preserving Embedding*. arXiv:1708.05045.
- Sun et al.: *A Benchmarking Study of Embedding-based Entity Alignment for KGs*. PVLDB 13(11), 2020.
- Zhang et al.: *An Experimental Study of State-of-the-Art Entity Alignment Approaches*. TKDE, 2022.
- Suchanek, Abiteboul, Senellart: *PARIS: Probabilistic Alignment of Relations, Instances, and Schema*. PVLDB 5(3), 2011.
- Clauset, Shalizi, Newman: *Power-Law Distributions in Empirical Data*. SIAM Review 51(4), 2009.
- OpenEA: <https://github.com/nju-websoft/OpenEA> · PARIS: <https://github.com/dig-team/PARIS>
