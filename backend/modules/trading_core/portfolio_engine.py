"""Portfolio Engine — Week 2

Управление портфелем:
- Balance tracking
- Position management
- PnL calculation
- Risk metrics (heat)
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Global portfolio state (in-memory для Week 2)
# Week 3: migrate to MongoDB
_portfolio_state = {
    "balance": 10000.0,  # Starting balance (USDT)
    "equity": 10000.0,   # Balance + unrealized PnL
    "positions": [],     # Open positions
    "closed_positions": [],  # Closed positions (for history)
    "realized_pnl": 0.0,  # Total realized PnL
    "unrealized_pnl": 0.0,  # Total unrealized PnL
    "total_pnl": 0.0,    # Realized + Unrealized
    "risk": {
        "heat": 0.0,      # Current risk exposure (0.0-1.0)
        "max_positions": 5,  # Max concurrent positions
        "open_positions_count": 0,
    },
    "last_updated": datetime.now(timezone.utc).isoformat(),
}


def get_portfolio() -> Dict[str, Any]:
    """Get current portfolio state."""
    return _portfolio_state.copy()


def open_position(decision: Dict[str, Any]) -> Dict[str, Any]:
    """Open new position from decision.
    
    Args:
        decision: Decision dict from Decision Engine
    
    Returns:
        Position dict
    """
    position_id = str(uuid.uuid4())
    
    position = {
        "position_id": position_id,
        "symbol": decision["symbol"],
        "side": decision["side"],
        "entry_price": decision["entry"],
        "current_price": decision["entry"],  # Initially same as entry
        "size": decision["size"],
        "stop_loss": decision["stop"],
        "take_profit": decision["target"],
        "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0,
        "status": "OPEN",
        "strategy": decision.get("strategy", "UNKNOWN"),
        "timeframe": decision.get("timeframe", "UNKNOWN"),
        "confidence": decision.get("confidence", 0),
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "closed_at": None,
    }
    
    _portfolio_state["positions"].append(position)
    _portfolio_state["risk"]["open_positions_count"] = len(_portfolio_state["positions"])
    _portfolio_state["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    logger.info(
        f"[Portfolio] Position opened: {position_id} {decision['symbol']} "
        f"{decision['side']} size={decision['size']:.4f} entry={decision['entry']}"
    )
    
    return position


def close_position(
    position_id: str,
    close_price: float,
    reason: str = "manual"
) -> Optional[Dict[str, Any]]:
    """Close position and realize PnL.
    
    Args:
        position_id: Position ID to close
        close_price: Exit price
        reason: Close reason (manual, stop_loss, take_profit)
    
    Returns:
        Closed position dict or None if not found
    """
    position = None
    for i, pos in enumerate(_portfolio_state["positions"]):
        if pos["position_id"] == position_id:
            position = _portfolio_state["positions"].pop(i)
            break
    
    if not position:
        logger.warning(f"[Portfolio] Position {position_id} not found")
        return None
    
    # Calculate realized PnL
    entry = position["entry_price"]
    size = position["size"]
    side = position["side"]
    
    if side == "LONG":
        pnl = (close_price - entry) * size
    else:  # SHORT
        pnl = (entry - close_price) * size
    
    pnl_pct = (pnl / (entry * size)) * 100 if entry > 0 else 0
    
    # Update position
    position["status"] = "CLOSED"
    position["close_price"] = close_price
    position["close_reason"] = reason
    position["realized_pnl"] = pnl
    position["realized_pnl_pct"] = pnl_pct
    position["closed_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update portfolio
    _portfolio_state["realized_pnl"] += pnl
    _portfolio_state["balance"] += pnl
    _portfolio_state["closed_positions"].append(position)
    _portfolio_state["risk"]["open_positions_count"] = len(_portfolio_state["positions"])
    _portfolio_state["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    logger.info(
        f"[Portfolio] Position closed: {position_id} {position['symbol']} "
        f"PnL={pnl:.2f} ({pnl_pct:+.2f}%) reason={reason}"
    )
    
    return position


def update_position_pnl(position_id: str, current_price: float) -> Optional[Dict[str, Any]]:
    """Update position's unrealized PnL with current price.
    
    Args:
        position_id: Position ID
        current_price: Current market price
    
    Returns:
        Updated position or None
    """
    for position in _portfolio_state["positions"]:
        if position["position_id"] == position_id:
            entry = position["entry_price"]
            size = position["size"]
            side = position["side"]
            
            if side == "LONG":
                pnl = (current_price - entry) * size
            else:  # SHORT
                pnl = (entry - current_price) * size
            
            pnl_pct = (pnl / (entry * size)) * 100 if entry > 0 else 0
            
            position["current_price"] = current_price
            position["unrealized_pnl"] = pnl
            position["unrealized_pnl_pct"] = pnl_pct
            
            return position
    
    return None


def calculate_portfolio_metrics() -> None:
    """Recalculate portfolio-level metrics.
    
    Updates:
    - unrealized_pnl (sum of all open positions)
    - total_pnl (realized + unrealized)
    - equity (balance + unrealized)
    - risk.heat (exposure / balance)
    """
    # Calculate unrealized PnL
    unrealized = sum(pos["unrealized_pnl"] for pos in _portfolio_state["positions"])
    
    # Update portfolio
    _portfolio_state["unrealized_pnl"] = unrealized
    _portfolio_state["total_pnl"] = _portfolio_state["realized_pnl"] + unrealized
    _portfolio_state["equity"] = _portfolio_state["balance"] + unrealized
    
    # Calculate risk heat (total exposure / balance)
    total_exposure = sum(
        pos["entry_price"] * pos["size"]
        for pos in _portfolio_state["positions"]
    )
    
    balance = _portfolio_state["balance"]
    heat = total_exposure / balance if balance > 0 else 0
    _portfolio_state["risk"]["heat"] = min(heat, 1.0)
    
    _portfolio_state["last_updated"] = datetime.now(timezone.utc).isoformat()


def reset_portfolio(initial_balance: float = 10000.0) -> None:
    """Reset portfolio to initial state (for testing/demo)."""
    global _portfolio_state
    _portfolio_state = {
        "balance": initial_balance,
        "equity": initial_balance,
        "positions": [],
        "closed_positions": [],
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "total_pnl": 0.0,
        "risk": {
            "heat": 0.0,
            "max_positions": 5,
            "open_positions_count": 0,
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"[Portfolio] Reset to ${initial_balance}")
