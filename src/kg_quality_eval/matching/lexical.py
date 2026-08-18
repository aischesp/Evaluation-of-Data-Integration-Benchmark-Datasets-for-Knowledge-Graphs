"""Wertbasierter Matcher auf Basis exakter Literalwert-Überlappung.

Das ist bewusst das einfachste sinnvolle Verfahren und dient als Baseline: zwei
Entitäten gelten als ähnlich, wenn sie dieselben Attributwerte tragen. Seltene
Werte — ein Geburtsdatum, eine externe Kennung — sind dabei viel
aussagekräftiger als häufige, deshalb werden die Werte IDF-gewichtet.

Abgrenzung zu `pyjedai_ngram`: dieser Matcher vergleicht *ganze* Werte exakt,
der andere Zeichen-n-Gramme über eine etablierte Record-Linkage-Bibliothek. Auf
Daten, deren Literale überwiegend Datumsangaben und Zahlen sind, ist exakte
Wertgleichheit das schärfere Signal; bei Schreibvarianten ist es das n-Gramm.
Beide zusammen zeigen, welches Signal ein Benchmark eigentlich hergibt.

Der Schwellenwert ist ein echter Parameter: unterhalb davon gibt der Matcher
keine Vorhersage ab. Ohne ihn wäre auch ein Score von 0,01 noch "der beste
Kandidat", was auf Benchmarks mit partnerlosen Entitäten direkt zu False
Positives führt.

Hinweis zu OpenEA v2.0: Die Entitäts-URIs sind anonymisiert und es gibt keine
Labels. Das einzige textuelle Signal sind die Literalwerte der Attribut-Tripel.
Die URI selbst wird nie gelesen — ein Matcher, der das täte, würde nur den
Name Bias messen, den v2.0 gerade entfernen soll.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.matching.base import SparseScoreMatcher, l2_normalize, sparse_cosine_topk
from kg_quality_eval.utils.literals import normalize_value


def _entity_values(kg: KnowledgeGraph) -> list[list[str]]:
    """Menge der normalisierten Literalwerte je Entität, in Entity-Index-Reihenfolge."""
    index = kg.entity_index
    docs: list[set[str]] = [set() for _ in range(kg.n_entities())]
    for head, literal in zip(kg.attr_triples["head"], kg.attr_triples["literal"], strict=False):
        i = index.get(head)
        if i is None:
            continue
        value = normalize_value(literal)
        if value:
            docs[i].add(value)
    return [sorted(d) for d in docs]


def _idf_matrices(
    docs1: list[list[str]], docs2: list[list[str]], max_df_ratio: float
) -> tuple[sp.csr_matrix, sp.csr_matrix]:
    """Gemeinsamer IDF-Raum über beide KGs, L2-normalisiert.

    Werte, die in mehr als `max_df_ratio` aller Entitäten vorkommen, fliegen
    raus: sie sind die Stoppwörter dieses Korpus, tragen kaum Information und
    verursachen den Grossteil der Dichte im Ähnlichkeitsprodukt.
    """
    n_docs = len(docs1) + len(docs2)
    df: dict[str, int] = {}
    for doc in (*docs1, *docs2):
        for value in set(doc):
            df[value] = df.get(value, 0) + 1

    max_df = max(int(max_df_ratio * n_docs), 2)
    kept = sorted(v for v, c in df.items() if 2 <= c <= max_df)
    vocab = {v: i for i, v in enumerate(kept)}
    idf = np.zeros(len(vocab), dtype=np.float32)
    for value, i in vocab.items():
        idf[i] = np.log(n_docs / df[value]) + 1.0

    def build(docs: list[list[str]]) -> sp.csr_matrix:
        rows, cols, data = [], [], []
        for r, doc in enumerate(docs):
            for value in doc:
                j = vocab.get(value)
                if j is not None:
                    rows.append(r)
                    cols.append(j)
                    data.append(idf[j])
        matrix = sp.csr_matrix(
            (np.asarray(data, dtype=np.float32), (rows, cols)),
            shape=(len(docs), len(vocab)),
        )
        return l2_normalize(matrix)

    return build(docs1), build(docs2)


class ValueOverlapMatcher(SparseScoreMatcher):
    """IDF-gewichtete Kosinus-Ähnlichkeit über exakte Literalwerte."""

    name = "value_overlap"
    family = "value"
    top_k = 10

    def __init__(
        self, min_score: float = 0.4, max_df_ratio: float = 0.01, chunk: int = 500
    ) -> None:
        self.min_score = min_score
        self.max_df_ratio = max_df_ratio
        self.chunk = chunk

    def score_matrix(self, kg_pair: KGPair, seeds: pd.DataFrame | None) -> sp.csr_matrix:
        a, b = _idf_matrices(
            _entity_values(kg_pair.kg1), _entity_values(kg_pair.kg2), self.max_df_ratio
        )
        return sparse_cosine_topk(a, b, k=self.top_k, chunk=self.chunk)
