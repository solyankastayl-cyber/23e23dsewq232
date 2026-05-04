"""
MTF Orchestrator v2.0
=====================

Multi-Timeframe Orchestration Layer with ROLE-BASED analysis.

TF Roles:
  HTF (1M, 6M, 1Y) → CONTEXT (trend, regime, major levels)
  MTF (1D, 7D) → PATTERNS (main TA layer)
  LTF (4H) → DETAIL (local patterns, confirmation)

Key principle: Each TF has its own role, not all TFs need patterns.

NO PATTERN on HTF is NOT an error — it's valid.
"""

from __future__ import annotations
from typing import Dict, Any, Optional

# Import new MTF Engine
from modules.ta_engine.mtf_engine import get_mtf_engine, MTFEngine


class MTFOrchestrator:
    """
    Orchestrates multiple timeframe contexts into one coherent view.
    
    v2.0: Uses MTF Engine for role-based analysis.
    """
    
    # TF Role classification
    TF_ROLES = MTFEngine.TF_ROLES

    def build(
        self,
        tf_map: Dict[str, Dict[str, Any]],
        bias_tf: str = "1D",
        setup_tf: str = "4H",
        entry_tf: str = "1H",
    ) -> Dict[str, Any]:
        """
        Build MTF orchestration from per-timeframe TA data.
        
        Uses MTF Engine v1.0 for role-based analysis.
        """
        # Run MTF Engine analysis
        mtf_engine = get_mtf_engine()
        mtf_analysis = mtf_engine.analyze(tf_map)
        
        # Legacy compatibility
        htf = tf_map.get(bias_tf, {})
        stf = tf_map.get(setup_tf, {})
        ltf = tf_map.get(entry_tf, {})

        global_bias = self._extract_bias(htf)
        setup_bias = self._extract_bias(stf)
        entry_bias = self._extract_bias(ltf)

        alignment = self._compute_alignment(global_bias, setup_bias, entry_bias)
        tradeability = self._compute_tradeability(
            global_bias=global_bias,
            setup=stf.get("unified_setup"),
            entry=ltf.get("trade_setup"),
            alignment=alignment,
        )

        return {
            "bias_tf": bias_tf,
            "setup_tf": setup_tf,
            "entry_tf": entry_tf,
            "global_bias": global_bias,
            "setup_bias": setup_bias,
            "entry_bias": entry_bias,
            "alignment": alignment,
            "tradeability": tradeability,
            "summary": self._build_summary(global_bias, stf, ltf, alignment),
            "timeframes": {
                bias_tf: self._compact(htf, bias_tf),
                setup_tf: self._compact(stf, setup_tf),
                entry_tf: self._compact(ltf, entry_tf),
            },
            # NEW: MTF Engine v2 analysis
            "mtf_analysis": mtf_analysis,
        }

    def _extract_bias(self, tf_payload: Dict[str, Any]) -> str:
        """Extract directional bias from timeframe payload."""
        if not tf_payload:
            return "neutral"
        
        # Try decision first
        decision = tf_payload.get("decision") or {}
        bias = decision.get("bias") or decision.get("direction")
        if bias and bias != "neutral":
            return bias.lower()
        
        # Try structure context
        structure = tf_payload.get("structure_context") or {}
        struct_bias = structure.get("bias")
        if struct_bias and struct_bias != "neutral":
            return struct_bias.lower()
        
        # Try unified setup
        unified = tf_payload.get("unified_setup") or {}
        unified_dir = unified.get("direction")
        if unified_dir and unified_dir not in {"no_trade", "neutral"}:
            return "bullish" if unified_dir == "long" else "bearish"
        
        return "neutral"

    def _compute_alignment(self, global_bias: str, setup_bias: str, entry_bias: str) -> str:
        """Compute alignment between timeframes."""
        if global_bias == "neutral":
            return "mixed"
        
        if setup_bias == global_bias and entry_bias in {global_bias, "neutral"}:
            return "aligned"
        
        if setup_bias != "neutral" and setup_bias != global_bias:
            return "counter_trend"
        
        if setup_bias == global_bias and entry_bias != "neutral" and entry_bias != global_bias:
            return "mixed"
        
        return "mixed"

    def _compute_tradeability(
        self,
        global_bias: str,
        setup: Optional[Dict[str, Any]],
        entry: Optional[Dict[str, Any]],
        alignment: str,
    ) -> str:
        """Compute overall tradeability score."""
        if not setup or not setup.get("valid", False):
            return "low"
        
        entry_valid = False
        if entry:
            primary = entry.get("primary", {})
            entry_valid = primary.get("valid", False)
        
        if alignment == "aligned" and global_bias != "neutral" and entry_valid:
            return "high"
        
        if alignment == "aligned" and global_bias != "neutral":
            return "medium"
        
        if alignment == "counter_trend":
            return "low"
        
        return "medium"

    def _build_summary(
        self,
        global_bias: str,
        stf: Dict[str, Any],
        ltf: Dict[str, Any],
        alignment: str,
    ) -> str:
        """Build human-readable summary."""
        parts = []
        
        parts.append(f"Higher timeframe {global_bias}")
        
        pattern = (stf.get("primary_pattern") or stf.get("pattern_v2", {}).get("primary_pattern") or {}).get("type")
        if pattern:
            pattern_bias = (stf.get("primary_pattern") or {}).get("direction_bias", "")
            if pattern_bias:
                parts.append(f"setup shows {pattern} ({pattern_bias})")
            else:
                parts.append(f"setup shows {pattern}")
        
        entry_setup = (ltf.get("trade_setup") or {}).get("primary") or {}
        entry_dir = entry_setup.get("direction")
        if entry_dir:
            parts.append(f"entry favors {entry_dir}")
        
        if alignment == "counter_trend":
            parts.append("WARNING: counter-trend setup")
        elif alignment == "aligned":
            parts.append("timeframes aligned")
        
        return ". ".join(parts) + "."

    def _compact(self, payload: Dict[str, Any], tf: str) -> Dict[str, Any]:
        """Extract compact view of timeframe data."""
        decision = payload.get("decision", {})
        pattern = payload.get("primary_pattern") or (payload.get("pattern_v2") or {}).get("primary_pattern")
        
        # Add role info
        role = self.TF_ROLES.get(tf, "mtf")
        
        return {
            "timeframe": tf,
            "role": role,  # NEW: TF role
            "bias": self._extract_bias(payload),
            "regime": (payload.get("structure_context") or {}).get("regime"),
            "pattern": {
                "type": pattern.get("type") if pattern else None,
                "direction_bias": pattern.get("direction_bias") if pattern else None,
                "score": pattern.get("score") if pattern else None,
            } if pattern else None,
            "unified_setup_valid": (payload.get("unified_setup") or {}).get("valid", False),
            "trade_setup_valid": ((payload.get("trade_setup") or {}).get("primary") or {}).get("valid", False),
        }


# Factory function
_mtf_orchestrator = None

def get_mtf_orchestrator() -> MTFOrchestrator:
    global _mtf_orchestrator
    if _mtf_orchestrator is None:
        _mtf_orchestrator = MTFOrchestrator()
    return _mtf_orchestrator
