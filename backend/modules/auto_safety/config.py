"""
Auto Safety Config
==================
Sprint A4: Hard limits to prevent system self-destruction in AUTO mode
"""

AUTO_SAFETY_DEFAULTS = {
    "enabled": False,  # ⚠️ TEMPORARILY DISABLED FOR QTY MATCH TEST

    # Trade frequency
    "max_trades_per_hour": 100,
    "max_concurrent_positions": 10,

    # Capital/risk
    "max_capital_deployed_pct": 1.0,   # 100%
    "max_single_trade_notional_pct": 1.0,  # 100%

    # Kill conditions
    "daily_loss_limit_usd": -999999.0,
    "max_consecutive_losses": 999,

    # Rollout
    "allowed_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "auto_mode_enabled": True,
}
