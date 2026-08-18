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
| F5: Was ändert sich, wenn der Benchmark realistischer wird? | §5 |
| F6: Skaliert die Berechnung über den Hauptspeicher hinaus? | §7 |

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
0,97–1,21. Es ändert sich also fast ausschliesslich die Struktur.

Auf dem Kernlauf, `EN_FR_15K` V1 gegen V2, mit den überarbeiteten Matchern:

| Matcher | V1 sparse | V2 dense | Δ |
| ------- | --------: | -------: | ---: |
| `value_overlap` | 0,560 | 0,584 | +0,02 |
| `pyjedai_ngram` | 0,447 | 0,504 | +0,06 |
| `structural_propagation` | 0,390 | 0,639 | **+0,25** |
| `paris` | 0,809 | 0,892 | +0,08 |

Verdopplung der Graphdichte verbessert das strukturelle Verfahren um ein
Vielfaches dessen, was die wertbasierten gewinnen. Das ist keine Korrelation,
sondern ein Experiment mit genau einer veränderten Variable.

Über alle vier Quellenpaare und beide Größen gemittelt (n = 8 Paare) ergab
derselbe Vergleich mit der vorherigen Matcher-Generation +0,28 für das
strukturelle und −0,02 für das wertbasierte Verfahren — die Richtung und die
Größenordnung sind also stabil. Die Neuberechnung dieses Mittels mit den
überarbeiteten Matchern steht noch aus
(`config/datasets_extended.yaml`).

### 3.2 Skalen-Effekt

15 K → 100 K Entitäten, der Kandidatenraum wächst um Faktor 44
(2,25·10⁸ → 10¹⁰). Alle Verfahren verlieren; am stärksten trifft es die
wertbasierten, weil exakte Werte, die bei 15 K noch eindeutig identifizieren,
bei 100 K mit mehreren Kandidaten kollidieren.

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

## 4. Was erklärt die Matching-Güte?

Spearman-Rangkorrelation über alle 16 OpenEA-Varianten. **Diese Werte stammen
aus dem Lauf mit der vorherigen Matcher-Generation**; die Neuberechnung mit den
überarbeiteten Matchern steht aus. Die Aussage betrifft die Verfahrensfamilien,
nicht die konkreten Implementierungen, und die Familienzuordnung hat sich nicht
geändert.

**Strukturelles Verfahren — reagiert auf Struktur:**

| Metrik | ρ | p |
| ------ | ---: | ---: |
| Relations-Property-Entropie | −0,738 | 0,001 |
| ø Total-Grad | +0,703 | 0,002 |
| Median-Grad (schwächerer KG) | +0,660 | 0,005 |
| Gold-Paare in größter Komponente | +0,656 | 0,006 |

**Wertbasiertes Verfahren — reagiert auf Literale, nicht auf Struktur:**

| Metrik | ρ | p |
| ------ | ---: | ---: |
| Literal-Jaccard der Gold-Paare | +0,612 | 0,012 |
| Gesamtzahl Tripel (Größeneffekt) | −0,603 | 0,013 |
| Grad-Korrelation der Gold-Paare | +0,497 | 0,050 |

Vier der fünf stärksten Prädiktoren des strukturellen Verfahrens sind
Struktur-Metriken; beim wertbasierten schafft es keine Grad-Metrik in die
Spitzengruppe.

`paris` hat einen dominanten Prädiktor, die Relations-Property-Entropie
(ρ = −0,871, p < 0,001); alles andere liegt unter 0,45 und ist nicht
signifikant. Das passt zu seiner durchgängig hohen Precision.

**Einschränkung.** Entropie und Grad sind auf diesen Daten korreliert, und die
16 Varianten sind keine unabhängigen Stichproben (4 Quellenpaare × 2 Größen ×
2 Dichten). Die kontrollierten Vergleiche aus §3 sind das stärkere Argument.

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
| `value_overlap` | 0,531 | 0,473 | −0,06 | 0,661 | 0,504 | −0,16 |
| `pyjedai_ngram` | 0,409 | 0,358 | −0,05 | 0,555 | 0,412 | −0,14 |
| `structural_propagation` | 0,500 | 0,187 | **−0,31** | 0,710 | 0,251 | **−0,46** |
| `paris` | 0,835 | 0,697 | −0,14 | 0,967 | 0,808 | −0,16 |

Drei Aussagen daraus:

1. **Auch PARIS verliert deutlich** — 14 F1-Punkte und 16 Precision-Punkte.
   Die auf OpenEA berichteten Werte sind also systematisch optimistisch, nicht
   nur die unserer eigenen Verfahren.
2. **Das strukturelle Verfahren bricht ein** (−0,31 F1, −0,46 Precision). Es
   ist doppelt betroffen: die entfernten Entitäten nehmen ihre Kanten mit, der
   Graph wird also zusätzlich dünner, und die Seed-Menge halbiert sich.
3. **Die Precision fällt bei allen Verfahren um 14–46 Punkte.** Genau diese
   Fehlerart — eine Vorhersage für etwas, das keinen Partner hat — kann ein
   bijektiver Benchmark prinzipiell nicht messen.

Absolute Zahl der False Positives auf partnerlosen Entitäten (Test-Split):

| Datensatz | `value_overlap` | `pyjedai_ngram` | `structural_prop.` | `paris` |
| --------- | --------------: | --------------: | -----------------: | ------: |
| `EN_FR_15K_V1` | 1 612 | 1 691 | 825 | 501 |
| `D_W_15K_V1` | 927 | 851 | 981 | 379 |
| `D_Y_15K_V1` | 602 | 439 | 1 024 | 450 |
| `EN_FR_100K_V1` | 11 440 | — | 5 392 | 3 220 |

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
| Nur ein Fold ausgewertet | Streuung über die fünf 721-Folds nicht quantifiziert |
| Korrelationen (§4) und das gemittelte Dichte-Experiment noch aus dem Lauf mit der vorherigen Matcher-Generation | Richtung bestätigt sich im Kernlauf (§3.1), das Mittel über 8 Paare ist neu zu rechnen |
| Zwei der vier Verfahren sind Eigenimplementierungen | absolute Niveaus unter dem Stand der Technik; die Familien-Kontraste sind davon nicht betroffen |
| Kein embedding-basiertes Verfahren | die für OpenEA typische Verfahrensklasse fehlt |
| `pyjedai_ngram` nicht auf 100K | Laufzeit; in der Auswertung als fehlender Wert ausgewiesen |
| Non-Match-Varianten mit einer festen Quote (33 %) | der Verlauf über verschiedene Quoten ist nicht vermessen |

### Naheliegende Fortsetzung

1. Alle fünf Folds rechnen und Konfidenzintervalle angeben.
2. Ein embedding-basiertes Verfahren einbinden oder die publizierten F1-Werte
   aus Sun et al. (2020) als Literaturwerte in die Korrelation aufnehmen.
3. Die Non-Match-Quote variieren (10 %, 33 %, 50 %, 75 %) statt nur einen Punkt
   zu messen.

---

## 8. Zusammenfassung

1. Verdopplung der Graphdichte bei identischer Entitätsmenge verbessert
   strukturelles Matching um 0,28 F1 und wertbasiertes um null.
2. Wert- und strukturbasierte Verfahren korrelieren nachweislich mit
   unterschiedlichen Datensatz-Eigenschaften.
3. Die Seed-Größe dominiert das Ergebnis semi-supervised Verfahren stärker als
   die meisten Datensatz-Eigenschaften und wird selten mitberichtet.
4. Sobald Entitäten ohne Gegenstück existieren, verlieren **alle** Verfahren
   14–46 Precision-Punkte — auch PARIS. Bijektive Benchmarks können diese
   Fehlerart prinzipiell nicht messen.
5. OpenEA v2.0 enthält praktisch keine Typ-Information, und die Dateien sind
   trotz des Namens kein RDF-Serialisierungsformat.
6. Die Kernmetriken liefern auf Pandas und PySpark bitgleiche Ergebnisse
   (174/174).
