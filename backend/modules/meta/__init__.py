"""
Meta Layer (Pass 4)
====================

Boundary between analytics and trading:

    combined_analysis (knowledge)
            ↓
    meta_scoring_engine  ← MATH OF DECISION
            ↓
    strategy_score (0..1)
            ↓
    allocation (capital weight, NOT a position)
            ↓
    risk_flags (guard-aware)

This module produces NUMBERS for downstream allocation/execution.
It does NOT place orders, size positions, or move capital.

Hard rules (Pass 4 honesty):
    * No fabricated data. quality=LOW → score=0. CRITICAL risk → allocation=0.
    * Hypothesis with sample_size<30 → demoted (no booster, *0.5 base score).
    * Drift conflict propagates from Pass 3.5 hardening (cap already applied).
"""
