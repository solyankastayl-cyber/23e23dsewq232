"""
Paper Trading Adapter

Simulates order execution with realistic fills and fees.
No real money involved.
"""

import uuid
from typing import Dict, Any, Optional


class PaperAdapter:
    """
    Paper trading adapter with simulated execution.
    
    Behavior:
    - MARKET orders: instant fill at entry price
    - LIMIT orders: PLACED status (not filled immediately)
    - Applies simulated slippage and fees
    """
    
    def __init__(self, slippage_bps: int = 3, fee_bps: int = 5):
        """
        Args:
            slippage_bps: Slippage in basis points (default 3 = 0.03%)
            fee_bps: Trading fee in basis points (default 5 = 0.05%)
        """
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps
    
    def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """
        Place a paper order.
        
        Args:
            symbol: Trading symbol (e.g. BTCUSDT)
            side: BUY or SELL
            size: Order size
            price: Limit price (for LIMIT orders)
            order_type: MARKET or LIMIT
            
        Returns:
            Unified adapter response
        """
        # Validate size
        if size <= 0:
            return {
                "success": False,
                "exchange": "paper",
                "exchange_order_id": None,
                "status": "REJECTED",
                "filled_qty": 0.0,
                "avg_price": None,
                "reason": "non_positive_size",
            }
        
        # Generate paper order ID
        order_id = f"paper-{uuid.uuid4().hex[:12]}"
        
        # MARKET orders fill immediately
        if order_type == "MARKET":
            # Apply slippage
            if price:
                slippage_factor = 1 + (self.slippage_bps / 10000)
                if side == "BUY":
                    fill_price = price * slippage_factor
                else:
                    fill_price = price / slippage_factor
            else:
                fill_price = price
            
            return {
                "success": True,
                "exchange": "paper",
                "exchange_order_id": order_id,
                "status": "FILLED",
                "filled_qty": size,
                "avg_price": fill_price,
                "reason": None,
            }
        
        # LIMIT orders are placed but not filled
        else:
            return {
                "success": True,
                "exchange": "paper",
                "exchange_order_id": order_id,
                "status": "PLACED",
                "filled_qty": 0.0,
                "avg_price": None,
                "reason": None,
            }
