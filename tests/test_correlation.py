"""Tests der Korrelationsanalyse und der Korrektur für multiples Testen.

Über alle Matcher und Metriken werden Dutzende Korrelationen gerechnet. Ohne
Korrektur wären allein durch Zufall einige davon "signifikant"; die Ausgabe
muss das sichtbar machen, statt rohe p-Werte als Test zu präsentieren.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from kg_quality_eval.reporting.correlation import adjust_p_values, correlate


def _frame(p_values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "matcher": ["m"] * len(p_values),
            "metric": [f"metric_{i}" for i in range(len(p_values))],
            "spearman_rho": [0.5] * len(p_values),
            "p_value": p_values,
            "n_datasets": [16] * len(p_values),
            "abs_rho": [0.5] * len(p_values),
        }
    )


def test_bonferroni_scales_with_the_number_of_tests():
    out = adjust_p_values(_frame([0.01, 0.02, 0.03, 0.04]))
    assert (out["n_tests"] == 4).all()
    assert out.loc[0, "p_bonferroni"] == pytest.approx(0.04)
    # 0.01 < 0.05/4 = 0.0125 -> überlebt gerade noch
    assert bool(out.loc[0, "survives_bonferroni"])
    assert not bool(out.loc[1, "survives_bonferroni"])


def test_bonferroni_is_capped_at_one():
    out = adjust_p_values(_frame([0.4, 0.5, 0.6]))
    assert (out["p_bonferroni"] <= 1.0).all()


def test_fdr_is_less_conservative_than_bonferroni():
    out = adjust_p_values(_frame([0.001, 0.01, 0.02, 0.04, 0.30]))
    assert (out["p_fdr"] <= out["p_bonferroni"] + 1e-12).all()
    assert int(out["survives_fdr"].sum()) >= int(out["survives_bonferroni"].sum())


def test_fdr_is_monotone_in_the_p_value_order():
    """Benjamini-Hochberg muss monoton sein: kleinere p, kleineres p_fdr."""
    out = adjust_p_values(_frame([0.001, 0.01, 0.02, 0.04, 0.30])).sort_values("p_value")
    assert out["p_fdr"].is_monotonic_increasing


def test_empty_frame_survives():
    assert adjust_p_values(pd.DataFrame()).empty


def test_correlate_reports_corrected_values():
    """Der Hauptpfad muss die korrigierten Spalten mitliefern."""
    rng = np.random.default_rng(0)
    merged = pd.DataFrame(
        {
            "matcher": ["a"] * 8 + ["b"] * 8,
            "f1": np.concatenate([np.linspace(0.1, 0.9, 8), rng.random(8)]),
            "metric_x": np.tile(np.linspace(0, 1, 8), 2),
            "metric_y": rng.random(16),
        }
    )
    out = correlate(merged, ["metric_x", "metric_y"])

    assert not out.empty
    for column in ("p_bonferroni", "p_fdr", "survives_bonferroni", "survives_fdr", "n_tests"):
        assert column in out.columns
    assert (out["n_tests"] == len(out)).all()


def test_correlate_needs_enough_datasets():
    """Bei zu wenigen Datenpunkten darf gar keine Korrelation berichtet werden."""
    merged = pd.DataFrame(
        {"matcher": ["a"] * 3, "f1": [0.1, 0.2, 0.3], "metric_x": [1.0, 2.0, 3.0]}
    )
    assert correlate(merged, ["metric_x"]).empty
