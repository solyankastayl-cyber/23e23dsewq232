"""
Concentration metrics — HHI + top_cause_share.

HHI (Herfindahl-Hirschman Index):
    sum(p_i ** 2) over the root_cause distribution

* 1 cause @ 100%        → 1.00
* 2 causes @ 50/50      → 0.50
* 10 even causes        → 0.10
* uniform distribution  → 1/K

Used only on the *error* sub-cohort (correct/underconfident excluded).
"""
from __future__ import annotations

from typing import Dict, Iterable, Tuple


def compute_hhi(distribution: Dict[str, int]) -> float:
    """
    Pure: HHI of a count distribution. Returns 0.0 for an empty
    distribution. Range: [1/K, 1.0] for K>=1 non-empty causes; can be
    interpreted as 1.0 for total monoculture, ~1/K for uniformity.
    """
    if not distribution:
        return 0.0
    total = float(sum(distribution.values()))
    if total <= 0:
        return 0.0
    return round(sum((c / total) ** 2 for c in distribution.values()), 6)


def compute_top_share(distribution: Dict[str, int]) -> Tuple[str, float]:
    """Return (top_cause, top_share). ('', 0.0) on empty."""
    if not distribution:
        return "", 0.0
    total = float(sum(distribution.values()))
    if total <= 0:
        return "", 0.0
    top_cause, top_count = max(distribution.items(), key=lambda kv: (kv[1], kv[0]))
    return top_cause, round(top_count / total, 6)


def build_distribution(causes: Iterable[str]) -> Dict[str, int]:
    """Helper to build a count distribution from an iterable of causes."""
    out: Dict[str, int] = {}
    for c in causes:
        if not c:
            c = "unknown_cause"
        out[c] = out.get(c, 0) + 1
    return out
