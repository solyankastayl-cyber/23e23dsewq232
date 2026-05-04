"""
Strategy Profile Registry (STR1)
================================

Pre-defined trading profiles.

CONSERVATIVE: Low risk, spot only, long horizon
BALANCED: Medium risk, spot + futures, trend following
AGGRESSIVE: High risk, futures, short horizon
"""

from .profile_types import (
    StrategyProfile,
    ProfileMode,
    MarketMode,
    HoldingHorizon,
    RiskLevel
)


# ===========================================
# CONSERVATIVE Profile
# ===========================================

CONSERVATIVE_PROFILE = StrategyProfile(
    profile_id="profile_conservative",
    name="Conservative",
    mode=ProfileMode.CONSERVATIVE,
    description="Low risk trading mode. Spot only, high confidence entries, long holding periods.",
    
    # Market
    market_mode=MarketMode.SPOT_ONLY,
    allowed_symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
    
    # Leverage
    max_leverage=1.0,
    default_leverage=1.0,
    
    # Signals - High confidence required
    signal_threshold=0.80,
    exit_threshold=0.60,
    
    # Position Sizing - Small positions
    max_position_pct=0.05,           # 5% max per position
    max_portfolio_exposure_pct=0.20,  # 20% total exposure
    min_position_usd=100.0,
    max_position_usd=5000.0,
    
    # Risk - Low
    max_drawdown_pct=0.08,           # 8% max drawdown
    daily_loss_limit_pct=0.02,       # 2% daily limit
    risk_level=RiskLevel.LOW,
    
    # Holding - Long term
    holding_horizon=HoldingHorizon.POSITION,
    min_holding_bars=24,             # At least 24 bars
    max_holding_bars=200,            # Up to 200 bars
    
    # Frequency - Few trades
    max_trades_per_day=3,
    min_time_between_trades_minutes=120,
    
    # Stops - Tight
    default_stop_loss_pct=0.02,      # 2% stop
    default_take_profit_pct=0.06,    # 6% take profit (3:1 ratio)
    use_trailing_stop=True,
    trailing_stop_pct=0.015,
    
    is_enabled=True
)


# ===========================================
# BALANCED Profile
# ===========================================

BALANCED_PROFILE = StrategyProfile(
    profile_id="profile_balanced",
    name="Balanced",
    mode=ProfileMode.BALANCED,
    description="Medium risk trading mode. Spot + light futures, trend following, moderate frequency.",
    
    # Market
    market_mode=MarketMode.SPOT_FUTURES,
    allowed_symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"],
    
    # Leverage - Light
    max_leverage=3.0,
    default_leverage=2.0,
    
    # Signals - Moderate confidence
    signal_threshold=0.65,
    exit_threshold=0.50,
    
    # Position Sizing - Medium
    max_position_pct=0.10,           # 10% max per position
    max_portfolio_exposure_pct=0.40,  # 40% total exposure
    min_position_usd=100.0,
    max_position_usd=15000.0,
    
    # Risk - Medium
    max_drawdown_pct=0.15,           # 15% max drawdown
    daily_loss_limit_pct=0.04,       # 4% daily limit
    risk_level=RiskLevel.MEDIUM,
    
    # Holding - Swing
    holding_horizon=HoldingHorizon.SWING,
    min_holding_bars=6,              # At least 6 bars
    max_holding_bars=80,             # Up to 80 bars
    
    # Frequency - Moderate
    max_trades_per_day=8,
    min_time_between_trades_minutes=30,
    
    # Stops - Standard
    default_stop_loss_pct=0.025,     # 2.5% stop
    default_take_profit_pct=0.05,    # 5% take profit (2:1 ratio)
    use_trailing_stop=True,
    trailing_stop_pct=0.02,
    
    is_enabled=True
)


# ===========================================
# AGGRESSIVE Profile
# ===========================================

AGGRESSIVE_PROFILE = StrategyProfile(
    profile_id="profile_aggressive",
    name="Aggressive",
    mode=ProfileMode.AGGRESSIVE,
    description="High risk trading mode. Futures focused, short horizon, high frequency, leverage.",
    
    # Market
    market_mode=MarketMode.FUTURES_ONLY,
    allowed_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT"],
    
    # Leverage - High
    max_leverage=10.0,
    default_leverage=5.0,
    
    # Signals - Lower threshold
    signal_threshold=0.55,
    exit_threshold=0.45,
    
    # Position Sizing - Larger
    max_position_pct=0.15,           # 15% max per position
    max_portfolio_exposure_pct=0.60,  # 60% total exposure
    min_position_usd=500.0,
    max_position_usd=50000.0,
    
    # Risk - High
    max_drawdown_pct=0.25,           # 25% max drawdown
    daily_loss_limit_pct=0.08,       # 8% daily limit
    risk_level=RiskLevel.HIGH,
    
    # Holding - Short term
    holding_horizon=HoldingHorizon.INTRADAY,
    min_holding_bars=1,              # Can exit quickly
    max_holding_bars=24,             # Max 24 bars
    
    # Frequency - High
    max_trades_per_day=20,
    min_time_between_trades_minutes=5,
    
    # Stops - Wide
    default_stop_loss_pct=0.03,      # 3% stop
    default_take_profit_pct=0.045,   # 4.5% take profit (1.5:1 ratio)
    use_trailing_stop=False,         # Quick exits instead
    trailing_stop_pct=0.02,
    
    is_enabled=True
)


# ===========================================
# Profile Registry
# ===========================================

PROFILE_REGISTRY = {
    ProfileMode.CONSERVATIVE: CONSERVATIVE_PROFILE,
    ProfileMode.BALANCED: BALANCED_PROFILE,
    ProfileMode.AGGRESSIVE: AGGRESSIVE_PROFILE
}


def get_profile(mode: ProfileMode) -> StrategyProfile:
    """Get profile by mode"""
    return PROFILE_REGISTRY.get(mode, BALANCED_PROFILE)


def get_all_profiles() -> list:
    """Get all registered profiles"""
    return list(PROFILE_REGISTRY.values())


def get_profile_by_name(name: str) -> StrategyProfile:
    """Get profile by name (case insensitive)"""
    name_upper = name.upper()
    for mode, profile in PROFILE_REGISTRY.items():
        if mode.value == name_upper or profile.name.upper() == name_upper:
            return profile
    return BALANCED_PROFILE


# ===========================================
# Profile Comparison
# ===========================================

def compare_profiles() -> dict:
    """Compare all profiles side by side"""
    return {
        "profiles": {
            mode.value: {
                "market_mode": profile.market_mode.value,
                "max_leverage": profile.max_leverage,
                "signal_threshold": profile.signal_threshold,
                "max_position_pct": profile.max_position_pct,
                "max_exposure_pct": profile.max_portfolio_exposure_pct,
                "max_drawdown_pct": profile.max_drawdown_pct,
                "holding_horizon": profile.holding_horizon.value,
                "max_trades_per_day": profile.max_trades_per_day,
                "stop_loss_pct": profile.default_stop_loss_pct,
                "risk_level": profile.risk_level.value
            }
            for mode, profile in PROFILE_REGISTRY.items()
        },
        "risk_order": ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
    }
