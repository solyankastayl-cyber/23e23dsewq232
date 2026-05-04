"""
Confluence Engine
=================
Aggregates indicator signals into bullish/bearish/neutral matrix.

Returns:
- bullish_indicators: list of indicators signaling bullish
- bearish_indicators: list of indicators signaling bearish
- neutral_indicators: list of neutral indicators
- conflicts: conflicting signals
- overall_strength: -1.0 (full bearish) to +1.0 (full bullish)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from modules.ta_engine.setup.indicator_engine import get_indicator_engine


@dataclass
class ConfluenceResult:
    """Confluence analysis result."""
    bullish: List[Dict] = field(default_factory=list)
    bearish: List[Dict] = field(default_factory=list)
    neutral: List[Dict] = field(default_factory=list)
    conflicts: List[Dict] = field(default_factory=list)
    overall_strength: float = 0.0
    overall_bias: str = "neutral"
    confidence: float = 0.0
    summary: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "bullish": self.bullish,
            "bearish": self.bearish,
            "neutral": self.neutral,
            "conflicts": self.conflicts,
            "overall_strength": round(self.overall_strength, 3),
            "overall_bias": self.overall_bias,
            "confidence": round(self.confidence, 2),
            "summary": self.summary,
            "counts": {
                "bullish": len(self.bullish),
                "bearish": len(self.bearish),
                "neutral": len(self.neutral),
                "conflicts": len(self.conflicts),
            }
        }


class ConfluenceEngine:
    """Aggregates indicator signals into confluence matrix."""
    
    def __init__(self):
        self.indicator_engine = get_indicator_engine()
    
    def build(self, candles: List[Dict]) -> ConfluenceResult:
        """
        Build confluence matrix from candles.
        
        Returns aggregated bullish/bearish/neutral indicators.
        """
        if len(candles) < 50:
            return ConfluenceResult(
                summary="Insufficient data for confluence analysis"
            )
        
        # Get all indicator signals
        signals = self.indicator_engine.analyze_all(candles)
        
        bullish = []
        bearish = []
        neutral = []
        
        for signal in signals:
            entry = {
                "name": signal.name,
                "signal_type": signal.signal_type,
                "strength": round(signal.strength, 2),
                "value": round(signal.value, 2) if signal.value else None,
                "description": signal.description,
            }
            
            if signal.direction.value == "bullish":
                bullish.append(entry)
            elif signal.direction.value == "bearish":
                bearish.append(entry)
            else:
                neutral.append(entry)
        
        # Detect conflicts (same indicator family with opposite signals)
        conflicts = self._detect_conflicts(bullish, bearish)
        
        # Calculate overall strength
        bullish_weight = sum(s["strength"] for s in bullish)
        bearish_weight = sum(s["strength"] for s in bearish)
        total_weight = bullish_weight + bearish_weight
        
        if total_weight > 0:
            overall_strength = (bullish_weight - bearish_weight) / total_weight
        else:
            overall_strength = 0.0
        
        # Determine bias
        if overall_strength > 0.3:
            overall_bias = "bullish"
        elif overall_strength < -0.3:
            overall_bias = "bearish"
        else:
            overall_bias = "neutral"
        
        # Calculate confidence (higher when signals agree)
        agreement = abs(overall_strength)
        signal_count = len(bullish) + len(bearish)
        confidence = min(0.95, agreement * 0.6 + min(signal_count / 10, 0.4))
        
        # Build summary
        summary = self._build_summary(bullish, bearish, neutral, overall_bias, confidence)
        
        return ConfluenceResult(
            bullish=bullish,
            bearish=bearish,
            neutral=neutral,
            conflicts=conflicts,
            overall_strength=overall_strength,
            overall_bias=overall_bias,
            confidence=confidence,
            summary=summary,
        )
    
    def _detect_conflicts(self, bullish: List[Dict], bearish: List[Dict]) -> List[Dict]:
        """Detect conflicting signals from same indicator family."""
        conflicts = []
        
        # Group by indicator family
        bullish_families = set()
        bearish_families = set()
        
        for s in bullish:
            family = s["name"].split("_")[0]  # e.g., EMA, RSI, MACD
            bullish_families.add(family)
        
        for s in bearish:
            family = s["name"].split("_")[0]
            bearish_families.add(family)
        
        # Find overlapping families
        conflicting_families = bullish_families & bearish_families
        
        for family in conflicting_families:
            bull_signals = [s for s in bullish if s["name"].startswith(family)]
            bear_signals = [s for s in bearish if s["name"].startswith(family)]
            
            if bull_signals and bear_signals:
                conflicts.append({
                    "family": family,
                    "bullish": bull_signals[0]["signal_type"],
                    "bearish": bear_signals[0]["signal_type"],
                    "note": f"{family} showing mixed signals"
                })
        
        return conflicts
    
    def _build_summary(
        self,
        bullish: List[Dict],
        bearish: List[Dict],
        neutral: List[Dict],
        overall_bias: str,
        confidence: float
    ) -> str:
        """Build human-readable summary."""
        
        total = len(bullish) + len(bearish) + len(neutral)
        if total == 0:
            return "No indicator signals available"
        
        parts = []
        
        # Overall bias
        if overall_bias == "bullish":
            parts.append(f"Bullish confluence: {len(bullish)} indicators favor upside")
        elif overall_bias == "bearish":
            parts.append(f"Bearish confluence: {len(bearish)} indicators favor downside")
        else:
            parts.append(f"Mixed signals: {len(bullish)} bullish vs {len(bearish)} bearish")
        
        # Top signals
        if bullish:
            top_bull = max(bullish, key=lambda x: x["strength"])
            parts.append(f"Strongest bullish: {top_bull['name']} ({top_bull['signal_type']})")
        
        if bearish:
            top_bear = max(bearish, key=lambda x: x["strength"])
            parts.append(f"Strongest bearish: {top_bear['name']} ({top_bear['signal_type']})")
        
        # Confidence
        conf_level = "high" if confidence > 0.7 else "moderate" if confidence > 0.4 else "low"
        parts.append(f"Confidence: {conf_level} ({int(confidence * 100)}%)")
        
        return " | ".join(parts)


# Singleton
_engine: Optional[ConfluenceEngine] = None


def get_confluence_engine() -> ConfluenceEngine:
    global _engine
    if _engine is None:
        _engine = ConfluenceEngine()
    return _engine
