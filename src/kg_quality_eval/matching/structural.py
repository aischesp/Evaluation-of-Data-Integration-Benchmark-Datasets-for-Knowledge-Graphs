"""Struktureller Matcher: typisierte Nachbarschaftspropagation über Seeds.

Die erste Fassung war zu grob: sie hat die Adjazenzmatrix symmetrisiert und nur
gespeichert, *dass* zwei Knoten verbunden sind. Damit war "verheiratet mit X"
nicht von "geboren in X" unterscheidbar, und `A --p--> B` nicht von
`B --p--> A`. Entsprechend viele False Positives entstanden, und der F1-Wert lag
unter dem, was als Baseline noch sinnvoll ist.

Diese Fassung nutzt drei Informationen, die vorher verworfen wurden:

1. **Kantenrichtung.** Ein- und ausgehende Nachbarschaft sind getrennte
   Merkmale.
2. **Relationstyp.** Der Knackpunkt: Relationstypen sind zwischen zwei KGs
   nicht direkt vergleichbar (`dbo:birthPlace` vs. `wdt:P19`), bei D_W und D_Y
   ist die Property-Überlappung sogar exakt null. Deshalb werden die Relationen
   zuerst *selbst* aligniert — aus den Seeds heraus, ohne Vokabularannahme.
   Erst danach ist ein typisierter Vergleich möglich.
3. **Gewichtung.** Relationen gehen mit ihrer Alignment-Evidenz und einem
   IDF-artigen Seltenheitsgewicht in den Score ein.

Das ist im Kern der Mechanismus, den PARIS iterativ betreibt (Entitäten und
Relationen wechselseitig verbessern), hier auf eine Richtung reduziert:
Relationen einmal alignieren, dann Entitäten propagieren.

Der Matcher liest bewusst kein einziges Literal. Diese Trennung ist die
Voraussetzung dafür, die Abhängigkeit von strukturellen und wertbasierten
Datensatz-Eigenschaften getrennt zu messen.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.matching.base import (
    SparseScoreMatcher,
    l2_normalize,
    seeds_to_matrix,
    top1_margin_per_row,
    topk_per_row,
)


def relation_matrices(
    kg: KnowledgeGraph, relations: list[str]
) -> dict[str, tuple[sp.csr_matrix, sp.csr_matrix]]:
    """Je Relationstyp eine gerichtete Adjazenzmatrix (out, in)."""
    index = kg.entity_index
    n = kg.n_entities()

    heads = kg.rel_triples["head"].map(index)
    tails = kg.rel_triples["tail"].map(index)
    rels = kg.rel_triples["relation"]
    valid = heads.notna() & tails.notna()

    wanted = set(relations)
    out: dict[str, tuple[sp.csr_matrix, sp.csr_matrix]] = {}
    for relation in relations:
        mask = valid & (rels == relation)
        if not mask.any():
            continue
        rows = heads[mask].to_numpy(dtype=np.int32)
        cols = tails[mask].to_numpy(dtype=np.int32)
        data = np.ones(rows.size, dtype=np.float32)
        forward = sp.csr_matrix((data, (rows, cols)), shape=(n, n))
        out[relation] = (forward, forward.T.tocsr())
    assert set(out) <= wanted
    return out


def align_relations(
    kg_pair: KGPair, seeds: pd.DataFrame, top_relations: int = 200, min_evidence: int = 3
) -> list[tuple[str, str, float, bool]]:
    """Ordnet Relationen aus KG1 Relationen aus KG2 zu — allein über die Seeds.

    Idee: Wenn (a, b) und (x, y) bekannte Seed-Paare sind und in KG1 gilt
    `a --r1--> x`, in KG2 `b --r2--> y`, dann ist das ein Beleg dafür, dass r1
    und r2 dieselbe Beziehung ausdrücken. Über alle Seeds gezählt ergibt das
    eine Zuordnung, die ohne gemeinsames Vokabular auskommt.

    Zusätzlich wird die **Gegenrichtung** geprüft (`y --r2--> b`): Zwei KGs
    modellieren dieselbe Beziehung oft mit umgekehrter Orientierung, etwa
    `hasCapital` gegenüber `capitalOf`. Ohne diesen Fall wäre die
    Richtungsinformation, die wir gerade nutzen wollen, bei solchen Paaren
    genau falsch herum.

    Rückgabe: (r1, r2, Gewicht, invertiert). Das Gewicht ist die
    Dice-Ähnlichkeit der Belegzahlen, damit häufige Relationen nicht allein
    durch ihre Masse gewinnen.
    """
    seed_map = dict(zip(seeds["e1"], seeds["e2"], strict=False))
    if not seed_map:
        return []

    # Nur die häufigsten Relationen betrachten — der lange Schwanz liefert zu
    # wenig Belege und kostet unverhältnismässig viel Rechenzeit.
    keep1 = set(kg_pair.kg1.rel_triples["relation"].value_counts().head(top_relations).index)
    keep2 = set(kg_pair.kg2.rel_triples["relation"].value_counts().head(top_relations).index)

    # Kanten von KG2 indizieren, in beiden Richtungen.
    forward2: dict[tuple[str, str], set[str]] = {}
    for head, relation, tail in zip(
        kg_pair.kg2.rel_triples["head"],
        kg_pair.kg2.rel_triples["relation"],
        kg_pair.kg2.rel_triples["tail"],
        strict=False,
    ):
        if relation in keep2:
            forward2.setdefault((head, tail), set()).add(relation)

    co: dict[tuple[str, str, bool], int] = {}
    count1: dict[str, int] = {}
    count2: dict[str, int] = {}

    for head, relation, tail in zip(
        kg_pair.kg1.rel_triples["head"],
        kg_pair.kg1.rel_triples["relation"],
        kg_pair.kg1.rel_triples["tail"],
        strict=False,
    ):
        if relation not in keep1:
            continue
        mapped_head, mapped_tail = seed_map.get(head), seed_map.get(tail)
        if mapped_head is None or mapped_tail is None:
            continue
        count1[relation] = count1.get(relation, 0) + 1

        for other in forward2.get((mapped_head, mapped_tail), ()):
            co[(relation, other, False)] = co.get((relation, other, False), 0) + 1
            count2[other] = count2.get(other, 0) + 1
        for other in forward2.get((mapped_tail, mapped_head), ()):
            co[(relation, other, True)] = co.get((relation, other, True), 0) + 1
            count2[other] = count2.get(other, 0) + 1

    candidates = []
    for (r1, r2, inverted), shared in co.items():
        if shared < min_evidence:
            continue
        dice = 2.0 * shared / (count1.get(r1, 0) + count2.get(r2, 0))
        candidates.append((r1, r2, float(dice), inverted))

    # Je KG1-Relation nur die beste Entsprechung behalten.
    best: dict[str, tuple[str, float, bool]] = {}
    for r1, r2, score, inverted in candidates:
        if r1 not in best or score > best[r1][1]:
            best[r1] = (r2, score, inverted)
    return sorted(
        ((r1, r2, s, inv) for r1, (r2, s, inv) in best.items()), key=lambda t: -t[2]
    )


class StructuralPropagationMatcher(SparseScoreMatcher):
    """Typisierte, gerichtete Nachbarschaftspropagation mit Bootstrapping.

    Für jedes alignierte Relationspaar (r1, r2) wird die über die Seeds nach
    KG2 übersetzte r1-Nachbarschaft mit der tatsächlichen r2-Nachbarschaft
    verglichen, getrennt nach Richtung:

        score = Σ_(r1,r2) w(r1,r2) · [ cos(A1ᵒᵘᵗ_r1 · S, A2ᵒᵘᵗ_r2)
                                     + cos(A1ⁱⁿ_r1  · S, A2ⁱⁿ_r2)  ]

    Danach werden die sichersten Treffer als zusätzliche Seeds übernommen und
    die Propagation wiederholt.
    """

    name = "structural_propagation"
    family = "structural"
    requires_seeds = True
    top_k = 10
    # Die Scores sind zeilenweise normiert, deshalb greift der
    # Schwellenwert am Abstand zum Zweitbesten, nicht am Score.
    confidence = "margin"

    def __init__(
        self,
        iterations: int = 5,
        bootstrap_threshold: float = 0.1,   # Mindestabstand zum Zweitbesten
        min_score: float = 0.1,
        top_relations: int = 200,
        use_relation_types: bool = True,
        untyped_weight: float = 0.3,
        directed: bool = True,
    ) -> None:
        self.iterations = iterations
        self.bootstrap_threshold = bootstrap_threshold
        self.min_score = min_score
        self.top_relations = top_relations
        self.use_relation_types = use_relation_types
        # Der untypisierte Kanal laeuft immer mit. Wo das Relations-Alignment
        # wenig findet (YAGO hat nur 28 Relationstypen), bleibt so wenigstens
        # das grobe Nachbarschaftssignal erhalten.
        self.untyped_weight = untyped_weight
        self.directed = directed

    def score_matrix(self, kg_pair: KGPair, seeds: pd.DataFrame | None) -> sp.csr_matrix:
        seeds = seeds if seeds is not None else pd.DataFrame(columns=["e1", "e2"])
        seed_matrix = seeds_to_matrix(seeds, kg_pair)

        if self.use_relation_types:
            aligned = align_relations(kg_pair, seeds, top_relations=self.top_relations)
        else:
            aligned = []

        blocks: list[tuple[tuple[sp.csr_matrix, sp.csr_matrix],
                           tuple[sp.csr_matrix, sp.csr_matrix], float]] = []
        if aligned:
            mats1 = relation_matrices(kg_pair.kg1, [r1 for r1, _, _, _ in aligned])
            mats2 = relation_matrices(kg_pair.kg2, [r2 for _, r2, _, _ in aligned])
            for r1, r2, weight, inverted in aligned:
                if r1 not in mats1 or r2 not in mats2:
                    continue
                out2, in2 = mats2[r2]
                # Bei umgekehrt modellierter Relation zeigt die Gegenrichtung
                # von KG2 auf dieselbe Beziehung.
                target = (in2, out2) if inverted else (out2, in2)
                blocks.append((mats1[r1], target, weight))
        if self.untyped_weight > 0 or not blocks:
            weight = self.untyped_weight if blocks else 1.0
            blocks.append((_untyped(kg_pair.kg1), _untyped(kg_pair.kg2), weight))

        normalized2 = [
            (l2_normalize(out2), l2_normalize(in2), weight)
            for _, (out2, in2), weight in blocks
        ]

        n1 = kg_pair.kg1.n_entities()
        n2 = kg_pair.kg2.n_entities()
        scores = sp.csr_matrix((n1, n2), dtype=np.float32)

        for _ in range(max(self.iterations, 1)):
            total = sp.csr_matrix((n1, n2), dtype=np.float32)
            for (m1, _m2, _w), (out2, in2, weight) in zip(blocks, normalized2, strict=False):
                out1, in1 = m1
                forward = l2_normalize((out1 @ seed_matrix).tocsr()) @ out2.T
                contribution = forward
                if self.directed:
                    contribution = contribution + l2_normalize((in1 @ seed_matrix).tocsr()) @ in2.T
                total = total + contribution.multiply(weight)
                total = topk_per_row(total.tocsr(), self.top_k * 3)

            scores = topk_per_row(_row_normalize(total.tocsr()), self.top_k)
            seed_matrix = self._bootstrap(seed_matrix, scores)

        return scores

    def _bootstrap(self, seeds: sp.csr_matrix, scores: sp.csr_matrix) -> sp.csr_matrix:
        """Übernimmt nur eindeutige Treffer als zusätzliche Seeds.

        Kriterium ist der Abstand zum zweitbesten Kandidaten, nicht der Score:
        die Scores sind zeilenweise auf 1 normiert, ein absoluter Schwellenwert
        wäre hier also wirkungslos.
        """
        rows, cols, margins = top1_margin_per_row(scores)
        keep = margins >= self.bootstrap_threshold
        if not keep.any():
            return seeds
        extra = sp.csr_matrix(
            (np.ones(int(keep.sum()), dtype=np.float32), (rows[keep], cols[keep])),
            shape=seeds.shape,
        )
        merged = (seeds + extra).tocsr()
        merged.data[:] = 1.0
        return merged


def _untyped(kg: KnowledgeGraph) -> tuple[sp.csr_matrix, sp.csr_matrix]:
    """Gerichtete Adjazenz ohne Relationstypen — Ablationsfall."""
    index = kg.entity_index
    n = kg.n_entities()
    heads = kg.rel_triples["head"].map(index)
    tails = kg.rel_triples["tail"].map(index)
    mask = heads.notna() & tails.notna()
    rows = heads[mask].to_numpy(dtype=np.int32)
    cols = tails[mask].to_numpy(dtype=np.int32)
    forward = sp.csr_matrix(
        (np.ones(rows.size, dtype=np.float32), (rows, cols)), shape=(n, n)
    )
    return forward, forward.T.tocsr()


def _row_normalize(matrix: sp.csr_matrix) -> sp.csr_matrix:
    """Skaliert jede Zeile auf Maximum 1.

    Nötig, weil sich die Beiträge der alignierten Relationen aufsummieren und
    der Wertebereich sonst von der Anzahl der Relationen abhinge — ein
    Schwellenwert wäre dann nicht mehr über Datensätze hinweg vergleichbar.
    """
    matrix = matrix.tocsr()
    if matrix.nnz == 0:
        return matrix

    peaks = matrix.max(axis=1).toarray().ravel()
    peaks[peaks == 0] = 1.0
    return (sp.diags(1.0 / peaks) @ matrix).tocsr()


def adjacency(kg: KnowledgeGraph) -> sp.csr_matrix:
    """Symmetrische, ungewichtete Adjazenz — für Metriken und Tests."""
    forward, _ = _untyped(kg)
    sym = forward + forward.T
    sym.data[:] = 1.0
    return sym.tocsr()
