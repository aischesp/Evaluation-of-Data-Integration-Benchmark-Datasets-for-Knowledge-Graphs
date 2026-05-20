# Offene Fragen an den Betreuer

> Adressat: Marvin Hofer · hofer@informatik.uni-leipzig.de
> Vorbereitet für Feedback-Treffen nach Abgabe des Entwurfsdokuments

## Scope der Datensätze

1. **Diversität vs. Tiefe** — Wir planen 6 OpenEA-Varianten + OAEI Conference + ein eigener DBpedia-Wikidata-Subset (8 Datensätze). Wäre Ihnen eine **stärkere Diversität jenseits von OpenEA** (z. B. zusätzlich YAGO-WD, AGRO-LD, NELL) lieber als ein direkter V1/V2-Vergleich innerhalb von OpenEA?

2. **100 K-Variante** — Im aktuellen OpenEA-Release ist die 100K-Variante teils nur als Teil von „OpenEA-large" verfügbar. Falls das Setup-Hürden bringt: 15 K reicht und wir demonstrieren Skalierbarkeit über das **Custom-Subset** + synthetisches Up-Sampling?

3. **Custom-Subset (DBpedia ↔ Wikidata, aktueller Dump)** — Ist die eigene Generierungspipeline aus Ihrer Sicht Teil des Frameworks (Aufwand: 2–3 Tage) oder eher ein optionaler „Could"?

## Scope der Metriken

4. **Attribut-Wert-Konsistenz** — Levenshtein- und numerische Distanzen sind teuer (O(n²) im worst case). Sollen wir das als **Must** mitnehmen oder reicht ein Sample-basierter Schätzwert?

5. **Type Distribution** — Bei OpenEA-Varianten ohne explizite `rdf:type`-Tripel ⇒ leiten wir den Typ aus dem URI-Präfix ab (`/Person/`, `/Place/`) ab oder lassen wir die Metrik weg, wenn keine Typ-Information vorliegt?

6. **Power-Law-Fit** — Methodisch via MLE nach Clauset et al. — möchten Sie zusätzlich einen alternativen Stresstest (z. B. Lognormal-Vergleich)?

## Output & Präsentation

7. **Output-Form** — Reicht aus Ihrer Sicht eine zentrale `comparison.csv` + statische Plots, oder erwarten Sie ein **interaktives Dashboard** (Plotly Dash / Streamlit)?

8. **Sprache der Endpräsentation** — Englisch oder Deutsch?

## Tooling

9. **Scala-Option** — Sie hatten Scala als Alternative angeboten. Wir bleiben bei Python (Pandas + PySpark) — ist das ok?

10. **Compute-Ressourcen** — Steht für die 100 K-Variante ggf. der Rechen-Cluster des Lehrstuhls bereit, oder rechnen wir lokal?

## Organisatorisches

11. **Repo-Zugang** — Sollen wir Sie als Collaborator auf GitHub einladen, oder bevorzugen Sie eine Spiegelung im GitLab des Lehrstuhls (`git.informatik.uni-leipzig.de/dbs/...`)?

12. **Testat-1-Format** — Reicht der Versand des PDFs per Mail, oder soll zusätzlich ein kurzes Treffen stattfinden?
