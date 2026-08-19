"""Fehler-Taxonomie: warum genau scheitert ein Matcher an einem Gold-Paar?

Die Korrelationsanalyse sagt, *dass* eine Datensatz-Eigenschaft mit der
Matching-Güte zusammenhängt. Sie sagt nicht, *wodurch*. Dieses Modul schliesst
die Lücke auf Einzelfallebene: jede Test-Entität wird einer Fehlerklasse
zugeordnet, und die Klassen sind so gewählt, dass sie direkt auf die Metriken
des Katalogs zurückzeigen.

Die Klassifikation ist eine Kaskade — die erste zutreffende Regel gewinnt, von
"gar nicht lösbar" hin zu "lösbar, aber falsch gelöst":

| Klasse | Bedeutung | zugehörige Metrik |
| ------ | --------- | ----------------- |
| `correct` | Top-1-Vorhersage ist das Gold-Paar | — |
| `no_signal` | Entität hat weder Relations- noch Attribut-Tripel | `share_no_information` |
| `structurally_unreachable` | eine Seite ohne Kante oder ausserhalb der grössten Komponente | `alignment_reachability` |
| `no_shared_literal` | Gold-Paar teilt keinen einzigen Literalwert | `literal_value_jaccard` |
| `abstained` | Matcher hat sich enthalten, obwohl es ein Gold-Paar gibt | `abstain_rate` |
| `false_on_unmatched` | Vorhersage für eine Entität, die korrekt keinen Partner hat | `n_false_on_unmatched` |
| `wrong_candidate` | falscher Partner gewählt, obwohl Signal vorhanden war | Rest |

**Die Zuordnung ist familienabhängig, und das ist der Kern.** Ein rein
struktureller Matcher liest keine Literale — ihm "fehlende Literal-Überlappung"
als Fehlerursache zuzuschreiben wäre sinnlos. Umgekehrt ist ein wertbasierter
Matcher nicht davon betroffen, ob die Gold-Entitäten in derselben
Zusammenhangskomponente liegen. Deshalb gilt je Familie ein anderer Blocker:

| Familie | was das Paar prinzipiell unlösbar macht |
| ------- | --------------------------------------- |
| `structural` | keine Kante bzw. ausserhalb der grössten Komponente |
| `value` | kein gemeinsamer Literalwert |
| `holistic` (PARIS) | **beides zugleich** — es nutzt Struktur *und* Literale |

Für alle Familien gilt zusätzlich `no_signal`: eine Entität ohne jedes Tripel
ist für kein Verfahren auffindbar.

Der Anteil der so blockierten Fälle ist eine Eigenschaft des *Benchmarks*; der
Rest (`wrong_candidate`, `abstained`) liegt am Verfahren. Das Verhältnis sagt,
ob eine Verbesserung am Matcher überhaupt noch etwas bringen kann.

Zwei Eigenheiten, die beim Lesen der Ausgabe wichtig sind:

* Für holistische Verfahren ist `no_shared_literal` konstruktionsbedingt immer
  null — fehlen beide Signale, wird der Fall unter `structurally_unreachable`
  geführt. Die Klasse trägt für PARIS also keine Information.
* `no_shared_literal` prüft die Literal-Überlappung **vollständig**, während
  die Metrik `literal_value_jaccard` aus dem Katalog auf einer Stichprobe von
  5 000 Paaren rechnet. Die beiden Grössen sind verwandt, aber nicht identisch.
"""

from __future__ import annotations

import pandas as pd

from kg_quality_eval.core import KGPair
from kg_quality_eval.utils.literals import normalize_value

# Reihenfolge der Kaskade: die erste zutreffende Regel gewinnt.
CLASSES = (
    "correct",
    "true_negative",
    "false_on_unmatched",
    "no_signal",
    "structurally_unreachable",
    "no_shared_literal",
    "abstained",
    "wrong_candidate",
)

# Klassen, die der Benchmark verursacht und das jeweilige Verfahren nicht lösen kann.
UNSOLVABLE = ("no_signal", "structurally_unreachable", "no_shared_literal")

# Welcher Blocker fuer welche Matcher-Familie zaehlt.
FAMILY_BLOCKERS = {
    "structural": ("structure",),
    "value": ("literal",),
    "holistic": ("structure", "literal"),   # nur blockiert, wenn beides fehlt
}


def _largest_component(kg) -> set[str]:
    import networkx as nx

    graph = nx.Graph()
    graph.add_nodes_from(kg.entities["entity_uri"])
    graph.add_edges_from(zip(kg.rel_triples["head"], kg.rel_triples["tail"], strict=False))
    components = list(nx.connected_components(graph))
    return max(components, key=len) if components else set()


def _value_sets(kg, heads: set[str]) -> dict[str, set[str]]:
    sub = kg.attr_triples[kg.attr_triples["head"].isin(heads)]
    out: dict[str, set[str]] = {}
    for head, literal in zip(sub["head"], sub["literal"], strict=False):
        value = normalize_value(literal)
        if value:
            out.setdefault(head, set()).add(value)
    return out


def largest_components(kg_pair: KGPair) -> tuple[set[str], set[str]]:
    """Grösste Zusammenhangskomponente beider KGs.

    Separat aufrufbar, damit ein Aufrufer sie einmal je Datensatz berechnen und
    an alle Matcher weiterreichen kann — sie hängt nicht vom Matcher ab, und
    auf den 100K-Varianten ist sie der teuerste Teil der Klassifikation.
    """
    return _largest_component(kg_pair.kg1), _largest_component(kg_pair.kg2)


def classify(
    kg_pair: KGPair,
    predictions: pd.DataFrame,
    split: str = "test",
    family: str = "holistic",
    components: tuple[set[str], set[str]] | None = None,
) -> pd.DataFrame:
    """Ordnet jeder Test-Entität eine Fehlerklasse zu.

    `predictions` sind die (e1, e2, score)-Paare eines Matchers, `family` seine
    Signalfamilie (`structural`, `value` oder `holistic`) — sie entscheidet,
    welches fehlende Signal als unlösbar gilt. Zurück kommt eine Zeile je
    Entität im Auswertungsumfang, inklusive der begründenden Merkmale.
    """
    scope = kg_pair.alignments if split == "all" else kg_pair.split(split)
    if scope.empty:
        return pd.DataFrame(columns=["e1", "e2_gold", "e2_pred", "error_class"])

    gold = dict(zip(scope["e1"], scope["e2"], strict=False))

    pred = predictions
    if not pred.empty:
        pred = pred.sort_values("score", ascending=False).drop_duplicates(subset=["e1"])
    predicted = dict(zip(pred["e1"], pred["e2"], strict=False))

    deg1 = kg_pair.kg1.degrees.set_index("entity_uri")["total_degree"]
    deg2 = kg_pair.kg2.degrees.set_index("entity_uri")["total_degree"]
    attr1 = kg_pair.kg1.attr_count
    lcc1, lcc2 = components if components is not None else largest_components(kg_pair)

    left = set(scope["e1"])
    right = {v for v in gold.values() if v}
    values1 = _value_sets(kg_pair.kg1, left)
    values2 = _value_sets(kg_pair.kg2, right)

    rows = []
    for e1 in scope["e1"]:
        e2_gold = gold.get(e1, "")
        e2_pred = predicted.get(e1)

        degree = float(deg1.get(e1, 0))
        n_attr = float(attr1.get(e1, 0))
        shared = len(values1.get(e1, set()) & values2.get(e2_gold, set())) if e2_gold else 0

        rows.append(
            {
                "e1": e1,
                "e2_gold": e2_gold,
                "e2_pred": e2_pred or "",
                "has_gold": bool(e2_gold),
                "degree_kg1": degree,
                "degree_kg2": float(deg2.get(e2_gold, 0)) if e2_gold else 0.0,
                "n_attr_kg1": n_attr,
                "shared_literals": shared,
                "error_class": _classify_one(
                    e2_gold=e2_gold,
                    e2_pred=e2_pred,
                    degree=degree,
                    n_attr=n_attr,
                    deg_gold=float(deg2.get(e2_gold, 0)) if e2_gold else 0.0,
                    in_lcc=e1 in lcc1 and (not e2_gold or e2_gold in lcc2),
                    shared_literals=shared,
                    family=family,
                ),
            }
        )

    return pd.DataFrame(rows)


def _classify_one(
    *, e2_gold: str, e2_pred: str | None, degree: float, n_attr: float,
    deg_gold: float, in_lcc: bool, shared_literals: int, family: str,
) -> str:
    """Die Kaskade. Reihenfolge ist bedeutungstragend, siehe Modul-Docstring."""
    if e2_pred and e2_gold and e2_pred == e2_gold:
        return "correct"

    # Entität hat korrekt keinen Partner. Eine Vorhersage ist hier falsch, eine
    # Enthaltung richtig — aber als True Negative, nicht als Treffer. Beides in
    # `correct` zu werfen würde den Anteil auf den Non-Match-Varianten stark
    # überhöhen (dort sind ein Drittel der Entitäten partnerlos).
    if not e2_gold:
        return "false_on_unmatched" if e2_pred else "true_negative"

    # Ab hier: es gibt ein Gold-Paar, das nicht getroffen wurde.
    if degree == 0 and n_attr == 0:
        return "no_signal"

    blockers = FAMILY_BLOCKERS.get(family, ("structure", "literal"))
    structure_missing = degree == 0 or deg_gold == 0 or not in_lcc
    literal_missing = shared_literals == 0

    if len(blockers) == 1:
        # Verfahren nutzt nur ein Signal: nur dessen Fehlen blockiert es.
        if "structure" in blockers and structure_missing:
            return "structurally_unreachable"
        if "literal" in blockers and literal_missing:
            return "no_shared_literal"
    elif structure_missing and literal_missing:
        # Holistisches Verfahren: erst blockiert, wenn *beide* Signale fehlen.
        # Der Fall wird unter `structurally_unreachable` geführt; dass auch die
        # Literale fehlen, steht in der Spalte `shared_literals` der
        # Einzelfalltabelle.
        return "structurally_unreachable"

    if not e2_pred:
        return "abstained"
    return "wrong_candidate"


def summarize(classified: pd.DataFrame, dataset: str, matcher: str) -> pd.DataFrame:
    """Verteilung der Fehlerklassen als eine Zeile je Klasse."""
    if classified.empty:
        return pd.DataFrame()

    counts = classified["error_class"].value_counts()
    total = int(counts.sum())
    return pd.DataFrame(
        [
            {
                "dataset": dataset,
                "matcher": matcher,
                "error_class": cls,
                "n": int(counts.get(cls, 0)),
                "share": float(counts.get(cls, 0) / total) if total else 0.0,
            }
            for cls in CLASSES
        ]
    )


def solvability(summary: pd.DataFrame) -> pd.DataFrame:
    """Trennt benchmark-bedingte von verfahrensbedingten Fehlern.

    `unsolvable_share` ist der Anteil der Fehler, an denen das Verfahren nichts
    ändern kann, weil ihm das benötigte Signal fehlt. Der Wert ist **nicht** für
    alle Matcher gleich: seit die Kaskade familienabhängig ist, hängt er davon
    ab, welches Signal die Familie überhaupt nutzt. Auf `D_W_15K_V1` reicht er
    von 0,11 (strukturell) bis 0,88 (wertbasiert) — genau das ist die Aussage.

    `method_share` ist der Rest: dort liegt der Spielraum für eine bessere
    Implementierung.
    """
    if summary.empty:
        return pd.DataFrame()

    # Weder Treffer noch korrekte Enthaltung sind Fehler.
    errors = summary[~summary["error_class"].isin(("correct", "true_negative"))]
    grouped = errors.groupby(["dataset", "matcher"])["n"].sum().rename("n_errors")

    unsolvable = (
        errors[errors["error_class"].isin(UNSOLVABLE)]
        .groupby(["dataset", "matcher"])["n"].sum().rename("n_unsolvable")
    )

    out = pd.concat([grouped, unsolvable], axis=1).fillna(0).reset_index()
    # Ohne Fehler ist der Anteil nicht definiert; 0/0 wuerde NaN liefern.
    has_errors = out["n_errors"] > 0
    out["unsolvable_share"] = (out["n_unsolvable"] / out["n_errors"].where(has_errors)).fillna(0.0)
    out["method_share"] = (1.0 - out["unsolvable_share"]).where(has_errors, 0.0)
    return out.round(4)
