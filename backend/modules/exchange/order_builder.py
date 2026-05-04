"""
Order Request Builder — P0.2 Single Source of Truth

CRITICAL: Only way to create OrderRequest payloads.
Prevents "type field missing" errors.
"""

from typing import Optional


def build_order_request(
    symbol: str,
    side: str,
    qty: float,
    order_type: str = "MARKET",
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "GTC",
    client_order_id: Optional[str] = None
) -> dict:
    """
    Build validated OrderRequest.
    
    Args:
        symbol: Trading pair (e.g., "BTCUSDT")
        side: "BUY" or "SELL"
        qty: Quantity to trade
        order_type: "MARKET" or "LIMIT"
        price: Limit price (required for LIMIT orders)
        stop_price: Stop price (for STOP_LOSS orders)
        time_in_force: "GTC", "IOC", "FOK"
        client_order_id: Optional client order ID
    
    Returns:
        OrderRequest dict with all required fields
    
    Raises:
        ValueError: If validation fails
    """
    # Validate required fields
    if not symbol:
        raise ValueError("symbol is required")
    
    if side not in ["BUY", "SELL"]:
        raise ValueError(f"Invalid side: {side}. Must be BUY or SELL")
    
    if qty <= 0:
        raise ValueError(f"Invalid qty: {qty}. Must be > 0")
    
    if order_type not in ["MARKET", "LIMIT", "STOP_LOSS", "STOP_LOSS_LIMIT"]:
        raise ValueError(f"Invalid order_type: {order_type}")
    
    # LIMIT orders require price
    if order_type in ["LIMIT", "STOP_LOSS_LIMIT"] and price is None:
        raise ValueError(f"{order_type} order requires price")
    
    # Build request
    request = {
        "symbol": symbol,
        "side": side,
        "type": order_type,  # CRITICAL: Always present
        "quantity": qty,
        "time_in_force": time_in_force,
    }
    
    # Optional fields
    if price is not None:
        request["price"] = price
    
    if stop_price is not None:
        request["stop_price"] = stop_price
    
    if client_order_id:
        request["client_order_id"] = client_order_id
    
    return request


def validate_order_request(request: dict) -> bool:
    """
    Validate OrderRequest has all required fields.
    
    Raises:
        ValueError: If validation fails
    
    Returns:
        True if valid
    """
    required = ["symbol", "side", "type", "quantity"]
    
    for field in required:
        if field not in request:
            raise ValueError(f"OrderRequest missing required field: {field}")
    
    if request["type"] in ["LIMIT", "STOP_LOSS_LIMIT"] and "price" not in request:
        raise ValueError(f"{request['type']} order requires 'price' field")
    
    return True
