"""
MARKET NARRATIVE ENGINE
========================

Превращает сырые данные TA в осмысленные описания рынка.

Было: "Loose Range Developing"
Стало: "Market is consolidating after bullish impulse, showing early compression signals"

НЕ генерируем текст "из головы" — собираем из:
STRUCTURE + PATTERN + CONTEXT
"""

from typing import Dict, Optional, Any


def build_market_narrative(
    structure: Optional[Dict[str, Any]] = None,
    pattern: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Build market narrative from structure, pattern and context.
    
    Returns:
        {
            "short": "First sentence only",
            "full": "Complete narrative"
        }
    """
    parts = []

    # 1. STRUCTURE
    if structure:
        trend = structure.get("trend") or structure.get("bias", "neutral")

        if trend in ("up", "bullish"):
            parts.append("Market is in an uptrend with higher highs and higher lows")
        elif trend in ("down", "bearish"):
            parts.append("Market is in a downtrend with lower highs and lower lows")
        else:
            parts.append("Market is moving in a neutral structure")

    # 2. PATTERN
    if pattern and pattern.get("type"):
        p_type = pattern["type"].replace("_", " ")
        mode = pattern.get("mode", "loose")
        bias = pattern.get("bias", "neutral")

        if mode == "strict":
            if bias == "bullish":
                parts.append(f"A confirmed {p_type} pattern suggests bullish continuation")
            elif bias == "bearish":
                parts.append(f"A confirmed {p_type} pattern suggests bearish pressure")
            else:
                parts.append(f"A confirmed {p_type} pattern is present")
        else:
            # LOOSE pattern
            if bias == "bullish":
                parts.append(f"A developing {p_type} structure is forming with bullish implications")
            elif bias == "bearish":
                parts.append(f"A developing {p_type} structure is forming with bearish implications")
            else:
                parts.append(f"A developing {p_type} structure is forming")

    # 3. CONTEXT (optional enrichment)
    if context:
        volatility = context.get("volatility")
        regime = context.get("regime")
        phase = context.get("phase")
        
        if volatility == "low":
            parts.append("Volatility is decreasing, indicating potential compression")
        elif volatility == "high":
            parts.append("Volatility is elevated, expect larger moves")
            
        if regime == "accumulation":
            parts.append("Market appears to be in accumulation phase")
        elif regime == "distribution":
            parts.append("Market shows signs of distribution")
            
        if phase == "consolidation":
            parts.append("Price is consolidating within range")
        elif phase == "expansion":
            parts.append("Price is in expansion mode")

    # Build result
    if not parts:
        return {
            "short": "Analyzing market structure",
            "full": "Market structure is developing. Waiting for clearer signals.",
        }

    full_narrative = ". ".join(parts) + "."
    short_narrative = parts[0] + "." if parts else "Analyzing..."

    return {
        "short": short_narrative,
        "full": full_narrative,
    }


def build_mtf_narrative(
    tf_data: Dict[str, Dict[str, Any]],
    alignment: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Build multi-timeframe narrative.
    
    tf_data = {
        "1D": {"pattern": {...}, "structure": {...}},
        "4H": {"pattern": {...}, "structure": {...}},
    }
    """
    parts = []

    # HTF (Higher Timeframe)
    htf_keys = ["1M", "7D", "1D"]
    for tf in htf_keys:
        if tf in tf_data and tf_data[tf].get("pattern"):
            p_type = tf_data[tf]["pattern"].get("type", "structure").replace("_", " ")
            parts.append(f"On higher timeframe ({tf}), market shows {p_type}")
            break

    # LTF (Lower Timeframe)
    ltf_keys = ["4H", "1H"]
    for tf in ltf_keys:
        if tf in tf_data and tf_data[tf].get("pattern"):
            p_type = tf_data[tf]["pattern"].get("type", "structure").replace("_", " ")
            mode = tf_data[tf]["pattern"].get("mode", "loose")
            
            if mode == "strict":
                parts.append(f"On lower timeframe ({tf}), confirmed {p_type} is present")
            else:
                parts.append(f"On lower timeframe ({tf}), {p_type} is forming")
            break

    # Alignment summary
    if alignment:
        direction = alignment.get("direction", "neutral")
        confidence = alignment.get("confidence", 0)

        if direction == "bullish":
            if confidence >= 0.7:
                parts.append("Overall structure strongly leans bullish across timeframes")
            else:
                parts.append("Overall structure leans bullish")
        elif direction == "bearish":
            if confidence >= 0.7:
                parts.append("Overall structure strongly leans bearish across timeframes")
            else:
                parts.append("Overall structure leans bearish")
        else:
            parts.append("Market shows mixed signals across timeframes")

    if not parts:
        return {
            "short": "Analyzing multi-timeframe structure",
            "full": "Multi-timeframe analysis in progress.",
        }

    full_narrative = ". ".join(parts) + "."
    short_narrative = parts[0] + "." if parts else "Analyzing..."

    return {
        "short": short_narrative,
        "full": full_narrative,
    }


# Factory
def get_narrative_engine():
    return {
        "build_market_narrative": build_market_narrative,
        "build_mtf_narrative": build_mtf_narrative,
    }
