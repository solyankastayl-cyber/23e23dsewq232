"""
PHASE 22.3 — Contagion Path Engine
==================================
Sub-engine for building contagion spread paths.

Traces how stress propagates through the cluster network.
"""

from typing import Dict, Optional, Any, List

from modules.institutional_risk.cluster_contagion.cluster_contagion_types import (
    CONTAGION_MAP,
)


class ContagionPathEngine:
    """
    Contagion Path Sub-Engine.
    
    Builds contagion spread paths using BFS/DFS on the contagion map.
    Only includes paths where contagion probability exceeds threshold.
    """

    def __init__(self):
        self._prob_threshold = 0.15  # Minimum probability to include in path

    def build_contagion_paths(
        self,
        cluster_stress: Dict[str, float],
        contagion_probabilities: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Build contagion spread paths.
        
        Returns:
            {
                "contagion_paths": ["btc_cluster -> majors_cluster -> alts_cluster", ...],
                "path_count": int,
                "longest_path_length": int,
            }
        """
        paths = []

        # For each source cluster, trace forward
        for source in CONTAGION_MAP:
            visited = set()
            current_path = [source]
            self._trace_path(
                source, current_path, visited,
                contagion_probabilities, paths,
            )

        # Deduplicate and sort by length
        unique_paths = list(set(paths))
        unique_paths.sort(key=lambda p: len(p.split(" -> ")), reverse=True)

        longest = max(
            (len(p.split(" -> ")) for p in unique_paths), default=0
        )

        return {
            "contagion_paths": unique_paths,
            "path_count": len(unique_paths),
            "longest_path_length": longest,
        }

    def _trace_path(
        self,
        current: str,
        path: List[str],
        visited: set,
        probabilities: Dict[str, float],
        results: List[str],
    ):
        """Recursively trace contagion paths."""
        visited.add(current)
        targets = CONTAGION_MAP.get(current, [])

        for target in targets:
            if target in visited:
                continue

            pair_key = f"{current}->{target}"
            prob = probabilities.get(pair_key, 0.0)

            if prob >= self._prob_threshold:
                new_path = path + [target]

                # Record path if length >= 2
                if len(new_path) >= 2:
                    results.append(" -> ".join(new_path))

                # Continue tracing
                self._trace_path(
                    target, new_path, visited.copy(),
                    probabilities, results,
                )


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ContagionPathEngine] = None


def get_contagion_path_engine() -> ContagionPathEngine:
    global _engine
    if _engine is None:
        _engine = ContagionPathEngine()
    return _engine
