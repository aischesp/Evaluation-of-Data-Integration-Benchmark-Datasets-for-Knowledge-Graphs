"""Matcher interface and the sparse machinery all in-house matchers share.

A matcher turns a KGPair into a set of predicted entity pairs. Most of ours
work the same way: build a sparse candidate-score matrix over KG1 x KG2, prune
it to the top-k candidates per row, then reduce it to one prediction per entity.
That common part lives in `SparseScoreMatcher` so the individual matchers only
have to define how the score matrix is built.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import scipy.sparse as sp

from kg_quality_eval.core import KGPair


@dataclass
class MatchResult:
    """Predictions of one matcher on one dataset."""

    matcher: str
    dataset: str
    pairs: pd.DataFrame           # columns: [e1, e2, score]
    runtime_s: float
    meta: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.pairs)


class BaseMatcher(ABC):
    """One subclass per entity-alignment approach."""

    name: str = "base"
    requires_seeds: bool = False
    family: str = "other"  # textual | structural | hybrid | holistic

    @abstractmethod
    def match(self, kg_pair: KGPair, seeds: pd.DataFrame | None = None) -> MatchResult:
        """Predict entity pairs. `seeds` holds the training alignment, if allowed."""
        ...


class SparseScoreMatcher(BaseMatcher):
    """Base for matchers that express themselves as a sparse similarity matrix."""

    top_k: int = 10
    min_score: float = 0.0

    @abstractmethod
    def score_matrix(self, kg_pair: KGPair, seeds: pd.DataFrame | None) -> sp.csr_matrix:
        """Sparse |E1| x |E2| candidate scores, already pruned to top_k per row."""
        ...

    def match(self, kg_pair: KGPair, seeds: pd.DataFrame | None = None) -> MatchResult:
        start = time.perf_counter()
        scores = self.score_matrix(kg_pair, seeds)
        pairs = self._reduce(scores, kg_pair)
        return MatchResult(
            matcher=self.name,
            dataset=kg_pair.name,
            pairs=pairs,
            runtime_s=time.perf_counter() - start,
            meta={"family": self.family, "n_candidates": int(scores.nnz)},
        )

    def _reduce(self, scores: sp.csr_matrix, kg_pair: KGPair) -> pd.DataFrame:
        """Sparse score matrix -> one predicted partner per KG1 entity."""
        e1_uris = kg_pair.kg1.entities["entity_uri"].to_numpy()
        e2_uris = kg_pair.kg2.entities["entity_uri"].to_numpy()

        rows, cols, vals = argmax_per_row(scores)
        keep = vals > self.min_score
        rows, cols, vals = rows[keep], cols[keep], vals[keep]

        return pd.DataFrame({"e1": e1_uris[rows], "e2": e2_uris[cols], "score": vals})


def argmax_per_row(matrix: sp.csr_matrix) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Highest-scoring column per non-empty row of a CSR matrix."""
    matrix = matrix.tocsr()
    rows, cols, vals = [], [], []
    indptr, indices, data = matrix.indptr, matrix.indices, matrix.data

    for r in range(matrix.shape[0]):
        lo, hi = indptr[r], indptr[r + 1]
        if lo == hi:
            continue
        best = lo + int(np.argmax(data[lo:hi]))
        rows.append(r)
        cols.append(int(indices[best]))
        vals.append(float(data[best]))

    return np.asarray(rows, dtype=int), np.asarray(cols, dtype=int), np.asarray(vals, dtype=float)


def topk_per_row(matrix: sp.csr_matrix, k: int) -> sp.csr_matrix:
    """Keep only the k largest entries of every row. Keeps memory bounded."""
    matrix = matrix.tocsr()
    indptr, indices, data = matrix.indptr, matrix.indices, matrix.data

    new_rows, new_cols, new_data = [], [], []
    for r in range(matrix.shape[0]):
        lo, hi = indptr[r], indptr[r + 1]
        if lo == hi:
            continue
        row_data = data[lo:hi]
        if row_data.size > k:
            sel = np.argpartition(row_data, -k)[-k:]
        else:
            sel = np.arange(row_data.size)
        new_rows.append(np.full(sel.size, r, dtype=np.int32))
        new_cols.append(indices[lo:hi][sel])
        new_data.append(row_data[sel])

    if not new_rows:
        return sp.csr_matrix(matrix.shape, dtype=np.float32)

    return sp.csr_matrix(
        (np.concatenate(new_data), (np.concatenate(new_rows), np.concatenate(new_cols))),
        shape=matrix.shape,
        dtype=np.float32,
    )


def sparse_cosine_topk(
    a: sp.csr_matrix, b: sp.csr_matrix, k: int = 10, chunk: int = 500
) -> sp.csr_matrix:
    """Row-wise top-k cosine similarity between two L2-normalised sparse matrices.

    The product is computed in row chunks and pruned immediately, so the dense
    intermediate never materialises — this is what makes the 100 K dataset fit
    into memory.
    """
    a = sp.csr_matrix(a, dtype=np.float32)
    bt = sp.csr_matrix(b, dtype=np.float32).T.tocsc()

    blocks = []
    for start in range(0, a.shape[0], chunk):
        block = (a[start : start + chunk] @ bt).tocsr()
        blocks.append(topk_per_row(block, k))

    return sp.vstack(blocks, format="csr") if blocks else sp.csr_matrix((a.shape[0], b.shape[0]))


def l2_normalize(matrix: sp.csr_matrix) -> sp.csr_matrix:
    """Scale every row to unit L2 norm; empty rows stay empty."""
    matrix = sp.csr_matrix(matrix, dtype=np.float32)
    norms = np.sqrt(matrix.multiply(matrix).sum(axis=1)).A.ravel()
    norms[norms == 0] = 1.0
    return sp.diags(1.0 / norms) @ matrix


def seeds_to_matrix(
    seeds: pd.DataFrame | None, kg_pair: KGPair
) -> sp.csr_matrix:
    """Training alignment as a sparse |E1| x |E2| indicator matrix."""
    n1, n2 = kg_pair.kg1.n_entities(), kg_pair.kg2.n_entities()
    if seeds is None or seeds.empty:
        return sp.csr_matrix((n1, n2), dtype=np.float32)

    idx1, idx2 = kg_pair.kg1.entity_index, kg_pair.kg2.entity_index
    rows, cols = [], []
    for e1, e2 in zip(seeds["e1"], seeds["e2"], strict=False):
        i, j = idx1.get(e1), idx2.get(e2)
        if i is not None and j is not None:
            rows.append(i)
            cols.append(j)

    return sp.csr_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(n1, n2)
    )
