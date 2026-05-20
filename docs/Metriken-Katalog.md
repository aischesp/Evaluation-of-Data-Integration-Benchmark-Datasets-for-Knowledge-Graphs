# Metriken-Katalog

> Vollständige Definition aller Metriken, die unser Framework berechnen soll.
> Strukturierung in 3 Gruppen: **Basis-Statistiken**, **Strukturelle Metriken**, **Qualitätsmetriken**.
> Stand: 2026-05-20

## Notation

Wir betrachten ein Benchmark-Datensatz-Paar bestehend aus zwei KGs $G_1 = (E_1, R_1, A_1, L_1, T_1^R, T_1^A)$ und $G_2$ mit:

- $E_i$ = Menge der Entitäten in $KG_i$
- $R_i$ = Menge der Relations-Properties (rel_triples)
- $A_i$ = Menge der Attribut-Properties (attr_triples)
- $L_i$ = Menge der Literale
- $T_i^R \subseteq E_i \times R_i \times E_i$ = Relations-Tripel
- $T_i^A \subseteq E_i \times A_i \times L_i$ = Attribut-Tripel
- $M \subseteq E_1 \times E_2$ = Referenz-Alignment (Gold-Standard)

---

## 1. Basis-Statistiken

Trivial zu berechnen, geben aber den ersten Eindruck der Größenordnung.

| Kürzel        | Definition                                                    | Relevanz                                                    |
| ------------- | ------------------------------------------------------------- | ----------------------------------------------------------- |
| `n_entities`  | $|E_i|$                                                       | Größe des KG, Compute-Bedarf                                |
| `n_relations` | $|R_i|$                                                       | Schema-Breite (wenige Properties ⇒ dichter Graph je Property) |
| `n_attributes`| $|A_i|$                                                       | Reichtum der Literal-Information                            |
| `n_literals`  | $|L_i|$                                                       | Lexikalischer Reichtum                                      |
| `n_rel_triples` | $|T_i^R|$                                                  | Größe der strukturellen Information                         |
| `n_attr_triples`| $|T_i^A|$                                                  | Größe der attributiven Information                          |
| `attr_to_rel_ratio` | $|T_i^A| / |T_i^R|$                                    | DBpedia ≈ 3 (Sun 2017) — fehlt bei vielen Methoden          |
| `n_alignments`| $|M|$                                                         | Anzahl Gold-Mappings                                        |
| `alignment_ratio` | $|M| / \min(|E_1|, |E_2|)$                                | wieviel Prozent der Entitäten sind aligned                  |

**Output**: einzeiliges JSON pro Datensatz.

---

## 2. Strukturelle Metriken

### 2.1 Degree-Verteilungen

Für jede Entität $e \in E_i$ berechnen wir:

$$
\text{in-deg}(e) = |\{(s,r,e) \in T_i^R\}|, \quad
\text{out-deg}(e) = |\{(e,r,o) \in T_i^R\}|, \quad
\text{total-deg}(e) = \text{in-deg}(e) + \text{out-deg}(e)
$$

**Berechnet als:**

- **Histogramm** (log-skalierte Bins, optimal für Power-Law-Verteilungen)
- **Kennzahlen**: Mean, Median, Std, Min, Max, 25 %/75 %/95 %/99 %-Quartile
- **Power-Law-Fit**: $P(\text{deg} = k) \propto k^{-\alpha}$ — Schätzung von $\alpha$ via MLE [Clauset 2009]

**Relevanz (vgl. Meeting-Notes Hofer):**

> "Embedding-Verfahren brauchen ausreichend viele Tripel pro Entität, um sinnvolle Vektoren zu lernen. Niedriger Median → strukturell schwacher Benchmark."

Sub-Metriken:

| Metrik                        | Bemerkung                                                          |
| ----------------------------- | ------------------------------------------------------------------ |
| `degree_skewness`             | Schiefe — hohe Werte ⇒ Hub-and-Spoke-Struktur                      |
| `degree_kurtosis`             | Wölbung — Heavy-Tail-Indikator                                     |
| `share_isolated` (deg = 0)    | Anteil isolierter Entitäten — würden Embedding sabotieren          |
| `share_low_deg` (deg ≤ 2)     | Anteil Entitäten mit zu wenigen Tripeln (Daumenregel aus [4])      |

### 2.2 Property-Frequenz-Verteilungen

Für jede Relation $r \in R_i$: Anzahl Tripel mit dieser Property.

- **Histogramm**: Property-Häufigkeit
- **Long-Tail-Quote**: Anteil Properties, die nur in $< 1\%$ der Tripel vorkommen
- **Top-k-Konzentration**: Anteil der Tripel, der auf die Top-10-Properties entfällt (Schema-Skewness)

### 2.3 Graph-Connectivity

| Metrik                    | Definition                                                    |
| ------------------------- | ------------------------------------------------------------- |
| `n_connected_components`  | Zerfällt der Graph in mehrere Komponenten?                    |
| `size_largest_cc`         | Anteil Entitäten in der größten Komponente                    |
| `avg_clustering_coeff`    | NetworkX-Standard (Sub-Sample bei großen Graphen)             |
| `density`                 | $|T^R| / (|E| \cdot (|E|-1))$ — global density                |

> Berechnung von Clustering & Path-Length nur auf **Sub-Sample** für 100K-Variante (Compute-Kosten!).

---

## 3. Qualitätsmetriken

### 3.1 Attribut-Vollständigkeit

Für jede Attribut-Property $a \in A_i$:

$$
\text{cov}(a) = \frac{|\{e \in E_i : (e, a, l) \in T_i^A \text{ für ein } l\}|}{|E_i|}
$$

**Output**:
- pro Property: Coverage in $[0,1]$
- aggregiert: Mean / Median Coverage über alle Properties
- **Heatmap** Property × Entity-Typ (wenn Typ verfügbar)

**Coverage-Vollständigkeit zwischen zwei KGs** (für aligned Entitäten):

$$
\text{attr\_overlap}(a_1, a_2) = \frac{|\{(e_1, e_2) \in M: a_1 \text{ für } e_1 \text{ und } a_2 \text{ für } e_2\}|}{|M|}
$$

Hilft, **Property-Mapping-Lücken** sichtbar zu machen.

### 3.2 Typen-Verteilung (Type Distribution)

Wenn `rdf:type` o.ä. vorhanden ist:

- **Histogramm der Typen** (Class-Frequenz)
- **Klassen-Skewness**: dominieren wenige Klassen?
- **Klassen-Heterogenität** zwischen $G_1$ und $G_2$ (Jaccard auf Typ-Mengen)
- **Pro aligned Pair**: stimmen die Typen überein? ⇒ `type_consistency_rate`

### 3.3 Long-Tail-Analyse

Untersucht, wie viele Entitäten *kaum vorkommen*:

- $P_k$: Anteil Entitäten mit Total-Degree ≤ $k$
- Plot $P_k$ vs. $k$
- **Power-Law-Fit** auf der Entity-Frequenz-Verteilung (vgl. 2.1)
- **Gini-Koeffizient** auf Degree-Verteilung ($G = 0$: uniform, $G = 1$: extrem skewed)

### 3.4 Alignment-Metriken

Eigenständige Gruppe — beschäftigt sich nur mit $M$:

| Metrik                           | Definition / Berechnung                                                                       |
| -------------------------------- | --------------------------------------------------------------------------------------------- |
| `alignment_coverage`             | $|M| / \min(|E_1|,|E_2|)$ — siehe Basis-Stats                                                |
| `entity_coverage_per_kg`         | $\frac{|\{e_1 : (e_1,*) \in M\}|}{|E_1|}$ (und analog für $KG_2$)                            |
| `ambiguity_1_to_n`               | wie oft $e_1$ auf mehrere $e_2$ mapped → Anteil $e_1$, die in $M$ mehrfach erscheinen        |
| `ambiguity_n_to_1`               | analog umgekehrt                                                                              |
| `bijective_share`                | Anteil $M$, die strikt 1:1-Mappings sind                                                      |
| `mapping_in_largest_cc`          | Liegen aligned Entitäten in der größten verbundenen Komponente?                               |

### 3.5 Konsistenz aligned Entitäten

Für aligned Paare $(e_1, e_2) \in M$:

- **Degree-Konsistenz**: Korrelation $\text{deg}(e_1)$ vs. $\text{deg}(e_2)$ (Spearman/Pearson)
- **Typ-Konsistenz**: Jaccard auf Typ-Menge von $e_1$ und $e_2$
- **Attribut-Wert-Konsistenz**: für gleiche Property — Equality / Distanz numerischer Werte / Levenshtein für Strings (Sub-Sample, kostspielig)

### 3.6 Schema-Heterogenität (über die zwei KGs)

| Metrik                | Definition                                                              |
| --------------------- | ----------------------------------------------------------------------- |
| `property_jaccard`    | Jaccard($R_1 \cup A_1, R_2 \cup A_2$)                                   |
| `class_jaccard`       | Jaccard auf Klassen-Mengen (falls Typen extrahierbar)                   |
| `namespace_overlap`   | Anteil Namespaces, die in beiden KGs vorkommen                         |
| `vocab_diversity`     | Entropy der Property-Verteilung                                         |

---

## 4. Output-Format

Pro Datensatz produziert das Framework:

```
results/reports/<dataset>/
├── basic_stats.json              ← Section 1
├── degree_stats.json             ← Section 2.1 (Kennzahlen)
├── degree_histograms.csv         ← Section 2.1 (Histogramm-Daten)
├── degree_plot.png               ← Visualisierung
├── property_stats.csv            ← Section 2.2
├── connectivity.json             ← Section 2.3
├── attribute_completeness.csv    ← Section 3.1
├── type_distribution.csv         ← Section 3.2
├── alignment_metrics.json        ← Section 3.4
├── consistency_metrics.json      ← Section 3.5
├── schema_heterogeneity.json     ← Section 3.6
└── summary.json                  ← Konsolidiertes Dashboard
```

Ein zentrales `results/reports/comparison.csv` enthält **alle Metriken über alle Datensätze** in einer Tabelle ⇒ Direktvergleich.

---

## 5. Priorisierung (MoSCoW) für Testat 2

| Priorität | Metriken                                                              |
| --------- | --------------------------------------------------------------------- |
| **Must**  | Sect. 1 komplett, 2.1 (in/out/total-deg + Kennzahlen + Histogramm)    |
| **Should**| 2.2, 2.3, 3.1, 3.4 (Alignment-Metriken komplett)                      |
| **Could** | 3.2, 3.3, 3.5 (degree-Konsistenz reicht), 3.6                         |
| **Won't** | Path-Length, vollständige Attribut-Wert-Distanzen (zu teuer)          |

---

## 6. Quellen

- [1] Sun, Hu, Li (2017): JAPE-Paper, arXiv:1708.05045.
- [2] Sun et al. (2020): OpenEA-Benchmarking-Study, PVLDB.
- [3] Clauset, Shalizi, Newman (2009): *Power-Law Distributions in Empirical Data*. SIAM Review.
- [4] Zhang et al. (2022): *Experimental Study of EA Approaches*, TKDE.
