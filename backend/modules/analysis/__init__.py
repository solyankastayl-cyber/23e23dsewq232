"""
Analysis Unification Layer (Pass 3)
====================================

Single endpoint that joins three INDEPENDENT analytics sources:

    TA          → "what is happening now"     (signal_explanation)
    Prediction  → "where it could go"         (ta_prediction.v2)
    Hypothesis  → "did this work historically" (research.hypothesis_engine)

into one coherent, agreement-scored payload.

Honesty rules (HARD — same discipline as Pass 2):
    * No fabricated confidence / fields.
    * If hypothesis has no completed run → hypothesis = null.
    * If prediction is unavailable → confidence = 0.
    * Direction conflicts must surface as LOW quality, not be hidden.
    * No mixing of timeframes — agreement is computed within the requested TF only.

This module is ANALYTICS, NOT TRADING. It produces knowledge,
it does NOT decide allocation, sizing, or execution.
"""
