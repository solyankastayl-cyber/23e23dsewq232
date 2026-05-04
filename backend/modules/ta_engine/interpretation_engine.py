"""
Interpretation Engine PRO
=========================

Превращает паттерны + слои в СМЫСЛ.

ВЫХОД: 1-2 строки, которые отвечают:
1. Контекст (режим рынка)
2. Главная идея (dominant)
3. Риск/условие (конфликт/ожидание)

ВХОД:
{
    "market_state": "COMPRESSION | CONFLICTED | TREND",
    "dominant": {...},
    "alternatives": [...],
    "regime": {...},
    "structure": {...},
    "mtf": {...},  # Multi-timeframe context
    "impulse": {...},  # Prior move data
}
"""

from typing import Dict, List, Optional


def build_interpretation(ctx: Dict) -> Dict:
    """
    Build interpretation from context.
    
    Returns:
        {
            "line1": "Main context + core idea",
            "line2": "Risk / condition",
            "narrative": "Full narrative for detailed view"
        }
    """
    state = ctx.get("market_state", "DEVELOPING")
    dom = ctx.get("dominant") or {}
    alts = ctx.get("alternatives", [])[:2]
    regime = ctx.get("regime") or {}
    mtf = ctx.get("mtf") or {}
    impulse = ctx.get("impulse") or {}
    
    t = dom.get("type", "")
    bias = dom.get("bias", "neutral")
    conf = dom.get("confidence", 0)
    stage = dom.get("stage", "forming")
    lifecycle = dom.get("lifecycle", "forming")
    
    # --- 1) CONTEXT (режим + MTF) ---
    context = _build_context(state, dom, mtf)
    
    # --- 2) CORE IDEA (dominant + impulse) ---
    core = _build_core_idea(t, bias, conf, stage, impulse)
    
    # --- 3) RISK / CONDITION ---
    risk = _build_risk(state, dom, alts)
    
    # --- 4) NARRATIVE V2 (MTF + impulse история) ---
    narrative = _build_narrative_v2(state, dom, alts, mtf, impulse, regime)
    
    # --- 5) LIFECYCLE OVERRIDE ---
    # If lifecycle is confirmed or invalidated, override interpretation
    if lifecycle in ("confirmed_up", "confirmed_down"):
        direction = "upward" if lifecycle == "confirmed_up" else "downward"
        core = "Breakout confirmed. " + direction.capitalize() + " expansion in progress."
        risk = "Monitor for continuation. Previous structure resolved."
    elif lifecycle == "invalidated":
        core = "Pattern invalidated. Previous scenario no longer valid."
        risk = "Wait for new structure to form."
    
    # финал: 1-2 строки
    line1 = f"{context} {core}".strip()
    line2 = risk
    
    return {
        "line1": line1,
        "line2": line2,
        "narrative": narrative,
        "market_state": state,
        "confidence": int(conf * 100) if conf < 1 else int(conf),
    }


# ═══════════════════════════════════════════════════════════════
# CONTEXT (режим + MTF)
# ═══════════════════════════════════════════════════════════════

def _build_context(state: str, dom: Dict, mtf: Dict) -> str:
    """Build context string with MTF awareness."""
    
    # MTF alignment info
    mtf_align = mtf.get("alignment", "neutral")
    higher_tf = mtf.get("higher_tf_bias")
    
    # Base context by state
    if state == "COMPRESSION":
        base = "Market is consolidating."
        if higher_tf == "bullish":
            return f"{base} Higher timeframe bullish."
        if higher_tf == "bearish":
            return f"{base} Higher timeframe bearish."
        return base
    
    if state == "CONFLICTED":
        if mtf_align == "conflicted":
            return "Conflicting signals across timeframes."
        return "Market shows competing structures."
    
    if state == "REVERSAL ↓":
        if higher_tf == "bearish":
            return "Bearish reversal aligns with higher timeframe."
        return "Potential bearish reversal forming."
    
    if state == "REVERSAL ↑":
        if higher_tf == "bullish":
            return "Bullish reversal aligns with higher timeframe."
        return "Potential bullish reversal forming."
    
    if state == "TREND":
        b = dom.get("bias")
        if b == "bullish":
            return "Market trending upward."
        if b == "bearish":
            return "Market trending downward."
        return "Directional move in progress."
    
    return "Market structure developing."


# ═══════════════════════════════════════════════════════════════
# CORE IDEA (dominant + impulse)
# ═══════════════════════════════════════════════════════════════

def _build_core_idea(t: str, bias: str, conf: float, stage: str, impulse: Dict) -> str:
    """Build core idea with impulse context."""
    
    # Normalize confidence
    c = int(conf * 100) if conf < 1 else int(conf)
    
    # Impulse context
    prior_move = impulse.get("prior_trend", "")
    move_strength = impulse.get("strength", "")
    
    # Pattern-specific interpretations
    if t in ["rectangle", "range"]:
        if prior_move == "up":
            return f"Range after uptrend — accumulation or distribution. ({c}%)"
        if prior_move == "down":
            return f"Range after downtrend — accumulation likely. ({c}%)"
        return f"Horizontal consolidation active. ({c}%)"
    
    if t in ["symmetrical_triangle"]:
        return f"Triangle compression — breakout imminent. ({c}%)"
    
    if t in ["ascending_triangle"]:
        return f"Ascending triangle — bullish bias. ({c}%)"
    
    if t in ["descending_triangle"]:
        return f"Descending triangle — bearish bias. ({c}%)"
    
    if t in ["double_top", "triple_top"]:
        if stage == "confirmed":
            return f"Bearish reversal confirmed. ({c}%)"
        return f"Potential top formation. ({c}%)"
    
    if t in ["double_bottom", "triple_bottom"]:
        if stage == "confirmed":
            return f"Bullish reversal confirmed. ({c}%)"
        return f"Potential bottom formation. ({c}%)"
    
    if t in ["head_shoulders"]:
        return f"Head & Shoulders — bearish reversal. ({c}%)"
    
    if t in ["inverse_head_shoulders"]:
        return f"Inverse H&S — bullish continuation. ({c}%)"
    
    if t in ["ascending_channel", "descending_channel", "horizontal_channel"]:
        return f"Channel structure active. ({c}%)"
    
    if t in ["bull_flag", "bear_flag"]:
        if move_strength == "strong":
            return f"Strong continuation pattern after impulse. ({c}%)"
        return f"Continuation pattern forming. ({c}%)"
    
    if t in ["pennant"]:
        return f"Pennant compression after move. ({c}%)"
    
    if t in ["rising_wedge"]:
        return f"Rising wedge — bearish reversal likely. ({c}%)"
    
    if t in ["falling_wedge"]:
        return f"Falling wedge — bullish reversal likely. ({c}%)"
    
    return f"Structure forming. ({c}%)"


# ═══════════════════════════════════════════════════════════════
# RISK / CONDITION
# ═══════════════════════════════════════════════════════════════

def _build_risk(state: str, dom: Dict, alts: List[Dict]) -> str:
    """Build risk/condition string."""
    
    t = dom.get("type", "")
    
    if state == "CONFLICTED":
        names = [a.get("type", "").replace("_", " ") for a in alts if a.get("type")]
        if names:
            return f"Competing: {', '.join(names)}. Wait for confirmation."
        return "Multiple signals conflict. Wait for clarity."
    
    # Pattern-specific risks
    if t in ["symmetrical_triangle", "rectangle", "range"]:
        return "Breakout direction will define next move."
    
    if t in ["ascending_triangle"]:
        return "Watch for breakout above resistance."
    
    if t in ["descending_triangle"]:
        return "Watch for breakdown below support."
    
    if t in ["double_top", "triple_top", "head_shoulders"]:
        return "Confirmation: breakdown below neckline."
    
    if t in ["double_bottom", "triple_bottom", "inverse_head_shoulders"]:
        return "Confirmation: breakout above neckline."
    
    if t in ["bull_flag", "pennant"] and dom.get("bias") == "bullish":
        return "Expect continuation higher after consolidation."
    
    if t in ["bear_flag"] or (t == "pennant" and dom.get("bias") == "bearish"):
        return "Expect continuation lower after consolidation."
    
    if t in ["rising_wedge"]:
        return "Watch for breakdown — wedge typically bearish."
    
    if t in ["falling_wedge"]:
        return "Watch for breakout — wedge typically bullish."
    
    return "Structure not yet confirmed."


# ═══════════════════════════════════════════════════════════════
# NARRATIVE V2 (MTF + impulse story)
# ═══════════════════════════════════════════════════════════════

def _build_narrative_v2(state: str, dom: Dict, alts: List[Dict], 
                        mtf: Dict, impulse: Dict, regime: Dict) -> str:
    """
    Build full narrative that reads market as connected story.
    
    This is for detailed view / tooltip, not main UI.
    """
    parts = []
    
    t = dom.get("type", "unknown")
    bias = dom.get("bias", "neutral")
    conf = dom.get("confidence", 0)
    c = int(conf * 100) if conf < 1 else int(conf)
    
    # --- 1) HIGHER TF CONTEXT ---
    htf_bias = mtf.get("higher_tf_bias")
    htf_pattern = mtf.get("higher_tf_pattern")
    
    if htf_bias:
        if htf_bias == "bullish":
            parts.append("Higher timeframe shows bullish structure.")
        elif htf_bias == "bearish":
            parts.append("Higher timeframe shows bearish structure.")
        elif htf_bias == "neutral":
            parts.append("Higher timeframe is range-bound.")
    
    # --- 2) PRIOR IMPULSE ---
    prior = impulse.get("prior_trend")
    strength = impulse.get("strength")
    
    if prior == "up":
        if strength == "strong":
            parts.append("Strong upward impulse preceded current structure.")
        else:
            parts.append("Upward move led into current pattern.")
    elif prior == "down":
        if strength == "strong":
            parts.append("Strong downward impulse preceded current structure.")
        else:
            parts.append("Downward move led into current pattern.")
    
    # --- 3) CURRENT STRUCTURE ---
    if t in ["rectangle", "range"]:
        parts.append(f"Price is now consolidating in a horizontal range ({c}% confidence).")
    elif t in ["symmetrical_triangle"]:
        parts.append(f"Compression forming symmetrical triangle ({c}% confidence).")
    elif t in ["ascending_triangle"]:
        parts.append(f"Ascending triangle with flat resistance ({c}% confidence).")
    elif t in ["descending_triangle"]:
        parts.append(f"Descending triangle with flat support ({c}% confidence).")
    elif "top" in t:
        parts.append(f"Potential top formation detected ({c}% confidence).")
    elif "bottom" in t:
        parts.append(f"Potential bottom formation detected ({c}% confidence).")
    elif "head_shoulders" in t:
        parts.append(f"Head & Shoulders structure visible ({c}% confidence).")
    elif "flag" in t or "pennant" in t:
        parts.append(f"Continuation pattern after impulse ({c}% confidence).")
    else:
        parts.append(f"Current structure: {t.replace('_', ' ')} ({c}% confidence).")
    
    # --- 4) ALTERNATIVES ---
    if alts:
        alt_names = [a.get("type", "").replace("_", " ") for a in alts[:2] if a.get("type")]
        if alt_names:
            parts.append(f"Alternative readings: {', '.join(alt_names)}.")
    
    # --- 5) EXPECTATION ---
    if state == "COMPRESSION":
        parts.append("Expect breakout to define next direction.")
    elif state == "CONFLICTED":
        parts.append("Wait for confirmation before taking positions.")
    elif "REVERSAL" in state:
        parts.append("Watch for pattern confirmation.")
    
    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════
# HELPER: Get market state from patterns
# ═══════════════════════════════════════════════════════════════

def get_market_state(dominant: Dict, alternatives: List[Dict] = None) -> str:
    """Determine market state from dominant pattern."""
    
    t = (dominant.get("type") or "").lower()
    
    # Compression patterns
    if t in ["rectangle", "range", "horizontal_channel", 
             "symmetrical_triangle", "ascending_triangle", "descending_triangle",
             "pennant"]:
        return "COMPRESSION"
    
    # Reversal patterns
    if t in ["double_top", "triple_top", "head_shoulders", "rising_wedge"]:
        return "REVERSAL ↓"
    
    if t in ["double_bottom", "triple_bottom", "inverse_head_shoulders", "falling_wedge"]:
        return "REVERSAL ↑"
    
    # Continuation
    if t in ["bull_flag", "bear_flag", "ascending_channel", "descending_channel"]:
        return "TREND"
    
    # Check for conflicts
    if alternatives and len(alternatives) >= 2:
        types = [a.get("type", "") for a in alternatives]
        has_reversal = any("top" in t or "bottom" in t or "head" in t for t in types)
        has_continuation = any("flag" in t or "channel" in t or "triangle" in t for t in types)
        
        if has_reversal and has_continuation:
            return "CONFLICTED"
    
    return "DEVELOPING"


__all__ = ["build_interpretation", "get_market_state"]
