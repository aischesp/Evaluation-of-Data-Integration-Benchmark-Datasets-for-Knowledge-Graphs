"""Attribute-based (textual) matchers.

These are the "encode the entity as text, then compare the text" family the
supervisor described. They ignore the graph structure completely, which is
exactly what makes them useful for the correlation study: their performance
should track attribute completeness, not degree.

Note on the OpenEA v2.0 datasets: entity URIs are deliberately anonymised
(`.../resource/E399772`) and there are no rdfs:label triples, so the only
textual signal comes from the literal values of attribute triples. We
therefore never touch the URI itself — a matcher that did would only measure
the name bias that v2.0 was built to remove.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.matching.base import SparseScoreMatcher, l2_normalize, sparse_cosine_topk
from kg_quality_eval.utils.literals import normalize_value, tokenize


def _entity_documents(kg: KnowledgeGraph) -> list[list[str]]:
    """Bag of literal tokens per entity, in entity-index order."""
    index = kg.entity_index
    docs: list[list[str]] = [[] for _ in range(kg.n_entities())]
    for head, literal in zip(kg.attr_triples["head"], kg.attr_triples["literal"], strict=False):
        i = index.get(head)
        if i is not None:
            docs[i].extend(tokenize(literal))
    return docs


def _entity_values(kg: KnowledgeGraph) -> list[list[str]]:
    """Set of whole normalised literal values per entity, in entity-index order."""
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


def _tfidf(
    docs1: list[list[str]], docs2: list[list[str]], max_df_ratio: float
) -> tuple[sp.csr_matrix, sp.csr_matrix]:
    """Joint TF-IDF over both KGs so the two matrices live in the same space.

    Terms that occur in more than `max_df_ratio` of all documents are dropped:
    they cost a lot of memory in the sparse product and carry almost no signal
    (they are the stop words of this corpus).
    """
    n_docs = len(docs1) + len(docs2)
    df: dict[str, int] = {}
    for doc in (*docs1, *docs2):
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    max_df = max(int(max_df_ratio * n_docs), 2)
    kept = sorted(t for t, c in df.items() if 2 <= c <= max_df)
    vocab = {t: i for i, t in enumerate(kept)}
    idf = np.zeros(len(vocab), dtype=np.float32)
    for term, i in vocab.items():
        idf[i] = np.log(n_docs / df[term]) + 1.0

    def build(docs: list[list[str]]) -> sp.csr_matrix:
        rows, cols, data = [], [], []
        for r, doc in enumerate(docs):
            counts: dict[int, int] = {}
            for term in doc:
                j = vocab.get(term)
                if j is not None:
                    counts[j] = counts.get(j, 0) + 1
            for j, c in counts.items():
                rows.append(r)
                cols.append(j)
                data.append((1.0 + np.log(c)) * idf[j])  # sublinear tf
        matrix = sp.csr_matrix(
            (np.asarray(data, dtype=np.float32), (rows, cols)),
            shape=(len(docs), len(vocab)),
        )
        return l2_normalize(matrix)

    return build(docs1), build(docs2)


class LiteralTFIDFMatcher(SparseScoreMatcher):
    """TF-IDF cosine similarity over the literal tokens of each entity.

    The classic textual baseline: every entity becomes a bag of words built
    from all its attribute values, and we take the nearest neighbour in the
    other KG.
    """

    name = "literal_tfidf"
    family = "textual"
    top_k = 10
    min_score = 0.0

    def __init__(self, max_df_ratio: float = 0.01, chunk: int = 500) -> None:
        self.max_df_ratio = max_df_ratio
        self.chunk = chunk

    def score_matrix(self, kg_pair: KGPair, seeds: pd.DataFrame | None) -> sp.csr_matrix:
        a, b = _tfidf(
            _entity_documents(kg_pair.kg1),
            _entity_documents(kg_pair.kg2),
            self.max_df_ratio,
        )
        return sparse_cosine_topk(a, b, k=self.top_k, chunk=self.chunk)


class ValueOverlapMatcher(SparseScoreMatcher):
    """IDF-weighted overlap of whole literal *values* (not tokens).

    Complements the TF-IDF matcher: a shared birth date or a shared external
    identifier is a much stronger signal than a shared word, and this matcher
    only fires on such exact value matches. It is also very cheap, because rare
    values act as blocking keys.
    """

    name = "value_overlap"
    family = "textual"
    top_k = 10
    min_score = 0.0

    def __init__(self, max_df_ratio: float = 0.01, chunk: int = 500) -> None:
        self.max_df_ratio = max_df_ratio
        self.chunk = chunk

    def score_matrix(self, kg_pair: KGPair, seeds: pd.DataFrame | None) -> sp.csr_matrix:
        a, b = _tfidf(
            _entity_values(kg_pair.kg1),
            _entity_values(kg_pair.kg2),
            self.max_df_ratio,
        )
        return sparse_cosine_topk(a, b, k=self.top_k, chunk=self.chunk)
