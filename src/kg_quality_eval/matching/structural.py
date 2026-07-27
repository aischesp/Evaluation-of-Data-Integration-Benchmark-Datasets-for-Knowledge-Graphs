"""Structure-based matchers.

Where the textual matchers encode an entity as a bag of words, these encode it
as its neighbourhood in the graph: two entities match if their neighbours match.
That makes them the natural counterpart in the correlation study — they should
depend on degree and connectivity rather than on attribute completeness.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.matching.base import (
    SparseScoreMatcher,
    argmax_per_row,
    l2_normalize,
    seeds_to_matrix,
    topk_per_row,
)


def adjacency(kg: KnowledgeGraph) -> sp.csr_matrix:
    """Symmetric binary adjacency matrix of the relation graph."""
    index = kg.entity_index
    n = kg.n_entities()

    heads = kg.rel_triples["head"].map(index)
    tails = kg.rel_triples["tail"].map(index)
    mask = heads.notna() & tails.notna()
    rows = heads[mask].to_numpy(dtype=np.int32)
    cols = tails[mask].to_numpy(dtype=np.int32)

    a = sp.csr_matrix(
        (np.ones(rows.size, dtype=np.float32), (rows, cols)), shape=(n, n)
    )
    a = a + a.T
    a.data[:] = 1.0  # collapse parallel edges
    return a.tocsr()


class StructuralPropagationMatcher(SparseScoreMatcher):
    """Seed-based neighbourhood propagation with bootstrapping.

    Given a seed alignment S, the neighbourhood of an entity in KG1 is
    translated into KG2 via S, and candidates are scored by the cosine
    similarity between that translated neighbourhood and their own
    neighbourhood:

        score = cos( A1 · S , A2 )

    After each round the most confident new predictions are added to the seed
    set and the propagation is repeated — the same bootstrapping idea that
    BootEA uses, but without any embedding training.

    Purely structural: no literal is ever read.
    """

    name = "structural_propagation"
    family = "structural"
    requires_seeds = True
    top_k = 10
    min_score = 0.0

    # Defaults selected on the *valid* split of EN_FR_15K_V1 and D_W_15K_V1,
    # never on test (see docs/Ergebnisse.md).
    def __init__(self, iterations: int = 3, bootstrap_threshold: float = 0.3) -> None:
        self.iterations = iterations
        self.bootstrap_threshold = bootstrap_threshold

    def score_matrix(self, kg_pair: KGPair, seeds: pd.DataFrame | None) -> sp.csr_matrix:
        a1 = adjacency(kg_pair.kg1)
        a2n = l2_normalize(adjacency(kg_pair.kg2))
        s = seeds_to_matrix(seeds, kg_pair)

        scores = sp.csr_matrix((a1.shape[0], a2n.shape[0]), dtype=np.float32)
        for _ in range(max(self.iterations, 1)):
            projected = l2_normalize((a1 @ s).tocsr())
            scores = topk_per_row((projected @ a2n.T).tocsr(), self.top_k)
            s = self._bootstrap(s, scores)

        return scores

    def _bootstrap(self, seeds: sp.csr_matrix, scores: sp.csr_matrix) -> sp.csr_matrix:
        """Add confident top-1 predictions to the seed matrix for the next round."""
        rows, cols, vals = argmax_per_row(scores)
        keep = vals >= self.bootstrap_threshold
        if not keep.any():
            return seeds

        extra = sp.csr_matrix(
            (np.ones(keep.sum(), dtype=np.float32), (rows[keep], cols[keep])),
            shape=seeds.shape,
        )
        merged = (seeds + extra).tocsr()
        merged.data[:] = 1.0
        return merged


class HybridMatcher(SparseScoreMatcher):
    """Linear combination of a textual and a structural score matrix.

    Included to show that the two signals are complementary: the datasets where
    the hybrid gains most over its parts are exactly the ones where neither
    signal alone is sufficient.
    """

    name = "hybrid"
    family = "hybrid"
    requires_seeds = True
    top_k = 10

    def __init__(self, weight_textual: float = 0.5) -> None:
        from kg_quality_eval.matching.lexical import LiteralTFIDFMatcher

        self.weight_textual = weight_textual
        self.textual = LiteralTFIDFMatcher()
        self.structural = StructuralPropagationMatcher()

    def score_matrix(self, kg_pair: KGPair, seeds: pd.DataFrame | None) -> sp.csr_matrix:
        text = _max_normalize(self.textual.score_matrix(kg_pair, seeds))
        struct = _max_normalize(self.structural.score_matrix(kg_pair, seeds))

        combined = (self.weight_textual * text) + ((1.0 - self.weight_textual) * struct)
        return topk_per_row(combined.tocsr(), self.top_k)


def _max_normalize(matrix: sp.csr_matrix) -> sp.csr_matrix:
    """Scale scores to [0, 1] so the two matchers contribute on the same scale."""
    matrix = matrix.tocsr()
    if matrix.nnz == 0:
        return matrix
    peak = float(matrix.data.max())
    if peak > 0:
        matrix = matrix.multiply(1.0 / peak).tocsr()
    return matrix
