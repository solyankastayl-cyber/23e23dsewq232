"""
PHASE 22.2 — Tail Severity Engine
=================================
Sub-engine for calculating tail loss severity.

Computes tail_loss_95 and tail_loss_99 from VaR/ES data.
Also computes asymmetry_score (ES/VaR ratio).
"""

from typing import Dict, Optional, Any


class TailSeverityEngine:
    """
    Tail Severity Sub-Engine.
    
    Calculates:
    - tail_loss_95 = expected_shortfall_95
    - tail_loss_99 = expected_shortfall_99
    - asymmetry_score = ES_95 / VaR_95
    """

    def compute_tail_severity(
        self,
        portfolio_var_95: float = 0.05,
        portfolio_var_99: float = 0.07,
        expected_shortfall_95: float = 0.06,
        expected_shortfall_99: float = 0.08,
    ) -> Dict[str, Any]:
        """
        Compute tail severity metrics.
        
        Returns:
            {
                "tail_loss_95": float,
                "tail_loss_99": float,
                "asymmetry_score": float,
                "normalized_tail_loss": float,
            }
        """
        tail_loss_95 = expected_shortfall_95
        tail_loss_99 = expected_shortfall_99

        # Asymmetry = ES / VaR — how much worse is the tail vs normal bad
        asymmetry_score = (
            expected_shortfall_95 / portfolio_var_95
            if portfolio_var_95 > 0 else 1.0
        )

        # Normalized tail loss (cap at 1.0 for scoring)
        # Use 0.50 as max expected tail loss for normalization
        normalized_tail_loss = min(tail_loss_95 / 0.50, 1.0)

        return {
            "tail_loss_95": tail_loss_95,
            "tail_loss_99": tail_loss_99,
            "asymmetry_score": asymmetry_score,
            "normalized_tail_loss": normalized_tail_loss,
        }

    def normalize_asymmetry(self, asymmetry_score: float) -> float:
        """
        Normalize asymmetry score to 0..1.
        
        asymmetry typically ranges from 1.0 to 2.0+.
        Map: 1.0 → 0.0, 2.0 → 1.0.
        """
        normalized = max(0.0, min((asymmetry_score - 1.0) / 1.0, 1.0))
        return normalized


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[TailSeverityEngine] = None


def get_tail_severity_engine() -> TailSeverityEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = TailSeverityEngine()
    return _engine
