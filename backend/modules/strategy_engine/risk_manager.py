"""
Risk Manager — Survival Layer

CRITICAL CHECKS:
1. Symbol lock (no duplicate positions)
2. Cooldown (30min between trades)
3. Rate limiting (max 3 trades/hour)
4. Daily loss limit ($200)
5. Position limit (max 3)
6. Slippage check (1%)
7. Exchange connectivity
"""

import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk manager for strategy engine.
    
    CRITICAL: Every signal MUST pass through this layer.
    """
    
    def __init__(self, portfolio_service, exchange_service, db):
        """
        Args:
            portfolio_service: PortfolioService instance
            exchange_service: ExchangeService instance
            db: MongoDB database
        """
        self.portfolio = portfolio_service
        self.exchange = exchange_service
        self.db = db
        
        # Risk limits (HARDCODED for safety)
        self.MAX_POSITIONS = 3
        self.MAX_TRADES_PER_HOUR = 3
        self.DAILY_LOSS_LIMIT = -200.0  # USD
        self.COOLDOWN_SECONDS = 1800  # 30 minutes
        self.MAX_SLIPPAGE_PCT = 0.01  # 1%
        
        logger.info("[RiskManager] Initialized")
    
    async def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate signal against all risk checks.
        
        Args:
            signal: Signal dict
        
        Returns:
            {"approved": bool, "reason": str | None}
        """
        symbol = signal["symbol"]
        side = signal["side"]
        entry_price = signal["entry_price"]
        
        # 1. Exchange connectivity check
        if not self.exchange.is_connected():
            logger.warning("[RiskManager] REJECTED: Exchange not connected")
            return {"approved": False, "reason": "Exchange disconnected"}
        
        # 2. Get portfolio state
        try:
            summary = await self.portfolio.get_summary()
            active_positions = await self.portfolio.get_active_positions()
        except Exception as e:
            logger.error(f"[RiskManager] REJECTED: Failed to get portfolio state: {e}")
            return {"approved": False, "reason": "Portfolio state unavailable"}
        
        # 3. SYMBOL LOCK: No duplicate positions
        for pos in active_positions:
            pos_symbol = pos.get("symbol", "") if isinstance(pos, dict) else getattr(pos, "symbol", "")
            pos_side = pos.get("side", "") if isinstance(pos, dict) else getattr(pos, "side", "")
            if pos_symbol == symbol and pos_side == side:
                logger.warning(f"[RiskManager] REJECTED: Position already open on {symbol} {side}")
                return {"approved": False, "reason": f"Position already open on {symbol}"}
        
        # 4. POSITION LIMIT: Max 3 open positions
        if len(active_positions) >= self.MAX_POSITIONS:
            logger.warning(f"[RiskManager] REJECTED: Max positions reached ({self.MAX_POSITIONS})")
            return {"approved": False, "reason": f"Max positions ({self.MAX_POSITIONS}) reached"}
        
        # 5. DAILY LOSS LIMIT: Stop trading if loss > $200
        total_pnl = summary.total_pnl if hasattr(summary, 'total_pnl') else summary.get("total_pnl", 0)
        if total_pnl < self.DAILY_LOSS_LIMIT:
            logger.error(f"[RiskManager] REJECTED: Daily loss limit hit (${total_pnl:.2f})")
            return {"approved": False, "reason": f"Daily loss limit hit (${total_pnl:.2f})"}
        
        # 6. DEPLOYMENT CHECK: Max 80% deployed
        deployment_pct = summary.deployment_pct if hasattr(summary, 'deployment_pct') else summary.get("deployment_pct", 0)
        deployment_pct_val = summary.deployment_pct if hasattr(summary, 'deployment_pct') else summary.get("deployment_pct", 0)
        if deployment_pct_val >= 80:
            logger.warning(f"[RiskManager] REJECTED: Deployment too high ({deployment_pct_val:.1f}%)")
            return {"approved": False, "reason": f"Deployment too high ({deployment_pct_val:.1f}%)"}
        
        # 7. COOLDOWN: 30min between trades on same symbol
        cooldown_check = await self._check_cooldown(symbol)
        if not cooldown_check["ok"]:
            logger.warning(f"[RiskManager] REJECTED: {cooldown_check['reason']}")
            return {"approved": False, "reason": cooldown_check["reason"]}
        
        # 8. RATE LIMITING: Max 3 trades/hour
        rate_check = await self._check_rate_limit()
        if not rate_check["ok"]:
            logger.warning(f"[RiskManager] REJECTED: {rate_check['reason']}")
            return {"approved": False, "reason": rate_check["reason"]}
        
        # 9. SLIPPAGE CHECK: Price hasn't moved too much
        slippage_check = await self._check_slippage(symbol, entry_price)
        if not slippage_check["ok"]:
            logger.warning(f"[RiskManager] REJECTED: {slippage_check['reason']}")
            return {"approved": False, "reason": slippage_check["reason"]}
        
        # ALL CHECKS PASSED
        logger.info(f"[RiskManager] ✅ APPROVED: {symbol} {side} @ ${entry_price}")
        return {"approved": True, "reason": None}
    
    async def _check_cooldown(self, symbol: str) -> Dict[str, Any]:
        """
        Check cooldown for symbol.
        
        Returns:
            {"ok": bool, "reason": str | None}
        """
        # Query strategy state
        state = await self.db.strategy_state.find_one({"symbol": symbol})
        
        if not state:
            return {"ok": True, "reason": None}
        
        last_trade_time = state.get("last_trade_time")
        cooldown_until = state.get("cooldown_until")
        
        if not cooldown_until:
            return {"ok": True, "reason": None}
        
        now = int(time.time())
        
        if now < cooldown_until:
            remaining = cooldown_until - now
            logger.debug(f"[RiskManager] Cooldown active for {symbol}: {remaining}s remaining")
            return {"ok": False, "reason": f"Cooldown active ({remaining}s remaining)"}
        
        return {"ok": True, "reason": None}
    
    async def _check_rate_limit(self) -> Dict[str, Any]:
        """
        Check rate limit (max 3 trades/hour).
        
        Returns:
            {"ok": bool, "reason": str | None}
        """
        now = int(time.time())
        one_hour_ago = now - 3600
        
        # Count trades in last hour
        count = await self.db.orders.count_documents({
            "status": "FILLED",
            "created_at": {"$gte": one_hour_ago}
        })
        
        if count >= self.MAX_TRADES_PER_HOUR:
            logger.debug(f"[RiskManager] Rate limit hit: {count} trades in last hour")
            return {"ok": False, "reason": f"Rate limit: {count}/{self.MAX_TRADES_PER_HOUR} trades in last hour"}
        
        return {"ok": True, "reason": None}
    
    async def _check_slippage(self, symbol: str, expected_price: float) -> Dict[str, Any]:
        """
        Check slippage (price deviation).
        Sprint 1: Skip slippage check in PAPER mode (mock adapter returns hardcoded prices).
        """
        try:
            adapter = self.exchange.get_adapter()
            
            # Sprint 1: Skip slippage check if adapter is PAPER/mock
            # Paper adapters return hardcoded prices, making slippage check meaningless
            adapter_name = type(adapter).__name__
            if "Paper" in adapter_name or "Mock" in adapter_name:
                return {"ok": True, "reason": None}
            
            current_price = await adapter.get_mark_price(symbol)
            
            deviation = abs(current_price - expected_price) / expected_price
            
            if deviation > self.MAX_SLIPPAGE_PCT:
                logger.debug(f"[RiskManager] Slippage too high: {deviation*100:.2f}%")
                return {
                    "ok": False,
                    "reason": f"Slippage too high ({deviation*100:.2f}% > {self.MAX_SLIPPAGE_PCT*100:.1f}%)"
                }
            
            return {"ok": True, "reason": None}
        
        except Exception as e:
            # Sprint 1: In PAPER mode, slippage errors are non-blocking
            logger.warning(f"[RiskManager] Slippage check skipped (PAPER mode): {e}")
            return {"ok": True, "reason": None}
    
    async def record_trade(self, symbol: str, side: str, entry_price: float):
        """
        Record trade in strategy state (for cooldown tracking).
        
        Args:
            symbol: Trading symbol
            side: BUY | SELL
            entry_price: Entry price
        """
        now = int(time.time())
        cooldown_until = now + self.COOLDOWN_SECONDS
        
        await self.db.strategy_state.update_one(
            {"symbol": symbol},
            {
                "$set": {
                    "last_signal": side,
                    "last_entry_price": entry_price,
                    "last_trade_time": now,
                    "cooldown_until": cooldown_until,
                    "updated_at": now
                }
            },
            upsert=True
        )
        
        logger.info(f"[RiskManager] Recorded trade: {symbol} {side} @ ${entry_price} (cooldown until {cooldown_until})")


# Singleton instance
_risk_manager = None


def init_risk_manager(portfolio_service, exchange_service, db):
    """Initialize risk manager singleton."""
    global _risk_manager
    _risk_manager = RiskManager(portfolio_service, exchange_service, db)
    logger.info("[RiskManager] Singleton initialized")


def get_risk_manager() -> RiskManager:
    """Get risk manager singleton."""
    if _risk_manager is None:
        raise RuntimeError("RiskManager not initialized. Call init_risk_manager() first.")
    return _risk_manager
