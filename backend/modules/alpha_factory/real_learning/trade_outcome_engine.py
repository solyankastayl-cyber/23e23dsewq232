"""
Trade Outcome Engine - AF6

Builds outcome objects from closed trades.
Calculates PnL, R:R, MAE, MFE and other trade metrics.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class TradeOutcomeEngine:
    """
    Trade outcome builder.
    
    Converts closed trade into structured outcome for learning.
    """
    
    def build(
        self,
        trade_id: str,
        symbol: str,
        timeframe: str,
        entry_mode: str,
        regime: str,
        side: str,
        entry_price: float,
        exit_price: float,
        size: float,
        mae: float = 0.0,
        mfe: float = 0.0,
        duration_sec: int = 0,
        exit_reason: str = "MANUAL",
        wrong_early: bool = False,
        strategy_id: str = "default",  # NEW: ORCH-7
    ) -> Dict[str, Any]:
        """
        Build trade outcome from closed trade.
        
        Args:
            trade_id: Unique trade identifier
            symbol: Trading symbol
            timeframe: Timeframe
            entry_mode: Entry mode used (GO_FULL, SNIPE, etc)
            regime: Market regime (TRENDING, RANGING, etc)
            side: LONG or SHORT
            entry_price: Entry price
            exit_price: Exit price
            size: Position size
            mae: Maximum adverse excursion (%)
            mfe: Maximum favorable excursion (%)
            duration_sec: Time in trade (seconds)
            exit_reason: Why trade was closed
            wrong_early: Was this a wrong_early entry
            
        Returns:
            Outcome dict with PnL, R:R, classification
        """
        # Calculate PnL
        if side == "LONG":
            pnl = (exit_price - entry_price) * size
            pnl_pct = ((exit_price - entry_price) / entry_price) if entry_price else 0.0
        else:
            pnl = (entry_price - exit_price) * size
            pnl_pct = ((entry_price - exit_price) / entry_price) if entry_price else 0.0
        
        # Calculate realized R:R
        rr_realized = None
        if mae and abs(mae) > 0:
            rr_realized = abs(mfe / mae) if mfe is not None else None
        
        # Classify outcome
        if pnl > 0:
            outcome = "WIN"
        elif pnl < 0:
            outcome = "LOSS"
        else:
            outcome = "BE"
        
        result = {
            "trade_id": trade_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "entry_mode": entry_mode,
            "regime": regime,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "size": size,
            "pnl": round(pnl, 8),
            "pnl_pct": round(pnl_pct, 6),
            "rr_realized": round(rr_realized, 4) if rr_realized is not None else None,
            "mae": mae,
            "mfe": mfe,
            "duration_sec": duration_sec,
            "outcome": outcome,
            "exit_reason": exit_reason,
            "wrong_early": wrong_early,
            "strategy_id": strategy_id,  # NEW: ORCH-7
        }
        
        logger.info(
            f"[TradeOutcomeEngine] Built outcome: {trade_id} | {symbol} | "
            f"{entry_mode} | {strategy_id} | {outcome} | pnl={pnl:.2f} ({pnl_pct*100:.2f}%)"
        )
        
        return result
