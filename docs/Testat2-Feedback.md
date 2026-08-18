# Feedback aus Testat 2 und seine Umsetzung

Testat 2 fand Mitte August 2026 statt. Das Software-Engineering, die
Dokumentation und das Evaluierungs-Skelett wurden positiv bewertet
("von der Methodologie super", "rein von der Substanz supergut"). Die Kritik
betraf durchgehend **fachliche und methodische Entscheidungen**, nicht die
Umsetzung: was das Programm tun sollte, hat es getan — aber was es tun sollte,
war an mehreren Stellen zu wenig.

Diese Seite hält fest, was bemängelt wurde und wie es behoben ist.

## Übersicht

| # | Kritikpunkt | Priorität | Status |
| - | ----------- | --------- | ------ |
| 1 | `min_score = 0.0`: jeder Kandidat wird als Match gewertet | kritisch | ✅ behoben |
| 2 | Datensätze rein bijektiv, keine Entitäten ohne Gegenstück | kritisch | ✅ behoben |
| 3 | Structural Matcher zu simpel: ungerichtet, ungewichtet, ohne Relationstypen | kritisch | ✅ behoben |
| 4 | Eigenimplementierung statt Standard-Library für Record Linkage | kritisch | ✅ behoben |
| 5 | Unsauberes RDF-Handling, `write_ntriples` statt rdflib | hoch | ✅ behoben |
| 6 | Falsche Matcher-Zählung ("fünf Matcher", "vier eigene") | hoch | ✅ korrigiert |
| 7 | Seed-Größe nie als Hyperparameter betrachtet | hoch | ✅ analysiert |
| 8 | Einseitige Commit-Historie | mittel | offen (organisatorisch) |
| 9 | Keine Integration ins Framework des Lehrstuhls | optional | nicht umgesetzt |

---

## 1. Schwellenwerte

> "Ihr habt sozusagen so einen Min-Score. Den habt ihr aber immer auf 0,0. Das
> heißt, ihr wertet immer alles als Matches. […] Aber so vermeidet man halt
> einfach False Positives."

**Behoben.** Jeder Matcher hat jetzt einen echten Schwellenwert; darunter gibt
er *keine* Vorhersage ab. Die Werte sind nicht gesetzt, sondern auf dem
Valid-Split abgetastet (`scripts/tune_thresholds.py`, Raster 0,0–0,9):

| Matcher | Schwellenwert | greift an |
| ------- | ------------: | --------- |
| `value_overlap` | 0,4 | Kosinus-Ähnlichkeit |
| `pyjedai_ngram` | 0,2 | Cluster-Ähnlichkeit |
| `structural_propagation` | 0,1 | relativer Abstand zum Zweitbesten |

Beim strukturellen Matcher fiel dabei ein Fehler im eigenen Entwurf auf: dessen
Scores sind zeilenweise normiert, der Bestwert ist also immer exakt 1,0 und ein
Schwellenwert auf den Score wirkungslos — im ersten Sweep verwarf jeder Wert
entweder nichts oder alles. Konfidenzmass ist dort jetzt (top1 − top2) / top1.

Die Bewertung wurde ergänzt um `abstain_rate` (Anteil Entitäten ohne
Vorhersage) und `n_false_on_unmatched`.

## 2. Non-Matches im Benchmark

> "Ihr müsst einfach aus A und B jeweils die Entities entfernen so, dass halt
> diese Non-Matches entstehen. […] Das ist ein kurzer Preprocessing-Schritt."

**Behoben** in `preprocessing/nonmatch.py`, umgesetzt genau wie beschrieben:
Aus dem Referenz-Alignment werden drei Gruppen gebildet — `keep` (beide Seiten
bleiben), `drop_left` (KG1-Seite entfernt, KG2-Seite wird partnerlos) und
`drop_right` (umgekehrt). Alle Tripel entfernter Entitäten verschwinden mit.

Bei `match_ratio = 0.5` behält ein 15 000er Benchmark 7 500 Gold-Paare; beide
KGs haben danach 11 250 Entitäten, davon 3 750 ohne Partner (33 %).
Konfiguration: `config/datasets_nonmatch.yaml`.

**Wichtig war eine zweite Änderung**, ohne die der Umbau wirkungslos geblieben
wäre: Die Bewertung ignorierte bisher Vorhersagen zu Entitäten ohne Gold-Paar.
Jetzt zählen sie als False Positive. Partnerlose Entitäten bleiben als
Alignment-Zeile mit leerem `e2` im Auswertungsumfang.

Ergebnis (Mittel über die sechs Datensätze):

| Matcher | F1 bijektiv | F1 mit Non-Matches | Precision bijektiv | Precision NM |
| ------- | ----------: | -----------------: | -----------------: | -----------: |
| `value_overlap` | 0,531 | 0,473 | 0,661 | 0,504 |
| `pyjedai_ngram` | 0,409 | 0,358 | 0,555 | 0,412 |
| `structural_propagation` | 0,500 | 0,187 | 0,710 | 0,251 |
| `paris` | 0,835 | 0,697 | 0,966 | 0,809 |

Auch PARIS verliert 14 F1- und 16 Precision-Punkte. Die auf OpenEA berichteten
Werte sind also generell optimistisch, nicht nur unsere.

## 3. Structural Matcher

> "Der ist halt einfach zu basic. Weil ihr komplett Relation Type außer Acht
> lasst […] Das ist überhaupt nicht mehr gerichtet, diese Information. […] Man
> hätte die Relationen anders gewichten müssen."

**Behoben**, alle drei Punkte:

- **Kantenrichtung** bleibt erhalten; ein- und ausgehende Nachbarschaft sind
  getrennte Merkmale.
- **Relationstypen** werden genutzt. Das war der schwierige Teil: Relationstypen
  sind zwischen zwei KGs nicht vergleichbar, bei `D_W` und `D_Y` ist die
  Property-Überlappung exakt null. Die Relationen werden deshalb zuerst *selbst
  aligniert*, allein aus der Seed-Evidenz — sind (a, b) und (x, y) Seed-Paare
  und gilt `a --r1--> x` in KG1 sowie `b --r2--> y` in KG2, ist das ein Beleg
  für r1 ≙ r2.
- **Gewichtung** über die Alignment-Evidenz (Dice) der Relationspaare.

Das Relations-Alignment funktioniert ohne gemeinsames Vokabular; auf `D_W`
findet es u. a. `party → P102`, `ideology → P1142`, `series → P179`.

Zusätzlich prüfen wir die **Gegenrichtung**, weil zwei KGs dieselbe Beziehung
oft invers modellieren. Bei `D_Y` sind **14 von 25 alignierten Relationspaaren
invertiert** — YAGO orientiert Relationen systematisch anders als DBpedia. Ohne
diesen Fall wäre die neu gewonnene Richtungsinformation dort genau falsch herum
gewesen; F1 lag mit 0,14 unter dem alten Wert und stieg mit 0,50 klar darüber.

| Datensatz | F1 vorher | F1 jetzt | Precision vorher | Precision jetzt |
| --------- | --------: | -------: | ---------------: | --------------: |
| `EN_FR_15K_V1` | 0,203 | 0,390 | 0,209 | 0,639 |
| `EN_FR_15K_V2` | 0,337 | 0,639 | 0,337 | 0,788 |
| `EN_DE_15K_V1` | 0,514 | 0,638 | 0,524 | 0,853 |
| `D_W_15K_V1` | 0,307 | 0,496 | 0,319 | 0,732 |
| `D_Y_15K_V1` | 0,330 | 0,500 | 0,349 | 0,643 |
| `EN_FR_100K_V1` | 0,163 | 0,338 | 0,167 | 0,603 |
| **Mittel** | **0,309** | **0,500** | **0,317** | **0,710** |

Die geforderte 0,5-Marke ist im Mittel erreicht, die Precision hat sich mehr
als verdoppelt.

## 4. Standard-Library statt Eigenbau

> "Ihr habt halt die Matcher selber implementieren lassen […] die so viele
> Probleme haben, die eigentlich in existierenden Libraries — zum Beispiel
> Python Record Linkage oder pyjedai — einfach schon für euch gemacht sind."

**Behoben.** `matching/record_linkage.py` bindet **pyJedAI** mit dem
Standard-Workflow für Clean-Clean Entity Resolution ein:

    StandardBlocking → BlockPurging → BlockFiltering → WeightedEdgePruning
    → EntityMatching (Zeichen-3-Gramme, Kosinus) → UniqueMappingClustering

Damit kommen Blocking, Kandidaten-Pruning und eine kalibrierte Zuordnungsstufe
aus der Bibliothek statt aus Eigenbau. Auch der Hinweis auf n-Gramme ist damit
umgesetzt.

**Warum pyJedAI und nicht `recordlinkage`?** Genannt waren beide.
`recordlinkage` erwartet, dass man den Blocking-Schlüssel selbst festlegt — bei
OpenEA v2.0 gibt es dafür kein naheliegendes Feld, weil die Entitäten weder
Labels noch sprechende URIs haben, sondern nur eine Menge heterogener
Literalwerte. Genau die Stufe, die uns gefehlt hat, hätten wir dort also wieder
selbst bauen müssen. pyJedAI bringt Blocking und Block-Bereinigung mit. Der
Modulname `record_linkage.py` bezeichnet das Problem, nicht die Bibliothek.

Ein Nebenergebnis, das wir offen berichten: die Bibliothek schlägt unseren
einfachen `value_overlap` **nicht** (F1 0,409 vs. 0,531). Der Grund liegt in
den Daten — die Literale in OpenEA v2.0 sind überwiegend Datumsangaben und
Zahlen, wo exakte Wertgleichheit schärfer trennt als Zeichen-n-Gramme
(`1990-01-01` und `1990-01-07` teilen fast alle 3-Gramme). Der Gewinn liegt
hier nicht in der besseren Zahl, sondern in der geprüften Implementierung.

## 5. RDF-Handling

> "Das habt ihr das RDF so fuzzy geparst. Und das ist nicht gut. […] Ihr hättet
> doch dann direkt rdflib benutzen können, oder? […] `write_n_triples` ist
> einfach die falsche Funktion, das macht man eigentlich über dieses
> Graph-Objekt."

**Behoben.** `write_ntriples` ist ersetzt: `rdf_export.py` baut jetzt einen
echten `rdflib.Graph` und lässt ihn per `serialize()` schreiben; das Gegenstück
`parse_ntriples` liest ihn wieder ein, und der Round-Trip ist per Test
abgesichert. In `utils/literals.py` ersetzt `rdflib.util.from_n3` die eigenen
regulären Ausdrücke.

Zur Annahme, OpenEA sei flat Turtle und man könne `g.parse(pfad)` direkt
aufrufen: das haben wir geprüft (`scripts/check_openea_rdf.py`) — es trifft
nicht zu.

| Prüfung | Ergebnis |
| ------- | -------- |
| `g.parse(datei, format="nt")` | scheitert auf **allen** Dateien (`ParserError`) |
| `g.parse(datei, format="turtle")` | scheitert auf **allen** Dateien (`BadSyntax`) |
| Objektwerte, die kein gültiger RDF-Term sind | 0,7 % bis 52 % je Datei |

Die Dateien sind tab-separiert, URIs stehen ohne spitze Klammern, die
abschliessenden Punkte fehlen, und YAGO-Terme wie `YAGO/E473489` sind gar keine
IRIs. Wir arbeiten deshalb spaltenweise, überlassen aber Termkonstruktion und
Serialisierung rdflib.

Nebenbefund aus rdflibs Validierung: die Daten enthalten ill-typed Literale wie
`"3.6e"^^xsd:double` und das Datum `"-0070-10-15"`.

## 6. Matcher-Zählung

> "Du hast ja gesagt, es sind fünf Matcher, aber es sind ja keine fünf Matcher.
> […] Der hybride Ansatz ist PARIS."

**Korrigiert.** Der eigene Hybrid-Matcher ist entfernt — PARIS alignt bereits
Entitäten, Relationen und Klassen gemeinsam, eine eigene Linearkombination wäre
kein eigenständiger Ansatz. Der TF-IDF-Matcher ist ebenfalls entfernt.

Die Darstellung lautet jetzt durchgehend: **zwei eigene Verfahren
(`value_overlap`, `structural_propagation`), eine Standard-Bibliothek
(`pyjedai_ngram`), ein Referenzsystem (`paris`)**.

## 7. Seed-Größe

> "Wenn man jetzt einen Seed hat, ist die Frage auch immer: Wie groß muss der
> Seed sein, damit es funktioniert?"

**Analysiert** in `scripts/analyze_seed_size.py`. F1 des strukturellen Matchers
nach Anteil des genutzten Train-Splits:

| Datensatz | 5 % | 10 % | 25 % | 50 % | 75 % | 100 % |
| --------- | --: | ---: | ---: | ---: | ---: | ----: |
| `EN_FR_15K_V2` | 0,015 | 0,064 | 0,263 | 0,509 | 0,581 | 0,639 |
| `D_Y_15K_V1` | 0,005 | 0,008 | 0,092 | 0,291 | 0,420 | 0,500 |
| `D_W_15K_V1` | 0,009 | 0,019 | 0,087 | 0,332 | 0,425 | 0,496 |
| `EN_FR_15K_V1` | 0,007 | 0,015 | 0,100 | 0,241 | 0,322 | 0,390 |

Bei 5 % des Train-Splits (1 % der Entitäten) ist das Verfahren praktisch
wirkungslos; brauchbar wird es erst ab etwa der Hälfte. Die Seed-Größe
dominiert das Ergebnis stärker als die meisten Datensatz-Eigenschaften.

## 8. Offene Punkte

**Commit-Historie.** Wir arbeiten an einem Rechner, daher laufen die Commits
über ein Konto. Für den weiteren Verlauf achten wir auf ausgeglichene Commits.

**Framework-Integration.** Die Einbettung als Unterordner in das Framework des
Lehrstuhls ist nicht umgesetzt; sie wurde als notenneutral eingestuft.

**Weiterhin offen aus Testat 1.** Kein embedding-basiertes Verfahren aus dem
OpenEA-Paper, und nur ein Fold ausgewertet.
