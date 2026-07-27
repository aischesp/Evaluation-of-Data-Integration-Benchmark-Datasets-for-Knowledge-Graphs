"""Distribution helpers shared by the structural and quality metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def summarize(values: np.ndarray | pd.Series, prefix: str) -> dict[str, float]:
    """Standard descriptive statistics of a (degree / frequency) distribution."""
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return {f"{prefix}.{k}": 0.0 for k in ("mean", "median", "std", "min", "max")}

    s = pd.Series(v)
    return {
        f"{prefix}.mean": float(v.mean()),
        f"{prefix}.median": float(np.median(v)),
        f"{prefix}.std": float(v.std(ddof=0)),
        f"{prefix}.min": float(v.min()),
        f"{prefix}.max": float(v.max()),
        f"{prefix}.p25": float(np.percentile(v, 25)),
        f"{prefix}.p75": float(np.percentile(v, 75)),
        f"{prefix}.p95": float(np.percentile(v, 95)),
        f"{prefix}.p99": float(np.percentile(v, 99)),
        f"{prefix}.skewness": float(s.skew()) if v.size > 2 else 0.0,
        f"{prefix}.kurtosis": float(s.kurtosis()) if v.size > 3 else 0.0,
        f"{prefix}.gini": gini(v),
    }


def gini(values: np.ndarray) -> float:
    """Gini coefficient. 0 = perfectly uniform, 1 = all mass on one element.

    Standard sorted-cumulative formulation; negative values are not expected
    for degree/frequency data and are clipped away.
    """
    v = np.sort(np.clip(np.asarray(values, dtype=float), 0, None))
    n = v.size
    total = v.sum()
    if n == 0 or total == 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2.0 * (index * v).sum()) / (n * total) - (n + 1.0) / n)


def entropy(counts: np.ndarray) -> float:
    """Shannon entropy (bits) of a frequency vector."""
    c = np.asarray(counts, dtype=float)
    c = c[c > 0]
    if c.size == 0:
        return 0.0
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def normalized_entropy(counts: np.ndarray) -> float:
    """Entropy divided by log2(n) so that different vocabulary sizes compare."""
    c = np.asarray(counts, dtype=float)
    c = c[c > 0]
    if c.size <= 1:
        return 0.0
    return entropy(c) / np.log2(c.size)


def powerlaw_alpha(values: np.ndarray, xmin: float = 1.0) -> tuple[float, float]:
    """MLE estimate of the power-law exponent alpha for a discrete distribution.

    Follows Clauset/Shalizi/Newman (2009), eq. 3.7 (continuous approximation
    with the 1/2 correction that is standard for integer degree data).
    Returns (alpha, xmin_used); alpha = nan when there is too little tail data.
    """
    v = np.asarray(values, dtype=float)
    tail = v[v >= xmin]
    if tail.size < 50:
        return float("nan"), xmin
    alpha = 1.0 + tail.size / np.sum(np.log(tail / (xmin - 0.5)))
    return float(alpha), float(xmin)


def log_histogram(values: np.ndarray, n_bins: int = 20) -> pd.DataFrame:
    """Logarithmically binned histogram — the right shape for heavy-tailed data.

    Degree 0 gets its own bin because log binning cannot represent it.
    """
    v = np.asarray(values, dtype=float)
    rows = [{"bin_lower": 0.0, "bin_upper": 0.0, "count": int((v == 0).sum())}]

    pos = v[v > 0]
    if pos.size:
        edges = np.unique(np.round(np.logspace(0, np.log10(max(pos.max(), 2.0)), n_bins)))
        counts, edges = np.histogram(pos, bins=np.append(edges, edges[-1] + 1))
        rows += [
            {"bin_lower": float(edges[i]), "bin_upper": float(edges[i + 1]), "count": int(counts[i])}
            for i in range(len(counts))
            if counts[i] > 0
        ]
    return pd.DataFrame(rows)


def top_k_concentration(counts: np.ndarray, k: int = 10) -> float:
    """Share of the total mass held by the k largest elements."""
    c = np.sort(np.asarray(counts, dtype=float))[::-1]
    total = c.sum()
    return float(c[:k].sum() / total) if total else 0.0


def long_tail_share(counts: np.ndarray, threshold: float = 0.01) -> float:
    """Share of items that individually account for < `threshold` of the mass."""
    c = np.asarray(counts, dtype=float)
    total = c.sum()
    if total == 0 or c.size == 0:
        return 0.0
    return float((c / total < threshold).sum() / c.size)
