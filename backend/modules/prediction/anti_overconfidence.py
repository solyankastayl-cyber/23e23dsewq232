"""
Anti-Overconfidence

Prevents confidence inflation in weak setups.
"""


def apply_anti_overconfidence(
    confidence: float,
    stability: float,
    regime: str
) -> float:
    """
    Apply anti-overconfidence adjustments.
    
    Rules:
    1. Low stability → reduce confidence
    2. Range regime → always less certain
    3. Cap at 90% max
    
    Args:
        confidence: Current confidence value
        stability: Stability score (0-1)
        regime: Detected regime
    
    Returns:
        Adjusted confidence
    """
    # Weak structure → cut confidence
    if stability < 0.6:
        confidence *= 0.85
    
    # Range is inherently less predictable
    if regime == "range":
        confidence *= 0.9
    
    # High volatility extra penalty
    if regime == "high_volatility" and stability < 0.5:
        confidence *= 0.85
    
    # Always cap at 90%
    return max(0.0, min(confidence, 0.90))
