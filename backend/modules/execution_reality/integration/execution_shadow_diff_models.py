"""
Execution Shadow Diff Models (P1.3.1D)
=======================================

Модели для сравнения queue vs legacy intents.

Diff Scope (расширенный, по указанию пользователя):
- symbol, side, quantity (normalized), price (normalized)
- orderType, reason, exchange, accountId
- (optional) clientOrderId

Severity Levels:
- CRITICAL: symbol/side mismatch
- HIGH: quantity mismatch
- MEDIUM: price mismatch
- LOW: reason mismatch
"""

from typing import Optional, Literal, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# Severity Level (строгий enum)
DiffSeverity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]


class ExecutionIntent(BaseModel):
    """
    Normalized execution intent для сравнения.
    
    Используется для сравнения queue intent vs legacy intent.
    """
    # Core fields
    symbol: str
    side: str  # BUY/SELL
    quantity: float  # Normalized (после округлений)
    price: Optional[float] = None  # Normalized (может быть None для MARKET)
    orderType: str  # MARKET/LIMIT
    reason: str  # Action или другой идентификатор
    
    # Extended fields (по требованию пользователя)
    exchange: str = "binance"
    accountId: str = "default"
    clientOrderId: Optional[str] = None
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionShadowDiff(BaseModel):
    """
    Execution Shadow Diff document (Mongo: execution_shadow_diff).
    
    Сохраняет результат сравнения queue_intent vs legacy_intent.
    """
    # Identity
    traceId: str
    jobId: Optional[str] = None  # Queue job ID (если был создан)
    
    # Intents (normalized)
    queueIntent: Optional[ExecutionIntent] = None
    legacyIntent: Optional[ExecutionIntent] = None
    
    # Diff results
    match: bool  # True если полное совпадение
    diff: Dict[str, Any]  # Детали различий
    severity: DiffSeverity  # Уровень критичности различий
    
    # Metadata
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True


def compare_intents(
    queue_intent: Optional[ExecutionIntent],
    legacy_intent: Optional[ExecutionIntent]
) -> tuple[bool, Dict[str, Any], DiffSeverity]:
    """
    Сравнить queue_intent vs legacy_intent и определить severity.
    
    Args:
        queue_intent: Normalized intent из queue dispatch
        legacy_intent: Normalized intent из legacy submit
    
    Returns:
        Tuple: (match: bool, diff: dict, severity: DiffSeverity)
    """
    # Edge case: оба None (нет данных для сравнения)
    if queue_intent is None and legacy_intent is None:
        return True, {}, "NONE"
    
    # Edge case: один из intents отсутствует
    if queue_intent is None:
        return False, {"error": "queue_intent_missing"}, "CRITICAL"
    
    if legacy_intent is None:
        return False, {"error": "legacy_intent_missing"}, "CRITICAL"
    
    # Построение diff
    diff = {}
    severity: DiffSeverity = "NONE"
    
    # 1. CRITICAL: symbol/side mismatch
    if queue_intent.symbol != legacy_intent.symbol:
        diff["symbol_match"] = False
        diff["symbol_queue"] = queue_intent.symbol
        diff["symbol_legacy"] = legacy_intent.symbol
        severity = "CRITICAL"
    else:
        diff["symbol_match"] = True
    
    if queue_intent.side != legacy_intent.side:
        diff["side_match"] = False
        diff["side_queue"] = queue_intent.side
        diff["side_legacy"] = legacy_intent.side
        severity = "CRITICAL"
    else:
        diff["side_match"] = True
    
    # 2. HIGH: quantity mismatch
    if abs(queue_intent.quantity - legacy_intent.quantity) > 0.0001:  # Float tolerance
        diff["quantity_match"] = False
        diff["quantity_queue"] = queue_intent.quantity
        diff["quantity_legacy"] = legacy_intent.quantity
        if severity != "CRITICAL":
            severity = "HIGH"
    else:
        diff["quantity_match"] = True
    
    # 3. MEDIUM: price mismatch
    # Учитываем, что price может быть None для MARKET orders
    if queue_intent.price is not None and legacy_intent.price is not None:
        if abs(queue_intent.price - legacy_intent.price) > 0.01:  # Price tolerance
            diff["price_match"] = False
            diff["price_queue"] = queue_intent.price
            diff["price_legacy"] = legacy_intent.price
            if severity not in ["CRITICAL", "HIGH"]:
                severity = "MEDIUM"
        else:
            diff["price_match"] = True
    elif queue_intent.price != legacy_intent.price:
        # Один None, другой не None
        diff["price_match"] = False
        diff["price_queue"] = queue_intent.price
        diff["price_legacy"] = legacy_intent.price
        if severity not in ["CRITICAL", "HIGH"]:
            severity = "MEDIUM"
    else:
        diff["price_match"] = True
    
    # 4. LOW: orderType/reason/exchange/accountId mismatch
    if queue_intent.orderType != legacy_intent.orderType:
        diff["orderType_match"] = False
        diff["orderType_queue"] = queue_intent.orderType
        diff["orderType_legacy"] = legacy_intent.orderType
        if severity == "NONE":
            severity = "LOW"
    else:
        diff["orderType_match"] = True
    
    if queue_intent.reason != legacy_intent.reason:
        diff["reason_match"] = False
        diff["reason_queue"] = queue_intent.reason
        diff["reason_legacy"] = legacy_intent.reason
        if severity == "NONE":
            severity = "LOW"
    else:
        diff["reason_match"] = True
    
    if queue_intent.exchange != legacy_intent.exchange:
        diff["exchange_match"] = False
        diff["exchange_queue"] = queue_intent.exchange
        diff["exchange_legacy"] = legacy_intent.exchange
        if severity == "NONE":
            severity = "LOW"
    else:
        diff["exchange_match"] = True
    
    if queue_intent.accountId != legacy_intent.accountId:
        diff["accountId_match"] = False
        diff["accountId_queue"] = queue_intent.accountId
        diff["accountId_legacy"] = legacy_intent.accountId
        if severity == "NONE":
            severity = "LOW"
    else:
        diff["accountId_match"] = True
    
    # 5. Optional: clientOrderId (не влияет на severity)
    if queue_intent.clientOrderId != legacy_intent.clientOrderId:
        diff["clientOrderId_match"] = False
        diff["clientOrderId_queue"] = queue_intent.clientOrderId
        diff["clientOrderId_legacy"] = legacy_intent.clientOrderId
    else:
        diff["clientOrderId_match"] = True
    
    # Финальное определение match
    match = (severity == "NONE")
    
    return match, diff, severity
