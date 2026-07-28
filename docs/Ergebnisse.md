# Ergebnisse

Stand: Testat 2. Alle Zahlen stammen aus `results/reports/` (sechs
Kern-Datensätze) bzw. `results/reports_extended/` (alle 16 OpenEA-Varianten)
und sind mit den Kommandos aus dem README reproduzierbar.

## Forschungsfrage

> **Welche strukturellen und semantischen Eigenschaften von
> Entity-Alignment-Benchmarks bestimmen, wie gut ein Matching-Verfahren auf
> ihnen abschneidet — und hängt das davon ab, welche Art von Verfahren man
> einsetzt?**

| Teilfrage | Beantwortet in |
| --------- | -------------- |
| F1: Wie unterscheiden sich gängige Benchmarks strukturell und semantisch? | §1 |
| F2: Wie unterschiedlich schneiden Matcher darauf ab? | §2 |
| F3: Welche Eigenschaften erklären diese Unterschiede kausal? | §3.1 (kontrollierte Vergleiche) |
| F4: Reagieren verschiedene Matcher-Familien auf verschiedene Eigenschaften? | §3.2 |
| F5: Skaliert die Berechnung über den Hauptspeicher hinaus? | §4 |

**Aufbau:** §1 Profiling der Benchmarks, §2 Matching-Güte, §3 was die
Matching-Güte erklärt, §4 Skalierbarkeit, §5 Grenzen.

---

## 1. Profiling: wie sehen die Benchmarks aus?

### 1.1 Kernprofil der sechs Datensätze

| Datensatz | ø Grad | Median Grad | Gini Grad | α (Power-Law) | Attr./Entität | Anteil Ent. mit Attribut | Property-Jaccard | Rel.-Entropie |
| --------- | -----: | ----------: | --------: | ------------: | ------------: | -----------------------: | ---------------: | ------------: |
| `EN_FR_15K_V1` | 5,88 | 4 | 0,52 | 1,49 | 3,72 | 0,90 | 0,29 | 0,69 |
| `EN_FR_15K_V2` | 11,76 | 9 | 0,41 | 1,34 | 3,62 | 0,89 | 0,31 | 0,61 |
| `EN_DE_15K_V1` | 6,54 | 4 | 0,54 | 1,49 | 6,54 | 0,93 | 0,42 | 0,53 |
| `D_W_15K_V1` | 5,40 | 4 | 0,49 | 1,52 | 6,35 | 0,94 | **0,00** | 0,67 |
| `D_Y_15K_V1` | 3,80 | 3 | 0,38 | 1,55 | 5,64 | 0,96 | **0,00** | 0,61 |
| `EN_FR_100K_V1` | 5,68 | 4 | 0,57 | 1,52 | 3,63 | 0,88 | 0,26 | 0,71 |

Die Auswahl spannt den beabsichtigten Raum tatsächlich auf: der Grad variiert
um Faktor 3 (3,8 bis 11,8), die Property-Überlappung zwischen den beiden KGs
eines Paars von 0 % bis 42 %.

### 1.2 Befund A — Typ-Information ist praktisch nicht vorhanden

| Datensatz | Anteil typisierter Entitäten KG1 | KG2 |
| --------- | -------------------------------: | --: |
| `EN_FR_15K_V1/V2`, `EN_DE_15K_V1`, `D_Y_15K_V1`, `EN_FR_100K_V1` | 0,000 | 0,000 |
| `D_W_15K_V1` | 0,000 | 0,309 |

In fünf von sechs Datensätzen gibt es **kein einziges** `rdf:type`-Tripel; nur
die Wikidata-Seite von `D_W` trägt über `P31` Typen für 31 % ihrer Entitäten.

Konsequenz: Verfahren, die Typ- oder Ontologie-Information nutzen — von
typ-beschränktem Blocking bis zu ontologie-bewussten Embeddings — lassen sich
auf diesen Benchmarks gar nicht sinnvoll evaluieren. Wer solche Verfahren
vergleichen will, braucht andere Daten. Das ist ein Ergebnis *über* den
Benchmark, das man ohne systematisches Profiling nicht sieht.

### 1.3 Befund B — der Gold-Standard ist unrealistisch einfach strukturiert

Für **alle** sechs Datensätze gilt exakt:

| Kennzahl | Wert |
| -------- | ---: |
| `alignment_coverage` | 1,000 |
| `entity_coverage_kg1` / `entity_coverage_kg2` | 1,000 / 1,000 |
| `bijective_share` | 1,000 |
| `ambiguity_1_to_n` / `ambiguity_n_to_1` | 0,000 |
| `share_pairs_both_with_edge` | 1,000 |

Jede Entität in KG1 hat genau einen Partner in KG2 und umgekehrt. Es gibt
keine Entität ohne Gegenstück, keine 1:n-Beziehung, und keine isolierte
Entität.

Das ist eine erhebliche Vereinfachung gegenüber echter Datenintegration, wo
typischerweise die *Mehrheit* der Entitäten kein Gegenstück hat. Ein Matcher
darf hier bedenkenlos für jede Entität eine Vorhersage abgeben — die
Entscheidung "dieses Paar existiert nicht" wird nie geprüft. Absolute
F1-Werte auf OpenEA sind deshalb systematisch optimistisch; belastbar sind nur
*relative* Vergleiche zwischen Verfahren oder Datensätzen.

### 1.4 Befund C — extremer Long Tail im Property-Vokabular

90–94 % aller Relations-Properties tragen jeweils weniger als 1 % der Tripel;
die zehn häufigsten tragen 46–80 %. Die Schema-Information konzentriert sich
also auf sehr wenige Properties, während der Rest Rauschen ist. Wie stark diese
Konzentration ist, misst `mean_rel_entropy_norm` — und diese Kennzahl erweist
sich in §3 als der stärkste Einzelprädiktor für die Matching-Güte überhaupt.

---

## 2. Matching-Güte

F1 auf dem Test-Split (70 % des Referenz-Alignments), Fold 1:

| Datensatz | `literal_tfidf` | `value_overlap` | `structural_prop.` | `hybrid` | `paris` |
| --------- | --------------: | --------------: | -----------------: | -------: | ------: |
| `EN_FR_15K_V1` | 0,318 | 0,558 | 0,203 | 0,406 | **0,809** |
| `EN_FR_15K_V2` | 0,308 | 0,579 | 0,337 | 0,525 | **0,892** |
| `EN_DE_15K_V1` | 0,228 | 0,616 | 0,514 | 0,563 | **0,900** |
| `D_W_15K_V1` | 0,160 | 0,403 | 0,307 | 0,347 | **0,748** |
| `D_Y_15K_V1` | 0,227 | 0,605 | 0,330 | 0,390 | **0,918** |
| `EN_FR_100K_V1` | 0,231 | 0,446 | 0,163 | 0,251 | **0,743** |

Drei Beobachtungen:

1. **PARIS dominiert deutlich** (F1 0,74–0,92) bei durchgängig sehr hoher
   Precision (0,93–0,99). Es nutzt Struktur *und* Literale gleichzeitig und
   iteriert beides gegeneinander — genau die Kombination, die den einzelnen
   Signalen fehlt. Sein Recall (0,56–0,97) ist der limitierende Faktor: PARIS
   gibt lieber keine Vorhersage ab als eine unsichere.
2. **Kein einzelnes Signal reicht.** Der beste rein textuelle Matcher kommt auf
   0,62, der rein strukturelle auf 0,51.
3. **Die Rangfolge der Matcher ist nicht datensatzstabil.** Auf `EN_DE_15K_V1`
   ist der strukturelle Matcher mehr als doppelt so gut wie auf
   `EN_FR_15K_V1` — bei gleicher Größe und gleicher Quelle. Wer auf einem
   einzigen Benchmark evaluiert, misst also die Eigenschaften dieses
   Benchmarks mit.

Punkt 3 ist die Rechtfertigung für den Rest des Berichts.

---

## 3. Was erklärt die Matching-Güte?

### 3.1 Kontrollierte Vergleiche (das belastbarste Ergebnis)

Die OpenEA-Familie erlaubt echte kontrollierte Experimente: V1 und V2 eines
Paares enthalten **dieselben Entitäten** und unterscheiden sich nur in der
Anzahl der Relations-Tripel. Gemittelt über alle vier Quellenpaare und beide
Größen (n = 8 Paare):

| Matcher | ø F1 auf V1 (sparse) | ø F1 auf V2 (dense) | Δ |
| ------- | -------------------: | ------------------: | ---: |
| `literal_tfidf` | 0,207 | 0,189 | **−0,018** |
| `value_overlap` | 0,475 | 0,451 | **−0,024** |
| `structural_propagation` | 0,334 | 0,614 | **+0,280** |
| `hybrid` | 0,386 | 0,550 | +0,163 |
| `paris` | 0,824 | 0,908 | +0,084 |

**Verdopplung der Graphdichte verbessert den strukturellen Matcher um 28
F1-Punkte und lässt die textuellen Matcher unverändert** (im Rahmen des
Rauschens sogar minimal schlechter).

Der Vergleich ist sauber, weil sich zwischen V1 und V2 im Wesentlichen nur die
Struktur ändert: die Relations-Tripel wachsen um Faktor 1,81–2,27, die
Attribut-Tripel dagegen nur um Faktor 0,97–1,21 bei identischer Entitätsmenge.
Es verändert sich also fast ausschließlich die Eigenschaft, auf die eine der
beiden Matcher-Familien angewiesen ist — und genau diese Familie reagiert.

Damit ist die Kernhypothese des Projekts nicht nur korreliert, sondern
kontrolliert belegt.

Analog für die Skalierung (15 K → 100 K, n = 8 Paare):

| Matcher | ø F1 bei 15 K | ø F1 bei 100 K | Δ |
| ------- | ------------: | -------------: | ---: |
| `paris` | 0,883 | 0,849 | −0,034 |
| `structural_propagation` | 0,499 | 0,450 | −0,049 |
| `literal_tfidf` | 0,223 | 0,172 | −0,052 |
| `hybrid` | 0,520 | 0,416 | −0,104 |
| `value_overlap` | 0,532 | 0,394 | **−0,138** |

Alle Verfahren verlieren, weil der Kandidatenraum um Faktor 44 wächst
(10⁸ → 10¹⁰ Paare). Am stärksten trifft es `value_overlap`: exakte
Literalwerte, die bei 15 K noch eindeutig identifizieren, kollidieren bei
100 K mit mehreren Kandidaten. Am robustesten ist PARIS.

Nach Quellenpaar (ø über Größen und Dichten):

| Matcher | D_W | D_Y | EN_DE | EN_FR |
| ------- | --: | --: | ----: | ----: |
| `literal_tfidf` | 0,134 | 0,182 | 0,205 | 0,269 |
| `value_overlap` | 0,364 | 0,464 | 0,513 | 0,511 |
| `structural_propagation` | 0,431 | 0,653 | 0,551 | 0,262 |
| `hybrid` | 0,415 | 0,544 | 0,523 | 0,389 |
| `paris` | 0,792 | 0,948 | 0,899 | 0,825 |

`D_W` (DBpedia ↔ Wikidata, Property-Jaccard = 0) ist für jeden Matcher der
schwerste Fall. Bemerkenswert ist die Umkehrung zwischen `D_Y` und `EN_FR`: für
textuelle Matcher ist `EN_FR` am leichtesten und `D_Y` schwer, für den
strukturellen Matcher genau umgekehrt (0,653 vs. 0,262). Dieselben zwei
Benchmarks führen also zu gegensätzlichen Aussagen darüber, welches Verfahren
besser ist.

### 3.2 Korrelationsanalyse über alle 16 Varianten

Spearman-Rangkorrelation zwischen Datensatz-Metrik und F1, n = 16
(`results/reports_extended/correlation.csv`). Je Matcher die stärksten
Zusammenhänge:

**`structural_propagation` — reagiert auf Struktur:**

| Metrik | ρ | p |
| ------ | ---: | ---: |
| Relations-Property-Entropie | −0,738 | 0,001 |
| ø Total-Grad | +0,703 | 0,002 |
| Median-Grad (schwächerer KG) | +0,661 | 0,005 |
| Anteil Gold-Paare in größter Komponente | +0,656 | 0,006 |
| Anteil Entitäten in größter Komponente | +0,650 | 0,006 |

**`literal_tfidf` — reagiert auf Literale, nicht auf Struktur:**

| Metrik | ρ | p |
| ------ | ---: | ---: |
| Literal-Jaccard der Gold-Paare | +0,612 | 0,012 |
| Gesamtzahl Tripel (Größeneffekt) | −0,603 | 0,013 |
| Attribut-Tripel pro Entität | −0,559 | 0,024 |
| Grad-Korrelation der Gold-Paare | +0,497 | 0,050 |

Unter den fünf stärksten Prädiktoren des strukturellen Matchers sind vier
Struktur-Metriken; beim textuellen Matcher ist die stärkste Kennzahl die
Literal-Überlappung der Gold-Paare, und keine Grad-Metrik schafft es in die
Spitzengruppe. Die Matcher-Familien reagieren nachweislich auf
unterschiedliche Datensatz-Eigenschaften.

**`paris`:** ein einziger dominanter Prädiktor, die Relations-Property-Entropie
(ρ = −0,871, p < 0,001). Alle übrigen Korrelationen liegen unter 0,45 und sind
nicht signifikant — PARIS ist gegenüber den meisten Eigenschaftsunterschieden
robust, was zu seiner konstant hohen Precision passt.

### 3.3 Die Property-Entropie als Leitindikator

`mean_rel_entropy_norm` — die normierte Shannon-Entropie der
Relations-Property-Verteilung — ist für drei der fünf Matcher der stärkste
Prädiktor und für die übrigen unter den ersten sechs. Sie misst, wie
gleichmäßig sich die Tripel über die Properties verteilen:

- **niedrige Entropie**: wenige Properties tragen fast alle Tripel — die
  Nachbarschaft einer Entität ist typisiert und wiedererkennbar
- **hohe Entropie**: die Tripel verteilen sich über hunderte seltene
  Properties — jede Nachbarschaft sieht anders aus

Interpretation: Ein *konzentriertes* Relations-Vokabular macht Nachbarschaften
vergleichbar und damit strukturelles Matching möglich. Für die
Benchmark-Bewertung heißt das: die Property-Verteilung, die in
Datensatz-Beschreibungen praktisch nie dokumentiert wird, ist aussagekräftiger
als die üblicherweise berichtete Entitäten- und Tripelzahl.

**Einschränkung.** Entropie und Grad sind auf diesen Daten korreliert (dichtere
Varianten haben tendenziell konzentriertere Vokabulare), und die 16 Varianten
sind keine unabhängigen Stichproben, sondern 4 Quellenpaare × 2 Größen ×
2 Dichten. Die effektive Stichprobe ist also kleiner als n = 16, und die
Korrelationen trennen nicht sauber zwischen beiden Erklärungen. Der
kontrollierte Dichte-Vergleich aus §3.1 ist deshalb das stärkere Argument; die
Korrelationen ergänzen ihn, ersetzen ihn nicht.

---

## 4. Skalierbarkeit

### 4.1 Pandas vs. PySpark

Die Kernmetriken (Basis-Statistiken, Grad-Verteilung, Property-Verteilung) sind
zweimal implementiert. `scripts/run_backend_benchmark.py` prüft metrikweise auf
Gleichheit:

**174 von 174 verglichenen Kennzahlen stimmen exakt überein** (29 Metriken ×
6 Datensätze, maximale absolute Abweichung 0,0).

| Datensatz | Pandas [s] | PySpark [s] |
| --------- | ---------: | ----------: |
| `EN_FR_15K_V1` | 0,4 | 9,9 (inkl. JVM-Start) |
| `EN_FR_15K_V2` | 0,4 | 5,5 |
| `EN_DE_15K_V1` | 0,5 | 5,1 |
| `D_W_15K_V1` | 0,4 | 4,6 |
| `D_Y_15K_V1` | 0,4 | 4,9 |
| `EN_FR_100K_V1` | 2,5 | 10,3 |

Auf dieser Datengröße ist Pandas erwartungsgemäß um ein Vielfaches schneller —
Spark zahlt JVM- und Shuffle-Overhead, den es hier nicht amortisieren kann.
Der Trend ist aber aufschlussreich: von 15 K auf 100 K (6,7-fache Datenmenge)
wächst die Pandas-Laufzeit um Faktor 6,3, die Spark-Laufzeit nur um 1,9. Der
Overhead ist konstant, die eigentliche Rechnung skaliert. Entscheidend ist
ohnehin nicht die Laufzeit, sondern dass der Spark-Pfad nicht am Hauptspeicher
hängt: er hält nie den ganzen Graphen im Treiber.

### 4.2 Laufzeit der Gesamt-Pipeline

| Datensatz | Metriken [s] | `literal_tfidf` | `value_overlap` | `structural_prop.` | `hybrid` | `paris` |
| --------- | -----------: | --------------: | --------------: | -----------------: | -------: | ------: |
| 15 K (Mittel) | 0,9 | 0,6 | 0,6 | 0,3 | 1,0 | 4–15 |
| `EN_FR_100K_V1` | 5,9 | 4,9 | 4,2 | 2,0 | 6,9 | 61,8 |

Der komplette Kernlauf (6 Datensätze × 11 Metriken × 5 Matcher inkl. Reports
und Figures) dauert rund 3 Minuten, der erweiterte Lauf über 16 Datensätze
18 Minuten — auf einem Laptop mit 8 GB RAM.

Der Schlüssel dazu ist das Speichermanagement der Ähnlichkeitsmatrix
(`docs/Architektur.md` §6): dicht wären es bei 100 K Entitäten 10¹⁰ Einträge.
Durch Vokabular-Beschneidung, blockweises Produkt und sofortiges
Top-k-Pruning bleibt der Bedarf linear in der Entitätenzahl.

### 4.3 Reproduzierbarkeit

Ein vollständiger Wiederholungslauf mit identischer Konfiguration wurde gegen
die hier berichteten Zahlen verglichen:

- **Alle 297 Metrik-Kennzahlen aller sechs Datensätze: exakt identisch.**
- **Die vier eigenen Matcher: F1 exakt identisch.**
- **PARIS: Abweichung bis 0,0013 F1.** Das externe Tool ist iterativ und nicht
  bit-deterministisch. Für die berichteten Effekte (Größenordnung 0,03–0,28 F1)
  ist das ohne Belang, sollte aber bekannt sein: PARIS-Werte in dieser Arbeit
  sind auf ±0,002 genau, nicht darüber hinaus.

---

## 5. Grenzen der Aussagen

| Einschränkung | Auswirkung |
| ------------- | ---------- |
| Nur OpenEA als Quelle | Aussagen gelten für diese Benchmark-Familie; ob sie auf andere Datensatzfamilien übertragen, ist offen |
| 16 Varianten, aber nur 4 unabhängige Quellenpaare | effektive Stichprobe der Korrelationen kleiner als n = 16 |
| Nur ein Fold ausgewertet | Streuung über die fünf 721-Folds nicht quantifiziert |
| Vier von fünf Matchern sind eigene, einfache Implementierungen | absolute F1-Werte liegen unter dem Stand der Technik; die Familien-Kontraste sind davon nicht betroffen, die absoluten Niveaus schon |
| Keine Embedding-basierten Verfahren (BootEA, RDGCN, …) | die für OpenEA typische Verfahrensklasse fehlt; ihr Verhalten muss nicht dem des `structural_propagation` folgen |
| Gold-Standard strikt 1:1 (§1.3) | absolute F1-Werte systematisch optimistisch |
| Korrelation ≠ Kausalität | nur die kontrollierten Vergleiche aus §3.1 stützen kausale Aussagen |

### Naheliegende Fortsetzung

1. Alle fünf Folds rechnen und Konfidenzintervalle statt Punktschätzern angeben.
2. Ein Embedding-Verfahren aus dem OpenEA-Repository einbinden, um die
   Verfahrensklasse abzudecken, für die diese Benchmarks gebaut wurden.
3. Künstlich Distraktor-Entitäten ohne Gegenstück einstreuen und messen, wie
   stark die F1-Werte einbrechen — das quantifiziert die Verzerrung aus §1.3.

---

## 6. Zusammenfassung in fünf Sätzen

1. OpenEA-v2.0-Benchmarks enthalten praktisch keine Typ-Information und einen
   strikt bijektiven, vollständig abdeckenden Gold-Standard — beides schränkt
   ein, welche Verfahren darauf überhaupt fair bewertbar sind.
2. Verdopplung der Graphdichte bei identischer Entitätsmenge verbessert
   strukturelles Matching um 28 F1-Punkte und textuelles Matching um null.
3. Textuelle und strukturelle Matcher korrelieren nachweislich mit
   unterschiedlichen Datensatz-Eigenschaften — Literal-Überlappung bzw. Grad
   und Konnektivität.
4. Die normierte Entropie der Relations-Property-Verteilung ist der stärkste
   Einzelprädiktor für die Matching-Güte und wird in Datensatz-Beschreibungen
   nie berichtet.
5. Die Kernmetriken liefern auf Pandas und PySpark bitgleiche Ergebnisse
   (174/174), womit der skalierbare Pfad verifiziert ist.
