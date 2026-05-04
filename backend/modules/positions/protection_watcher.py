"""
Protection Watcher
Sprint A7: Background task that monitors positions and triggers TP/SL
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class ProtectionWatcher:
    """
    Watches positions and triggers TP/SL when mark price crosses thresholds.
    
    Architecture:
    - Runs every 2 seconds
    - Checks all active protection rules
    - Compares mark_price vs tp_price/sl_price
    - Sends MARKET reduceOnly when triggered
    """
    
    def __init__(self, exchange_adapter, repo):
        self.exchange = exchange_adapter
        self.repo = repo
        self._running = False
    
    async def start(self):
        """
        Start watcher loop.
        """
        self._running = True
        logger.info("[A7] ProtectionWatcher started (2s interval)")
        
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"[A7] Watcher error: {e}")
            
            await asyncio.sleep(2)  # 2 seconds
    
    async def stop(self):
        """
        Stop watcher loop.
        """
        self._running = False
        logger.info("[A7] ProtectionWatcher stopped")
    
    async def _tick(self):
        """
        Single watcher iteration.
        """
        protections = await self.repo.get_all_active()
        
        if protections:
            logger.info(f"[A7] 🔍 Monitoring {len(protections)} active protections")
        
        for p in protections:
            symbol = p["symbol"]
            
            # Get current position
            position = self.exchange.get_position(symbol)
            if not position:
                # Position doesn't exist anymore — disable protection
                await self.repo.disable(symbol)
                continue
            
            # Get mark price
            try:
                mark_price = await self.exchange.get_mark_price(symbol)
            except Exception as e:
                logger.error(f"[A7] Failed to get mark price for {symbol}: {e}")
                continue
            
            # Check TP
            await self._check_tp(symbol, position, mark_price, p)
            
            # Check SL
            await self._check_sl(symbol, position, mark_price, p)
    
    async def _check_tp(self, symbol, pos, mark, p):
        """
        Check if TP should trigger.
        """
        if not p.get("tp_enabled"):
            return
        
        tp_price = p.get("tp_price")
        if not tp_price:
            return
        
        side = pos["side"]
        
        # LONG: TP triggers when mark >= tp_price
        if side == "LONG" and mark >= tp_price:
            logger.info(f"[A7] 🎯 TP HIT: {symbol} LONG @ {mark} (tp={tp_price})")
            await self._close_position(symbol, pos, "TP")
            await self.repo.disable(symbol)
        
        # SHORT: TP triggers when mark <= tp_price
        elif side == "SHORT" and mark <= tp_price:
            logger.info(f"[A7] 🎯 TP HIT: {symbol} SHORT @ {mark} (tp={tp_price})")
            await self._close_position(symbol, pos, "TP")
            await self.repo.disable(symbol)
    
    async def _check_sl(self, symbol, pos, mark, p):
        """
        Check if SL should trigger.
        """
        if not p.get("sl_enabled"):
            return
        
        sl_price = p.get("sl_price")
        if not sl_price:
            return
        
        side = pos["side"]
        
        # LONG: SL triggers when mark <= sl_price
        if side == "LONG" and mark <= sl_price:
            logger.warning(f"[A7] 🛑 SL HIT: {symbol} LONG @ {mark} (sl={sl_price})")
            await self._close_position(symbol, pos, "SL")
            await self.repo.disable(symbol)
        
        # SHORT: SL triggers when mark >= sl_price
        elif side == "SHORT" and mark >= sl_price:
            logger.warning(f"[A7] 🛑 SL HIT: {symbol} SHORT @ {mark} (sl={sl_price})")
            await self._close_position(symbol, pos, "SL")
            await self.repo.disable(symbol)
    
    async def _close_position(self, symbol, pos, reason):
        """
        Close position via MARKET reduceOnly.
        """
        try:
            result = self.exchange.close_position(symbol)
            
            if result.get("ok"):
                logger.info(f"[A7] Position closed: {symbol} (reason={reason}) → {result.get('exchange_order_id')}")
            else:
                logger.error(f"[A7] Position close failed: {symbol} → {result.get('error')}")
        
        except Exception as e:
            logger.error(f"[A7] Position close exception: {symbol} → {e}")
