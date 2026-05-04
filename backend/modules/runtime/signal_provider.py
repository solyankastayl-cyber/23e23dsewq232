"""
Signal Provider Adapter — Abstraction over signal engine
"""

import time
import logging
from typing import Any, Dict, List
from uuid import uuid4

logger = logging.getLogger(__name__)


class SignalProvider:
    """Adapter for signal engine."""
    
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        logger.info(f"[SignalProvider] Initialized (mock={use_mock})")
    
    async def get_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get signals for a symbol.
        
        Returns list of signal dicts.
        """
        if self.use_mock:
            # Mock signal for testing
            return [
                {
                    "signal_id": f"sig_{uuid4().hex[:10]}",
                    "symbol": symbol,
                    "side": "BUY",
                    "strategy": "momentum",
                    "confidence": 0.74,
                    "entry_price": 70000 if symbol == "BTCUSDT" else 3500,
                    "stop_price": 68900 if symbol == "BTCUSDT" else 3420,
                    "target_price": 72100 if symbol == "BTCUSDT" else 3620,
                    "thesis": f"{symbol} momentum continuation",
                    "timeframe": "1H",
                    "created_at": int(time.time())
                }
            ]
        
        # TODO: Hook real signal engine here
        raise NotImplementedError("Real signal engine not implemented")
