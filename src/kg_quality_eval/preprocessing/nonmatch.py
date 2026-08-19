"""Erzeugt Benchmark-Varianten mit Entitäten ohne Gegenstück.

Die OpenEA-Benchmarks sind strikt bijektiv: jede Entität in KG1 hat genau eine
in KG2 und umgekehrt (`alignment_coverage` = 1,0, `bijective_share` = 1,0). Das
ist praxisfern — in echter Datenintegration hat die Mehrheit der Entitäten kein
Gegenstück — und es verdeckt einen konkreten Fehler: Ohne Non-Matches ist es
immer richtig, für jede Entität *irgendeinen* Partner vorherzusagen. Ein
Matcher ohne Schwellenwert wird dafür nie bestraft.

Dieses Modul bricht die Bijektivität kontrolliert auf. Aus dem Referenz-
Alignment werden drei Gruppen gebildet:

    keep         beide Seiten bleiben -> weiterhin ein Gold-Paar
    drop_left    die KG1-Seite wird entfernt -> die KG2-Seite wird partnerlos
    drop_right   die KG2-Seite wird entfernt -> die KG1-Seite wird partnerlos

Alle Tripel entfernter Entitäten verschwinden mit. Übrig bleibt ein kleinerer,
aber realistischerer Benchmark, in dem ein Teil der Entitäten korrekterweise
*keinen* Match hat.

Partnerlose KG1-Entitäten bleiben als Alignment-Zeile mit leerem `e2` erhalten.
Sie gehören damit weiterhin zum Auswertungsumfang, und eine Vorhersage für sie
zählt als False Positive — genau das soll gemessen werden.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from kg_quality_eval.core import KGPair, KnowledgeGraph


def inject_non_matches(
    kg_pair: KGPair, match_ratio: float = 0.5, seed: int = 42
) -> KGPair:
    """Bricht die 1:1-Struktur auf.

    `match_ratio` ist der Anteil der Gold-Paare, der intakt bleibt. Der Rest
    wird je zur Hälfte auf `drop_left` und `drop_right` verteilt, sodass beide
    Graphen partnerlose Entitäten bekommen.

    Bei `match_ratio = 0.5` behält ein 15 000er Benchmark 7 500 Gold-Paare;
    KG1 und KG2 haben danach je 11 250 Entitäten, davon 3 750 ohne Partner
    (33 % Non-Match-Quote).
    """
    if not 0.0 < match_ratio <= 1.0:
        raise ValueError(f"match_ratio muss in (0, 1] liegen, war {match_ratio}")

    pairs = kg_pair.matched().drop_duplicates(subset=["e1", "e2"])
    if pairs.empty:
        return kg_pair

    # Stabil sortieren, bevor gezogen wird. Die Zeilenreihenfolge des
    # Alignment-Frames haengt vom gewaehlten Fold ab (train/valid/test werden in
    # dieser Reihenfolge konkateniert); ohne Sortierung wuerden je Fold andere
    # Entitaeten entfernt, und eine Fold-Streuung ueber Non-Match-Varianten
    # mischte zwei Quellen.
    pairs = pairs.sort_values(["e1", "e2"], kind="stable").reset_index(drop=True)

    rng = np.random.default_rng(seed)
    order = rng.permutation(len(pairs))

    n_keep = int(round(len(pairs) * match_ratio))
    n_rest = len(pairs) - n_keep
    n_drop_left = n_rest // 2

    keep_idx = order[:n_keep]
    drop_left_idx = order[n_keep : n_keep + n_drop_left]
    drop_right_idx = order[n_keep + n_drop_left :]

    keep = pairs.iloc[keep_idx]
    drop_left = pairs.iloc[drop_left_idx]     # KG1-Seite fliegt raus
    drop_right = pairs.iloc[drop_right_idx]   # KG2-Seite fliegt raus

    removed_1 = set(drop_left["e1"])
    removed_2 = set(drop_right["e2"])

    kg1 = _drop_entities(kg_pair.kg1, removed_1)
    kg2 = _drop_entities(kg_pair.kg2, removed_2)

    # Die KG1-Seite eines drop_right-Paares bleibt bestehen, hat aber jetzt
    # keinen Partner mehr: als Zeile mit leerem e2 im Auswertungsumfang halten.
    orphans_1 = pd.DataFrame(
        {"e1": drop_right["e1"].to_numpy(), "e2": "", "split": drop_right["split"].to_numpy()}
    )
    alignments = pd.concat([keep, orphans_1], ignore_index=True)

    meta = dict(kg_pair.meta)
    meta.update(
        {
            "non_match_variant": True,
            "match_ratio": match_ratio,
            "non_match_seed": seed,
            "n_gold_pairs": int(len(keep)),
            "n_unmatched_kg1": int(len(drop_right)),
            "n_unmatched_kg2": int(len(drop_left)),
            "source_pairs": int(len(pairs)),
        }
    )

    return KGPair(
        name=kg_pair.name,
        kg1=kg1,
        kg2=kg2,
        alignments=alignments.reset_index(drop=True),
        meta=meta,
    )


def _drop_entities(kg: KnowledgeGraph, removed: set[str]) -> KnowledgeGraph:
    """Entfernt Entitäten samt aller Tripel, in denen sie vorkommen."""
    if not removed:
        return kg

    rel = kg.rel_triples
    rel = rel[~rel["head"].isin(removed) & ~rel["tail"].isin(removed)]

    attr = kg.attr_triples
    attr = attr[~attr["head"].isin(removed)]

    entities = kg.entities[~kg.entities["entity_uri"].isin(removed)]

    # replace() statt Mutation, damit die cached_property-Werte des Originals
    # (degrees, entity_index) nicht mit umziehen.
    return replace(
        kg,
        entities=entities.reset_index(drop=True),
        rel_triples=rel.reset_index(drop=True),
        attr_triples=attr.reset_index(drop=True),
    )


def summarize_variant(original: KGPair, variant: KGPair) -> dict[str, float]:
    """Kennzahlen für den Vorher-Nachher-Vergleich einer Variante."""
    n1, n2 = variant.kg1.n_entities(), variant.kg2.n_entities()
    return {
        "orig_entities_kg1": float(original.kg1.n_entities()),
        "orig_gold_pairs": float(original.n_matched()),
        "entities_kg1": float(n1),
        "entities_kg2": float(n2),
        "gold_pairs": float(variant.n_matched()),
        "unmatched_kg1": float(len(variant.unmatched())),
        "non_match_share_kg1": float(len(variant.unmatched()) / n1) if n1 else 0.0,
        "alignment_coverage": float(variant.n_matched() / min(n1, n2)) if min(n1, n2) else 0.0,
        "rel_triples_kg1": float(variant.kg1.n_rel_triples()),
        "rel_triples_kg2": float(variant.kg2.n_rel_triples()),
    }
