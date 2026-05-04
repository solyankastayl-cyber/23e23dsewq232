"""Close Service — PHASE 2: REAL PRICE INTEGRATION

Automatic position closing logic:
- Check TP/SL conditions using LIVE mark prices from PriceService
- Submit close orders to exchange
- Update portfolio

NO MOCKS: All prices from PriceService (single source of truth)
"""

import logging
from typing import List

from modules.trading_core.portfolio_service import get_portfolio_service
from modules.exchange.service import exchange_service
from modules.exchange.models import OrderRequest
from modules.trading_core.execution_events import get_events_service
from modules.market_data.price_service import get_price_service

logger = logging.getLogger(__name__)


async def check_and_close_positions() -> int:
    """Check all open positions for TP/SL and close if conditions met.
    
    Returns:
        Number of positions closed
    """
    portfolio_service = get_portfolio_service()
    portfolio = await portfolio_service.get_portfolio_state()
    
    positions = portfolio.get("positions", [])
    
    if not positions:
        return 0
    
    closed_count = 0
    
    for position in positions:
        # Check close conditions
        close_reason = await _check_close_condition(position)
        
        if close_reason:
            # Close position
            success = await _close_position(position, close_reason)
            
            if success:
                closed_count += 1
    
    return closed_count


async def _check_close_condition(position: dict) -> str:
    """Check if position should be closed.
    
    Uses LIVE mark price from PriceService for TP/SL checks.
    
    Args:
        position: Position dict
    
    Returns:
        Close reason ('TP', 'SL', None)
    """
    symbol = position["symbol"]
    side = position["side"]
    entry_price = position["entry_price"]
    tp = position.get("take_profit")
    sl = position.get("stop_loss")
    
    # Get current LIVE mark price from PriceService
    price_service = await get_price_service()
    
    try:
        mark_price = await price_service.get_mark_price(symbol)
    except Exception as e:
        logger.error(f"[CloseService] Failed to get mark price for {symbol}: {e}")
        return None
    
    logger.debug(
        f"[CloseService] {symbol} mark=${mark_price:.2f}, entry=${entry_price:.2f}, "
        f"TP={tp}, SL={sl}"
    )
    
    # Check TP/SL against LIVE mark price
    if side == "LONG":
        # LONG: TP when mark >= target, SL when mark <= stop
        if tp and mark_price >= tp:
            logger.info(f"[CloseService] LONG TP hit: {symbol} mark={mark_price:.2f} >= tp={tp:.2f}")
            return "TP"
        if sl and mark_price <= sl:
            logger.info(f"[CloseService] LONG SL hit: {symbol} mark={mark_price:.2f} <= sl={sl:.2f}")
            return "SL"
    
    elif side == "SHORT":
        # SHORT: TP when mark <= target, SL when mark >= stop
        if tp and mark_price <= tp:
            logger.info(f"[CloseService] SHORT TP hit: {symbol} mark={mark_price:.2f} <= tp={tp:.2f}")
            return "TP"
        if sl and mark_price >= sl:
            logger.info(f"[CloseService] SHORT SL hit: {symbol} mark={mark_price:.2f} >= sl={sl:.2f}")
            return "SL"
    
    return None


async def _close_position(position: dict, reason: str) -> bool:
    """Close position by submitting reverse order to exchange.
    
    Args:
        position: Position dict
        reason: Close reason ('TP', 'SL')
    
    Returns:
        True if closed successfully
    """
    logger.info(
        f"[CloseService] Closing position: {position['symbol']} {position['side']} "
        f"reason={reason}"
    )
    
    try:
        # Get exchange adapter
        if not exchange_service.is_connected():
            logger.error("[CloseService] Exchange not connected")
            return False
        
        adapter = exchange_service.get_adapter()
        events_service = get_events_service()
        
        # Create reverse order (close position)
        close_order = OrderRequest(
            symbol=position["symbol"],
            side="SELL" if position["side"] == "LONG" else "BUY",  # Reverse side
            order_type="MARKET",
            quantity=abs(position["size"]),
            client_order_id=f"close-{position.get('opened_at', '')}-{reason}",
        )
        
        # Submit order
        response = await adapter.place_order(close_order)
        
        if response.success and response.status == "FILLED":
            # Log event
            await events_service.log_event("POSITION_CLOSED", position["symbol"], {
                "reason": reason,
                "side": position["side"],
                "size": position["size"],
                "entry": position["entry_price"],
                "close_price": response.avg_fill_price,
            })
            
            # Apply fill to portfolio (this will update/close the position)
            portfolio_service = get_portfolio_service()
            await portfolio_service.apply_fill(response)
            
            logger.info(
                f"[CloseService] ✅ Position closed: {position['symbol']} "
                f"@ ${response.avg_fill_price:.2f} reason={reason}"
            )
            
            return True
        else:
            logger.error(
                f"[CloseService] Failed to close position: {position['symbol']} "
                f"status={response.status}"
            )
            return False
    
    except Exception as e:
        logger.error(f"[CloseService] Error closing position: {e}", exc_info=True)
        return False
