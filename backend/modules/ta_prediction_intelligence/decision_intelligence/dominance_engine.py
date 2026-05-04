"""
Dominance engine — quantifies the spread between primary and secondary
probability and labels it on a fixed ladder.

Thresholds are intentionally explicit constants; bump carefully.
"""
from __future__ import annotations

from typing import Tuple

DOM_DOMINANT = 0.30
DOM_CLEAR = 0.15
DOM_THIN = 0.07


def compute_dominance(primary_prob: float, secondary_prob: float) -> Tuple[float, str]:
    try:
        dominance = max(float(primary_prob) - float(secondary_prob), 0.0)
    except (TypeError, ValueError):
        dominance = 0.0
    if dominance >= DOM_DOMINANT:
        label = "dominant"
    elif dominance >= DOM_CLEAR:
        label = "clear"
    elif dominance >= DOM_THIN:
        label = "thin"
    else:
        label = "ambiguous"
    return dominance, label
