"""
Probability Engine - Layer 7
============================

Обчислює ймовірності напрямку руху.
Це НЕ prediction - це aggregation факторів.

Output:
{
    "bullish": 38,
    "bearish": 62,
    "neutral": 0,
    "confidence": "medium",
    "factors": [...]
}
"""

from typing import Dict, List


class ProbabilityEngine:
    """
    Probability Engine V1 - агрегація факторів у ймовірність.
    
    Фактори:
    - Structure (trend direction, BOS/CHOCH)
    - Impulse (direction, strength)
    - Regime (trend/range/compression)
    - Pattern (if any)
    - Position in range (near top/bottom/mid)
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Ваги факторів
        self.weights = {
            "structure": 0.25,
            "impulse": 0.20,
            "regime": 0.15,
            "pattern": 0.15,
            "position": 0.15,
            "momentum": 0.10,
        }
    
    def calculate_probability(
        self,
        structure: Dict,
        impulse: Dict,
        regime: Dict,
        pattern: Dict = None,
        current_price: float = None,
    ) -> Dict:
        """
        Обчислює ймовірності на основі всіх факторів.
        
        Returns:
            {
                "bullish": int (0-100),
                "bearish": int (0-100),
                "neutral": int (0-100),
                "confidence": "low" | "medium" | "high",
                "dominant_bias": "bullish" | "bearish" | "neutral",
                "factors": [
                    {"name": "structure", "bias": "bearish", "weight": 0.25, "score": -0.7},
                    ...
                ]
            }
        """
        factors = []
        
        # 1. Structure factor
        structure_score = self._score_structure(structure)
        factors.append({
            "name": "structure",
            "bias": "bullish" if structure_score > 0 else "bearish" if structure_score < 0 else "neutral",
            "weight": self.weights["structure"],
            "score": structure_score,
        })
        
        # 2. Impulse factor
        impulse_score = self._score_impulse(impulse)
        factors.append({
            "name": "impulse",
            "bias": "bullish" if impulse_score > 0 else "bearish" if impulse_score < 0 else "neutral",
            "weight": self.weights["impulse"],
            "score": impulse_score,
        })
        
        # 3. Regime factor
        regime_score = self._score_regime(regime, current_price)
        factors.append({
            "name": "regime",
            "bias": "bullish" if regime_score > 0 else "bearish" if regime_score < 0 else "neutral",
            "weight": self.weights["regime"],
            "score": regime_score,
        })
        
        # 4. Pattern factor
        pattern_score = self._score_pattern(pattern)
        factors.append({
            "name": "pattern",
            "bias": "bullish" if pattern_score > 0 else "bearish" if pattern_score < 0 else "neutral",
            "weight": self.weights["pattern"],
            "score": pattern_score,
        })
        
        # 5. Position in range factor
        position_score = self._score_position(regime, current_price)
        factors.append({
            "name": "position",
            "bias": "bullish" if position_score > 0 else "bearish" if position_score < 0 else "neutral",
            "weight": self.weights["position"],
            "score": position_score,
        })
        
        # Aggregate
        total_score = sum(f["score"] * f["weight"] for f in factors)
        
        # Convert to probabilities
        if total_score > 0:
            bullish = min(50 + int(total_score * 50), 95)
            bearish = 100 - bullish
        elif total_score < 0:
            bearish = min(50 + int(abs(total_score) * 50), 95)
            bullish = 100 - bearish
        else:
            bullish = 50
            bearish = 50
        
        # Determine confidence
        confidence = self._determine_confidence(factors)
        
        return {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": 0,
            "confidence": confidence,
            "dominant_bias": "bullish" if bullish > bearish else "bearish" if bearish > bullish else "neutral",
            "factors": factors,
        }
    
    def _score_structure(self, structure: Dict) -> float:
        """Score from -1 to +1 based on market structure."""
        if not structure:
            return 0
        
        trend = structure.get("trend", "neutral")
        strength = structure.get("strength", 0.5)
        
        if trend == "bullish":
            return strength
        elif trend == "bearish":
            return -strength
        return 0
    
    def _score_impulse(self, impulse: Dict) -> float:
        """Score based on last impulse."""
        if not impulse or not impulse.get("has_impulse"):
            return 0
        
        direction = impulse.get("direction", "none")
        strength = impulse.get("strength", "weak")
        bars_ago = impulse.get("bars_ago", 100)
        
        # Base score
        if direction == "bullish":
            base = 0.5
        elif direction == "bearish":
            base = -0.5
        else:
            return 0
        
        # Strength modifier
        strength_mult = {"weak": 0.5, "moderate": 0.75, "strong": 1.0, "extreme": 1.2}.get(strength, 0.5)
        
        # Recency modifier (newer = more relevant)
        if bars_ago <= 5:
            recency = 1.0
        elif bars_ago <= 10:
            recency = 0.8
        elif bars_ago <= 20:
            recency = 0.5
        else:
            recency = 0.2
        
        return base * strength_mult * recency
    
    def _score_regime(self, regime: Dict, current_price: float = None) -> float:
        """Score based on market regime."""
        if not regime:
            return 0
        
        regime_type = regime.get("regime", "unknown")
        
        if regime_type == "trend":
            direction = regime.get("trend_direction", "neutral")
            return 0.5 if direction == "bullish" else -0.5 if direction == "bearish" else 0
        
        elif regime_type == "range":
            # In range - bias depends on position
            return 0  # Position factor handles this
        
        elif regime_type == "compression":
            return 0  # No bias in compression
        
        return 0
    
    def _score_pattern(self, pattern: Dict) -> float:
        """Score based on detected pattern."""
        if not pattern:
            return 0
        
        pattern_type = (pattern.get("type") or "").lower()
        confidence = pattern.get("confidence", 0.5)
        
        bullish_patterns = ["inverse_head_shoulders", "double_bottom", "ascending_triangle", "bull_flag"]
        bearish_patterns = ["head_shoulders", "double_top", "descending_triangle", "bear_flag"]
        
        if any(p in pattern_type for p in bullish_patterns):
            return confidence * 0.7
        elif any(p in pattern_type for p in bearish_patterns):
            return -confidence * 0.7
        
        return 0
    
    def _score_position(self, regime: Dict, current_price: float = None) -> float:
        """Score based on position in range."""
        if not regime or not current_price:
            return 0
        
        range_data = regime.get("range")
        if not range_data:
            return 0
        
        top = range_data.get("top", 0)
        bottom = range_data.get("bottom", 0)
        
        if top <= bottom:
            return 0
        
        # Position in range (0 = bottom, 1 = top)
        position = (current_price - bottom) / (top - bottom)
        position = max(0, min(1, position))
        
        # Near bottom = bullish bias, near top = bearish bias
        if position < 0.3:
            return 0.5  # Near support - bullish
        elif position > 0.7:
            return -0.5  # Near resistance - bearish
        
        return 0
    
    def _determine_confidence(self, factors: List[Dict]) -> str:
        """Determine confidence based on factor agreement."""
        bullish_count = sum(1 for f in factors if f["score"] > 0.2)
        bearish_count = sum(1 for f in factors if f["score"] < -0.2)
        
        agreement = max(bullish_count, bearish_count)
        
        if agreement >= 4:
            return "high"
        elif agreement >= 3:
            return "medium"
        else:
            return "low"


# Singleton
_probability_engine = None

def get_probability_engine(config: Dict = None) -> ProbabilityEngine:
    global _probability_engine
    if _probability_engine is None:
        _probability_engine = ProbabilityEngine(config)
    return _probability_engine


def calculate_probability(
    structure: Dict,
    impulse: Dict,
    regime: Dict,
    pattern: Dict = None,
    current_price: float = None,
) -> Dict:
    """Shortcut функція."""
    engine = get_probability_engine()
    return engine.calculate_probability(structure, impulse, regime, pattern, current_price)
