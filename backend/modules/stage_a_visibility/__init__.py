"""
Stage A — Read-only visibility for orphaned TA branches.

Provides a single aggregator endpoint that probes the health of each
restored branch (Exchange Intelligence, Fractal, Macro-Fractal, Cross-Asset)
and reports alive/dead/payload-freshness. Used by ops + admin UI.

This module is STRICTLY read-only:
    - no Mongo writes
    - no calls to execution / aggregator / decision pipeline
    - no mutation of state
"""
