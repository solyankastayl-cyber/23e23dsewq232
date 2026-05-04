"""Binance WebSocket Feed for Live Kline Updates"""

import asyncio
import json
import logging
import websockets

logger = logging.getLogger(__name__)


class BinanceWSFeed:
    """Binance WebSocket feed for live kline updates."""
    
    def __init__(self, on_kline, testnet: bool = False):
        """
        Args:
            on_kline: Async callback for kline updates
            testnet: Use testnet endpoint
        """
        self.on_kline = on_kline
        self.testnet = testnet
        self._running = False
        self._task = None
    
    def _build_url(self, symbols: list[str], interval: str):
        """Build WebSocket URL for combined streams."""
        streams = "/".join(
            f"{s.lower()}@kline_{interval}" for s in symbols
        )
        
        if self.testnet:
            return f"wss://stream.testnet.binance.vision/stream?streams={streams}"
        
        return f"wss://data-stream.binance.vision/stream?streams={streams}"
    
    async def _run(self, symbols: list[str], interval: str):
        """Main WebSocket loop with reconnection."""
        url = self._build_url(symbols, interval)
        logger.info(f"[BinanceWS] Starting stream for {symbols} {interval}")
        
        while self._running:
            try:
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=60
                ) as ws:
                    logger.info(f"[BinanceWS] Connected")
                    
                    while self._running:
                        raw = await ws.recv()
                        payload = json.loads(raw)
                        
                        data = payload.get("data", {})
                        k = data.get("k")
                        if not k:
                            continue
                        
                        candle = {
                            "symbol": k["s"],
                            "interval": k["i"],
                            "open_time": k["t"],
                            "open": float(k["o"]),
                            "high": float(k["h"]),
                            "low": float(k["l"]),
                            "close": float(k["c"]),
                            "volume": float(k["v"]),
                            "close_time": k["T"],
                            "is_closed": bool(k["x"]),
                        }
                        
                        await self.on_kline(candle)
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("[BinanceWS] Connection closed, reconnecting in 3s...")
                await asyncio.sleep(3)
            
            except Exception as e:
                logger.error(f"[BinanceWS] Error: {e}", exc_info=True)
                await asyncio.sleep(3)
    
    async def start(self, symbols: list[str], interval: str = "4h"):
        """Start WebSocket feed."""
        if self._running:
            logger.warning("[BinanceWS] Already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run(symbols, interval))
    
    async def stop(self):
        """Stop WebSocket feed."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[BinanceWS] Stopped")
