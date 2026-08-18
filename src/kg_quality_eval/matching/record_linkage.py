"""Wertbasiertes Matching über pyJedAI — eine etablierte Record-Linkage-Bibliothek.

Warum eine Bibliothek statt einer Eigenimplementierung: Ein wertbasierter
Matcher braucht mehr als eine Ähnlichkeitsfunktion. Er braucht Blocking (damit
nicht |E1| x |E2| Paare verglichen werden), Block-Bereinigung (überfüllte Blöcke
tragen nichts bei), Kandidaten-Pruning, eine kalibrierte Ähnlichkeit und eine
Zuordnungsstufe, die aus Kandidatenpaaren eine 1:1-Abbildung macht. All das ist
in pyJedAI implementiert und getestet; selbst geschrieben wäre es genau die Art
von Rad-Neuerfindung, die man vermeiden sollte.

Der Workflow entspricht dem Standard-Rezept für Clean-Clean Entity Resolution:

    StandardBlocking -> BlockPurging -> BlockFiltering -> WeightedEdgePruning
    -> EntityMatching (Zeichen-n-Gramme, Kosinus) -> UniqueMappingClustering

`UniqueMappingClustering` bekommt einen echten Schwellenwert: Paare darunter
werden verworfen, statt den besten verfügbaren Kandidaten zu nehmen.

pyJedAI arbeitet auf Tabellen, nicht auf Graphen. Jede Entität wird deshalb zu
einem Record mit einem Textfeld aus ihren Attributwerten verdichtet — das ist
die übliche Repräsentation für Record Linkage und der Grund, warum dieses
Verfahren die Graphstruktur bewusst nicht sieht.
"""

from __future__ import annotations

import logging
import time
import warnings

import pandas as pd

from kg_quality_eval.core import KGPair, KnowledgeGraph
from kg_quality_eval.matching.base import BaseMatcher, MatchResult
from kg_quality_eval.utils.literals import normalize_value

log = logging.getLogger("kg_quality_eval")


def entity_records(kg: KnowledgeGraph) -> pd.DataFrame:
    """Eine Entität -> ein Record mit ihren normalisierten Attributwerten."""
    attr = kg.attr_triples
    values = (
        attr.assign(_v=[normalize_value(v) for v in attr["literal"]])
        .query("_v != ''")
        .groupby("head")["_v"]
        .apply(lambda s: " ".join(sorted(set(s))))
    )
    frame = pd.DataFrame({"id": kg.entities["entity_uri"].to_numpy()})
    frame["values"] = frame["id"].map(values).fillna("")
    return frame.reset_index(drop=True)


class PyJedAIMatcher(BaseMatcher):
    """Wertbasiertes Matching mit dem Standard-Workflow von pyJedAI."""

    name = "pyjedai_ngram"
    family = "value"
    requires_seeds = False

    def __init__(
        self,
        similarity_threshold: float = 0.2,
        qgram: int = 3,
        metric: str = "cosine",
        tokenizer: str = "char_tokenizer",
        weighting_scheme: str = "EJS",
        max_entities: int | None = 60_000,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.qgram = qgram
        self.metric = metric
        self.tokenizer = tokenizer
        self.weighting_scheme = weighting_scheme
        # pyJedAI baut einen expliziten Kandidatengraphen; auf den 100K-Varianten
        # sprengt das die Laufzeit. Oberhalb dieser Grenze wird übersprungen und
        # das in der Auswertung als fehlender Wert ausgewiesen.
        self.max_entities = max_entities

    def match(self, kg_pair: KGPair, seeds: pd.DataFrame | None = None) -> MatchResult:
        n_max = max(kg_pair.kg1.n_entities(), kg_pair.kg2.n_entities())
        if self.max_entities is not None and n_max > self.max_entities:
            raise RuntimeError(
                f"{self.name}: {n_max} Entitäten überschreiten das Limit "
                f"{self.max_entities} (Laufzeit); Datensatz übersprungen."
            )

        start = time.perf_counter()
        pairs = self._run(kg_pair)
        return MatchResult(
            matcher=self.name,
            dataset=kg_pair.name,
            pairs=pairs,
            runtime_s=time.perf_counter() - start,
            meta={
                "family": self.family,
                "library": "pyjedai",
                "similarity_threshold": self.similarity_threshold,
                "qgram": self.qgram,
            },
        )

    def build_candidate_graph(self, kg_pair: KGPair):
        """Blocking + Ähnlichkeitsberechnung — der schwellenwertunabhängige Teil.

        Getrennt herausgezogen, damit ein Threshold-Sweep den teuren Teil nur
        einmal rechnen muss (siehe scripts/tune_thresholds.py).
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from pyjedai.block_building import StandardBlocking
            from pyjedai.block_cleaning import BlockFiltering, BlockPurging
            from pyjedai.comparison_cleaning import WeightedEdgePruning
            from pyjedai.datamodel import Data
            from pyjedai.matching import EntityMatching

            left = entity_records(kg_pair.kg1)
            right = entity_records(kg_pair.kg2)
            gold = (
                kg_pair.matched()[["e1", "e2"]]
                .rename(columns={"e1": "l", "e2": "r"})
                .reset_index(drop=True)
            )

            data = Data(
                dataset_1=left, id_column_name_1="id",
                dataset_2=right, id_column_name_2="id",
                ground_truth=gold,
            )

            blocks = StandardBlocking().build_blocks(data, tqdm_disable=True)
            blocks = BlockPurging().process(blocks, data, tqdm_disable=True)
            blocks = BlockFiltering().process(blocks, data, tqdm_disable=True)
            blocks = WeightedEdgePruning(weighting_scheme=self.weighting_scheme).process(
                blocks, data, tqdm_disable=True
            )

            graph = EntityMatching(
                metric=self.metric,
                tokenizer=self.tokenizer,
                qgram=self.qgram,
                similarity_threshold=0.0,   # Filterung passiert im Clustering
            ).predict(blocks, data, tqdm_disable=True)

        return graph, data, left, right

    def cluster(self, graph, data, left, right, threshold: float) -> pd.DataFrame:
        """Schwellenwertabhängiger Teil: Kandidatengraph -> eindeutige Zuordnung."""
        from pyjedai.clustering import UniqueMappingClustering

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            clusters = UniqueMappingClustering().process(
                graph, data, similarity_threshold=threshold
            )
        return self._clusters_to_pairs(clusters, graph, left, right)

    def _run(self, kg_pair: KGPair) -> pd.DataFrame:
        graph, data, left, right = self.build_candidate_graph(kg_pair)
        return self.cluster(graph, data, left, right, self.similarity_threshold)

    @staticmethod
    def _clusters_to_pairs(clusters, graph, left: pd.DataFrame, right: pd.DataFrame):
        """pyJedAI-Cluster -> unser (e1, e2, score)-Format.

        Cluster sind Knotenmengen über einen gemeinsamen Index: Positionen
        < len(left) gehören zu KG1, alles darüber zu KG2 (versetzt um len(left)).
        """
        n_left = len(left)
        left_ids = left["id"].to_numpy()
        right_ids = right["id"].to_numpy()

        rows = []
        for cluster in clusters:
            members = list(cluster)
            first = [m for m in members if m < n_left]
            second = [m for m in members if m >= n_left]
            if len(first) != 1 or len(second) != 1:
                continue
            i, j = first[0], second[0]
            score = 1.0
            if graph.has_edge(i, j):
                score = float(graph[i][j].get("weight", 1.0))
            rows.append((left_ids[i], right_ids[j - n_left], score))

        return pd.DataFrame(rows, columns=["e1", "e2", "score"])
