"""
MTF Engine v1.0 (Multi-Timeframe Analysis)
==========================================

Proper multi-timeframe analysis where each TF has its own role.

Roles:
- HTF (1M, 6M, 1Y): Global context, trend, regime, major levels
- MTF (1D, 7D): Primary TA layer, main patterns
- LTF (4H): Local detail, micro patterns, confirmation

Key principle: HTF gives CONTEXT, MTF gives PATTERNS, LTF gives DETAIL

NO PATTERN on HTF is NOT an error - it's valid.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class TFAnalysis:
    """Analysis result for a single timeframe."""
    tf: str
    role: str  # ltf, mtf, htf
    trend: str = "neutral"  # uptrend, downtrend, range, neutral
    regime: str = "unknown"  # trending, ranging, compression, expansion
    pattern: Optional[Dict] = None
    structure: Optional[Dict] = None
    levels: List[Dict] = field(default_factory=list)
    message: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "tf": self.tf,
            "role": self.role,
            "trend": self.trend,
            "regime": self.regime,
            "pattern": self.pattern,
            "structure": self.structure,
            "levels": self.levels[:5] if self.levels else [],
            "message": self.message,
        }


class MTFEngine:
    """
    Multi-Timeframe Analysis Engine.
    
    Each timeframe has a specific role:
    - HTF: Context (trend, regime, major levels)
    - MTF: Main patterns
    - LTF: Local detail
    """
    
    # Timeframe classification
    # 1M/6M are proper TA names, 30D/180D are legacy aliases
    TF_ROLES = {
        "4H": "ltf",
        "1D": "mtf",
        "7D": "mtf",
        "1M": "htf",      # Monthly (proper name)
        "30D": "htf",     # Legacy alias for 1M
        "6M": "htf",      # Semi-annual (proper name)
        "180D": "htf",    # Legacy alias for 6M
        "1Y": "htf",
    }
    
    # TF normalization (legacy → proper)
    TF_NORMALIZE = {
        "30D": "1M",
        "180D": "6M",
    }
    
    # HTF pattern threshold (only show very confident patterns)
    HTF_PATTERN_MIN_SCORE = 0.78
    
    # Role display names
    ROLE_NAMES = {
        "htf": "Macro",
        "mtf": "Mid-term",
        "ltf": "Short-term",
    }
    
    def __init__(self):
        pass
    
    @staticmethod
    def classify_tf(tf: str) -> str:
        """Classify timeframe into role."""
        return MTFEngine.TF_ROLES.get(tf, "mtf")
    
    @staticmethod
    def normalize_tf(tf: str) -> str:
        """Normalize legacy TF names."""
        mapping = {
            "30D": "1M",
            "180D": "6M",
        }
        return mapping.get(tf, tf)
    
    # ═══════════════════════════════════════════════════════════════
    # TREND INFERENCE
    # ═══════════════════════════════════════════════════════════════
    
    def _infer_trend(self, structure: Dict) -> str:
        """
        Infer trend from structure (HH/HL/LH/LL sequence).
        """
        if not structure:
            return "neutral"
        
        # Get swing sequence
        swings = structure.get("swings", [])
        if len(swings) < 4:
            return "neutral"
        
        # Analyze last 4 swings
        recent = swings[-4:]
        
        highs = [s for s in recent if s.get("type") in ["H", "HH", "LH", "high"]]
        lows = [s for s in recent if s.get("type") in ["L", "HL", "LL", "low"]]
        
        if len(highs) < 2 or len(lows) < 2:
            return "neutral"
        
        # Check HH/HL (uptrend) or LH/LL (downtrend)
        h1_price = highs[-2].get("price", highs[-2].get("value", 0))
        h2_price = highs[-1].get("price", highs[-1].get("value", 0))
        l1_price = lows[-2].get("price", lows[-2].get("value", 0))
        l2_price = lows[-1].get("price", lows[-1].get("value", 0))
        
        if h2_price > h1_price and l2_price > l1_price:
            return "uptrend"
        elif h2_price < h1_price and l2_price < l1_price:
            return "downtrend"
        elif abs(h2_price - h1_price) / max(h1_price, 1) < 0.03:
            return "range"
        
        return "neutral"
    
    def _infer_regime(self, structure: Dict, levels: List[Dict]) -> str:
        """
        Infer market regime.
        """
        if not structure:
            return "unknown"
        
        regime = structure.get("regime", "unknown")
        if regime != "unknown":
            return regime
        
        # Try to infer from structure properties
        bias = structure.get("bias", "neutral")
        trend = structure.get("trend", "neutral")
        
        if trend in ["bullish", "bearish"]:
            return "trending"
        elif bias == "compression":
            return "compression"
        elif bias == "expansion":
            return "expansion"
        
        return "ranging"
    
    # ═══════════════════════════════════════════════════════════════
    # HTF ANALYSIS (1M, 6M, 1Y)
    # ═══════════════════════════════════════════════════════════════
    
    def _build_htf_context(self, tf: str, data: Dict) -> TFAnalysis:
        """
        Build HTF context analysis.
        
        Focus on:
        - Global trend
        - Regime
        - Major levels
        - Pattern ONLY if very confident
        """
        structure = data.get("structure_context", data.get("structure", {}))
        levels = data.get("levels", [])
        pattern = data.get("primary_pattern")
        
        trend = self._infer_trend(structure)
        regime = self._infer_regime(structure, levels)
        
        # Only include pattern if very confident
        final_pattern = None
        if pattern:
            score = pattern.get("final_score", pattern.get("confidence", 0))
            if score >= self.HTF_PATTERN_MIN_SCORE:
                final_pattern = pattern
        
        # Build message
        message = self._build_htf_message(tf, trend, regime, final_pattern)
        
        return TFAnalysis(
            tf=tf,
            role="htf",
            trend=trend,
            regime=regime,
            pattern=final_pattern,
            structure=structure,
            levels=levels[:3],  # Only major levels
            message=message,
        )
    
    def _build_htf_message(self, tf: str, trend: str, regime: str, pattern: Optional[Dict]) -> str:
        """Build human-readable message for HTF."""
        parts = []
        
        # Trend
        trend_map = {
            "uptrend": "Bullish macro trend",
            "downtrend": "Bearish macro trend",
            "range": "Macro range/consolidation",
            "neutral": "Neutral macro structure",
        }
        parts.append(trend_map.get(trend, "Unknown macro context"))
        
        # Regime
        if regime == "compression":
            parts.append("compression phase")
        elif regime == "expansion":
            parts.append("expansion phase")
        elif regime == "ranging":
            parts.append("ranging environment")
        
        # Pattern (only if present)
        if pattern:
            parts.append(f"with {pattern.get('type', 'pattern').replace('_', ' ')}")
        
        return ", ".join(parts)
    
    # ═══════════════════════════════════════════════════════════════
    # MTF ANALYSIS (1D, 7D)
    # ═══════════════════════════════════════════════════════════════
    
    def _build_mtf_analysis(self, tf: str, data: Dict) -> TFAnalysis:
        """
        Build MTF pattern analysis.
        
        This is the PRIMARY TA layer.
        """
        structure = data.get("structure_context", data.get("structure", {}))
        levels = data.get("levels", [])
        pattern = data.get("primary_pattern")
        
        trend = self._infer_trend(structure)
        regime = self._infer_regime(structure, levels)
        
        message = self._build_mtf_message(tf, pattern, structure)
        
        return TFAnalysis(
            tf=tf,
            role="mtf",
            trend=trend,
            regime=regime,
            pattern=pattern,
            structure=structure,
            levels=levels[:5],
            message=message,
        )
    
    def _build_mtf_message(self, tf: str, pattern: Optional[Dict], structure: Dict) -> str:
        """Build message for MTF."""
        if pattern:
            ptype = pattern.get("type", "pattern").replace("_", " ").title()
            direction = pattern.get("direction", "neutral")
            score = pattern.get("final_score", pattern.get("confidence", 0))
            return f"{ptype} ({direction}, score {score:.2f})"
        
        # No pattern - describe structure
        trend = structure.get("trend", structure.get("bias", "neutral"))
        if trend:
            return f"No clear pattern, {trend} structure"
        
        return "No clear pattern or structure"
    
    # ═══════════════════════════════════════════════════════════════
    # LTF ANALYSIS (4H)
    # ═══════════════════════════════════════════════════════════════
    
    def _build_ltf_analysis(self, tf: str, data: Dict) -> TFAnalysis:
        """
        Build LTF detail analysis.
        
        Local patterns, micro structure, confirmation.
        """
        structure = data.get("structure_context", data.get("structure", {}))
        levels = data.get("levels", [])
        pattern = data.get("primary_pattern")
        
        trend = self._infer_trend(structure)
        regime = self._infer_regime(structure, levels)
        
        message = self._build_ltf_message(tf, pattern, structure)
        
        return TFAnalysis(
            tf=tf,
            role="ltf",
            trend=trend,
            regime=regime,
            pattern=pattern,
            structure=structure,
            levels=levels[:3],
            message=message,
        )
    
    def _build_ltf_message(self, tf: str, pattern: Optional[Dict], structure: Dict) -> str:
        """Build message for LTF."""
        if pattern:
            ptype = pattern.get("type", "pattern").replace("_", " ").title()
            return f"Local {ptype}"
        
        bias = structure.get("bias", "neutral")
        if bias in ["bullish", "bearish"]:
            return f"Local {bias} structure"
        
        return "Local consolidation"
    
    # ═══════════════════════════════════════════════════════════════
    # GLOBAL SUMMARY
    # ═══════════════════════════════════════════════════════════════
    
    def _build_global_summary(self, analyses: Dict[str, TFAnalysis]) -> Dict:
        """
        Build global summary combining all timeframes.
        """
        # Find representative for each role
        htf = None
        mtf = None
        ltf = None
        
        for tf in ["1Y", "6M", "1M", "180D", "30D"]:
            if tf in analyses:
                htf = analyses[tf]
                break
        
        for tf in ["7D", "1D"]:
            if tf in analyses:
                mtf = analyses[tf]
                break
        
        if "4H" in analyses:
            ltf = analyses["4H"]
        
        # Build narrative
        narrative = self._build_narrative(htf, mtf, ltf)
        
        # One-line summary
        parts = []
        if htf:
            parts.append(f"{htf.tf}: {htf.trend.title()}")
        if mtf:
            if mtf.pattern:
                parts.append(f"{mtf.tf}: {mtf.pattern.get('type', 'pattern').replace('_', ' ').title()}")
            else:
                parts.append(f"{mtf.tf}: No pattern")
        if ltf:
            if ltf.pattern:
                parts.append(f"{ltf.tf}: {ltf.pattern.get('type', 'pattern').replace('_', ' ').title()}")
            else:
                parts.append(f"{ltf.tf}: {ltf.trend.title()}")
        
        one_line = " · ".join(parts)
        
        return {
            "macro_trend": htf.trend if htf else "unknown",
            "macro_regime": htf.regime if htf else "unknown",
            "primary_pattern": mtf.pattern if mtf else None,
            "local_confirmation": ltf.pattern if ltf else None,
            "one_line": one_line,
            "narrative": narrative,
        }
    
    def _build_narrative(
        self, 
        htf: Optional[TFAnalysis], 
        mtf: Optional[TFAnalysis], 
        ltf: Optional[TFAnalysis]
    ) -> str:
        """Build human-readable narrative."""
        parts = []
        
        # HTF context
        if htf:
            if htf.trend == "uptrend":
                parts.append("Macro trend remains bullish")
            elif htf.trend == "downtrend":
                parts.append("Macro trend remains bearish")
            elif htf.trend == "range":
                parts.append("Macro picture shows range/consolidation")
            else:
                parts.append("Macro context is neutral")
        
        # MTF pattern
        if mtf:
            if mtf.pattern:
                ptype = mtf.pattern.get("type", "").replace("_", " ")
                direction = mtf.pattern.get("direction", "")
                parts.append(f"Mid-term shows {ptype} ({direction})")
            else:
                parts.append("No clear mid-term pattern")
        
        # LTF confirmation
        if ltf:
            if ltf.pattern:
                ptype = ltf.pattern.get("type", "").replace("_", " ")
                parts.append(f"Short-term shows local {ptype}")
            elif ltf.trend in ["uptrend", "downtrend"]:
                parts.append(f"Short-term in local {ltf.trend}")
        
        return ". ".join(parts) + "." if parts else "Insufficient data for analysis."
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN ENTRY POINT
    # ═══════════════════════════════════════════════════════════════
    
    def analyze(self, tf_map: Dict[str, Dict]) -> Dict:
        """
        Run multi-timeframe analysis.
        
        Args:
            tf_map: Dict of {timeframe: data} from per_tf_builder
        
        Returns:
            MTF analysis with per-TF results and global summary
        """
        # Import interpretation engine
        from modules.ta_engine.interpretation.interpretation_engine import get_interpretation_engine
        ie = get_interpretation_engine()
        
        analyses = {}
        
        for tf, data in tf_map.items():
            role = self.classify_tf(tf)
            
            if role == "htf":
                analyses[tf] = self._build_htf_context(tf, data)
            elif role == "mtf":
                analyses[tf] = self._build_mtf_analysis(tf, data)
            else:  # ltf
                analyses[tf] = self._build_ltf_analysis(tf, data)
            
            # ADD INTERPRETATION — always provide meaningful analysis text
            tf_data = analyses[tf].to_dict()
            interpretation = ie.interpret(role, tf_data)
            analyses[tf].message = interpretation  # Override with rich interpretation
            
            print(f"[MTFEngine] {tf} ({role}): trend={analyses[tf].trend}, "
                  f"pattern={'YES' if analyses[tf].pattern else 'NO'}")
        
        summary = self._build_global_summary(analyses)
        
        # Add interpretation summary
        htf_data = None
        mtf_data = None
        ltf_data = None
        
        for tf in ["1Y", "6M", "1M", "180D", "30D"]:
            if tf in analyses:
                htf_data = analyses[tf].to_dict()
                break
        for tf in ["7D", "1D"]:
            if tf in analyses:
                mtf_data = analyses[tf].to_dict()
                break
        if "4H" in analyses:
            ltf_data = analyses["4H"].to_dict()
        
        summary["summary_text"] = ie.build_one_line_summary(htf_data, mtf_data, ltf_data)
        
        return {
            "analyses": {tf: a.to_dict() for tf, a in analyses.items()},
            "summary": summary,
        }


# Singleton
_mtf_engine = None

def get_mtf_engine() -> MTFEngine:
    """Get MTF engine singleton."""
    global _mtf_engine
    if _mtf_engine is None:
        _mtf_engine = MTFEngine()
    return _mtf_engine
