# Feedback aus Testat 1 und seine Umsetzung

Testat 1 fand Anfang Juni 2026 statt. Der Entwurf wurde inhaltlich angenommen
("saubere Arbeit", "die Datensätze sind super", "die Metriken sind genug"), mit
mehreren konkreten Auflagen für die Implementierungsphase.

## Übersicht: unsere Gesprächsnotizen abgehakt

| # | Auflage aus dem Gespräch | Status | Wo |
| - | ------------------------ | ------ | -- |
| 0 | **Forschungsfrage fehlt**: welche strukturellen Eigenschaften führen zu Matcher-Performance, und warum schauen wir uns das an? | ✅ umgesetzt | README, `docs/Ergebnisse.md` (Kopf) |
| 1 | **Entity Matching muss im Vordergrund stehen — die Matcher fehlen**; existierende Repositories nutzen, ggf. Format konvertieren | ✅ umgesetzt | §1 unten |
| 2 | **PARIS als Matcher nutzen** | ✅ umgesetzt | `matching/paris.py` |
| 3 | **Pandas *oder* PySpark — nicht beides**; Pandas reicht auch für 100 K | ⚠️ **bewusst abgewichen** | §3 unten |
| 4 | **Nur rdflib probieren**, statt Pandas/PySpark | ⚠️ **geprüft und verworfen, mit Messung** | §4 unten |
| 5 | **Nur OpenEA**, OAEI (7. Datensatz) weglassen | ✅ umgesetzt | `docs/Datensaetze.md` §1 |
| 6 | **rdflib-API reicht für die meisten Sachen** | ⚠️ teilweise — siehe §4 | `loaders/rdf_export.py` |
| 7 | **Pipeline zuerst bauen**, dann nach und nach Metriken ergänzen | ✅ umgesetzt | §7 unten |
| 8 | Metriken gruppieren und **tabellarisch** statt als Fließtext | ✅ umgesetzt | `docs/Metriken-Katalog.md` |
| 9 | **Am Ende zählt der Unterschied auf den Matchern**, nicht nur strukturelle Unterschiede der Datensätze | ✅ umgesetzt | `docs/Ergebnisse.md` §3 |
| 10 | Auf die **Präsentation** hinarbeiten | ⚠️ Drehbuch fertig, **Folien fehlen** | nicht im Repository |
| 11 | *(Matcher aus dem OpenEA-Paper)* | ❌ **nicht umgesetzt** | §5 unten |

---

## 0. Forschungsfrage (war der erste Kritikpunkt)

> "Da fehlt jetzt sozusagen leider so ein bisschen … am Ende wollen wir das auch
> mal testen, wie gut das matcht auf verschiedenen Strukturen, damit wir so
> Korrelationen ziehen können."

Der Entwurf beschrieb, *was* berechnet wird, aber nicht, *welche Frage* damit
beantwortet werden soll. Jetzt explizit formuliert:

> **Welche strukturellen und semantischen Eigenschaften von
> Entity-Alignment-Benchmarks bestimmen, wie gut ein Matching-Verfahren auf
> ihnen abschneidet — und hängt das davon ab, welche Art von Verfahren man
> einsetzt?**

Und die Begründung, warum man das anschaut: Wer auf einem einzelnen Benchmark
evaluiert, misst die Eigenschaften dieses Benchmarks mit. Unser Beleg dafür:
derselbe strukturelle Matcher erreicht auf `D_Y` F1 0,65 und auf `EN_FR` 0,26 —
beim textuellen Matcher ist es genau umgekehrt. Zwei Benchmarks, zwei
gegensätzliche Aussagen darüber, welches Verfahren besser ist.

## 1. Matching-Ansätze — Hauptkritik

> "Es fehlen so ein bisschen die Matcher. […] Qualitätsbewertung ist halt nicht
> nur dieses Profiling. Das Profiling ist halt nur der erste Schritt, um
> überhaupt irgendwelche Werte zu haben, wo man dann sehen kann: aha, der
> Datensatz war unterschiedlich und deswegen ist das Matching-Ergebnis
> schlechter oder besser."

**Umgesetzt.** Fünf Matcher, bewusst über die Signaltypen verteilt, damit die
Korrelationen überhaupt unterscheidbar werden:

| Matcher | Familie | Signal | Herkunft |
| ------- | ------- | ------ | -------- |
| `literal_tfidf` | textuell | TF-IDF über Literal-Tokens | eigene Implementierung |
| `value_overlap` | textuell | Überlappung ganzer Literalwerte | eigene Implementierung |
| `structural_propagation` | strukturell | Nachbarschaft über Seeds, mit Bootstrapping | eigene Implementierung |
| `hybrid` | hybrid | Kombination beider | eigene Implementierung |
| `paris` | holistisch | Struktur + Literale | **PARIS v0.3, dig-team — externes Tool** |

Zum Hinweis "existierende Python-Repositories nehmen, das muss man nicht selber
bauen": Bei PARIS haben wir genau das getan. Die vier anderen sind eigene, sehr
kompakte Implementierungen — das war schneller, als fremde Repositories auf das
OpenEA-Format umzubiegen, und wir brauchten gezielt Verfahren, die *je genau
einen* Signaltyp nutzen. Genau diese Trennschärfe macht die Familien-Analyse
möglich. Für die absolute Leistungsfähigkeit steht PARIS als etabliertes
Verfahren daneben.

## 2. PARIS

> "PARIS ist einfach nur eine Jar-Datei und das hat keine Python-API. Du
> brauchst zwei Input-Files im RDF-N-Triple-Format und dann gibt das dir einen
> Ordner zurück und in dem Ordner sind so Iterations-Ordner."

**Umgesetzt, genau so.** `matching/paris.py`: N-Triples-Export über rdflib,
Subprozess-Aufruf, Einlesen der letzten nicht-leeren `*_eqv.tsv`. Zwei
Stolperstellen, die dabei auftraten (PARIS kürzt URIs mit eigenen Präfixen; die
letzte Iterationsdatei ist leer), sind in `docs/Architektur.md` §10
dokumentiert und durch Tests abgesichert.

Ergebnis: F1 0,74–0,98 bei Precision 0,93–0,99 — der mit Abstand beste Matcher.

## 3. Pandas oder PySpark — hier sind wir abgewichen

> "Es gibt keinen Sinn, beides zu machen. […] Ihr könnt das jetzt auch nur mit
> Pandas machen." — aber auch: *"Die Idee war, PySpark zu benutzen, weil es
> skaliert, weil es ja eigentlich das Big Data Praktikum ist. Aber es ist nicht
> schlimm."*

**Wir haben beides gebaut.** Das ist eine bewusste Abweichung, und sie muss in
der Präsentation begründet werden können.

*Was kritisiert wurde:* die **Reihenfolge** im Zeitplan — erst alles in Pandas,
Wochen später alles nochmal in Spark. Das wäre doppelte Arbeit ohne Erkenntnis.

*Was wir gemacht haben:* Pandas ist der Standardpfad für alle elf
Metrik-Gruppen. Spark existiert **nur für die drei Kernmetrik-Gruppen**
(~300 Zeilen), wurde in einem Zug mitgebaut statt als eigene Phase, und liefert
etwas, das die Pandas-Version allein nicht kann: einen **Äquivalenznachweis**.
`scripts/run_backend_benchmark.py` rechnet beide Wege und vergleicht
metrikweise — 174 von 174 Kennzahlen exakt identisch.

*Warum wir das für vertretbar halten:* Die offizielle Aufgabenstellung verlangt
wörtlich "implement the conceptualized framework in Python (PySpark)" und ein
modulares Design, in dem "different processing frameworks (e.g. Pandas or
PySpark) can be easily integrated and **compared**". Ohne einen zweiten Pfad
gibt es nichts zu vergleichen.

*Falls der Betreuer das anders sieht:* Der Spark-Teil ist vollständig
gekapselt (`backends/spark.py`, `scripts/run_backend_benchmark.py`, ein
Config-Block). Er lässt sich ohne jede Änderung am übrigen Framework entfernen.

## 4. Nur rdflib statt Pandas — geprüft und mit Zahlen verworfen

> "Ihr könnt sozusagen versuchen, Pandas wegzulassen, PySpark wegzulassen, nur
> rdflib zu benutzen. […] Die rdflib-API ist uralt, das ist so maintained, das
> ist auch eine ganz einfache API."

Diesen Vorschlag haben wir nicht einfach übergangen, sondern gemessen:
`scripts/benchmark_rdflib.py` lädt denselben KG einmal in einen rdflib-Graph
und einmal in unsere Pandas-Repräsentation und rechnet in beiden
Triple-Count und Grad-Verteilung.

| Datensatz | Backend | Laden | Metriken | Peak-RSS |
| --------- | ------- | ----: | -------: | -------: |
| `EN_FR_15K_V1` (KG1) | Pandas | 0,29 s | 0,011 s | 129 MB |
| | rdflib | 1,66 s | 0,174 s | 239 MB |
| `EN_FR_100K_V1` (KG1) | Pandas | 2,26 s | 0,084 s | 338 MB |
| | rdflib | 21,4 s | 1,49 s | 891 MB |

**Ergebnis: rdflib rechnet dasselbe, aber deutlich teurer.** Grad-Verteilung
(ø 6,19, Max 1293) und Entitätsmenge (100 000) stimmen exakt überein — eine
schöne Kreuzvalidierung über zwei völlig verschiedene Datenmodelle. Aber der
Ladefaktor gegenüber Pandas wächst von 5,7 (15 K) auf **9,5** (100 K), der
Speicherfaktor von 1,8 auf 2,6. Beides verschlechtert sich mit der Größe.

Drei Gründe, warum rdflib hier trotzdem nicht der Hauptpfad ist:

1. **OpenEA liefert gar kein RDF.** Die Dateien sind Tab-getrennt, YAGO-Terme
   wie `YAGO/E473489` sind keine gültigen IRIs. Vor dem rdflib-Laden müsste
   erst konvertiert werden — der N-Triples-Export kostet zusätzliche 6,3 s und
   19–130 MB Plattenplatz je KG.
2. **rdflib hält ebenfalls alles im Hauptspeicher**, nur ineffizienter. Der
   Skalierungsvorteil, um den es im Big-Data-Praktikum geht, entsteht dadurch
   nicht.
3. **Die Metriken sind ihrer Natur nach relational.** Grad-Verteilung,
   Property-Häufigkeiten und Alignment-Ambiguität sind Group-Bys und Joins.
   Genau dafür ist ein DataFrame gebaut, und genau so ließ es sich 1:1 nach
   Spark übertragen.

**Wo rdflib trotzdem eingesetzt wird:** für den N-Triples-Export nach PARIS
(`loaders/rdf_export.py`) — dort ist es genau richtig, weil es korrektes
IRI- und Literal-Escaping mitbringt, das wir sonst selbst hätten schreiben
müssen. Der Round-Trip ist durch Tests abgesichert.

**Nebenbefund aus dem Vergleich:** Pandas zählt 693 855 Tripel, rdflib 693 809.
Die Differenz von 46 erklärt sich vollständig: 45 Attribut-Tripel mit leerem
Literalwert (kein gültiges RDF-Objekt, wird beim Export übersprungen) und **ein
echtes Duplikat in den Rohdaten** — `E366684 dbo:bSide "Haunted Castle"` steht
zweimal in der Datei. RDF ist eine *Menge* von Tripeln, eine TSV-Datei eine
*Liste*. Das ist keine Ungenauigkeit, sondern der semantische Unterschied
zwischen den beiden Datenmodellen, und es ist zugleich ein kleiner
Datenqualitätsbefund über den Benchmark.

## 5. Matcher aus dem OpenEA-Paper — offen

> "Bei dem OpenEA, da sind eigentlich auch schon Matcher dabei gewesen. Die
> haben ja vor allem welche mit Trainingsdaten genommen. Wäre in dem Fall ja
> kein Problem, weil es das ja gibt."

**Nicht umgesetzt.** Kein embedding-basiertes Verfahren (MTransE, GCN-Align,
BootEA, RDGCN) ist eingebunden. Diese Verfahren trainieren pro Datensatz ein
Modell, brauchen realistisch eine GPU, und das OpenEA-Repository hängt an
TensorFlow 1.x — das ließ sich im verbleibenden Zeitbudget nicht seriös
aufsetzen.

**Konsequenz für die Aussagekraft:** Es fehlt genau die Verfahrensklasse, für
die diese Benchmarks ursprünglich gebaut wurden. Unser
`structural_propagation` nutzt zwar dasselbe Signal (Struktur + Seeds), aber
ein gelerntes Embedding muss darauf nicht genauso reagieren. Das ist in
`docs/Ergebnisse.md` §5 als Einschränkung dokumentiert und die naheliegendste
Fortsetzung bis Testat 3.

*Günstigere Alternative, falls Zeit bleibt:* die publizierten F1-Werte aus Sun
et al. (2020) als Literaturwerte in die Korrelationsanalyse aufnehmen — der
Betreuer hat das ausdrücklich angeboten ("ihr könnt auch in der Literatur
gucken, ob ihr Leute findet, die genau das benutzt haben, und könnt denen ihre
F1-Scores nehmen").

## 6. OAEI streichen

> "Also wir machen nur Entity Alignment, also nehmt das OAEI weg."

**Umgesetzt.** OAEI ist aus Config, Datensatz-Dokument, Architektur und README
entfernt; der geplante RDF/OWL-Loader entfällt damit.

Passender Nebenbefund: Die OpenEA-Datensätze enthalten praktisch **keine**
Typ-Tripel (in fünf von sechs Datensätzen null). Ontologie-Information ist dort
also gar nicht vorhanden — was die Trennung der beiden Probleme zusätzlich
untermauert.

## 7. Iterativ statt Wasserfall

> "Es ist besser, so schnell wie möglich zu versuchen, eine Pipeline
> hinzubekommen und dann nach und nach immer wieder Metriken hinzuzufügen. […]
> Die erste Comparison Table kommt halt erst nach Phase 6. Und das ist viel zu
> spät."

**Umgesetzt.** Reihenfolge war: Loader → eine Metrik → eine Bewertung
end-to-end lauffähig, danach Metriken und Matcher einzeln ergänzt. Die
`comparison.csv` existierte, bevor die Hälfte der Metriken geschrieben war. Der
Runner hat drei einzeln abschaltbare Stufen (`--no-profile`, `--no-match`,
`--no-report`), damit das Vorgehen weiterhin möglich bleibt. Der Zeitplan aus
§8 des Entwurfsdokuments gilt nicht mehr.

## 8. Metriken tabellarisch

> "Wenn ihr da auch eine Tabelle nochmal machen könnt für die Metriken. Das ist
> vor allem für die Präsentation dann auch einfacher. […] Ihr habt das ja in
> Fließtext einfach so runtergeschrieben."

**Umgesetzt.** `docs/Metriken-Katalog.md` ist durchgängig tabellarisch,
gruppiert in Basis / strukturell / Qualität, jede Zeile mit Definition *und*
Begründung ("Warum relevant"). Dieselbe Gliederung findet sich im Code und in
der Präsentation wieder.

## 9. Der Unterschied auf den Matchern, nicht nur auf den Datensätzen

> "Da haben wir diese Comparison-CSV raus, aber da sieht man ja dann nur die
> strukturellen Unterschiede und man sieht da jetzt gerade noch nicht, was
> eigentlich dann der Unterschied auf diesen Matchern ist."

**Umgesetzt** und über eine reine Korrelation hinaus: Die OpenEA-Familie
erlaubt einen **kontrollierten Vergleich**. V1 und V2 enthalten dieselben
Entitäten, nur die Relations-Tripel verdoppeln sich (Attribut-Tripel bleiben
bei Faktor 0,97–1,21). Gemittelt über 8 Datensatzpaare:

| Matcher | V1 sparse | V2 dense | Δ |
| ------- | --------: | -------: | ---: |
| `value_overlap` | 0,470 | 0,445 | −0,03 |
| `structural_propagation` | 0,498 | 0,733 | **+0,24** |
| `paris` | 0,825 | 0,908 | +0,08 |

> Die Werte sind nach der Überarbeitung zu Testat 2 neu gerechnet; `literal_tfidf`
> und `hybrid` sind seitdem entfernt (siehe `docs/Testat2-Feedback.md`).

Das ist keine Korrelation, sondern ein Experiment mit genau einer veränderten
Variable.

## 10. Kleinere Punkte

| Punkt | Status |
| ----- | ------ |
| Property-Verteilung beibehalten ("finde ich immer ganz wichtig") | ✅ und erweist sich als **stärkster Prädiktor** über alle Matcher |
| Namespace-Overlap eher weglassen ("zu kompliziert zu verstehen") | wird berechnet, ist aber weder in der Headline-Tabelle noch in der Präsentation |
| Zeitplan dynamisch halten | ✅ Zeitplan entfällt, Fortschritt über die Commit-Historie |
| Bestehende Repositories nutzen statt alles neu schreiben | teilweise — PARIS ja, die vier eigenen Matcher nein (Begründung §1) |
