"""
Coinbase Provider Auto-Init
============================

Auto-initializes Coinbase provider at startup for live market data.
No API keys required - uses public Coinbase Exchange API.

Providers: Coinbase (Active), Binance (Inactive), Bybit (Inactive), Hyperliquid (Inactive)
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from modules.data.coinbase_provider import CoinbaseProvider, coinbase_provider
from modules.validation.coinbase_provider import CoinbaseDataProvider, coinbase_provider as validation_provider


class CoinbaseAutoInit:
    """
    Auto-initializes and manages Coinbase provider connection.
    Runs health checks and maintains live data feed.
    """
    
    _instance: Optional['CoinbaseAutoInit'] = None
    
    def __init__(self):
        self.data_provider = coinbase_provider
        self.validation_provider = validation_provider
        self.is_initialized = False
        self.last_health_check: Optional[datetime] = None
        self.status = "disconnected"
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_ticker": None,
        }
    
    @classmethod
    def get_instance(cls) -> 'CoinbaseAutoInit':
        if cls._instance is None:
            cls._instance = CoinbaseAutoInit()
        return cls._instance
    
    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize Coinbase provider and verify connection.
        Called automatically at server startup.
        """
        print("[CoinbaseAutoInit] Initializing Coinbase provider...")
        
        try:
            # Test connection with ticker request
            ticker = await self.data_provider.get_ticker("BTC-USD")
            
            if ticker and ticker.get("price", 0) > 0:
                self.is_initialized = True
                self.status = "connected"
                self.last_health_check = datetime.now(timezone.utc)
                self.stats["last_ticker"] = ticker
                self.stats["successful_requests"] += 1
                
                print(f"[CoinbaseAutoInit] Connected! BTC: ${ticker['price']:,.2f}")
                
                return {
                    "ok": True,
                    "status": "connected",
                    "provider": "coinbase",
                    "btc_price": ticker["price"],
                    "timestamp": self.last_health_check.isoformat()
                }
            else:
                raise Exception("Invalid ticker response")
                
        except Exception as e:
            self.status = "error"
            self.stats["failed_requests"] += 1
            print(f"[CoinbaseAutoInit] Connection failed: {e}")
            
            return {
                "ok": False,
                "status": "error",
                "provider": "coinbase",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Run health check on Coinbase provider."""
        self.stats["total_requests"] += 1
        
        try:
            # Use validation provider health check
            health = await self.validation_provider.health_check()
            
            if health.get("ok"):
                self.status = "connected"
                self.last_health_check = datetime.now(timezone.utc)
                self.stats["successful_requests"] += 1
            else:
                self.status = "degraded"
                self.stats["failed_requests"] += 1
            
            return {
                "provider": "coinbase",
                "status": self.status,
                "latency_ms": health.get("latencyMs", -1),
                "last_check": self.last_health_check.isoformat() if self.last_health_check else None,
                "stats": self.stats
            }
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            return {
                "provider": "coinbase",
                "status": "error",
                "error": str(e),
                "stats": self.stats
            }
    
    async def get_live_candles(
        self,
        symbol: str = "BTC",
        timeframe: str = "1h",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Fetch live candles from Coinbase.
        Converts symbol format: BTC -> BTC-USD
        """
        self.stats["total_requests"] += 1
        
        try:
            # Normalize symbol
            product_id = f"{symbol.upper()}-USD" if "-" not in symbol else symbol
            
            candles = await self.data_provider.get_candles(
                product_id=product_id,
                timeframe=timeframe,
                limit=limit
            )
            
            self.stats["successful_requests"] += 1
            
            return {
                "ok": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": candles,
                "count": len(candles),
                "source": "coinbase_live"
            }
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            return {
                "ok": False,
                "error": str(e),
                "symbol": symbol,
                "candles": [],
                "source": "coinbase_live"
            }
    
    async def get_live_ticker(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get live ticker from Coinbase."""
        self.stats["total_requests"] += 1
        
        try:
            product_id = f"{symbol.upper()}-USD" if "-" not in symbol else symbol
            ticker = await self.data_provider.get_ticker(product_id)
            
            self.stats["successful_requests"] += 1
            self.stats["last_ticker"] = ticker
            
            return {
                "ok": True,
                "symbol": symbol,
                "ticker": ticker,
                "source": "coinbase_live"
            }
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            return {
                "ok": False,
                "error": str(e),
                "symbol": symbol,
                "source": "coinbase_live"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current provider status."""
        return {
            "provider": "coinbase",
            "status": self.status,
            "is_initialized": self.is_initialized,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "stats": self.stats,
            "supported_pairs": ["BTC-USD", "ETH-USD", "SOL-USD"],
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
        }


# Singleton instance
coinbase_auto_init = CoinbaseAutoInit.get_instance()


async def init_coinbase_provider() -> Dict[str, Any]:
    """
    Initialize Coinbase provider. Called at server startup.
    """
    return await coinbase_auto_init.initialize()


async def get_coinbase_status() -> Dict[str, Any]:
    """Get Coinbase provider status."""
    return coinbase_auto_init.get_status()


async def coinbase_health_check() -> Dict[str, Any]:
    """Run Coinbase health check."""
    return await coinbase_auto_init.health_check()
