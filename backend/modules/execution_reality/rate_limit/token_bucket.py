"""
Token Bucket Rate Limiter (P1-B)
==================================

Production-grade rate limiting для Binance API.

Binance Limits (Spot):
- 1200 weight / minute (rolling window)
- Order endpoints: weight = 1-5
- Cancel endpoints: weight = 1

Usage:
    bucket = TokenBucket(capacity=1200, refill_rate=20)  # 1200/min = 20/sec
    
    if bucket.consume(weight=1):
        # proceed with API call
    else:
        # reject or throttle
"""

import time
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token Bucket rate limiter.
    
    Refills tokens at constant rate, allows bursts up to capacity.
    Thread-safe via lock-free atomic operations (single-threaded async context).
    
    Args:
        capacity: Maximum tokens (bucket size)
        refill_rate: Tokens added per second
        initial_tokens: Starting token count (default: capacity)
    """
    
    def __init__(
        self,
        capacity: float,
        refill_rate: float,
        initial_tokens: Optional[float] = None
    ):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("Refill rate must be positive")
        
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill = time.time()
        
        logger.info(
            f"✅ TokenBucket initialized: capacity={capacity}, "
            f"refill_rate={refill_rate}/sec ({refill_rate * 60}/min)"
        )
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate
        
        # Update tokens (cap at capacity)
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume (e.g., Binance API weight)
        
        Returns:
            True if tokens consumed successfully, False if insufficient tokens
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            logger.debug(
                f"✅ Consumed {tokens} tokens | "
                f"Remaining: {self.tokens:.2f}/{self.capacity}"
            )
            return True
        else:
            logger.warning(
                f"❌ Insufficient tokens: requested={tokens}, "
                f"available={self.tokens:.2f}/{self.capacity}"
            )
            return False
    
    def peek(self) -> float:
        """
        Check available tokens without consuming.
        
        Returns:
            Current token count (after refill)
        """
        self._refill()
        return self.tokens
    
    def get_metrics(self) -> dict:
        """
        Get rate limiter metrics.
        
        Returns:
            {
                "available_tokens": float,
                "capacity": float,
                "refill_rate": float,
                "utilization": float  # 0.0 - 1.0
            }
        """
        available = self.peek()
        utilization = 1.0 - (available / self.capacity)
        
        return {
            "available_tokens": round(available, 2),
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "utilization": round(utilization, 4)
        }
    
    def wait_time(self, tokens: float = 1.0) -> float:
        """
        Calculate wait time until tokens available.
        
        Args:
            tokens: Number of tokens needed
        
        Returns:
            Wait time in seconds (0 if tokens available now)
        """
        available = self.peek()
        
        if available >= tokens:
            return 0.0
        
        # Calculate time needed to refill deficit
        deficit = tokens - available
        wait_seconds = deficit / self.refill_rate
        
        return wait_seconds


class BinanceRateLimiter:
    """
    Binance-specific rate limiter.
    
    Implements Binance weight-based rate limiting:
    - Spot: 1200 weight/min
    - Futures: 2400 weight/min (optional, can add later)
    
    Endpoint weights:
    - POST /api/v3/order: weight = 1
    - DELETE /api/v3/order: weight = 1
    - GET /api/v3/openOrders: weight = 40
    """
    
    # Binance API weights per endpoint
    WEIGHTS = {
        "order_new": 1,
        "order_cancel": 1,
        "order_query": 2,
        "open_orders": 40,
        "account_info": 10
    }
    
    def __init__(self, market_type: str = "spot"):
        """
        Args:
            market_type: "spot" (1200/min) or "futures" (2400/min)
        """
        if market_type == "spot":
            capacity = 1200
        elif market_type == "futures":
            capacity = 2400
        else:
            raise ValueError(f"Unknown market_type: {market_type}")
        
        # Refill rate = capacity / 60 seconds
        refill_rate = capacity / 60.0
        
        self.bucket = TokenBucket(
            capacity=capacity,
            refill_rate=refill_rate
        )
        self.market_type = market_type
        
        logger.info(
            f"✅ BinanceRateLimiter initialized: {market_type} "
            f"({capacity} weight/min)"
        )
    
    def can_submit_order(self) -> bool:
        """Check if can submit new order (weight=1)."""
        return self.bucket.peek() >= self.WEIGHTS["order_new"]
    
    def consume_order_new(self) -> bool:
        """Consume tokens for new order submission."""
        return self.bucket.consume(self.WEIGHTS["order_new"])
    
    def consume_order_cancel(self) -> bool:
        """Consume tokens for order cancellation."""
        return self.bucket.consume(self.WEIGHTS["order_cancel"])
    
    def get_metrics(self) -> dict:
        """Get rate limiter metrics."""
        return self.bucket.get_metrics()
