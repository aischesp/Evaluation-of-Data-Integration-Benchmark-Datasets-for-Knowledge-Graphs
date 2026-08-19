# Metriken-Katalog

Alle Metriken, die das Framework berechnet. Gegliedert in Basis-Statistiken (§1),
strukturelle Metriken (§2) und Qualitätsmetriken (§3); §4 beschreibt die
Matching-Ansätze und ihre Bewertung, §5 das Output-Format.

Jede Metrik ist eine `BaseMetric`-Subklasse in `src/kg_quality_eval/metrics/`
und wird über ihren Namen in `config/datasets.yaml` aktiviert.

## Notation

Ein Benchmark besteht aus zwei KGs $G_i = (E_i, R_i, A_i, L_i, T_i^R, T_i^A)$
und einem Referenz-Alignment $M \subseteq E_1 \times E_2$:

| Symbol | Bedeutung |
| ------ | --------- |
| $E_i$ | Entitäten in $KG_i$ (inkl. solcher, die nur im Alignment vorkommen) |
| $R_i$, $A_i$ | Relations- bzw. Attribut-Properties |
| $L_i$ | Literale |
| $T_i^R \subseteq E_i \times R_i \times E_i$ | Relations-Tripel |
| $T_i^A \subseteq E_i \times A_i \times L_i$ | Attribut-Tripel |
| $M$ | Referenz-Alignment (Gold-Standard) |

---

## 1. Basis-Statistiken — `basic_stats`

| Schlüssel | Definition | Warum relevant |
| --------- | ---------- | -------------- |
| `n_entities` | $\lvert E_i \rvert$ | Größe, Suchraum, Compute-Bedarf |
| `n_relations` | $\lvert R_i \rvert$ | Schema-Breite |
| `n_attributes` | $\lvert A_i \rvert$ | Reichtum der Literal-Information |
| `n_literals` | $\lvert L_i \rvert$ | Lexikalische Vielfalt |
| `n_rel_triples` | $\lvert T_i^R \rvert$ | Menge struktureller Information |
| `n_attr_triples` | $\lvert T_i^A \rvert$ | Menge attributiver Information |
| `attr_to_rel_ratio` | $\lvert T_i^A \rvert / \lvert T_i^R \rvert$ | Balance Text vs. Struktur |
| `rel_triples_per_entity` | $\lvert T_i^R \rvert / \lvert E_i \rvert$ | strukturelle Dichte |
| `alignments.n`, `alignments.ratio` | $\lvert M \rvert$, $\lvert M \rvert / \min(\lvert E_1\rvert,\lvert E_2\rvert)$ | Umfang des Gold-Standards |
| `pair.size_asymmetry` | relative Differenz $\lvert T_1^R\rvert$ vs. $\lvert T_2^R\rvert$ | einseitig dünne Benchmarks |

---

## 2. Strukturelle Metriken

### 2.1 Degree-Verteilung — `degree_distribution`

Pro Entität: $\text{in-deg}$, $\text{out-deg}$, $\text{total-deg}$ über $T_i^R$.

| Schlüssel | Definition | Warum relevant |
| --------- | ---------- | -------------- |
| `<deg>.mean/median/std/min/max` | Lagemaße | Grundcharakter des Graphen |
| `<deg>.p25/p75/p95/p99` | Quantile | Verteilungsform ohne Verteilungsannahme |
| `<deg>.skewness`, `<deg>.kurtosis` | Schiefe, Wölbung | Hub-and-Spoke- bzw. Heavy-Tail-Indikator |
| `<deg>.gini` | Gini-Koeffizient | 0 = uniform, 1 = alles auf einer Entität |
| `powerlaw_alpha` | MLE-Schätzer $\alpha$, $P(k)\propto k^{-\alpha}$ | Tail-Schwere; nach Clauset et al. (2009) |
| `share_isolated` | Anteil mit $\text{deg}=0$ | Obergrenze für strukturelle Matcher |
| `share_deg_le_2`, `share_deg_le_5` | Anteil strukturell schwacher Entitäten | Embedding-Verfahren brauchen Tripel pro Entität |
| `pair.min_median_total_degree` | Minimum über beide KGs | der schwächere KG limitiert das Matching |

**Output**: `degree_distribution.json`, `degree_distribution.degree_histogram.csv`
(log-binniertes Histogramm), `degree_distribution.entity_degrees.csv`.

### 2.2 Property-Verteilung — `property_distribution`

Getrennt für Relations- und Attribut-Properties.

| Schlüssel | Definition | Warum relevant |
| --------- | ---------- | -------------- |
| `n_properties` | $\lvert R_i \rvert$ bzw. $\lvert A_i \rvert$ | Vokabulargröße |
| `top10_concentration` | Anteil Tripel auf den 10 häufigsten Properties | Schema-Skewness |
| `long_tail_share` | Anteil Properties mit $< 1\,\%$ der Tripel | Rausch-Vokabular |
| `entropy_norm` | Shannon-Entropie / $\log_2 \lvert R_i \rvert$ | 0 = eine Property dominiert, 1 = uniform |
| `freq.*` | Lagemaße der Häufigkeiten | Verteilungsform |

### 2.3 Connectivity — `connectivity`

Ungerichteter Graph über $T_i^R$, via NetworkX.

| Schlüssel | Definition |
| --------- | ---------- |
| `n_connected_components` | Anzahl Zusammenhangskomponenten |
| `size_largest_cc`, `share_largest_cc` | Größe und Anteil der größten Komponente |
| `share_singleton_cc` | Anteil Komponenten der Größe 1 |
| `density` | $\lvert T^R \rvert / (\lvert E\rvert (\lvert E\rvert-1))$ |
| `avg_clustering` | mittlerer Clustering-Koeffizient (Stichprobe von 5 000 Knoten ab dieser Größe) |

### 2.4 Long-Tail — `long_tail`

$P_k = \lvert \{e : \text{total-deg}(e) \le k\}\rvert / \lvert E\rvert$ für
$k \in \{0,1,2,3,5,10,20,50\}$, zusätzlich `share_no_information` (weder
Relations- noch Attribut-Tripel) und `mean_facts_per_entity`.

---

## 3. Qualitätsmetriken

### 3.1 Attribut-Vollständigkeit — `attribute_completeness`

$\text{cov}(a) = \lvert\{e : (e,a,l) \in T^A\}\rvert / \lvert E\rvert$ pro Property.

| Schlüssel | Definition | Warum relevant |
| --------- | ---------- | -------------- |
| `share_entities_with_attribute` | Anteil Entitäten mit ≥ 1 Attribut-Tripel | textuelle Matcher können sonst nichts encodieren |
| `mean_attr_per_entity` | $\lvert T^A\rvert / \lvert E\rvert$ | Informationsdichte |
| `property_coverage.mean/median/max` | Aggregat über alle Properties | Verteilung der Vollständigkeit |
| `n_properties_cov_gt_10pct` | Properties mit Coverage > 10 % | Anzahl wirklich nutzbarer Features |
| `share_literals_text/numeric/date` | Datentyp-Mix | Text ist für Embedding-Matcher nutzbarer als Zahlen |
| `mean_literal_length` | mittlere Literal-Länge | Länge des encodierbaren Texts |

### 3.2 Typen-Verteilung — `type_distribution`

Sucht Typ-Tripel (`rdf:type`, `wdt:P31`) und misst `n_type_triples`,
`n_distinct_types`, `share_entities_typed`, `type_entropy_norm`,
`pair.type_jaccard`.

> **Befund:** Auf den OpenEA-v2.0-Benchmarks ist diese Gruppe faktisch leer
> (siehe `docs/Ergebnisse.md`). Typ-basierte und ontologie-nutzende
> Matching-Ansätze sind auf diesen Daten also gar nicht evaluierbar — das ist
> selbst ein Ergebnis der Benchmark-Bewertung.

### 3.3 Schema-Heterogenität — `schema_heterogeneity`

| Schlüssel | Definition |
| --------- | ---------- |
| `rel_property_jaccard`, `attr_property_jaccard`, `property_jaccard` | Jaccard der Property-Mengen beider KGs |
| `property_namespace_jaccard`, `entity_namespace_jaccard` | Jaccard der Namespaces |
| `n_shared_rel_properties`, `n_shared_attr_properties` | absolute Überlappung |
| `vocab_size_ratio` | Verhältnis der Vokabulargrößen |

### 3.4 Alignment-Metriken — `alignment_metrics`

| Schlüssel | Definition |
| --------- | ---------- |
| `alignment_coverage` | $\lvert M\rvert / \min(\lvert E_1\rvert,\lvert E_2\rvert)$ |
| `entity_coverage_kg1/kg2` | Anteil Entitäten, die in $M$ vorkommen |
| `ambiguity_1_to_n`, `ambiguity_n_to_1` | Anteil mehrfach gemappter Entitäten |
| `bijective_share` | Anteil strikter 1:1-Mappings |
| `max_fanout_kg1/kg2` | größter Verzweigungsgrad |
| `candidate_space_log10` | $\log_{10}(\lvert E_1\rvert \cdot \lvert E_2\rvert)$ — Größe des Suchraums |
| `aligned_degree_bias_kg1/kg2` | mittlerer Grad aligned Entitäten / mittlerer Grad aller — Sampling-Bias des Gold-Standards |

### 3.5 Alignment-Erreichbarkeit — `alignment_reachability`

Obergrenze für rein strukturelle Verfahren: `share_aligned_with_edge`,
`share_aligned_in_lcc`, `share_pairs_both_with_edge`, `share_pairs_both_in_lcc`.
Ein Gold-Paar, bei dem eine Seite isoliert ist, kann strukturell nicht gefunden
werden.

### 3.6 Konsistenz aligned Entitäten — `aligned_consistency`

Beschreiben beide Seiten eines Gold-Paars dieselbe Entität vergleichbar?

| Schlüssel | Definition |
| --------- | ---------- |
| `degree_pearson`, `degree_spearman` | Korrelation $\text{deg}(e_1)$ vs. $\text{deg}(e_2)$ |
| `mean_abs_degree_diff`, `abs_degree_diff.*` | Verteilung der Grad-Differenz |
| `share_pairs_one_side_isolated` | Paare mit isolierter Seite |
| `attr_count_spearman` | Korrelation der Attribut-Anzahl |
| `literal_value_jaccard.mean` | mittlerer Jaccard der normalisierten Literalwerte (Stichprobe 5 000 Paare) |
| `literal_value_containment.mean` | Überlappung relativ zur kleineren Menge |
| `share_pairs_no_shared_literal` | Paare ganz ohne gemeinsamen Literalwert |

---

## 4. Matching-Ansätze und Bewertung

Die Profilierung allein sagt noch nichts über die Eignung eines Benchmarks.
Deshalb führt das Framework auf jedem Datensatz zusätzlich Entity-Alignment-
Verfahren aus und setzt deren Güte in Beziehung zu den Metriken oben.

### 4.1 Die Verfahren

**Zwei eigene Verfahren, eine Standard-Bibliothek, ein Referenzsystem.** Die
beiden eigenen sind bewusst so gebaut, dass jedes *ein* Signal isoliert nutzt —
nur so lässt sich messen, welche Datensatz-Eigenschaft auf welche
Verfahrensart wirkt.

| Matcher | Familie | Signal | Seeds | Herkunft |
| ------- | ------- | ------ | ----- | -------- |
| `value_overlap` | wertbasiert | exakte Literalwerte, IDF-gewichtet | nein | eigen |
| `pyjedai_ngram` | wertbasiert | Zeichen-n-Gramme + Blocking | nein | **pyJedAI** |
| `structural_propagation` | strukturell | gerichtete, typisierte Nachbarschaft | ja | eigen |
| `paris` | holistisch | Struktur + Literale, iterativ | nein | **PARIS v0.3** |

Nicht enthalten und bewusst gestrichen:

- **TF-IDF über Literal-Tokens.** Fachlich zu nah am Wertvergleich, ohne
  eigenen Erkenntniswert.
- **Ein eigener Hybrid-Matcher.** PARIS *ist* bereits ein hybrides Verfahren —
  es alignt Entitäten, Relationen und Klassen gemeinsam und iteriert das. Eine
  eigene Linearkombination zweier Verfahren wäre kein eigenständiger Ansatz,
  sondern nur eine Ensembling-Variante.

### 4.2 Struktureller Matcher im Detail

Der entscheidende Punkt ist, dass Relationstypen zwischen zwei KGs nicht
direkt vergleichbar sind (`dbo:birthPlace` vs. `wdt:P19`; bei D_W und D_Y ist
die Property-Überlappung exakt null). Die Relationen werden deshalb zuerst
**selbst aligniert**, allein aus der Seed-Evidenz:

> Sind (a, b) und (x, y) bekannte Seed-Paare und gilt in KG1 `a --r1--> x`
> sowie in KG2 `b --r2--> y`, ist das ein Beleg dafür, dass r1 und r2 dieselbe
> Beziehung ausdrücken.

Zusätzlich wird die Gegenrichtung geprüft (`y --r2--> b`), weil zwei KGs
dieselbe Beziehung oft invers modellieren. Erst danach werden die
Nachbarschaften typisiert verglichen, getrennt nach ein- und ausgehenden
Kanten und gewichtet mit der Alignment-Evidenz.

| Parameter | Wert | Herkunft |
| --------- | ---- | -------- |
| `iterations` | 5 | Valid-Split |
| `top_relations` | 200 | Valid-Split |
| `untyped_weight` | 0,3 | Valid-Split |
| `bootstrap_threshold` | 0,1 (Mindestabstand zum Zweitbesten) | Valid-Split |
| `min_score` | 0,1 | Threshold-Sweep, s. u. |

### 4.3 Schwellenwerte

Jeder Matcher hat einen echten Schwellenwert: darunter gibt er **keine**
Vorhersage ab, statt den besten verfügbaren Kandidaten zu nehmen. Die Werte
sind auf dem Valid-Split abgetastet (`scripts/tune_thresholds.py`, Raster
0,0–0,9), nicht gesetzt:

| Matcher | Schwellenwert | greift an |
| ------- | ------------- | --------- |
| `value_overlap` | 0,4 | Kosinus-Ähnlichkeit |
| `pyjedai_ngram` | 0,2 | Cluster-Ähnlichkeit |
| `structural_propagation` | 0,1 | **relativer Abstand zum Zweitbesten** |

Beim strukturellen Matcher greift der Schwellenwert bewusst nicht am Score:
dessen Scores sind zeilenweise normiert, der Bestwert ist also immer 1,0 und
ein Score-Schwellenwert damit wirkungslos. Konfidenzmass ist dort
(top1 − top2) / top1.

### 4.4 Bewertung

Bewertet wird auf dem **Test-Split von Fold 1** (70 % von M). Die
semi-supervised Matcher sehen den Train-Split (20 %) als Seeds, Parameter
wurden auf dem Valid-Split (10 %) gewählt.

**Auswertungsumfang:** alle Entitäten des Splits — auch die *ohne* Partner in
KG2 (siehe §4.5). Für sie ist jede Vorhersage falsch. Vorhersagen zu Entitäten
ausserhalb des Splits werden ignoriert statt als False Positive gezählt, sonst
würde ein unüberwachter Matcher dafür bestraft, dass er auch auf den
Trainingsentitäten richtig liegt.

| Kennzahl | Definition |
| -------- | ---------- |
| `precision` | korrekte / vorhergesagte Paare |
| `recall` | korrekte / Gold-Paare |
| `f1` | harmonisches Mittel |
| `abstain_rate` | Anteil Entitäten ohne Vorhersage |
| `n_false_on_unmatched` | Vorhersagen für Entitäten, die korrekt keinen Partner haben |

### 4.5 Non-Match-Varianten der Benchmarks

Die OpenEA-Benchmarks sind strikt bijektiv (`alignment_coverage` = 1,0,
`bijective_share` = 1,0). Damit ist es immer richtig, für jede Entität
*irgendeinen* Partner vorherzusagen — ein fehlender Schwellenwert fällt gar
nicht auf.

`preprocessing/nonmatch.py` bricht das auf. Aus dem Referenz-Alignment werden
drei Gruppen gebildet: `keep` (beide Seiten bleiben), `drop_left` (die
KG1-Seite wird entfernt, die KG2-Seite wird partnerlos) und `drop_right`
(umgekehrt). Alle Tripel entfernter Entitäten verschwinden mit.

Bei `match_ratio = 0.5` behält ein 15 000er Benchmark 7 500 Gold-Paare; beide
KGs haben danach 11 250 Entitäten, davon 3 750 ohne Partner — eine
Non-Match-Quote von 33 %. Konfiguration in `config/datasets_nonmatch.yaml`.

### 4.6 Seed-Größe

Wie viel Referenz-Alignment ein semi-supervised Matcher braucht, ist eine
Hyperparameter-Frage und wird in `scripts/analyze_seed_size.py` gemessen
(5 %, 10 %, 25 %, 50 %, 75 %, 100 % des Train-Splits). Ergebnis in
`docs/Ergebnisse.md`.

### 4.7 Fehler-Taxonomie

Die Metriken oben beschreiben Datensätze, die Bewertung beschreibt Verfahren.
Die Taxonomie (`reporting/error_taxonomy.py`) verbindet beides auf
Einzelfallebene: sie ordnet jede Test-Entität einer Fehlerursache zu, und jede
Klasse zeigt auf eine Metrik dieses Katalogs zurück.

| Klasse | Bedeutung | zugehörige Metrik |
| ------ | --------- | ----------------- |
| `correct` | Top-1-Vorhersage ist das Gold-Paar (oder korrekte Enthaltung) | — |
| `no_signal` | Entität hat weder Relations- noch Attribut-Tripel | `share_no_information` |
| `structurally_unreachable` | keine Kante bzw. ausserhalb der grössten Komponente | `alignment_reachability` |
| `no_shared_literal` | Gold-Paar teilt keinen Literalwert | `literal_value_jaccard` |
| `abstained` | Enthaltung, obwohl es ein Gold-Paar gibt | `abstain_rate` |
| `false_on_unmatched` | Vorhersage für eine korrekt partnerlose Entität | `n_false_on_unmatched` |
| `wrong_candidate` | falscher Partner gewählt, obwohl Signal vorhanden war | Rest |

**Die Kaskade ist familienabhängig.** Als *blockiert* gilt nur das Fehlen des
Signals, das die jeweilige Familie überhaupt nutzt:

| Familie | Blocker |
| ------- | ------- |
| `structural` | fehlende Struktur |
| `value` | kein gemeinsamer Literalwert |
| `holistic` (PARIS) | beides zugleich |

Daraus folgt `unsolvable_share`: der Anteil der Fehler, an denen kein Verfahren
dieser Familie etwas ändern kann. Der Rest liegt am Verfahren und sagt, ob eine
Verbesserung überhaupt noch Spielraum hat.

Ausgabe: `error_taxonomy.csv`, `error_solvability.csv`, `error_examples.csv`,
`figures/error_taxonomy.png` (`scripts/analyze_errors.py`).

### 4.8 Streuung über die Folds

OpenEA liefert fünf disjunkte 721-Splits je Datensatz. `scripts/run_folds.py`
rechnet alle Matcher auf allen fünf und aggregiert zu Mittel und
Standardabweichung — dasselbe Protokoll, das Sun et al. (2020) für dieselben
Datensätze verwenden.

Die Profiling-Metriken werden dabei nicht neu gerechnet: die Folds
partitionieren dasselbe Referenz-Alignment, Graphen und Struktur bleiben
identisch. Nur die Matcher hängen vom Fold ab, weil sich ihre Seed-Menge
ändert.

Ausgabe: `fold_scores.csv`, `fold_variance.csv`, `figures/fold_variance.png`.

## 5. Output-Format

Pro Datensatz unter `results/reports/<dataset>/`:

```
basic_stats.json                    §1
degree_distribution.json            §2.1  + .degree_histogram.csv, .entity_degrees.csv
property_distribution.json          §2.2  + .property_counts.csv
connectivity.json                   §2.3  + .components.csv
long_tail.json                      §2.4  + .long_tail_curve.csv
attribute_completeness.json         §3.1  + .property_coverage.csv
type_distribution.json              §3.2  + .types.csv
schema_heterogeneity.json           §3.3  + .shared_properties.csv
alignment_metrics.json              §3.4  + .splits.csv
alignment_reachability.json         §3.5  + .reachability.csv
aligned_consistency.json            §3.6  + .pair_consistency_sample.csv
matching/<matcher>_pairs.csv        §4    vorhergesagte Paare je Matcher
```

Datensatzübergreifend unter `results/reports/`:

| Datei | Inhalt |
| ----- | ------ |
| `comparison.csv` | alle Skalar-Metriken × alle Datensätze (Breitformat) |
| `comparison_headline.csv` | die Kennzahlen für Bericht und Präsentation |
| `matching_results.csv` | Precision/Recall/F1/Hits@1 je (Datensatz, Matcher) |
| `matching_f1_matrix.csv` | F1-Matrix Datensätze × Matcher |
| `merged_metrics_scores.csv` | Join aus beidem — Basis der Korrelationsanalyse |
| `correlation.csv`, `correlation_top.csv` | Spearman-Korrelation Metrik ↔ F1 |
| `backend_equivalence.csv` | Pandas vs. PySpark, metrikweise |
| `runtimes.csv`, `backend_runtimes.csv` | Laufzeiten |

Figures unter `results/figures/`.

---

## 6. Quellen

- [1] Sun, Hu, Li (2017): *Cross-lingual Entity Alignment via Joint Attribute-Preserving Embedding*. arXiv:1708.05045.
- [2] Sun et al. (2020): *A Benchmarking Study of Embedding-based Entity Alignment for KGs*. PVLDB 13(11).
- [3] Clauset, Shalizi, Newman (2009): *Power-Law Distributions in Empirical Data*. SIAM Review 51(4).
- [4] Zhang et al. (2022): *An Experimental Study of State-of-the-Art Entity Alignment Approaches*. TKDE.
- [5] Suchanek, Abiteboul, Senellart (2011): *PARIS: Probabilistic Alignment of Relations, Instances, and Schema*. PVLDB 5(3).
