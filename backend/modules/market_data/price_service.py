"""Price Service — PHASE 1: SINGLE SOURCE OF TRUTH

⚠️  ВАЖНО: GEO-БЛОКИРОВКА BINANCE
    Emergent платформа хостится в регионе, заблокированном Binance (HTTP 451).
    Для MVP используем REALISTIC MOCK PRICES с волатильностью.
    
    Для production:
    - Развернуть систему на сервере вне блока (EU/Asia)
    - Использовать прокси/VPN
    - Или переключить на Binance.US / другую биржу
    
    После этого достаточно заменить _fetch_rest_price() на реальный API.

Единый источник цен для всей системы:
- Primary: Simulated prices (realistic с волатильностью ±0.5% каждые 2с)
- Fallback: Binance REST (когда geo-блок снят)

Usage:
    from modules.market_data.price_service import get_price_service
    
    service = await get_price_service()
    price = await service.get_mark_price("BTCUSDT")
"""

import logging
import time
import random
from typing import Optional, Dict
import asyncio

import aiohttp

logger = logging.getLogger(__name__)


class PriceService:
    """Price service with realistic mock prices (geo-block workaround)."""
    
    _instance: Optional['PriceService'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self.binance_rest_url = "https://api.binance.com/api/v3/ticker/price"
        self.cache_ttl = 2.0  # Цена валидна 2 секунды
        self.session: Optional[aiohttp.ClientSession] = None
        
        # In-memory cache: {symbol: {price: float, timestamp: float}}
        self.cache: Dict[str, dict] = {}
        self.cache_lock = asyncio.Lock()
        
        # Base prices (realistic current market levels, updated Apr 2026)
        self.base_prices = {
            "BTCUSDT": 74000.0,
            "ETHUSDT": 2325.0,
            "SOLUSDT": 83.60,
            "BNBUSDT": 612.34,
            "XRPUSDT": 2.34,
            "ADAUSDT": 0.98,
            "AVAXUSDT": 38.45,
            "LINKUSDT": 21.67,
            "DOGEUSDT": 0.32,
        }
        
        # Volatility
        self.volatility = 0.005  # ±0.5%
    
    @classmethod
    async def get_instance(cls) -> 'PriceService':
        """Get singleton instance."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    await instance.init()
                    cls._instance = instance
        return cls._instance
    
    async def init(self):
        """Initialize price service."""
        # Create HTTP session (для будущего Binance API)
        self.session = aiohttp.ClientSession()
        logger.info("[PriceService] Initialized (MOCK MODE due to Binance geo-block)")
        logger.warning("[PriceService] ⚠️  Using simulated prices. Deploy outside geo-block for real data.")
    
    async def close(self):
        """Close service."""
        if self.session:
            await self.session.close()
    
    async def get_mark_price(self, symbol: str) -> float:
        """Get mark price for symbol.
        
        Flow:
        1. Check memory cache
        2. If miss/stale → generate new simulated price
        
        Args:
            symbol: Trading symbol (e.g. "BTCUSDT")
        
        Returns:
            Current mark price
        
        Raises:
            ValueError: If symbol not supported
        """
        # Try cache first
        async with self.cache_lock:
            cached = self.cache.get(symbol)
        
        if cached:
            age = time.time() - cached["timestamp"]
            
            if age < self.cache_ttl:
                logger.debug(f"[PriceService] {symbol} = ${cached['price']:.2f} (cache, age={age:.1f}s)")
                return cached["price"]
        
        # Generate new simulated price
        price = await self._generate_simulated_price(symbol)
        
        # Update cache
        async with self.cache_lock:
            self.cache[symbol] = {
                "price": price,
                "timestamp": time.time(),
            }
        
        return price
    
    async def _generate_simulated_price(self, symbol: str) -> float:
        """Generate realistic simulated price with volatility.
        
        Симуляция:
        - Базовая цена из base_prices
        - Каждый запрос: ±0.5% случайное движение
        - Это создаёт realistic ценовое движение для тестирования TP/SL logic
        """
        if symbol not in self.base_prices:
            raise ValueError(f"Symbol {symbol} not supported in mock mode")
        
        base = self.base_prices[symbol]
        
        # Random walk: ±0.5%
        movement = random.uniform(-self.volatility, self.volatility)
        simulated_price = base * (1 + movement)
        
        # Update base для накопительного эффекта
        self.base_prices[symbol] = simulated_price
        
        logger.debug(f"[PriceService] {symbol} = ${simulated_price:.2f} (SIMULATED, movement={movement*100:.2f}%)")
        return simulated_price
    
    async def _fetch_rest_price(self, symbol: str) -> float:
        """Fetch price from Binance REST API.
        
        NOTE: CURRENTLY BLOCKED by geo-restriction (HTTP 451).
        
        When deploying outside restricted region:
        1. Remove simulated price logic
        2. Enable this method as primary
        3. Update init() log message
        
        Endpoint: GET /api/v3/ticker/price?symbol=BTCUSDT
        Response: {"symbol":"BTCUSDT","price":"67123.45"}
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            params = {"symbol": symbol}
            
            async with self.session.get(
                self.binance_rest_url, 
                params=params, 
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ValueError(f"Binance API error: {resp.status} {text}")
                
                data = await resp.json()
                price = float(data["price"])
                
                logger.debug(f"[PriceService] {symbol} = ${price:.2f} (REST)")
                return price
        
        except asyncio.TimeoutError:
            raise ValueError(f"Timeout fetching price for {symbol}")
        
        except Exception as e:
            logger.error(f"[PriceService] REST error for {symbol}: {e}")
            raise ValueError(f"Failed to fetch price for {symbol}: {e}")
    
    async def get_multiple_prices(self, symbols: list[str]) -> dict[str, float]:
        """Get prices for multiple symbols.
        
        Returns:
            {symbol: price}
        """
        result = {}
        
        for symbol in symbols:
            try:
                result[symbol] = await self.get_mark_price(symbol)
            except Exception as e:
                logger.warning(f"[PriceService] Failed to get price for {symbol}: {e}")
        
        return result
    
    def get_status(self) -> dict:
        """Get service status."""
        return {
            "mode": "SIMULATED (Binance geo-blocked)",
            "rest_url": self.binance_rest_url,
            "cache_ttl": self.cache_ttl,
            "cached_symbols": len(self.cache),
            "supported_symbols": list(self.base_prices.keys()),
        }


# Singleton accessor
async def get_price_service() -> PriceService:
    """Get global price service instance."""
    return await PriceService.get_instance()
