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
Deshalb führt das Framework auf jedem Datensatz zusätzlich fünf
Entity-Alignment-Verfahren aus und setzt deren Güte in Beziehung zu den
Metriken oben.

| Matcher | Familie | Genutztes Signal | Seeds | Implementierung |
| ------- | ------- | ---------------- | ----- | --------------- |
| `literal_tfidf` | textuell | TF-IDF-Kosinus über Literal-Tokens | nein | `matching/lexical.py` |
| `value_overlap` | textuell | IDF-gewichtete Überlappung ganzer Literalwerte | nein | `matching/lexical.py` |
| `structural_propagation` | strukturell | Nachbarschaft über Seeds propagiert, mit Bootstrapping | ja | `matching/structural.py` |
| `hybrid` | hybrid | Linearkombination textuell + strukturell | ja | `matching/structural.py` |
| `paris` | holistisch | externes Java-Tool (dig-team/PARIS v0.3), Struktur + Literale | nein | `matching/paris.py` |

**Bewertung** (`matching/evaluate.py`): Alle Matcher werden auf dem
**Test-Split von Fold 1** (70 % von $M$) bewertet. Die semi-supervised Matcher
sehen den Train-Split (20 %) als Seeds, Parameter wurden auf dem Valid-Split
(10 %) gewählt. Vorhersagen zu Entitäten außerhalb des Test-Splits werden
ignoriert statt als False Positive gezählt — sonst würde ein unüberwachter
Matcher dafür bestraft, dass er auch auf den Trainingsentitäten richtig liegt.

| Kennzahl | Definition |
| -------- | ---------- |
| `precision` | korrekte Paare / vorhergesagte Paare (im Test-Universum) |
| `recall` | korrekte Paare / Gold-Paare |
| `f1` | harmonisches Mittel |
| `hits_at_1` | Anteil Test-Entitäten mit korrektem Top-1-Partner |
| `coverage` | Anteil Test-Entitäten, für die überhaupt vorhergesagt wurde |

---

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
