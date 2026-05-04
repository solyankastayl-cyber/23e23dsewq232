"""Execution Quality Configuration

Настройки для реалистичной симуляции качества исполнения:
- Slippage по символам (зависит от ликвидности)
- Depth factor (влияние размера ордера)
- Partial fill thresholds
- Fee structure
- Rejection limits
"""

# Slippage configuration по символам
# base_bps: базовое проскальзывание в basis points (1 bps = 0.01%)
# depth_factor: множитель для учёта глубины рынка (выше = хуже ликвидность)
SLIPPAGE_CONFIG = {
    "BTCUSDT": {"base_bps": 2, "depth_factor": 1.0},   # Лучшая ликвидность
    "ETHUSDT": {"base_bps": 3, "depth_factor": 1.1},
    "BNBUSDT": {"base_bps": 4, "depth_factor": 1.2},
    "SOLUSDT": {"base_bps": 6, "depth_factor": 1.4},
    "XRPUSDT": {"base_bps": 8, "depth_factor": 1.5},
    "ADAUSDT": {"base_bps": 10, "depth_factor": 1.6},
    "AVAXUSDT": {"base_bps": 12, "depth_factor": 1.7},
    "LINKUSDT": {"base_bps": 10, "depth_factor": 1.6},
    "DOGEUSDT": {"base_bps": 15, "depth_factor": 1.8}, # Худшая ликвидность
}

# Default для неизвестных символов
DEFAULT_SLIPPAGE = {"base_bps": 20, "depth_factor": 2.0}

# Fee structure (Binance-like)
FEE_CONFIG = {
    "taker_fee_rate": 0.001,  # 0.1% (10 bps)
    "maker_fee_rate": 0.0005, # 0.05% (5 bps) — для будущего LIMIT support
}

# Partial fill thresholds
PARTIAL_FILL_CONFIG = {
    "min_notional_for_partial": 5000,  # USD notional выше которого возможен partial fill
    "partial_probability": 0.3,        # 30% вероятность partial fill для крупных ордеров
    "min_fill_ratio": 0.4,             # Минимум 40% исполняется сразу
    "max_fill_ratio": 0.9,             # Максимум 90% исполняется сразу (остаток — второй fill)
    "second_fill_delay_min": 0.2,      # Минимальная задержка второго fill (секунды)
    "second_fill_delay_max": 1.0,      # Максимальная задержка второго fill (секунды)
}

# Order rejection limits
REJECTION_CONFIG = {
    "min_notional_usdt": 10.0,         # Минимальный размер ордера в USDT
    "max_positions": 20,               # Максимум открытых позиций
    "min_lot_size": 0.00001,           # Минимальный lot size (символьный, упрощённо)
}


def get_slippage_config(symbol: str) -> dict:
    """Get slippage config for symbol."""
    return SLIPPAGE_CONFIG.get(symbol, DEFAULT_SLIPPAGE)


def calculate_slippage(symbol: str, notional: float, base_price: float) -> float:
    """Calculate realistic slippage for order.
    
    Formula:
    - base_bps from config
    - size_factor = 1 + (notional / 5000), capped at 3x
    - slippage_pct = random(±base) * size_factor * depth_factor
    
    Args:
        symbol: Trading symbol
        notional: Order notional value in USDT
        base_price: Mark price before slippage
    
    Returns:
        Slippage-adjusted price
    """
    import random
    
    config = get_slippage_config(symbol)
    
    # Base slippage in percentage
    base_pct = config["base_bps"] / 10000
    
    # Size impact: larger orders get worse fills
    size_factor = min(3.0, 1.0 + (notional / 5000.0))
    
    # Combined slippage
    slippage_pct = random.uniform(-base_pct, base_pct) * size_factor * config["depth_factor"]
    
    return base_price * (1 + slippage_pct)


def calculate_fee(notional: float, liquidity_type: str = "TAKER") -> float:
    """Calculate trading fee.
    
    Args:
        notional: Fill notional value in USDT
        liquidity_type: "TAKER" or "MAKER"
    
    Returns:
        Fee amount in USDT
    """
    if liquidity_type == "MAKER":
        return notional * FEE_CONFIG["maker_fee_rate"]
    else:  # TAKER (default for MARKET orders)
        return notional * FEE_CONFIG["taker_fee_rate"]


def should_partial_fill(notional: float) -> tuple[bool, float]:
    """Determine if order should be partially filled.
    
    Args:
        notional: Order notional value in USDT
    
    Returns:
        (should_partial, fill_ratio) where fill_ratio is for first fill
    """
    import random
    
    if notional < PARTIAL_FILL_CONFIG["min_notional_for_partial"]:
        return False, 1.0
    
    # Random chance for partial fill
    if random.random() > PARTIAL_FILL_CONFIG["partial_probability"]:
        return False, 1.0
    
    # Partial fill: first fill gets partial ratio
    fill_ratio = random.uniform(
        PARTIAL_FILL_CONFIG["min_fill_ratio"],
        PARTIAL_FILL_CONFIG["max_fill_ratio"]
    )
    
    return True, fill_ratio
