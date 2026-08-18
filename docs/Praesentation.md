# Abschlusspräsentation (Testat 3) — Drehbuch

10 Minuten Vortrag + 5 Minuten Diskussion, in Präsenz. Zwei Vortragende.

Leitsatz aus dem Testat-1-Gespräch: *"Die Arbeit arbeitet eigentlich die ganze
Zeit darauf hin, dass es eine gute Präsentation wird."* Entsprechend ist dieses
Dokument nach **Aussagen** gegliedert, nicht nach Code-Modulen. Jede Folie hat
genau eine Kernaussage; alles, was nicht auf eine Kernaussage einzahlt, gehört
in den Backup-Teil.

## Zeitplan

| # | Folie | Zeit | Wer |
| - | ----- | ---: | --- |
| 1 | Titel | 0:20 | A |
| 2 | Problem: Benchmarks werden benutzt, aber nicht bewertet | 1:00 | A |
| 3 | Fragestellung und Beitrag | 0:40 | A |
| 4 | Daten: 6 Benchmarks, kontrolliert variiert | 0:50 | A |
| 5 | Architektur der Pipeline | 1:00 | A |
| 6 | Metriken-Katalog (Tabelle) | 0:50 | B |
| 7 | Die Matcher: 2 eigene, 1 Library, PARIS | 0:50 | B |
| 8 | Befund 1: Profiling deckt Benchmark-Schwächen auf | 1:00 | B |
| 9 | Befund 2: Dichte-Experiment (Kernfolie) | 1:30 | B |
| 10 | Befund 3: Familien reagieren auf verschiedene Metriken | 0:50 | B |
| 10b | Befund 4: was Bijektivität verdeckt | 0:50 | B |
| 11 | Skalierbarkeit: Pandas ≡ PySpark | 0:40 | A |
| 12 | Fazit und Grenzen | 0:40 | A |
| | **Summe** | **~10:45** | |

---

## Folie 1 — Titel

Quality Evaluation of Data Integration Benchmark Datasets for Knowledge Graphs
· Big-Data-Praktikum SoSe 2026 · Aische Vera Spieker, Berkay Ethem Özcekic ·
Betreuer: Marvin Hofer

---

## Folie 2 — Das Problem

**Kernaussage: Wir vergleichen Verfahren auf Datensätzen, die wir selbst nicht
vermessen haben.**

- Entity Alignment = dieselbe reale Entität in zwei Knowledge Graphs finden
  (nicht zu verwechseln mit Ontology Alignment: dort Klassen und Properties)
- Verfahren werden auf Benchmarks wie OpenEA verglichen und danach gereiht
- Dokumentiert sind meist nur Entitäten- und Tripelzahl
- Nicht dokumentiert: Grad-Verteilung, Attribut-Vollständigkeit, Struktur des
  Gold-Standards, Property-Verteilung

*Aufhänger:* Vorgriff auf Folie 9 — verdoppelt man die Graphdichte bei
identischer Entitätsmenge, gewinnt das strukturelle Verfahren 0,24 F1 und das
wertbasierte null. Der Unterschied liegt am Benchmark, nicht am Verfahren.

---

## Folie 3 — Fragestellung und Beitrag

**Kernaussage: Profiling allein reicht nicht — es muss gegen eine echte
Matching-Aufgabe validiert werden.**

Drei Schritte:

1. Benchmarks systematisch profilieren (11 Metrik-Gruppen)
2. Auf denselben Benchmarks vier Entity-Alignment-Verfahren ausführen
3. Beides in Beziehung setzen: welche Eigenschaft erklärt welche Güte?

> Sprechhinweis: Schritt 2 kam als Auflage aus Testat 1 dazu und ist im
> Nachhinein der Kern der Arbeit — ohne ihn wäre die Comparison-Tabelle eine
> Sammlung von Zahlen ohne Interpretation.

---

## Folie 4 — Datensätze

**Kernaussage: Die Auswahl ist so gebaut, dass sich benachbarte Paare in genau
einer Dimension unterscheiden.**

Tabelle mit den sechs Kern-Datensätzen und der Rolle jedes einzelnen
(`docs/Datensaetze.md` §3). Vier isolierende Vergleiche hervorheben: Dichte,
Sprache, Quelle, Skala.

Zwei Punkte laut aussprechen:

- **OAEI wurde gestrichen** — das ist Ontology Alignment, ein anderes Problem
- **OpenEA v2.0, nicht v1.1** — v2.0 anonymisiert die URIs und entfernt damit
  den Name Bias; unsere Matcher lesen die URI nie

Für die Korrelationsanalyse laufen zusätzlich alle 16 Varianten (n = 6 wäre für
Korrelationen zu klein).

---

## Folie 5 — Architektur

**Kernaussage: Loader, Metriken und Matcher sind Plugins hinter einem
einheitlichen Datenmodell.**

Mermaid-Diagramm aus `docs/Architektur.md` §2.

Ein technisches Detail nennen (nicht mehr), das die Big-Data-Relevanz zeigt:
Bei 100 K × 100 K Entitäten hätte die Ähnlichkeitsmatrix 10¹⁰ Einträge.
Vokabular-Beschneidung + blockweises Produkt + sofortiges Top-k-Pruning machen
den Speicherbedarf linear statt quadratisch — deshalb läuft der 100 K-Datensatz
mit denselben Parametern auf einem 8-GB-Laptop.

---

## Folie 6 — Metriken-Katalog

**Kernaussage: 11 Metrik-Gruppen in drei Kategorien, jede mit einer Begründung,
warum sie fürs Matching relevant sein sollte.**

Kompakte Tabelle (Kategorie → Gruppe → Beispiel-Kennzahl → erwartete Wirkung).
Nicht vorlesen, nur die drei Kategorien benennen und zwei Beispiele
herausgreifen:

- `share_isolated` — eine isolierte Entität kann strukturell nie gefunden werden
- `literal_value_jaccard` — teilen sich die Gold-Paare überhaupt Literalwerte?

> Diese Folie ist die Antwort auf "macht daraus eine Tabelle statt Fließtext".

---

## Folie 7 — Die Matcher

**Kernaussage: Zwei eigene Verfahren, eine Standard-Bibliothek, ein
Referenzsystem — die eigenen isolieren je ein Signal, damit die Korrelationen
unterscheidbar werden.**

| Matcher | Familie | Signal | Seeds | Schwelle | Herkunft |
| ------- | ------- | ------ | ----- | -------- | -------- |
| `value_overlap` | wertbasiert | exakte Literalwerte, IDF | nein | 0,4 | eigen |
| `pyjedai_ngram` | wertbasiert | Zeichen-3-Gramme, Blocking | nein | 0,2 | pyJedAI |
| `structural_propagation` | strukturell | gerichtete, typisierte Nachbarschaft | ja | 0,1 | eigen |
| `paris` | holistisch | Struktur + Literale, iterativ | nein | — | PARIS v0.3 |

Zwei Punkte laut aussprechen:

- **PARIS ist selbst schon hybrid** — ein eigener Hybrid-Matcher wäre kein
  eigenständiger Ansatz. Deshalb gestrichen, ebenso der TF-IDF-Matcher.
- **Alle Schwellenwerte sind gemessen**, nicht gesetzt: Sweep 0,0–0,9 auf dem
  Valid-Split.

Methodik in einem Satz: bewertet auf dem Test-Split (70 %), Seeds nur aus dem
Train-Split, Parameter auf dem Valid-Split — nie auf Test.

---

## Folie 8 — Befund 1: Profiling deckt Benchmark-Schwächen auf

**Kernaussage: Zwei Eigenschaften dieser Benchmarks schränken ein, was man auf
ihnen überhaupt messen kann.**

1. **Typ-Information fehlt praktisch vollständig.** In fünf von sechs
   Datensätzen kein einziges `rdf:type`-Tripel. Typ- und ontologie-basierte
   Verfahren sind hier gar nicht evaluierbar.
2. **Der Gold-Standard ist strikt bijektiv und vollständig.**
   `alignment_coverage` = 1,0, `bijective_share` = 1,0, `ambiguity` = 0,0 —
   jede Entität hat genau einen Partner. In echter Datenintegration hat die
   Mehrheit der Entitäten *keinen* Partner. Die Entscheidung "dieses Paar
   existiert nicht" wird nie geprüft ⇒ absolute F1-Werte sind systematisch
   optimistisch.

> Diese Folie zeigt, dass Profiling ohne Matching schon eigenständigen Wert hat.

---

## Folie 9 — Befund 2: das Dichte-Experiment (Kernfolie)

**Kernaussage: Wir können den Effekt einer einzelnen Datensatz-Eigenschaft
kontrolliert isolieren — und er trifft nur eine Matcher-Familie.**

Figure `results/figures_extended/contrast_density.png`.

| Matcher | V1 (sparse) | V2 (dense) | Δ |
| ------- | ----------: | ---------: | ---: |
| `value_overlap` (wertbasiert) | 0,470 | 0,445 | −0,03 |
| `structural_propagation` | 0,498 | 0,733 | **+0,24** |
| `paris` | 0,825 | 0,908 | +0,08 |

Warum das ein sauberes Experiment ist: V1 und V2 enthalten **dieselben
Entitäten**; die Relations-Tripel wachsen um Faktor ~2, die Attribut-Tripel
bleiben nahezu gleich (Faktor 0,97–1,21). Gemittelt über alle vier
Quellenpaare und beide Größen, n = 8 Paare.

Das ist keine Korrelation, sondern ein kontrollierter Vergleich.

*Für die Diskussion vorbereiten:* Warum verliert `value_overlap` minimal?
Weil dichtere Graphen bei OpenEA nicht mehr Literale mitbringen, der
Kandidatenraum durch die zusätzlichen Kanten aber leicht wächst.

---

## Folie 10 — Befund 3: Familien hängen an verschiedenen Eigenschaften

**Kernaussage: Es gibt nicht „den schweren Benchmark" — Schwierigkeit ist
relativ zum Verfahren.**

Figure `results/figures_extended/correlation_heatmap.png`. Der schärfste
Einzelvergleich (Spearman, n = 16):

| Datensatz-Eigenschaft | strukturell | wertbasiert |
| --------------------- | ----------: | ----------: |
| ø Total-Grad | **+0,68** (p = 0,004) | −0,30 (p = 0,25) |
| Median-Grad | **+0,68** (p = 0,004) | −0,15 (p = 0,58) |
| Gold-Paare in größter Komponente | **+0,62** (p = 0,010) | — |
| Gesamtzahl Tripel (Größe) | — | **−0,70** (p = 0,003) |

Dieselbe Kennzahl — der mittlere Grad — ist für das eine Verfahren der
zweitstärkste Prädiktor und für das andere ohne Erklärungswert.

Plastisch nach Quellenpaar (ø F1 über Größen und Dichten):

| Matcher | D_W | D_Y | EN_DE | EN_FR |
| ------- | --: | --: | ----: | ----: |
| `value_overlap` | 0,353 | 0,457 | 0,506 | **0,514** |
| `structural_propagation` | 0,618 | **0,737** | 0,628 | 0,479 |

Für das wertbasierte Verfahren ist `EN_FR` der leichteste Fall, für das
strukturelle der schwerste.

Übergreifend stärkster Einzelprädiktor: die **normierte Entropie der
Relations-Property-Verteilung** (bei PARIS ρ = −0,85). Konzentriertes
Vokabular ⇒ wiedererkennbare Nachbarschaften. Diese Kennzahl wird in
Datensatz-Beschreibungen nie berichtet.

*Ehrlich dazusagen:* Die Literal-Überlappung der Gold-Paare korreliert mit dem
wertbasierten Verfahren nur mit ρ = +0,31 (p = 0,24) — das ist **nicht**
signifikant. Dort dominiert der reine Größeneffekt.

---

## Folie 10b — Befund 4: was Bijektivität verdeckt

**Kernaussage: Sobald Entitäten ohne Gegenstück existieren, verlieren alle
Verfahren massiv Precision — auch PARIS.**

Die OpenEA-Benchmarks sind strikt 1:1. Wir haben das kontrolliert aufgebrochen
(`preprocessing/nonmatch.py`): 33 % der Entitäten haben danach keinen Partner.

| Matcher | Precision bijektiv | Precision mit Non-Matches | Δ |
| ------- | -----------------: | ------------------------: | ---: |
| `value_overlap` | 0,661 | 0,504 | −0,16 |
| `pyjedai_ngram` | 0,555 | 0,412 | −0,14 |
| `structural_propagation` | 0,710 | 0,251 | **−0,46** |
| `paris` | 0,966 | 0,809 | −0,16 |

**Nicht F1 in den Vordergrund stellen, sondern die Fehlerart.** Die relevante
Zahl ist `n_false_on_unmatched`: Vorhersagen für Entitäten, die korrekt keinen
Partner haben. Auf `EN_FR_15K_V1` sind das 1 612 (value_overlap), 825
(strukturell) und 501 (PARIS). Ein bijektiver Benchmark kann diese Fehlerart
prinzipiell nicht messen.

> **Vorbereitete Antwort**, falls die niedrigen F1-Werte angesprochen werden:
> „Auf den Non-Match-Varianten fällt unser strukturelles Verfahren auf F1 0,187.
> Das ist kein Implementierungsproblem, sondern das Ergebnis: die Aufgabe wird
> dort doppelt schwerer, weil die entfernten Entitäten ihre Kanten mitnehmen und
> sich die Seed-Menge halbiert. Entscheidend ist der Vergleich — PARIS verliert
> im selben Szenario 14 F1- und 16 Precision-Punkte. Die auf OpenEA berichteten
> Zahlen sind also generell optimistisch, nicht nur unsere."

---

## Folie 11 — Skalierbarkeit

**Kernaussage: Die Kernmetriken liefern auf Pandas und PySpark identische
Zahlen — der skalierbare Pfad ist verifiziert, nicht nur behauptet.**

- **174 von 174 verglichenen Kennzahlen exakt gleich** (29 Metriken ×
  6 Datensätze, max. Abweichung 0,0)
- Von 15 K auf 100 K (6,7× Daten): Pandas-Laufzeit ×6,3, Spark-Laufzeit ×1,9 —
  Spark-Overhead ist konstant, die Rechnung skaliert
- Auf dieser Größe ist Pandas absolut schneller; der Punkt ist, dass der
  Spark-Pfad nicht am Hauptspeicher hängt

Figure `results/figures/backend_runtime.png`.

---

## Folie 12 — Fazit und Grenzen

**Vier Sätze:**

1. Benchmark-Eigenschaften, die niemand dokumentiert, entscheiden messbar über
   die Matching-Güte.
2. Verdopplung der Dichte: +0,28 F1 strukturell, ±0 textuell — kontrolliert
   nachgewiesen.
3. Diese Benchmarks können ganze Verfahrensklassen nicht fair bewerten (keine
   Typen, bijektiver Gold-Standard).
4. Wer ein Verfahren auf einem einzigen Benchmark evaluiert, misst die
   Eigenschaften dieses Benchmarks mit.

**Grenzen offen ansprechen** (kommt sonst in der Diskussion):

- nur OpenEA, nur 4 unabhängige Quellenpaare
- nur ein Fold, keine Konfidenzintervalle
- zwei der vier Verfahren sind Eigenimplementierungen — die Familien-Kontraste
  tragen, die absoluten Niveaus liegen unter dem Stand der Technik
- kein Embedding-Verfahren dabei

---

## Backup-Folien (nur auf Nachfrage)

| # | Inhalt | Erwartete Frage |
| - | ------ | --------------- |
| B1 | Vollständige F1-Tabelle über alle 16 Varianten | "Wie sieht das auf den anderen aus?" |
| B2 | Precision/Recall-Scatter | "Warum ist PARIS so gut?" — hohe Precision, Recall limitiert |
| B3 | Grad-Verteilungen log-log, alle Datensätze | "Sind das Power-Law-Graphen?" α ≈ 1,3–1,6 |
| B4 | Attribut-Coverage je Property | "Welche Attribute gibt es überhaupt?" |
| B5 | Skalen-Effekt 15 K → 100 K | "Was passiert bei größeren Graphen?" |
| B6 | Speichermanagement der Ähnlichkeitsmatrix | "Wie geht 100 K × 100 K auf einem Laptop?" |
| B7 | PARIS-Integration: URI-Round-Trip, Iterationsdateien | "Wie habt ihr PARIS eingebunden?" |
| B8 | Backend-Äquivalenztabelle | "Wie stellt ihr sicher, dass beide Backends dasselbe rechnen?" |

## Vorbereitete Antworten

**"Warum sind eure F1-Werte niedriger als in den OpenEA-Papern?"**
Wir rechnen auf v2.0 mit anonymisierten URIs — dort ist der Name Bias entfernt,
den ältere Ergebnisse auf v1.1 mitmessen. Außerdem sind vier unserer fünf
Matcher bewusst einfache Verfahren; PARIS als etabliertes Tool liegt mit
F1 0,74–0,98 im erwarteten Bereich.

**"Ist n = 16 nicht zu klein für Korrelationen?"**
Ja, und die 16 sind zusätzlich nicht unabhängig (4 Quellenpaare × 2 Größen ×
2 Dichten). Deshalb ist unser Hauptargument der kontrollierte Dichte-Vergleich
aus Folie 9, nicht die Korrelation. Die Korrelationen ergänzen, sie tragen
nicht allein.

**"Warum kein Embedding-Verfahren?"**
Zeitbudget und Hardware — die OpenEA-Verfahren brauchen GPU-Training pro
Datensatz. Wir haben stattdessen die Signaltypen abgedeckt und mit PARIS ein
etabliertes Verfahren eingebunden. Das ist die naheliegendste Fortsetzung.

**"Warum Pandas *und* Spark, wenn Pandas schneller ist?"**
Weil die Aufgabenstellung ein modulares Design verlangt, in dem verschiedene
Processing-Frameworks vergleichbar sind. Der Wert liegt im verifizierten
Äquivalenztest: derselbe Metrik-Katalog, zwei Ausführungsmodelle, identische
Zahlen. Für die vorliegenden Datengrößen genügt Pandas, für größere Graphen
hängt nur der Spark-Pfad nicht am Hauptspeicher.

## Materialien

| Was | Wo |
| --- | -- |
| Figures Kernlauf | `results/figures/` |
| Figures erweiterter Lauf, Kontraste | `results/figures_extended/` |
| Zahlen für alle Tabellen | `docs/Ergebnisse.md` |
| Architektur-Diagramm | `docs/Architektur.md` §2 |
| Metriken-Tabelle | `docs/Metriken-Katalog.md` |
