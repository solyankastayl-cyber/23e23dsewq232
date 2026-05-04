"""Decision Engine — PHASE 2: REAL RISK SIZING

Конвертирует signals → trading decisions (BUY/SELL/WAIT).

CRITICAL RULES:
1. Confidence >= 0.65 (minimum threshold)
2. Risk heat < 0.7 (portfolio safety)
3. Position size = risk / stop_distance (NOT fixed %)
4. stop_distance MUST be > minimum threshold
5. Validate signal quality (entry/stop/target present)
6. Use LIVE mark price from PriceService for entry
"""

from typing import Dict, Any, Optional
import logging

from modules.market_data.price_service import get_price_service

logger = logging.getLogger(__name__)

# Risk settings
MIN_CONFIDENCE = 0.65
MAX_RISK_HEAT = 0.7
RISK_PER_TRADE_PCT = 0.01  # 1% of account per trade
MAX_POSITION_SIZE_PCT = 0.15  # Max 15% of account per position
MIN_STOP_DISTANCE_PCT = 0.005  # Min 0.5% stop distance (защита от слишком близких стопов)


def calculate_position_size(
    portfolio: Dict[str, Any],
    signal: Dict[str, Any],
    mark_price: float
) -> float:
    """Calculate position size based on risk and stop distance.
    
    CRITICAL FORMULA:
    risk_amount = balance * RISK_PER_TRADE_PCT
    stop_distance = abs(entry - stop)
    position_size = risk_amount / stop_distance
    
    GUARDS:
    - stop_distance must be > MIN_STOP_DISTANCE_PCT * entry
    - position notional must be <= MAX_POSITION_SIZE_PCT * balance
    - reject if stop too close (prevents over-leveraged trades)
    
    Args:
        portfolio: Portfolio state {balance, equity, ...}
        signal: Signal with {entry, stop, target}
        mark_price: Current LIVE mark price from PriceService
    
    Returns:
        Position size in base currency (e.g., BTC quantity for BTCUSDT)
    """
    balance = portfolio.get("balance", 10000)
    entry = mark_price  # Use LIVE price as entry
    stop = signal.get("stop", 0)
    
    if entry == 0 or stop == 0:
        logger.warning("[DecisionEngine] entry or stop is zero, rejecting")
        return 0.0
    
    # Stop distance
    stop_distance = abs(entry - stop)
    
    # Validate minimum stop distance (защита от слишком близких стопов)
    min_stop_distance = entry * MIN_STOP_DISTANCE_PCT
    
    if stop_distance < min_stop_distance:
        logger.warning(
            f"[DecisionEngine] Stop too close: {stop_distance:.2f} < {min_stop_distance:.2f} "
            f"({MIN_STOP_DISTANCE_PCT*100}% of entry), rejecting"
        )
        return 0.0
    
    # Risk amount in USD
    risk_amount = balance * RISK_PER_TRADE_PCT
    
    # Position size = risk / stop_distance
    position_size = risk_amount / stop_distance
    
    logger.info(
        f"[DecisionEngine] Sizing: risk=${risk_amount:.2f}, stop_dist=${stop_distance:.2f}, "
        f"size={position_size:.4f}"
    )
    
    # Max position size check (notional value limit)
    max_position_value = balance * MAX_POSITION_SIZE_PCT
    position_value = position_size * entry
    
    if position_value > max_position_value:
        position_size = max_position_value / entry
        logger.info(
            f"[DecisionEngine] Capped position: notional=${position_value:.2f} > "
            f"max=${max_position_value:.2f}, new size={position_size:.4f}"
        )
    
    return round(position_size, 8)


async def make_decision(
    signal: Optional[Dict[str, Any]],
    portfolio: Dict[str, Any]
) -> Dict[str, Any]:
    """Make trading decision from signal.
    
    Uses LIVE mark price from PriceService for entry price.
    
    Args:
        signal: Market signal from Signal Engine
        portfolio: Current portfolio state
    
    Returns:
        Decision dict:
        {
            "action": "WAIT" | "OPEN" | "CLOSE",
            "symbol": str,
            "side": "LONG" | "SHORT",
            "size": float,
            "entry": float,
            "stop": float,
            "target": float,
            "confidence": float,
            "mark_price_at_decision": float,
            "reason": str (if WAIT)
        }
    """
    # No signal
    if not signal:
        return {
            "action": "WAIT",
            "reason": "no_signal"
        }
    
    # Extract signal data
    confidence = signal.get("confidence", 0)
    direction = signal.get("direction", "")
    symbol = signal.get("symbol", "")
    
    # Confidence check
    if confidence < MIN_CONFIDENCE:
        return {
            "action": "WAIT",
            "symbol": symbol,
            "reason": f"confidence_low_{confidence}"
        }
    
    # Risk check
    risk_heat = portfolio.get("risk", {}).get("heat", 0)
    if risk_heat > MAX_RISK_HEAT:
        return {
            "action": "WAIT",
            "symbol": symbol,
            "reason": f"risk_limit_heat_{risk_heat:.2f}"
        }
    
    # Validate signal has all required fields
    required_fields = ["stop", "target"]
    if not all(field in signal for field in required_fields):
        return {
            "action": "WAIT",
            "symbol": symbol,
            "reason": "incomplete_signal"
        }
    
    # Get LIVE mark price from PriceService
    price_service = await get_price_service()
    
    try:
        mark_price = await price_service.get_mark_price(symbol)
    except Exception as e:
        logger.error(f"[DecisionEngine] Failed to get mark price for {symbol}: {e}")
        return {
            "action": "WAIT",
            "symbol": symbol,
            "reason": f"price_unavailable_{str(e)}"
        }
    
    # Calculate position size using LIVE mark price
    size = calculate_position_size(portfolio, signal, mark_price)
    
    if size == 0:
        return {
            "action": "WAIT",
            "symbol": symbol,
            "reason": "zero_size_or_stop_too_close"
        }
    
    # EXECUTION QUALITY FILTER (CRITICAL)
    notional = size * mark_price
    
    # Estimate expected slippage
    slippage_config = get_slippage_config(symbol)
    expected_slippage_bps = slippage_config["base_bps"] * slippage_config["depth_factor"]
    
    # Adjust for size (larger orders = worse slippage)
    if notional > 5000:
        size_factor = min(3.0, 1.0 + (notional / 5000.0))
        expected_slippage_bps *= size_factor
    
    if expected_slippage_bps > MAX_EXPECTED_SLIPPAGE_BPS:
        logger.warning(
            f"[DecisionEngine] SKIP: {symbol} expected slippage {expected_slippage_bps:.1f}bps "
            f"> max {MAX_EXPECTED_SLIPPAGE_BPS}bps (notional=${notional:.0f})"
        )
        return {
            "action": "WAIT",
            "symbol": symbol,
            "reason": f"expected_slippage_too_high_{expected_slippage_bps:.1f}bps"
        }
    
    # Generate OPEN decision
    decision = {
        "action": "OPEN",
        "symbol": symbol,
        "side": direction,  # LONG or SHORT
        "size": size,
        "entry": mark_price,  # Use LIVE mark price as entry
        "stop": signal["stop"],
        "target": signal["target"],
        "confidence": confidence,
        "strategy": signal.get("strategy", "UNKNOWN"),
        "timeframe": signal.get("timeframe", "UNKNOWN"),
        "reasoning": signal.get("reasoning", ""),
        "mark_price_at_decision": mark_price,  # Log mark price at decision time
    }
    
    logger.info(
        f"[DecisionEngine] OPEN {symbol} {direction} size={size:.4f} "
        f"entry=${mark_price:.2f} stop=${decision['stop']:.2f} target=${decision['target']:.2f} "
        f"conf={confidence:.2f}"
    )
    
    return decision
