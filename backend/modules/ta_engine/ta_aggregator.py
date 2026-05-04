"""
TA Aggregator - 10 Layer Decision System
=========================================

Агрегує всі шари TA в єдиний стан ринку.

Шари:
1. Market Structure (HH/HL/LH/LL, trend, BOS/CHOCH)
2. Impulse & Context
3. Volatility / Regime
4. Range Engine (активний range)
5. Pattern Detection
6. Confluence Layer
7. Probability Engine
8. Scenario Engine
9. Timing Layer
10. Narrative Engine

Output: unified market state для UI
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .impulse_engine import detect_impulse
from .probability_engine import calculate_probability


class TALayerAggregator:
    """
    TA Layer Aggregator V1
    
    Збирає всі слої аналізу в єдиний об'єкт market_state.
    Це МОЗОК системи.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    def aggregate(
        self,
        candles: List[Dict],
        structure: Dict = None,
        pivots: Dict = None,
        pattern: Dict = None,
        pattern_render_contract: Dict = None,
        indicators: Dict = None,
        current_price: float = None,
        timeframe: str = "1D",
    ) -> Dict:
        """
        Головна функція агрегації.
        
        Returns:
            {
                "structure": {...},     # Layer 1
                "impulse": {...},       # Layer 2
                "regime": {...},        # Layer 3 + 4
                "pattern": {...},       # Layer 5
                "confluence": {...},    # Layer 6
                "probability": {...},   # Layer 7
                "scenarios": {...},     # Layer 8
                "timing": {...},        # Layer 9
                "narrative": str,       # Layer 10
                "active_range": {...},  # Quick access
                "timestamp": str,
            }
        """
        # Get current price if not provided
        if current_price is None and candles:
            current_price = candles[-1].get("close", 0)
        
        # Layer 1: Market Structure
        layer1_structure = self._build_structure_layer(structure, pivots)
        
        # Layer 2: Impulse & Context
        layer2_impulse = detect_impulse(candles) if candles else {}
        
        # Layer 3 + 4: Regime & Range
        layer3_regime = self._build_regime_layer(
            candles, layer1_structure, layer2_impulse, current_price, pattern_render_contract
        )
        
        # Layer 5: Pattern
        layer5_pattern = self._build_pattern_layer(pattern, pattern_render_contract)
        
        # Layer 6: Confluence
        layer6_confluence = self._calculate_confluence(
            layer1_structure, layer2_impulse, layer3_regime, layer5_pattern, current_price
        )
        
        # Layer 7: Probability
        layer7_probability = calculate_probability(
            layer1_structure, layer2_impulse, layer3_regime, layer5_pattern, current_price
        )
        
        # Layer 8: Scenarios
        layer8_scenarios = self._build_scenarios(
            layer3_regime, layer7_probability, current_price
        )
        
        # Layer 9: Timing
        layer9_timing = self._determine_timing(
            candles, layer3_regime, layer2_impulse
        )
        
        # Layer 10: Narrative
        layer10_narrative = self._generate_narrative(
            layer1_structure, layer2_impulse, layer3_regime, 
            layer5_pattern, layer7_probability, timeframe
        )
        
        # Active range shortcut
        active_range = layer3_regime.get("range") if layer3_regime.get("regime") == "range" else None
        
        return {
            "structure": layer1_structure,
            "impulse": layer2_impulse,
            "regime": layer3_regime,
            "pattern": layer5_pattern,
            "confluence": layer6_confluence,
            "probability": layer7_probability,
            "scenarios": layer8_scenarios,
            "timing": layer9_timing,
            "narrative": layer10_narrative,
            "active_range": active_range,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    # =========================================================================
    # LAYER BUILDERS
    # =========================================================================
    
    def _build_structure_layer(self, structure: Dict, pivots: Dict) -> Dict:
        """Layer 1: Market Structure."""
        if not structure:
            return {
                "trend": "neutral",
                "phase": "unknown",
                "strength": 0.5,
                "last_bos": None,
                "last_choch": None,
            }
        
        return {
            "trend": structure.get("trend", structure.get("direction", "neutral")),
            "phase": structure.get("phase", "unknown"),
            "strength": structure.get("strength", 0.5),
            "last_bos": structure.get("last_bos"),
            "last_choch": structure.get("last_choch"),
            "sequence": structure.get("sequence", []),
        }
    
    def _build_regime_layer(
        self,
        candles: List[Dict],
        structure: Dict,
        impulse: Dict,
        current_price: float,
        pattern_render_contract: Dict = None,
    ) -> Dict:
        """Layer 3 + 4: Regime & Range."""
        
        if not candles or len(candles) < 20:
            return {"regime": "unknown"}
        
        # PRIORITY: If PRO_PATTERN_ENGINE detected range, use it
        if pattern_render_contract:
            prc_type = (pattern_render_contract.get("type") or "").lower()
            if "range" in prc_type and pattern_render_contract.get("display_approved"):
                # Use range from pattern_render_contract
                meta = pattern_render_contract.get("meta", {})
                boundaries = meta.get("boundaries", {})
                
                resistance = meta.get("resistance", 0)
                support = meta.get("support", 0)
                
                if resistance > 0 and support > 0:
                    # Build range from PRO engine data
                    upper = boundaries.get("upper", {})
                    lower = boundaries.get("lower", {})
                    
                    start_time = upper.get("x1", lower.get("x1", 0))
                    end_time = candles[-1].get("time", 0)
                    
                    # Forward extension
                    if len(candles) >= 2:
                        bar_duration = candles[-1].get("time", 0) - candles[-2].get("time", 0)
                        forward_time = end_time + bar_duration * 30
                    else:
                        forward_time = end_time
                    
                    # State based on current price
                    if current_price > resistance * 0.98:
                        state = "testing_upper"
                    elif current_price < support * 1.02:
                        state = "testing_lower"
                    else:
                        state = "active"
                    
                    return {
                        "regime": "range",
                        "state": state,
                        "range": {
                            "status": "active",
                            "top": resistance,
                            "bottom": support,
                            "mid": (resistance + support) / 2,
                            "width_pct": round((resistance - support) / support * 100, 2),
                            "start_time": start_time,
                            "end_time": end_time,
                            "forward_time": forward_time,
                            "state": state,
                            "context": impulse.get("context", "unknown"),
                            "source": "PRO_PATTERN_ENGINE",
                        },
                        "volatility": "medium",
                    }
        
        # Fallback: detect regime from data
        recent = candles[-20:]
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]
        
        max_high = max(highs)
        min_low = min(lows)
        range_pct = (max_high - min_low) / min_low if min_low > 0 else 0
        
        # Check compression
        very_recent = candles[-5:]
        recent_range = (max(c["high"] for c in very_recent) - min(c["low"] for c in very_recent))
        avg_range = (max_high - min_low) / 4
        is_compression = recent_range < avg_range * 0.5
        
        if is_compression:
            return {
                "regime": "compression",
                "state": "squeeze",
                "volatility": "low",
            }
        
        # Check for range (no fresh impulse + limited volatility)
        is_range = (
            (not impulse.get("has_impulse") or impulse.get("bars_ago", 100) > 15)
            and range_pct < 0.15
        )
        
        if is_range:
            range_data = self._build_active_range(candles, impulse, current_price)
            return {
                "regime": "range",
                "state": range_data.get("state", "active"),
                "range": range_data,
                "volatility": "medium",
            }
        
        # Trend
        trend_direction = structure.get("trend", "neutral")
        return {
            "regime": "trend",
            "state": "impulsive" if impulse.get("has_impulse") else "grinding",
            "trend_direction": trend_direction,
            "volatility": "high" if impulse.get("strength") in ["strong", "extreme"] else "medium",
        }
    
    def _build_active_range(
        self,
        candles: List[Dict],
        impulse: Dict,
        current_price: float,
    ) -> Dict:
        """Будує активний range."""
        
        if len(candles) < 20:
            return {}
        
        # Шукаємо boundaries
        lookback = min(50, len(candles))
        recent = candles[-lookback:]
        
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]
        
        resistance = max(highs)
        support = min(lows)
        
        # Знаходимо коли почався баланс
        # Якщо був імпульс - починаємо після нього
        if impulse.get("has_impulse") and impulse.get("bars_ago", 100) < lookback:
            start_idx = len(candles) - lookback + impulse.get("bars_ago", 0)
        else:
            start_idx = len(candles) - lookback
        
        start_time = candles[start_idx].get("time", 0)
        end_time = candles[-1].get("time", 0)
        
        # Forward extension
        if len(candles) >= 2:
            bar_duration = candles[-1].get("time", 0) - candles[-2].get("time", 0)
            forward_time = end_time + bar_duration * 30  # 30 bars forward
        else:
            forward_time = end_time
        
        # Визначаємо стан
        if current_price > resistance * 0.98:
            state = "testing_upper"
        elif current_price < support * 1.02:
            state = "testing_lower"
        else:
            state = "active"
        
        return {
            "status": "active",
            "top": resistance,
            "bottom": support,
            "mid": (resistance + support) / 2,
            "width_pct": round((resistance - support) / support * 100, 2),
            "start_time": start_time,
            "end_time": end_time,
            "forward_time": forward_time,
            "state": state,
            "context": impulse.get("context", "unknown"),
            "duration_bars": lookback - impulse.get("bars_ago", 0),
        }
    
    def _build_pattern_layer(self, pattern: Dict, render_contract: Dict) -> Dict:
        """Layer 5: Pattern."""
        
        # Приоритет: render_contract (PRO Engine)
        if render_contract and render_contract.get("display_approved"):
            return {
                "type": render_contract.get("type"),
                "confidence": render_contract.get("confidence", 0.5),
                "source": render_contract.get("source", "PRO_ENGINE"),
                "direction": render_contract.get("bias", "neutral"),
                "meta": render_contract.get("meta", {}),
            }
        
        if pattern:
            return {
                "type": pattern.get("type"),
                "confidence": pattern.get("confidence", pattern.get("score", 0.5)),
                "source": "legacy_detector",
                "direction": pattern.get("direction", "neutral"),
            }
        
        return {"type": None, "confidence": 0}
    
    def _calculate_confluence(
        self,
        structure: Dict,
        impulse: Dict,
        regime: Dict,
        pattern: Dict,
        current_price: float,
    ) -> Dict:
        """Layer 6: Confluence."""
        
        factors = []
        
        # Structure
        if structure.get("trend") in ["bullish", "bearish"]:
            factors.append(f"structure_{structure['trend']}")
        
        # Impulse
        if impulse.get("has_impulse"):
            factors.append(f"impulse_{impulse['direction']}")
        
        # Range position
        if regime.get("regime") == "range":
            range_data = regime.get("range", {})
            state = range_data.get("state")
            if state == "testing_upper":
                factors.append("at_resistance")
            elif state == "testing_lower":
                factors.append("at_support")
        
        # Pattern
        if pattern.get("type"):
            p_type = pattern["type"].lower()
            if any(b in p_type for b in ["inverse", "bottom", "ascending", "bull"]):
                factors.append("bullish_pattern")
            elif any(b in p_type for b in ["head_shoulders", "top", "descending", "bear"]):
                factors.append("bearish_pattern")
        
        # Count bias
        bullish_factors = [f for f in factors if "bullish" in f or "support" in f]
        bearish_factors = [f for f in factors if "bearish" in f or "resistance" in f]
        
        return {
            "count": len(factors),
            "factors": factors,
            "bullish_factors": len(bullish_factors),
            "bearish_factors": len(bearish_factors),
            "alignment": "bullish" if len(bullish_factors) > len(bearish_factors) else 
                        "bearish" if len(bearish_factors) > len(bullish_factors) else "mixed",
        }
    
    def _build_scenarios(
        self,
        regime: Dict,
        probability: Dict,
        current_price: float,
    ) -> Dict:
        """Layer 8: Scenarios."""
        
        if not current_price:
            return {}
        
        range_data = regime.get("range", {})
        
        if range_data:
            top = range_data.get("top", current_price * 1.05)
            bottom = range_data.get("bottom", current_price * 0.95)
            
            return {
                "break_up": {
                    "target": round(top + (top - bottom) * 0.5, 2),  # Measured move
                    "trigger": top,
                    "probability": probability.get("bullish", 50),
                },
                "break_down": {
                    "target": round(bottom - (top - bottom) * 0.5, 2),
                    "trigger": bottom,
                    "probability": probability.get("bearish", 50),
                },
            }
        
        # No range - use basic targets
        return {
            "break_up": {
                "target": round(current_price * 1.05, 2),
                "probability": probability.get("bullish", 50),
            },
            "break_down": {
                "target": round(current_price * 0.95, 2),
                "probability": probability.get("bearish", 50),
            },
        }
    
    def _determine_timing(
        self,
        candles: List[Dict],
        regime: Dict,
        impulse: Dict,
    ) -> Dict:
        """Layer 9: Timing."""
        
        range_data = regime.get("range", {})
        
        if not range_data:
            return {"phase": "unknown", "compression": False}
        
        duration = range_data.get("duration_bars", 0)
        
        if duration < 5:
            phase = "early"
        elif duration < 15:
            phase = "mid"
        else:
            phase = "late"
        
        # Check compression
        if candles and len(candles) >= 5:
            recent = candles[-5:]
            recent_range = max(c["high"] for c in recent) - min(c["low"] for c in recent)
            total_range = range_data.get("top", 0) - range_data.get("bottom", 0)
            compression = recent_range < total_range * 0.3 if total_range > 0 else False
        else:
            compression = False
        
        return {
            "phase": phase,
            "compression": compression,
            "bars_in_range": duration,
        }
    
    def _generate_narrative(
        self,
        structure: Dict,
        impulse: Dict,
        regime: Dict,
        pattern: Dict,
        probability: Dict,
        timeframe: str,
    ) -> str:
        """Layer 10: Narrative Engine - людське пояснення."""
        
        parts = []
        
        # Structure context
        trend = structure.get("trend", "neutral")
        if trend == "bullish":
            parts.append("Market structure is bullish")
        elif trend == "bearish":
            parts.append("Market structure is bearish")
        else:
            parts.append("Market structure is neutral")
        
        # Impulse context
        if impulse.get("has_impulse"):
            direction = impulse.get("direction")
            strength = impulse.get("strength")
            bars_ago = impulse.get("bars_ago", 0)
            
            if bars_ago <= 5:
                parts.append(f"with a recent {strength} {direction} impulse")
            elif bars_ago <= 15:
                parts.append(f"after a {direction} impulse")
        
        # Regime
        regime_type = regime.get("regime")
        if regime_type == "range":
            range_data = regime.get("range", {})
            state = range_data.get("state", "active")
            top = range_data.get("top", 0)
            bottom = range_data.get("bottom", 0)
            
            if state == "testing_upper":
                parts.append(f"Price is testing range resistance near {top:.0f}")
            elif state == "testing_lower":
                parts.append(f"Price is testing range support near {bottom:.0f}")
            else:
                parts.append(f"Price is consolidating in range ({bottom:.0f} - {top:.0f})")
        
        elif regime_type == "compression":
            parts.append("Volatility is compressing - breakout expected")
        
        # Probability bias
        bullish = probability.get("bullish", 50)
        bearish = probability.get("bearish", 50)
        
        if bullish > 60:
            parts.append(f"Bullish bias ({bullish}%)")
        elif bearish > 60:
            parts.append(f"Bearish bias ({bearish}%)")
        
        return ". ".join(parts) + "."


# Singleton
_aggregator = None

def get_ta_aggregator(config: Dict = None) -> TALayerAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = TALayerAggregator(config)
    return _aggregator


def aggregate_ta_layers(
    candles: List[Dict],
    structure: Dict = None,
    pivots: Dict = None,
    pattern: Dict = None,
    pattern_render_contract: Dict = None,
    indicators: Dict = None,
    current_price: float = None,
    timeframe: str = "1D",
) -> Dict:
    """Shortcut функція."""
    aggregator = get_ta_aggregator()
    return aggregator.aggregate(
        candles=candles,
        structure=structure,
        pivots=pivots,
        pattern=pattern,
        pattern_render_contract=pattern_render_contract,
        indicators=indicators,
        current_price=current_price,
        timeframe=timeframe,
    )
