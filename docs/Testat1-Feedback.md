# Feedback aus Testat 1 und seine Umsetzung

Testat 1 fand Anfang Juni 2026 statt. Der Entwurf wurde inhaltlich angenommen
("saubere Arbeit", "die Datensätze sind super", "die Metriken sind genug"), mit
mehreren konkreten Auflagen für die Implementierungsphase. Diese Seite hält
fest, was gefordert war und wo es umgesetzt ist — auch damit in der
Abschlusspräsentation nachvollziehbar bleibt, welche Entscheidungen aus dem
Gespräch stammen.

## 1. Matching-Ansätze fehlten komplett — Hauptkritik

> "Es fehlen so ein bisschen die Matcher. […] Qualitätsbewertung ist halt nicht
> nur dieses Profiling. Also was ihr geschrieben habt, ist dieses Profiling.
> […] Das Profiling ist halt nur der erste Schritt, um überhaupt irgendwelche
> Werte zu haben, wo man dann sehen kann: aha, der Datensatz war unterschiedlich
> gegenüber dem anderen und deswegen ist das Matching-Ergebnis schlechter oder
> besser."

Der Entwurf beschrieb ausschließlich die Berechnung von Kennzahlen. Es fehlte
der Datenintegrations-Task selbst, gegen den sich diese Kennzahlen erst
validieren lassen.

**Umgesetzt.** Fünf Entity-Alignment-Matcher, bewusst über die Signaltypen
verteilt, damit die Korrelationen unterscheidbar werden:

| Matcher | Familie | Signal | Warum dabei |
| ------- | ------- | ------ | ----------- |
| `literal_tfidf` | textuell | TF-IDF über Literal-Tokens | der vom Betreuer beschriebene "textuelle Matcher, der die Entität in Text encodiert" |
| `value_overlap` | textuell | Überlappung ganzer Literalwerte | klassisches blocking-basiertes ER |
| `structural_propagation` | strukturell | Nachbarschaft über Seeds, mit Bootstrapping | Gegenstück, das nur die Graphstruktur nutzt |
| `hybrid` | hybrid | Kombination beider | zeigt Komplementarität |
| `paris` | holistisch | PARIS v0.3 | vom Betreuer namentlich empfohlen |

> "Da gibt es zum Beispiel den PARIS-Algorithmus. […] PARIS ist einfach nur eine
> Jar-Datei und das hat keine Python-API. Du brauchst zwei Input-Files im
> RDF-N-Triple-Format und dann gibt das dir einen Ordner zurück und in dem
> Ordner sind so Iterations-Ordner."

Genau so umgesetzt in `src/kg_quality_eval/matching/paris.py`: N-Triples-Export
über rdflib, Subprozess-Aufruf des Jars, Einlesen der letzten nicht-leeren
`*_eqv.tsv`. Zwei Fallstricke, die dabei auftraten, sind in
`docs/Architektur.md` §10 dokumentiert.

**Wirkung:** aus der Comparison-Tabelle allein wären die Datensätze nur
"unterschiedlich" gewesen. Jetzt zeigt `results/reports/correlation.csv`, welche
Unterschiede tatsächlich auf die Matching-Güte durchschlagen — und dass das je
nach Matcher-Familie andere sind.

## 2. OAEI streichen — nur Entity Alignment

> "Also wir machen nur Entity Alignment, also nehmt das OAEI weg. […] Bei dem
> Ontology Alignment Evaluation geht es um Ontologien, da geht es darum zu
> alignen, was die gleichen Properties sind und die gleichen Klassen. […] Und
> Entity Alignment ist halt wirklich zu sagen, das sind die gleichen Personen."

**Umgesetzt.** OAEI ist aus Config, Datensatz-Dokument, Architektur und README
entfernt. Der geplante RDF/OWL-Loader entfällt damit ebenfalls.

Nebenbefund, der genau in diese Unterscheidung fällt: die OpenEA-Datensätze
enthalten praktisch **keine** Typ-Tripel (`rdf:type`). Ontologie-Information
ist dort also gar nicht vorhanden — siehe `docs/Ergebnisse.md`.

## 3. Nicht Pandas *und* PySpark nacheinander

> "Die Idee war ja auch PySpark eigentlich direkt zu benutzen und kein Pandas.
> […] Es gibt keinen Sinn, beides zu machen. […] Weil ich das nur sehe von der
> Zeit her, weil ihr das so eingeplant habt, dass ihr da erst in den Pandas und
> dann macht ihr irgendwann später noch das PySpark-Backend. Das ergibt nicht so
> viel Sinn."

Kritisiert wurde die *Reihenfolge* im Zeitplan (erst alles in Pandas, danach
alles nochmal in Spark), nicht die Existenz zweier Backends.

**Umgesetzt, mit bewusster Abweichung.** Pandas ist der Standardpfad für alle
elf Metrik-Gruppen. Zusätzlich gibt es ein PySpark-Backend, aber nur für die
drei Kernmetrik-Gruppen, und es wurde in einem Zug mit der Pandas-Version
gebaut statt als nachgelagerte Phase. `scripts/run_backend_benchmark.py` prüft
metrikweise, dass beide Wege dieselben Zahlen liefern (Ergebnis: 29/29
identisch).

Begründung für die Abweichung: die Aufgabenstellung verlangt explizit
"implement the conceptualized framework in Python (PySpark)" und ein modulares
Design, in dem "different processing frameworks (e.g. Pandas or PySpark) can be
easily integrated and compared". Ein verifizierter Äquivalenztest zwischen
beiden ist die direkte Antwort darauf — und kostete deutlich weniger Zeit als
die ursprünglich geplante vollständige Zweitimplementierung.

## 4. Iterativ statt Wasserfall

> "Ihr müsst nicht alle Metriken implementieren und dann den Loader und dann das
> Szenario, sondern es ist besser, so schnell wie möglich zu versuchen, eine
> Pipeline hinzubekommen und dann nach und nach immer wieder Metriken
> hinzuzufügen. […] Weil ihr müsst euch vorstellen, die erste Comparison Table
> kommt halt erst nach Phase 6. Und das ist viel zu spät, weil da stellt man
> fest, dass vieles nicht funktioniert, und da ist gar keine Zeit mehr."

**Umgesetzt.** Vorgehen war: Loader + eine Metrik + eine Bewertung
end-to-end lauffähig, danach Metriken und Matcher einzeln ergänzt. Die
`comparison.csv` existierte, bevor die Hälfte der Metriken geschrieben war.
Der Runner hat drei einzeln abschaltbare Stufen (`--no-profile`, `--no-match`,
`--no-report`), damit dieses Vorgehen auch weiterhin möglich bleibt.

## 5. Metriken gruppieren und tabellarisch darstellen

> "Ihr könnt die dann ein bisschen unterteilen, weil es gibt so strukturelle
> Metriken, also es gibt sozusagen Kernmetriken. […] Wenn ihr da auch eine
> Tabelle nochmal machen könnt für die Metriken. Das ist vor allem für die
> Präsentation dann auch einfacher. […] Ihr habt das ja in Fließtext einfach so
> runtergeschrieben, das hätte auch eine Tabelle sein können."

**Umgesetzt.** `docs/Metriken-Katalog.md` ist durchgängig tabellarisch, gruppiert
in Basis / strukturell / Qualität, jede Zeile mit Definition *und* Begründung.
Dieselbe Gliederung findet sich im Code (`metrics/basic.py`,
`metrics/structural.py`, `metrics/quality.py`) und in der Präsentation wieder.

## 6. Strukturelle Eigenschaften explizit begründen

> "Je mehr Attribute da sind, desto einfacher ist das für irgendeinen
> Matching-Ansatz. […] Wenn das ein Graph ist, der eh wenig textuelle
> Beschreibung hat, dann funktioniert der Matcher vermutlich schlechter, als
> wenn man einen Matcher nimmt, der wirklich diese Struktur sich anguckt. […]
> Dass halt so diese strukturellen Eigenschaften irgendwie diesen Unterschied
> machen, dass ein Matcher besser oder schlechter funktioniert, das fehlt mir
> ein bisschen, dass das explizit erwähnt ist."

**Umgesetzt und empirisch belegt.** Jede Metrik im Katalog hat eine Spalte
"Warum relevant". Wichtiger: die Hypothese wird nicht mehr nur behauptet,
sondern gemessen — die Matcher-Familien reagieren nachweislich auf
unterschiedliche Eigenschaften (`docs/Ergebnisse.md`, Abschnitt
Korrelationsanalyse).

## 7. Kleinere Punkte

| Punkt aus dem Gespräch | Status |
| ---------------------- | ------ |
| rdflib einsetzen | genutzt für den N-Triples-Export nach PARIS (`loaders/rdf_export.py`), inkl. Round-Trip-Test |
| Property-Verteilung beibehalten ("finde ich immer ganz wichtig") | `property_distribution`, erweist sich als stärkster Prädiktor für den strukturellen Matcher |
| Namespace-Overlap eher weglassen ("zu kompliziert zu verstehen") | bleibt berechnet, ist aber nicht in der Headline-Tabelle und nicht in der Präsentation |
| Zeitplan dynamisch halten | Zeitplan aus dem Entwurfsdokument entfällt, Fortschritt läuft über die Commit-Historie |
| Bestehende Repositories nutzen statt alles neu schreiben | PARIS wird als fertiges Tool eingebunden statt nachgebaut |
