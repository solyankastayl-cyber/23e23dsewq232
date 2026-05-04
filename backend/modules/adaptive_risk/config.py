"""
Adaptive Risk Configuration
Phase 5: R2 Adaptive Risk v1

Defines deterministic mapping rules for context-aware sizing adjustments.

R2 v1 Scope:
- Drawdown-aware sizing
- Loss-streak dampening

R2 = multiplicative layer AFTER R1
"""

# R2 v1: Drawdown-Aware Sizing
# Maps portfolio drawdown to risk reduction multiplier
DRAWDOWN_MAPPING = [
    {"max_drawdown_pct": 5.0, "multiplier": 1.0},    # No drawdown → no reduction
    {"max_drawdown_pct": 10.0, "multiplier": 0.8},   # Small drawdown → 20% reduction
    {"max_drawdown_pct": 20.0, "multiplier": 0.6},   # Medium drawdown → 40% reduction
    {"max_drawdown_pct": float('inf'), "multiplier": 0.4}  # Large drawdown → 60% reduction
]

# R2 v1: Loss-Streak Dampening
# Maps consecutive losses to risk reduction multiplier
LOSS_STREAK_MAPPING = [
    {"max_streak": 0, "multiplier": 1.0},    # No losses → no reduction
    {"max_streak": 1, "multiplier": 0.9},    # 1 loss → 10% reduction
    {"max_streak": 2, "multiplier": 0.75},   # 2 losses → 25% reduction
    {"max_streak": float('inf'), "multiplier": 0.5}  # 3+ losses → 50% reduction
]

# R2 Clamp Limits
# R2 v1 only reduces risk (multiplier ≤ 1.0)
# Minimum multiplier prevents complete risk shutdown
R2_MIN_MULTIPLIER = 0.3  # Never reduce below 30% of R1 size
R2_MAX_MULTIPLIER = 1.0  # Never increase beyond R1 size (v1 constraint)

# Loss Streak Lookback
# Number of recent trades to check for streak calculation
LOSS_STREAK_LOOKBACK = 10  # Check last 10 trades

# Default Config
ADAPTIVE_RISK_DEFAULTS = {
    "drawdown_mapping": DRAWDOWN_MAPPING,
    "loss_streak_mapping": LOSS_STREAK_MAPPING,
    "min_multiplier": R2_MIN_MULTIPLIER,
    "max_multiplier": R2_MAX_MULTIPLIER,
    "loss_streak_lookback": LOSS_STREAK_LOOKBACK
}
