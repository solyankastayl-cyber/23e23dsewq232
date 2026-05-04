"""
Dummy Builders

Placeholder functions for TA and Prediction building.
Replace with real implementations.
"""

import random
from typing import Dict, Any


def build_dummy_ta(symbol: str, timeframe: str) -> Dict[str, Any]:
    """
    Build dummy TA payload.
    
    Replace with real TA Engine integration.
    """
    # Random pattern
    patterns = ["triangle", "range", "channel", "wedge", "none"]
    directions = ["bullish", "bearish", "neutral"]
    structures = ["trend", "range", "compression", "expansion"]
    trends = ["up", "down", "flat"]
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "pattern": {
            "type": random.choice(patterns),
            "direction": random.choice(directions),
            "confidence": round(random.uniform(0.3, 0.9), 2),
        },
        "structure": {
            "state": random.choice(structures),
            "trend": random.choice(trends),
            "trend_strength": round(random.uniform(0.3, 0.8), 2),
        },
        "indicators": {
            "momentum": round(random.uniform(-0.5, 0.5), 2),
            "trend_strength": round(random.uniform(0.3, 0.8), 2),
            "volatility": round(random.uniform(0.2, 0.6), 2),
            "rsi": round(random.uniform(30, 70), 1),
        },
        "price": round(random.uniform(100, 100000), 2),
    }


def build_dummy_prediction(ta_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build dummy prediction from TA.
    
    Replace with real Prediction Engine integration.
    """
    pattern = ta_payload.get("pattern", {})
    structure = ta_payload.get("structure", {})
    indicators = ta_payload.get("indicators", {})
    price = ta_payload.get("price", 1000)
    
    # Determine direction
    pattern_dir = pattern.get("direction", "neutral")
    momentum = indicators.get("momentum", 0)
    
    if pattern_dir == "bullish" or momentum > 0.2:
        direction_label = "bullish"
        direction_score = random.uniform(0.2, 0.8)
    elif pattern_dir == "bearish" or momentum < -0.2:
        direction_label = "bearish"
        direction_score = random.uniform(-0.8, -0.2)
    else:
        direction_label = "neutral"
        direction_score = random.uniform(-0.2, 0.2)
    
    # Calculate targets
    base_move = pattern.get("confidence", 0.5) * 0.05 * (1 + indicators.get("volatility", 0.3))
    
    if direction_label == "bullish":
        base_target = price * (1 + base_move)
        bull_target = price * (1 + base_move * 1.5)
        bear_target = price * (1 - base_move * 0.5)
    elif direction_label == "bearish":
        base_target = price * (1 - base_move)
        bull_target = price * (1 + base_move * 0.5)
        bear_target = price * (1 - base_move * 1.5)
    else:
        base_target = price
        bull_target = price * (1 + base_move * 0.8)
        bear_target = price * (1 - base_move * 0.8)
    
    # Confidence
    confidence = round(
        pattern.get("confidence", 0.5) * 0.4 +
        indicators.get("trend_strength", 0.5) * 0.3 +
        (1 - abs(momentum)) * 0.3,
        2
    )
    
    return {
        "symbol": ta_payload.get("symbol", "UNKNOWN"),
        "timeframe": ta_payload.get("timeframe", "1D"),
        "current_price": price,
        "direction": {
            "label": direction_label,
            "score": round(direction_score, 4),
        },
        "confidence": {
            "value": confidence,
            "label": "HIGH" if confidence > 0.7 else ("MEDIUM" if confidence > 0.5 else "LOW"),
        },
        "scenarios": {
            "bull": {
                "probability": 0.55 if direction_label == "bullish" else 0.25,
                "target_price": round(bull_target, 2),
                "expected_return": round((bull_target - price) / price, 4),
            },
            "base": {
                "probability": 0.30,
                "target_price": round(base_target, 2),
                "expected_return": round((base_target - price) / price, 4),
            },
            "bear": {
                "probability": 0.55 if direction_label == "bearish" else 0.15,
                "target_price": round(bear_target, 2),
                "expected_return": round((bear_target - price) / price, 4),
            },
        },
        "horizon_days": 5 if ta_payload.get("timeframe") == "1D" else 2,
        "version": "v2",
    }


def get_real_ta_builder():
    """
    Get real TA builder function.
    
    Connects to actual TA Engine.
    """
    try:
        # Import real TA engine
        # from modules.ta_engine import build_ta_for_symbol
        # return build_ta_for_symbol
        return build_dummy_ta
    except ImportError:
        return build_dummy_ta


def get_real_prediction_builder():
    """
    Get real prediction builder function.
    
    Connects to actual Prediction Engine.
    """
    try:
        from modules.prediction import build_prediction
        from modules.prediction.ta_interpreter import interpret_ta_output
        
        def build_real_prediction(ta_payload: Dict) -> Dict:
            symbol = ta_payload.get("symbol", "UNKNOWN")
            timeframe = ta_payload.get("timeframe", "1D")
            
            pred_input = interpret_ta_output(ta_payload, symbol, timeframe)
            prediction = build_prediction(pred_input)
            return prediction.to_dict()
        
        return build_real_prediction
    except ImportError:
        return build_dummy_prediction
