# Ergebnisse

Stand nach Testat 2. Alle Zahlen stammen aus `results/reports/` (bijektive
Originaldatensätze), `results/reports_nonmatch/` (Varianten mit partnerlosen
Entitäten) und `results/reports_extended/` (alle 16 OpenEA-Varianten) und sind
mit den Kommandos aus dem README reproduzierbar.

## Forschungsfrage

> **Welche strukturellen und semantischen Eigenschaften von
> Entity-Alignment-Benchmarks bestimmen, wie gut ein Matching-Verfahren auf
> ihnen abschneidet — und hängt das davon ab, welche Art von Verfahren man
> einsetzt?**

| Teilfrage | Beantwortet in |
| --------- | -------------- |
| F1: Wie unterscheiden sich gängige Benchmarks strukturell und semantisch? | §1 |
| F2: Wie unterschiedlich schneiden Matcher darauf ab? | §2 |
| F3: Welche Eigenschaften erklären diese Unterschiede kausal? | §3 |
| F4: Reagieren verschiedene Matcher-Familien auf verschiedene Eigenschaften? | §4 |
| F5: Sind die Effekte grösser als das Rauschen zwischen den Folds? | §3.4 |
| F6: Was ändert sich, wenn der Benchmark realistischer wird? | §5 |
| F7: Woran genau scheitern die Verfahren im Einzelfall? | §5a |
| F8: Skaliert die Berechnung über den Hauptspeicher hinaus? | §6 |

---

## 1. Profiling: wie sehen die Benchmarks aus?

### 1.1 Kernprofil

| Datensatz | ø Grad | Median | Gini | α | Attr./Ent. | Property-Jaccard | Rel.-Entropie | LCC |
| --------- | -----: | -----: | ---: | -: | ---------: | ---------------: | ------------: | --: |
| `EN_FR_15K_V1` | 5,88 | 4 | 0,52 | 1,49 | 3,72 | 0,29 | 0,69 | 0,89 |
| `EN_FR_15K_V2` | 11,76 | 8 | 0,41 | 1,34 | 3,62 | 0,31 | 0,61 | 0,99 |
| `EN_DE_15K_V1` | 6,54 | 4 | 0,54 | 1,49 | 6,54 | 0,42 | 0,53 | 0,95 |
| `D_W_15K_V1` | 5,40 | 3 | 0,49 | 1,52 | 6,35 | **0,00** | 0,67 | 0,93 |
| `D_Y_15K_V1` | 3,80 | 3 | 0,38 | 1,55 | 5,64 | **0,00** | 0,61 | 0,84 |
| `EN_FR_100K_V1` | 5,68 | 3 | 0,57 | 1,52 | 3,63 | 0,26 | 0,71 | 0,93 |

Fünf der sechs sind nominell „15K-Datensätze" mit exakt 15 000 Entitäten. Die
Kennzahl, die üblicherweise berichtet wird, unterscheidet sie also gar nicht,
während der mittlere Grad um Faktor 3 und die Schema-Überlappung von 0 % bis
42 % variiert.

### 1.2 Befund A — Typ-Information fehlt praktisch vollständig

| Datensatz | typisierte Entitäten KG1 | KG2 |
| --------- | -----------------------: | --: |
| alle ausser `D_W_15K_V1` | 0,000 | 0,000 |
| `D_W_15K_V1` | 0,000 | 0,309 |

In fünf von sechs Datensätzen gibt es **kein einziges** `rdf:type`-Tripel; nur
die Wikidata-Seite von `D_W` trägt über `P31` Typen. Typ- und
ontologiebasierte Verfahren lassen sich auf diesen Benchmarks also gar nicht
evaluieren.

### 1.3 Befund B — der Gold-Standard ist unrealistisch einfach

Für alle sechs Datensätze gilt exakt: `alignment_coverage` = 1,000,
`bijective_share` = 1,000, `ambiguity_1_to_n` = 0,000. Jede Entität hat genau
einen Partner.

Das ist nicht nur praxisfern, es verdeckt einen konkreten methodischen Fehler:
Ohne partnerlose Entitäten ist es *immer* richtig, für jede Entität irgendeinen
Partner vorherzusagen. Ein Matcher ohne Schwellenwert wird dafür nie bestraft.
§5 misst, was passiert, wenn man diese Annahme aufhebt.

### 1.4 Befund C — die Dateien sind kein RDF

OpenEA gilt als RDF-Datensatz. Wir haben geprüft, ob sich die Dateien direkt
mit `rdflib.Graph().parse()` einlesen lassen (`scripts/check_openea_rdf.py`):

| Prüfung | Ergebnis |
| ------- | -------- |
| `g.parse(datei, format="nt")` | scheitert auf **allen** Dateien (`ParserError`) |
| `g.parse(datei, format="turtle")` | scheitert auf **allen** Dateien (`BadSyntax`) |
| Anteil Objektwerte, die kein gültiger RDF-Term sind | 0,7 % bis 52 % je Datei |

Die Dateien sind tab-separiert, die URIs stehen ohne spitze Klammern da, die
abschliessenden Punkte fehlen, und YAGO-Terme wie `YAGO/E473489` oder
`isLocatedIn` sind gar keine IRIs. Je nach Datei sind zwischen 0,7 % und 52 %
der Objektwerte unquotierte Rohstrings und damit kein gültiger RDF-Term.

Konsequenz für die Implementierung: Wir arbeiten spaltenweise, überlassen aber
die Termkonstruktion rdflib (`rdflib.util.from_n3`) und den Export nach
N-Triples dem `Graph`-Objekt mit `serialize()`. Der Round-Trip ist per Test
abgesichert.

Nebenbefund aus rdflibs eigener Validierung: die Daten enthalten ill-typed
Literale — Werte, deren Lexikalform nicht zum angegebenen Datentyp passt, etwa
`"3.6e"^^xsd:double` und das Datum `"-0070-10-15"`. In der YAGO-Seite von
`D_Y_15K_V1` sind das 4 150 Literale.

### 1.5 Befund D — extremer Long Tail im Vokabular

90–94 % aller Relations-Properties tragen jeweils weniger als 1 % der Tripel;
die zehn häufigsten tragen 46–80 %.

---

## 2. Matching-Güte auf den Originaldatensätzen

F1 auf dem Test-Split (70 %), Fold 1, mit den in §2.2 bestimmten
Schwellenwerten:

| Datensatz | `value_overlap` | `pyjedai_ngram` | `structural_prop.` | `paris` |
| --------- | --------------: | --------------: | -----------------: | ------: |
| `EN_FR_15K_V1` | 0,560 | 0,447 | 0,390 | **0,809** |
| `EN_FR_15K_V2` | 0,584 | 0,504 | 0,639 | **0,892** |
| `EN_DE_15K_V1` | 0,611 | 0,339 | 0,638 | **0,900** |
| `D_W_15K_V1` | 0,390 | 0,320 | 0,496 | **0,744** |
| `D_Y_15K_V1` | 0,594 | 0,434 | 0,500 | **0,919** |
| `EN_FR_100K_V1` | 0,448 | — | 0,338 | **0,743** |
| **Mittel** | 0,531 | 0,409 | 0,500 | **0,835** |

`pyjedai_ngram` wird auf der 100K-Variante übersprungen: die Bibliothek baut
einen expliziten Kandidatengraphen, was dort die Laufzeit sprengt.

### 2.1 Überarbeitung des strukturellen Matchers

Die erste Fassung war zu grob — sie symmetrisierte die Adjazenzmatrix und
speicherte nur, *dass* zwei Knoten verbunden sind. Drei Informationen kamen
hinzu: Kantenrichtung, Relationstyp und Gewichtung.

Der Knackpunkt ist der Relationstyp. Relationstypen sind zwischen zwei KGs
nicht direkt vergleichbar; bei `D_W` und `D_Y` ist die Property-Überlappung
sogar exakt null. Die Relationen werden deshalb **selbst aligniert**, allein
aus der Seed-Evidenz: Sind (a, b) und (x, y) Seed-Paare und gilt in KG1
`a --r1--> x` sowie in KG2 `b --r2--> y`, ist das ein Beleg für r1 ≙ r2.

Das funktioniert ohne gemeinsames Vokabular. Auf `D_W` gefundene Zuordnungen:

| KG1 (DBpedia) | KG2 (Wikidata) | Dice |
| ------------- | -------------- | ---: |
| `series` | `P179` | 1,00 |
| `party` | `P102` | 1,00 |
| `ideology` | `P1142` | 1,00 |

Zusätzlich wird die **Gegenrichtung** geprüft, weil zwei KGs dieselbe
Beziehung oft invers modellieren. Das war bei `D_Y` entscheidend: **14 von 25
alignierten Relationspaaren sind invertiert** — YAGO orientiert Relationen
systematisch anders als DBpedia. Ohne diesen Fall wäre die
Richtungsinformation dort genau falsch herum gewesen (F1 0,14 statt 0,50).

Ergebnis der Überarbeitung:

| Datensatz | F1 vorher | F1 jetzt | Precision vorher | Precision jetzt |
| --------- | --------: | -------: | ---------------: | --------------: |
| `EN_FR_15K_V1` | 0,203 | 0,390 | 0,209 | 0,639 |
| `EN_FR_15K_V2` | 0,337 | 0,639 | 0,337 | 0,788 |
| `EN_DE_15K_V1` | 0,514 | 0,638 | 0,524 | 0,853 |
| `D_W_15K_V1` | 0,307 | 0,496 | 0,319 | 0,732 |
| `D_Y_15K_V1` | 0,330 | 0,500 | 0,349 | 0,643 |
| `EN_FR_100K_V1` | 0,163 | 0,338 | 0,167 | 0,603 |
| **Mittel** | **0,309** | **0,500** | **0,317** | **0,710** |

Die Precision hat sich mehr als verdoppelt. Das ist der eigentliche Gewinn:
das Verfahren produziert nicht mehr überwiegend False Positives.

### 2.2 Schwellenwerte

In der ersten Fassung stand `min_score` auf 0,0 — für jede Entität wurde der
bestbewertete Kandidat ausgegeben, auch bei einem Score von 0,01. Die Werte
sind jetzt auf dem Valid-Split abgetastet (Raster 0,0–0,9,
`scripts/tune_thresholds.py`) und über die Datensätze gemittelt gewählt:

| Matcher | Schwellenwert | greift an | valid-F1 |
| ------- | ------------: | --------- | -------: |
| `value_overlap` | 0,4 | Kosinus-Ähnlichkeit | 0,485 |
| `pyjedai_ngram` | 0,2 | Cluster-Ähnlichkeit | 0,356 |
| `structural_propagation` | 0,1 | **relativer Abstand zum Zweitbesten** | 0,206 |

Beim strukturellen Matcher greift der Schwellenwert bewusst nicht am Score.
Dessen Scores sind zeilenweise normiert, der Bestwert ist also immer exakt 1,0
und ein Score-Schwellenwert damit wirkungslos — das war im ersten Sweep
sichtbar (jeder Wert ausser 0,0 verwarf entweder nichts oder alles).
Konfidenzmass ist dort (top1 − top2) / top1.

Auf den bijektiven Originaldatensätzen ändert der Schwellenwert am F1 wenig
(`value_overlap` 0,534 → 0,531), hebt aber die Precision (0,640 → 0,661). Das
ist erwartbar: wo jede Entität einen Partner hat, kostet Enthaltung nur Recall.
Der Nutzen wird erst in §5 sichtbar.

### 2.3 Standard-Bibliothek statt Eigenimplementierung

`pyjedai_ngram` nutzt den Standard-Workflow von pyJedAI für Clean-Clean Entity
Resolution: `StandardBlocking → BlockPurging → BlockFiltering →
WeightedEdgePruning → EntityMatching (Zeichen-3-Gramme, Kosinus) →
UniqueMappingClustering`.

Bemerkenswert: die Bibliothek schlägt unseren einfachen `value_overlap` **nicht**
(0,409 vs. 0,531 im Mittel). Der Grund liegt in den Daten — die Literale in
OpenEA v2.0 sind überwiegend Datumsangaben, Zahlen und Kennungen. Dort ist
exakte Wertgleichheit das schärfere Signal, während Zeichen-n-Gramme
Datumsangaben verwischen (`1990-01-01` und `1990-01-07` teilen fast alle
3-Gramme). Der Wert der Bibliothek liegt hier nicht in der besseren Zahl,
sondern in Blocking, Kandidaten-Pruning und einer kalibrierten
Zuordnungsstufe, die wir sonst selbst hätten bauen müssen.

---

## 3. Kontrollierte Vergleiche

### 3.1 Dichte-Effekt

V1 und V2 eines Quellenpaares enthalten **dieselben Entitäten**; die
Relations-Tripel wachsen um Faktor 1,81–2,27, die Attribut-Tripel nur um
0,97–1,21. Es ändert sich also fast ausschliesslich die Struktur. Gemittelt
über alle vier Quellenpaare und beide Größen (n = 8 Paare):

| Matcher | V1 sparse | V2 dense | Δ |
| ------- | --------: | -------: | ---: |
| `value_overlap` (wertbasiert) | 0,470 | 0,445 | **−0,03** |
| `structural_propagation` | 0,498 | 0,733 | **+0,24** |
| `paris` | 0,825 | 0,908 | +0,08 |

Verdopplung der Graphdichte verbessert das strukturelle Verfahren um 24
F1-Punkte und lässt das wertbasierte unverändert (im Rahmen des Rauschens
minimal schlechter). Das ist keine Korrelation, sondern ein Experiment mit
genau einer veränderten Variable — und genau die Verfahrensfamilie, die diese
Variable nutzt, reagiert darauf.

Auf dem Kernlauf einzeln nachvollziehbar an `EN_FR_15K` V1 → V2:
`structural_propagation` 0,390 → 0,639, `value_overlap` 0,560 → 0,584.

### 3.2 Skalen-Effekt

15 K → 100 K Entitäten, der Kandidatenraum wächst um Faktor 44
(2,25·10⁸ → 10¹⁰). Gemittelt über 8 Paare:

| Matcher | 15 K | 100 K | Δ |
| ------- | ---: | ----: | ---: |
| `paris` | 0,883 | 0,850 | −0,03 |
| `structural_propagation` | 0,641 | 0,590 | −0,05 |
| `value_overlap` | 0,526 | 0,389 | **−0,14** |

Am stärksten trifft es das wertbasierte Verfahren: exakte Literalwerte, die bei
15 K noch eindeutig identifizieren, kollidieren bei 100 K mit mehreren
Kandidaten.

### 3.3 Seed-Größe

Wie viel Referenz-Alignment ein semi-supervised Verfahren braucht, war bisher
ungeprüft — wir hatten schlicht den Train-Split (20 %) übernommen. F1 des
strukturellen Matchers nach Anteil des genutzten Train-Splits:

| Datensatz | 5 % | 10 % | 25 % | 50 % | 75 % | 100 % |
| --------- | --: | ---: | ---: | ---: | ---: | ----: |
| `EN_FR_15K_V2` | 0,015 | 0,064 | 0,263 | 0,509 | 0,581 | **0,639** |
| `D_Y_15K_V1` | 0,005 | 0,008 | 0,092 | 0,291 | 0,420 | 0,500 |
| `D_W_15K_V1` | 0,009 | 0,019 | 0,087 | 0,332 | 0,425 | 0,496 |
| `EN_FR_15K_V1` | 0,007 | 0,015 | 0,100 | 0,241 | 0,322 | 0,390 |

Der Zusammenhang ist steil und monoton. Bei 5 % des Train-Splits (also 1 % der
Entitäten) ist das Verfahren praktisch wirkungslos; erst ab etwa der Hälfte
wird es brauchbar. Wer solche Verfahren vergleicht, muss die Seed-Größe
mitberichten — sie dominiert das Ergebnis stärker als die meisten
Datensatz-Eigenschaften.

---

### 3.4 Streuung über die Folds

Bis hierhin ist jede Zahl ein Punktschätzer aus Fold 1. Ob ein Unterschied von
+0,24 F1 aussagekräftig ist, hängt davon ab, wie stark die Werte allein durch
die Wahl des Folds schwanken. `scripts/run_folds.py` rechnet deshalb alle
Matcher auf allen fünf 721-Splits — dasselbe Protokoll, das Sun et al. (2020)
für dieselben Datensätze verwenden.

F1 als Mittel ± Standardabweichung über fünf Folds:

| Datensatz | `value_overlap` | `pyjedai_ngram` | `structural_prop.` | `paris` |
| --------- | --------------: | --------------: | -----------------: | ------: |
| `EN_FR_15K_V1` | 0,559 ± 0,002 | 0,444 ± 0,002 | 0,388 ± 0,004 | 0,810 ± 0,001 |
| `EN_FR_15K_V2` | 0,580 ± 0,004 | 0,504 ± 0,002 | 0,625 ± 0,012 | 0,889 ± 0,001 |
| `EN_DE_15K_V1` | 0,613 ± 0,003 | 0,340 ± 0,004 | 0,637 ± 0,004 | 0,898 ± 0,001 |
| `D_W_15K_V1` | 0,392 ± 0,002 | 0,322 ± 0,003 | 0,490 ± 0,013 | 0,747 ± 0,003 |
| `D_Y_15K_V1` | 0,593 ± 0,003 | 0,434 ± 0,001 | 0,498 ± 0,007 | 0,922 ± 0,001 |

**Die Streuung ist durchweg klein:** maximal 0,013, im Median 0,003; die
gesamte Spannweite zwischen bestem und schlechtestem Fold überschreitet nirgends
0,032. Damit ist der Dichte-Effekt aus §3.1 (+0,235 F1) rund das **19-fache der
größten** und das **79-fache der medianen** Fold-Streuung. Er liegt also weit
außerhalb dessen, was durch die Fold-Wahl erklärbar wäre.

Zwei Nebenbeobachtungen:

- Der strukturelle Matcher streut am stärksten (bis 0,013). Das ist plausibel:
  er ist das einzige Verfahren, dessen Eingabe sich mit dem Fold ändert — die
  Seed-Menge ist der Train-Split.
- PARIS streut praktisch nicht (≤ 0,003), obwohl es gar keine Seeds nutzt. Die
  verbleibende Schwankung stammt aus dem wechselnden Test-Split und aus seiner
  eigenen Nicht-Determiniertheit (§6.3).

Nicht enthalten sind die 100K-Varianten: fünf Folds hätten dort die Rechenzeit
vervielfacht, ohne zur Streuungsschätzung etwas beizutragen, was die fünf
kleineren nicht schon zeigen. Figure: `results/figures/fold_variance.png`.

---

## 4. Was erklärt die Matching-Güte?

Spearman-Rangkorrelation über alle 16 OpenEA-Varianten.

**Strukturelles Verfahren — hängt an der Struktur:**

| Metrik | ρ | p |
| ------ | ---: | ---: |
| Relations-Property-Entropie | −0,724 | 0,002 |
| Median-Grad (schwächerer KG) | +0,679 | 0,004 |
| ø Total-Grad | +0,676 | 0,004 |
| Gold-Paare in größter Komponente | +0,624 | 0,010 |
| Entitäten in größter Komponente | +0,609 | 0,012 |

Vier der fünf stärksten Prädiktoren sind Struktur-Metriken, alle mit p < 0,02.

**Wertbasiertes Verfahren — hängt nicht an der Struktur:**

| Metrik | ρ | p |
| ------ | ---: | ---: |
| Gesamtzahl Tripel (Größeneffekt) | −0,697 | 0,003 |
| Property-Überlappung der Schemata | +0,553 | 0,026 |
| Grad-Korrelation der Gold-Paare | +0,503 | 0,047 |
| ø Total-Grad | −0,303 | 0,254 |
| Median-Grad | −0,149 | 0,583 |

**Der Kontrast ist die eigentliche Aussage:** Der mittlere Grad korreliert beim
strukturellen Verfahren mit ρ = +0,68 (p = 0,004), beim wertbasierten mit
ρ = −0,30 (p = 0,25). Dieselbe Datensatz-Eigenschaft ist für das eine Verfahren
der zweitstärkste Prädiktor und für das andere ohne Erklärungswert.

Was wir **nicht** belegen können: dass die Literal-Überlappung der Gold-Paare
das wertbasierte Verfahren treibt. Sie korreliert nur mit ρ = +0,31 (p = 0,24)
und ist damit nicht signifikant. Dominierend ist dort der reine Größeneffekt.

`paris` hat einen dominanten Prädiktor, die Relations-Property-Entropie
(ρ = −0,847, p < 0,001); alle übrigen liegen unter 0,43 und sind nicht
signifikant. Das passt zu seiner durchgängig hohen Precision.

**Diese Zahlen sind deskriptiv, keine Signifikanztests.** Drei Gründe, und wir
nennen sie, bevor jemand danach fragt:

1. **Multiples Testen.** Über alle Matcher und Metriken sind es 48 Tests. Bei
   α = 0,05 wären allein zufällig rund zwei "signifikante" Ergebnisse zu
   erwarten. Bonferroni-korrigiert (α = 0,00104) überlebt **genau einer**:
   `paris` × Relations-Property-Entropie (p = 3,5·10⁻⁵). Mit der weniger
   strengen FDR-Korrektur (Benjamini-Hochberg) überleben fünf:

   | Matcher | Metrik | ρ | p | p_fdr |
   | ------- | ------ | ---: | ---: | ---: |
   | `paris` | Rel.-Property-Entropie | −0,847 | 0,00004 | 0,002 |
   | `structural_propagation` | Rel.-Property-Entropie | −0,724 | 0,0015 | 0,037 |
   | `structural_propagation` | ø Total-Grad | +0,677 | 0,0040 | 0,039 |
   | `structural_propagation` | Median-Grad | +0,679 | 0,0038 | 0,046 |
   | `value_overlap` | Gesamtzahl Tripel | −0,697 | 0,0027 | 0,043 |

   Die Ausgabe enthält `p_bonferroni`, `p_fdr` sowie `survives_bonferroni` und
   `survives_fdr`, damit das nachprüfbar ist.
2. **Abhängige Stichprobe.** Die 16 Varianten sind 4 Quellenpaare × 2 Größen ×
   2 Dichtestufen, keine unabhängigen Ziehungen. Die effektive Stichprobe ist
   kleiner als n = 16.
3. **Konfundierung.** Entropie und Grad sind auf diesen Daten korreliert; die
   Korrelationen trennen die beiden Erklärungen nicht.

Was die Aussage trägt, ist deshalb nicht ein einzelner p-Wert, sondern das
**Vorzeichenmuster über die Familien** — dieselbe Kennzahl positiv für das eine
Verfahren, negativ für das andere, und das über alle vier Strukturmetriken
hinweg — zusammen mit dem kontrollierten Experiment aus §3.1, das ohne
Signifikanztest auskommt.

### 4.1 Gegenprobe: hängen die Aussagen an unseren eigenen Matchern?

Zwei der vier Verfahren sind Eigenimplementierungen und erreichen auf den
Non-Match-Varianten F1-Werte unter 0,5. Die naheliegende Frage ist, ob die
Familien-Kontraste aus §4 überhaupt tragen oder nur das schwache Niveau dieser
Verfahren widerspiegeln. Zwei unabhängige Gegenproben sagen: sie tragen.

**Erstens, intern über PARIS.** PARIS ist ein etabliertes, unstrittig starkes
Verfahren (F1 0,835). Wenn die Richtungen aus §4 echt sind, muss es sie
mitzeigen:

| Metrik | strukturell | **PARIS** | wertbasiert |
| ------ | ----------: | --------: | ----------: |
| ø Total-Grad | +0,68 | **+0,42** | −0,30 |
| Relations-Property-Entropie | −0,72 | **−0,85** | −0,11 |
| Anteil Entitäten in größter Komponente | +0,61 | **+0,26** | −0,32 |
| Gold-Paare in größter Komponente | +0,62 | **+0,28** | −0,34 |

PARIS hat bei allen vier Strukturmetriken dasselbe Vorzeichen wie unser
strukturelles Verfahren; das wertbasierte hat bei drei von vier das
umgekehrte. Der Kontrast hängt also nicht am absoluten Niveau der eigenen
Implementierungen.

**Zweitens, extern über die Literatur.** Sun et al. (2020) evaluieren zwölf
embedding-basierte Verfahren auf denselben Datensätzen und mit demselben
Protokoll (fünf Folds, 20 % Seeds / 10 % Validierung / 70 % Test). Ihre
Befunde decken sich mit unseren:

| Ihre Aussage | unser Befund |
| ------------ | ------------ |
| „most relation-based approaches perform better on the dense datasets than on the sparse ones" | Dichte-Effekt: strukturell +0,24, wertbasiert −0,03 (§3.1) |
| „all the relation-based approaches run better in aligning entities with rich relation triples while their results decline on long-tail entities" | ø Grad korreliert strukturell mit +0,68, wertbasiert mit −0,30 (§4) |
| „all the approaches perform better on the 15K datasets than on the 100K datasets" | Skalen-Effekt, alle Verfahren verlieren (§3.2) |

Das ist keine Bestätigung unserer Zahlen — die Verfahrensklasse ist eine andere
und ihre Ergebnisse liegen auf der v1.1-Fassung der Datensätze, während wir auf
v2.0 mit anonymisierten URIs rechnen. Es ist eine Bestätigung der *Richtungen*,
und zwar aus einer Verfahrensfamilie, die wir selbst nicht abdecken.

---

## 5. Was passiert ohne Bijektivität?

Der zentrale neue Befund. `preprocessing/nonmatch.py` entfernt gezielt
Entitäten aus beiden Graphen, sodass Entitäten ohne Gegenstück entstehen. Bei
`match_ratio = 0.5` behält ein 15 000er Benchmark 7 500 Gold-Paare; beide KGs
haben danach 11 250 Entitäten, davon 3 750 ohne Partner (Non-Match-Quote 33 %).

Die Bewertung zählt Vorhersagen für partnerlose Entitäten als False Positive —
ohne diese Änderung wäre der ganze Umbau wirkungslos geblieben.

| Matcher | F1 bijektiv | F1 mit Non-Matches | Δ | Precision bijektiv | Precision NM | Δ |
| ------- | ----------: | -----------------: | ---: | -----------------: | -----------: | ---: |
| `value_overlap` | 0,531 | 0,472 | −0,06 | 0,661 | 0,500 | −0,16 |
| `pyjedai_ngram` | 0,409 | 0,354 | −0,06 | 0,555 | 0,406 | −0,15 |
| `structural_propagation` | 0,500 | 0,182 | **−0,32** | 0,710 | 0,245 | **−0,47** |
| `paris` | 0,835 | 0,698 | −0,14 | 0,966 | 0,806 | −0,16 |

Drei Aussagen daraus:

1. **Auch PARIS verliert deutlich** — 14 F1-Punkte und 16 Precision-Punkte.
   Die auf OpenEA berichteten Werte sind also systematisch optimistisch, nicht
   nur die unserer eigenen Verfahren.
2. **Das strukturelle Verfahren bricht ein** (−0,32 F1, −0,47 Precision). Es
   ist doppelt betroffen: die entfernten Entitäten nehmen ihre Kanten mit, der
   Graph wird also zusätzlich dünner, und die Seed-Menge halbiert sich.
3. **Die Precision fällt bei allen Verfahren um 14–46 Punkte.** Genau diese
   Fehlerart — eine Vorhersage für etwas, das keinen Partner hat — kann ein
   bijektiver Benchmark prinzipiell nicht messen.

Dass die Varianten wirklich nicht mehr bijektiv sind, ist an den Profiling-
Kennzahlen nachprüfbar — `alignment_coverage` fällt von 1,000 auf 0,667,
`entity_coverage_kg2` ebenso, und `non_match_share_kg1` liegt bei 0,333.

Über alle sechs Datensätze summierte False Positives auf partnerlosen
Entitäten: `value_overlap` 17 707, `structural_propagation` 9 992,
`pyjedai_ngram` 6 693, `paris` 5 691. Die Rangfolge ist eine andere als beim
F1 — PARIS ist hier mit Abstand am zurückhaltendsten, `value_overlap` trotz
gutem F1 am fehleranfälligsten.

Absolute Zahl der False Positives auf partnerlosen Entitäten (Test-Split):

| Datensatz | `value_overlap` | `pyjedai_ngram` | `structural_prop.` | `paris` |
| --------- | --------------: | --------------: | -----------------: | ------: |
| `EN_FR_15K_V1` | 1 612 | 1 691 | 825 | 501 |
| `D_W_15K_V1` | 927 | 851 | 981 | 379 |
| `D_Y_15K_V1` | 602 | 439 | 1 024 | 450 |
| `EN_FR_100K_V1` | 11 440 | — | 5 392 | 3 220 |

---

## 5a. Fehler-Taxonomie: woran genau scheitern die Verfahren?

Die Korrelationsanalyse sagt, *dass* eine Eigenschaft zusammenhängt, nicht
*wodurch*. `reporting/error_taxonomy.py` klassifiziert deshalb jede einzelne
Test-Entität nach der Ursache ihres Fehlers.

**Die Zuordnung ist familienabhängig.** Ein rein struktureller Matcher liest
keine Literale — ihm „fehlende Literal-Überlappung" als Ursache zuzuschreiben
wäre sinnlos; umgekehrt ist ein wertbasierter Matcher nicht davon betroffen, ob
die Gold-Entitäten in derselben Zusammenhangskomponente liegen. Als *blockiert*
gilt daher je Familie ein anderes fehlendes Signal, bei PARIS nur das Fehlen
von beiden.

Eine Unterscheidung, die auf den Non-Match-Varianten wichtig wird: eine
korrekte **Enthaltung** bei einer partnerlosen Entität ist richtig, aber kein
Treffer. Sie zählt als eigene Klasse `true_negative` und nicht als `correct` —
sonst wäre der Anteil dort um rund 26 Prozentpunkte überhöht, weil ein Drittel
der Entitäten keinen Partner hat.

Anteile über die sechs Kern-Datensätze (dort ist `true_negative` per
Konstruktion null, weil jede Entität einen Partner hat):

| Matcher | korrekt | falscher Kandidat | Enthaltung | vom Benchmark blockiert |
| ------- | ------: | ----------------: | ---------: | ----------------------: |
| `paris` | 0,740 | **0,022** | 0,193 | 0,045 |
| `value_overlap` | 0,452 | 0,116 | 0,030 | **0,402** |
| `structural_propagation` | 0,391 | 0,142 | **0,388** | 0,078 |
| `pyjedai_ngram` | 0,335 | 0,178 | 0,098 | 0,390 |

Und der daraus abgeleitete Anteil an allen *Fehlern*, der auf den Benchmark
statt auf das Verfahren zurückgeht:

| Matcher | Fehler durch den Benchmark | Fehler durch das Verfahren |
| ------- | -------------------------: | -------------------------: |
| `value_overlap` | **0,720** | 0,280 |
| `pyjedai_ngram` | 0,573 | 0,427 |
| `paris` | 0,169 | 0,831 |
| `structural_propagation` | 0,123 | **0,877** |

Drei Aussagen, die aus dem F1 allein nicht ablesbar sind:

1. **PARIS wählt fast nie einen falschen Kandidaten** (2,2 %). Wenn es eine
   Vorhersage abgibt, stimmt sie fast immer; seine Fehler sind Enthaltungen.
   Das erklärt die durchgängige Precision von 0,97 besser als jede
   Korrelation.
2. **Die wertbasierten Verfahren sind nahe an ihrer Decke.** 72 % bzw. 57 %
   ihrer Fehler betreffen Gold-Paare, die *keinen einzigen* Literalwert teilen.
   Dort kann kein wertbasiertes Verfahren etwas ausrichten — eine Verbesserung
   der Implementierung würde am Ergebnis wenig ändern.
3. **Beim strukturellen Verfahren ist es umgekehrt.** Nur 12 % seiner Fehler
   sind benchmark-bedingt; die dominierende Klasse ist mit 39 % die
   **Enthaltung**. Sein niedriges F1 kommt also nicht daher, dass es falsch
   liegt, sondern daher, dass es zu vorsichtig ist. Das ist eine direkte Folge
   des Margin-Schwellenwerts und wäre der nächste Ansatzpunkt.

Punkt 3 ist auch die Antwort auf den naheliegenden Einwand, unsere eigenen
Verfahren seien für eine Analyse zu schwach: der strukturelle Matcher ist nicht
überwiegend *falsch*, er ist überwiegend *still*.

Auf den Non-Match-Varianten kommen zwei Klassen dazu: `false_on_unmatched` —
eine Vorhersage für eine Entität, die korrekt keinen Partner hat — mit 12 %
(PARIS) bis 17 % (`value_overlap`) aller Test-Entitäten, und `true_negative`,
die korrekte Enthaltung, mit 16 % bis 27 %. PARIS erreicht dort mit 26,8 % den
höchsten True-Negative-Anteil: es erkennt am zuverlässigsten, wann es *keinen*
Partner gibt. Beides ist auf bijektiven Benchmarks prinzipiell nicht messbar.

Ausgabe: `error_taxonomy.csv`, `error_solvability.csv`, `error_examples.csv`
(klassifizierte Einzelfälle) und `figures/error_taxonomy.png`.

---

## 6. Skalierbarkeit

Pandas und PySpark rechnen die Kernmetriken unabhängig voneinander; ein
metrikweiser Vergleich über alle sechs Datensätze ergibt **174 von 174
identischen Kennzahlen** (maximale Abweichung 0,0).

Von 15 K auf 100 K (6,7-fache Datenmenge) wächst die Pandas-Laufzeit um
Faktor 6,3, die Spark-Laufzeit nur um 1,9 — der Overhead ist konstant, die
Rechnung skaliert.

Die rdflib-Gegenprobe liefert identische Grad-Verteilung und Entitätsmenge,
braucht aber beim 100K-Datensatz Faktor 9,5 der Ladezeit (21,4 s gegen 2,3 s)
und das 2,6-fache an Speicher.

Der komplette Kernlauf (6 Datensätze × 11 Metriken × 4 Matcher) dauert rund
12 Minuten auf einem Laptop mit 8 GB RAM; der Non-Match-Lauf 7 Minuten.

---

## 7. Grenzen

| Einschränkung | Auswirkung |
| ------------- | ---------- |
| Nur OpenEA als Quelle | Aussagen gelten für diese Benchmark-Familie |
| 16 Varianten, aber nur 4 unabhängige Quellenpaare | effektive Stichprobe der Korrelationen kleiner als n = 16 |
| Nur die 15K-Datensätze über fünf Folds | für die 100K-Varianten liegt weiterhin nur Fold 1 vor (Rechenzeit) |
| Zwei der vier Verfahren sind Eigenimplementierungen | absolute Niveaus unter dem Stand der Technik; die Familien-Kontraste sind davon nicht betroffen |
| Kein embedding-basiertes Verfahren | die für OpenEA typische Verfahrensklasse fehlt; die Richtungen unserer Befunde werden aber von Sun et al. (2020) für genau diese Klasse bestätigt (§4.1) |
| `pyjedai_ngram` nicht auf 100K und nicht im erweiterten Lauf | Laufzeit (expliziter Kandidatengraph); deckt 5 der 6 Kern-Datensätze ab |
| Non-Match-Varianten mit einer festen Quote (33 %) | der Verlauf über verschiedene Quoten ist nicht vermessen |

### Naheliegende Fortsetzung

1. Ein embedding-basiertes Verfahren einbinden. Die publizierten F1-Werte aus
   Sun et al. (2020) direkt in unsere Korrelation zu übernehmen wäre der
   billigere Weg, aber methodisch angreifbar: ihre Ergebnisse liegen auf der
   v1.1-Fassung der Datensätze, wir rechnen auf v2.0 mit anonymisierten URIs —
   und genau dieser Unterschied betrifft attributnutzende Verfahren. Wir nutzen
   die Arbeit deshalb als qualitative Bestätigung der Richtungen (§4.1), nicht
   als Datenpunkte.
3. Die Non-Match-Quote variieren (10 %, 33 %, 50 %, 75 %) statt nur einen Punkt
   zu messen.
4. Den Schwellenwert des strukturellen Verfahrens senken: die Fehler-Taxonomie
   (§5a) zeigt, dass dort 39 % der Test-Entitäten auf Enthaltung entfallen und
   nur 12 % der Fehler benchmark-bedingt sind — der Spielraum liegt also im
   Verfahren, nicht in den Daten.

---

## 8. Zusammenfassung

1. Verdopplung der Graphdichte bei identischer Entitätsmenge verbessert
   strukturelles Matching um 0,24 F1 und wertbasiertes um null — das ist rund
   das 19-fache der grössten über fünf Folds gemessenen Streuung.
2. Wert- und strukturbasierte Verfahren hängen an unterschiedlichen
   Eigenschaften: der mittlere Grad erklärt das strukturelle Verfahren
   (ρ = +0,68) und das wertbasierte nicht (ρ = −0,30, nicht signifikant).
3. Die Seed-Größe dominiert das Ergebnis semi-supervised Verfahren stärker als
   die meisten Datensatz-Eigenschaften und wird selten mitberichtet.
4. Sobald Entitäten ohne Gegenstück existieren, verlieren **alle** Verfahren
   14–46 Precision-Punkte — auch PARIS. Bijektive Benchmarks können diese
   Fehlerart prinzipiell nicht messen.
5. OpenEA v2.0 enthält praktisch keine Typ-Information, und die Dateien sind
   trotz des Namens kein RDF-Serialisierungsformat.
6. Die Fehler-Taxonomie trennt benchmark- von verfahrensbedingten Fehlern: die
   wertbasierten Verfahren sind mit 72 % unlösbarer Fehler nahe an ihrer Decke,
   das strukturelle Verfahren mit 12 % weit davon entfernt — sein niedriges F1
   kommt aus Enthaltung, nicht aus Fehlern.
7. Die Kernmetriken liefern auf Pandas und PySpark bitgleiche Ergebnisse
   (174/174), und die Fold-Streuung liegt bei maximal 0,013 F1.
