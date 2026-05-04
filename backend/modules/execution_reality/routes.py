"""Execution Reality Routes

API эндпоинты для Milestone A.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .execution_reality_controller import ExecutionRealityController
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/execution-reality", tags=["execution_reality"])

# Глобальный экземпляр controller (в production — dependency injection)
controller = ExecutionRealityController()

# Флаг инициализации
_initialized = False


async def ensure_initialized():
    """Гарантировать, что controller инициализирован (boot restore выполнен)"""
    global _initialized
    if not _initialized:
        await controller.initialize()
        _initialized = True
        logger.info("🚀 Execution Reality controller initialized (boot restore complete)")


class SubmitLimitRequest(BaseModel):
    symbol: str
    side: str  # BUY | SELL
    qty: float
    price: float
    trace_id: Optional[str] = None  # P0.7.1: Audit trace ID
    intent_type: str = "ENTRY"  # P1.5: Intent type (STOP_LOSS, CLOSE, REDUCE, TAKE_PROFIT, ENTRY)


class ManualFillRequest(BaseModel):
    client_order_id: str
    fill_qty: float
    fill_price: float


@router.post("/test-submit")
async def test_submit_limit(req: SubmitLimitRequest):
    """
    Test submit LIMIT order (Milestone A use-case).
    
    DEPRECATED: Use /submit-async for P1.1 async queue.
    
    Пример:
    POST /api/execution-reality/test-submit
    {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "qty": 0.001,
        "price": 50000.0
    }
    """
    await ensure_initialized()  # Boot restore
    try:
        result = await controller.test_submit_limit(
            symbol=req.symbol,
            side=req.side,
            qty=req.qty,
            price=req.price,
            trace_id=req.trace_id  # P0.7.1
        )
        return result
    except Exception as e:
        logger.error(f"Error in test_submit_limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-async")
async def submit_limit_async(req: SubmitLimitRequest):
    """
    P1.1B: Async submit LIMIT order via persistent queue.
    
    NEW SEMANTICS:
    - Returns "accepted_for_processing" (NOT exchange-accepted)
    - Order is enqueued in Mongo persistent queue
    - Workers emit execution events asynchronously
    - Queue survives restart (durable)
    
    Example:
    POST /api/execution-reality/submit-async
    {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "qty": 0.001,
        "price": 50000.0,
        "trace_id": "uuid-from-terminal-decision"
    }
    
    Response:
    {
        "accepted": true,
        "task_id": "uuid",
        "client_order_id": "uuid",
        "trace_id": "uuid",
        "status": "accepted_for_processing"
    }
    """
    await ensure_initialized()
    try:
        result = await controller.submit_limit_async(
            symbol=req.symbol,
            side=req.side,
            qty=req.qty,
            price=req.price,
            trace_id=req.trace_id,
            intent_type=req.intent_type  # P1.5: Pass intent type
        )
        return result
    except Exception as e:
        logger.error(f"Error in submit_limit_async: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual-fill")
async def manual_fill(req: ManualFillRequest):
    """
    Вручную записать ORDER_FILL_RECORDED событие (для DoD Test 3).
    
    Пример:
    POST /api/execution-reality/manual-fill
    {
        "client_order_id": "abc-123",
        "fill_qty": 0.001,
        "fill_price": 50000.0
    }
    """
    try:
        result = await controller.manual_record_fill(
            client_order_id=req.client_order_id,
            fill_qty=req.fill_qty,
            fill_price=req.fill_price
        )
        return result
    except Exception as e:
        logger.error(f"Error in manual_fill: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/retry-budget")
async def get_retry_budget_stats():
    """
    P1.1+ Retry Budget Stats
    
    Returns current retry budget utilization.
    Used for monitoring and alerting on self-DDoS risk.
    """
    try:
        from modules.execution_reality.reliability import get_retry_budget
        
        budget = get_retry_budget()
        stats = budget.get_stats()
        
        return {
            "ok": True,
            **stats
        }
    except Exception as e:
        logger.exception("Failed to get retry budget stats")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_events(limit: int = 5, symbol: Optional[str] = None, client_order_id: Optional[str] = None):
    """
    Получить последние execution events.
    
    Пример:
    GET /api/execution-reality/events?limit=10
    GET /api/execution-reality/events?client_order_id=abc-123
    """
    await ensure_initialized()  # Boot restore
    try:
        events = await controller.event_store.list_last(
            limit=limit,
            symbol=symbol,
            client_order_id=client_order_id
        )
        return {"events": [event.dict() for event in events]}
    except Exception as e:
        logger.error(f"Error in get_events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{client_order_id}")
async def get_order(client_order_id: str):
    """
    Получить ордер по client_order_id (из projection).
    
    Пример:
    GET /api/execution-reality/orders/abc-123
    """
    await ensure_initialized()  # Boot restore
    order = controller.order_projection.get_order(client_order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order": order.dict()}


@router.get("/orders")
async def list_orders(limit: int = 20):
    """
    Список всех ордеров (из projection).
    
    Пример:
    GET /api/execution-reality/orders?limit=10
    """
    await ensure_initialized()  # Boot restore
    orders = controller.order_projection.list_orders(limit=limit)
    return {"orders": [order.dict() for order in orders]}


@router.get("/positions/{symbol}")
async def get_position(symbol: str):
    """
    Получить позицию по symbol (из projection).
    
    Пример:
    GET /api/execution-reality/positions/BTCUSDT
    """
    position = controller.position_projection.get_position(symbol)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"position": position.dict()}


@router.get("/positions")
async def list_positions():
    """
    Список всех позиций (из projection).
    
    Пример:
    GET /api/execution-reality/positions
    """
    positions = controller.position_projection.list_positions()
    return {"positions": [pos.dict() for pos in positions]}


@router.post("/test/simulate-execution-report")
async def simulate_execution_report(data: dict):
    """
    Симулировать execution report от Binance (для DoD Test 1).
    
    Пример:
    POST /api/execution-reality/test/simulate-execution-report
    {
      "e": "executionReport",
      "x": "TRADE",
      "X": "PARTIALLY_FILLED",
      "s": "BTCUSDT",
      "c": "test-client-order-123",
      "i": 12345,
      "S": "BUY",
      "l": "0.001",
      "L": "50000.0",
      "z": "0.001",
      "t": 999,
      "n": "0.05",
      "N": "USDT"
    }
    """
    await ensure_initialized()
    try:
        # Импортируем mapper
        from .adapters.binance_mapper_v2 import BinanceMapperV2
        mapper = BinanceMapperV2()
        
        # Маппим execution report
        event = mapper.map_execution_report(data)
        
        if event:
            # Записываем в event store
            await controller.event_store.append(event)
            # Публикуем в event bus
            await controller.event_bus.publish(event)
            
            return {
                "success": True,
                "event": event.dict(),
                "message": f"ExecutionReport → {event.event_type}"
            }
        else:
            return {"success": False, "message": "No event generated (possibly skipped exec_type)"}
    except Exception as e:
        logger.error(f"Error in simulate_execution_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/simulate-reconciliation")
async def simulate_reconciliation():
    """
    Симулировать reconciliation (для DoD Test 2).
    Создаёт искусственный mismatch между local и exchange позицией.
    """
    await ensure_initialized()
    try:
        from .reconciliation.reconciliation_engine import ReconciliationEngine
        from .reconciliation.mismatch_emitter import emit_mismatch
        
        recon_engine = ReconciliationEngine()
        
        # Симулируем mismatch: локальная позиция 0.005 BTC, exchange 0.0 BTC
        local_positions = [
            {"symbol": "BTCUSDT", "qty": 0.005}
        ]
        exchange_positions = [
            {"symbol": "BTCUSDT", "positionAmt": "0.0"}
        ]
        
        mismatches = recon_engine.reconcile_positions(local_positions, exchange_positions, qty_tolerance=1e-8)
        
        # Генерируем RECONCILIATION_MISMATCH events
        for mismatch in mismatches:
            await emit_mismatch(controller.event_store, controller.event_bus, mismatch)
        
        return {
            "success": True,
            "mismatches_found": len(mismatches),
            "mismatches": mismatches
        }
    except Exception as e:
        logger.error(f"Error in simulate_reconciliation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/pnl-scenario")
async def test_pnl_scenario(scenario: dict):
    """
    Тестовый endpoint для симуляции PnL сценариев (P0.5 Tests).
    
    Пример Basic PnL Test:
    POST /api/execution-reality/test/pnl-scenario
    {
      "scenario": "basic_pnl",
      "symbol": "BTCUSDT",
      "trades": [
        {"side": "BUY", "qty": 0.001, "price": 50000.0, "fee": 0.05, "fee_asset": "USDT"},
        {"side": "SELL", "qty": 0.001, "price": 51000.0, "fee": 0.051, "fee_asset": "USDT"}
      ]
    }
    """
    await ensure_initialized()
    try:
        from .adapters.binance_mapper_v2 import BinanceMapperV2
        mapper = BinanceMapperV2()
        
        symbol = scenario.get("symbol", "BTCUSDT")
        trades = scenario.get("trades", [])
        client_order_id_base = scenario.get("client_order_id", "test-pnl")
        
        # Создаём execution reports для каждой сделки
        for idx, trade in enumerate(trades):
            # Генерируем уникальные ID
            client_order_id = f"{client_order_id_base}-{idx}"
            exchange_order_id = f"ex-{idx}"
            trade_id = 10000 + idx
            
            # Сначала ORDER_ACKNOWLEDGED (optional, но реалистично)
            # submit_event = create_event(
            #     event_type=EXECUTION_EVENT_TYPES["ORDER_SUBMIT_REQUESTED"],
            #     exchange="binance",
            #     symbol=symbol,
            #     client_order_id=client_order_id,
            #     payload=trade
            # )
            # await controller.event_store.append(submit_event)
            # await controller.event_bus.publish(submit_event)
            
            # Затем FILL (FULL)
            execution_report = {
                "e": "executionReport",
                "x": "TRADE",
                "X": "FILLED",
                "s": symbol,
                "c": client_order_id,
                "i": exchange_order_id,
                "S": trade["side"],
                "l": str(trade["qty"]),
                "L": str(trade["price"]),
                "z": str(trade["qty"]),  # cumulative = qty (fully filled)
                "t": trade_id,
                "n": str(trade.get("fee", 0.0)),
                "N": trade.get("fee_asset", "USDT")
            }
            
            event = mapper.map_execution_report(execution_report)
            if event:
                await controller.event_store.append(event)
                await controller.event_bus.publish(event)
        
        # Получаем PnL
        current_price = scenario.get("current_price", trades[-1]["price"] if trades else 0.0)
        pnl = controller.pnl_projection.get_symbol_pnl(
            symbol,
            current_price,
            price_map={"BNBUSDT": 600.0, symbol: current_price}
        )
        
        return {
            "success": True,
            "scenario": scenario.get("scenario", "custom"),
            "trades_executed": len(trades),
            "pnl": pnl
        }
    except Exception as e:
        logger.error(f"Error in test_pnl_scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/trades")
async def debug_trades(symbol: Optional[str] = None):
    """Debug endpoint: показать все trades из ledger"""
    await ensure_initialized()
    if symbol:
        trades = controller.pnl_projection.ledger.get_trades_for_symbol(symbol)
    else:
        trades = controller.pnl_projection.ledger.get_all_trades()
    return {"trades": trades, "count": len(trades)}


@router.get("/health")
async def get_system_health():
    """
    Получить health status системы (P0.6 — Protection Layer).
    
    Пример:
    GET /api/execution-reality/health
    
    Returns:
        {
          "status": "HEALTHY" | "WARNING" | "CRITICAL",
          "metrics": {
            "daily_pnl_pct": -0.05,
            "drawdown_pct": -0.08,
            "reject_rate": 0.12,
            "latency_ms": 180,
            "reconciliation_critical": 0
          },
          "actions": ["REDUCE_SIZE", "FREEZE_WEAK_STRATEGIES"]
        }
    """
    await ensure_initialized()
    try:
        # Простая price_map (в будущем — из market_state)
        current_prices = {
            "BTCUSDT": 67000.0,
            "ETHUSDT": 3200.0,
            "SOLUSDT": 110.0,
            "LINKUSDT": 12.0,
            "ADAUSDT": 0.55,
            "BNBUSDT": 600.0
        }
        
        health = await controller.get_system_health(current_prices)
        return health
    except Exception as e:
        logger.error(f"Error in get_system_health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/simulate-health")
async def simulate_health_scenario(scenario: dict):
    """
    Симулировать health scenario для тестирования (P0.6 Tests).
    
    Пример WARNING:
    POST /api/execution-reality/test/simulate-health
    {"scenario": "warning", "daily_pnl_pct": -0.08}
    
    Пример CRITICAL:
    POST /api/execution-reality/test/simulate-health
    {"scenario": "critical", "drawdown_pct": -0.20}
    """
    await ensure_initialized()
    try:
        # Переопределяем metrics вручную
        override_metrics = {
            "daily_pnl_pct": scenario.get("daily_pnl_pct", 0.0),
            "drawdown_pct": scenario.get("drawdown_pct", 0.0),
            "reject_rate": scenario.get("reject_rate", 0.0),
            "latency_ms": scenario.get("latency_ms", 0),
            "reconciliation_critical": scenario.get("reconciliation_critical", 0)
        }
        
        controller.health_model.update_metrics(override_metrics)
        health_status = controller.health_model.evaluate()
        guard_actions = controller.risk_guard.evaluate(health_status)
        
        return {
            "scenario": scenario.get("scenario", "custom"),
            "status": health_status,
            "metrics": controller.health_model.metrics,
            "actions": guard_actions
        }
    except Exception as e:
        logger.error(f"Error in simulate_health_scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution-health")
async def get_execution_health():
    """
    P1-A: Get execution health metrics.
    
    Returns comprehensive execution health including:
    - Latencies (p50, p95): submit_to_ack_ms, submit_to_fill_ms
    - Queue metrics: depth, inflight_orders
    - Reject/timeout rates
    - Overall health status: HEALTHY / WARNING / CRITICAL
    
    Example:
    GET /api/execution-reality/execution-health
    
    Response:
    {
        "status": "HEALTHY",
        "latency": {
            "avg_submit_to_ack_ms": 120.5,
            "p50_submit_to_ack_ms": 115.0,
            "p95_submit_to_ack_ms": 180.0,
            "avg_submit_to_fill_ms": 450.2,
            "p50_submit_to_fill_ms": 420.0,
            "p95_submit_to_fill_ms": 650.0
        },
        "queue": {
            "queue_depth": 12,
            "inflight_orders": 5,
            "avg_queue_depth": 8.5
        },
        "execution": {
            "total_submits": 1000,
            "total_acks": 980,
            "total_fills": 975,
            "total_rejects": 15,
            "total_timeouts": 5,
            "reject_rate": 0.015,
            "timeout_rate": 0.005
        },
        "timestamp": "2025-01-15T10:30:00Z"
    }
    """
    await ensure_initialized()
    try:
        health = await controller.get_execution_health()
        return health
    except Exception as e:
        logger.error(f"Error in get_execution_health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl/{symbol}")
async def get_pnl(symbol: str, current_price: Optional[float] = None):
    """
    Получить PnL для символа (P0.5 — PnL Truth Layer).
    
    Пример:
    GET /api/execution-reality/pnl/BTCUSDT?current_price=51000.0
    
    Returns:
        {
          "symbol": "BTCUSDT",
          "position_qty": 0.001,
          "avg_entry": 50000.0,
          "realized_pnl": 12.5,
          "unrealized_pnl": 3.2,
          "total_pnl": 15.7,
          "fees_usdt": 0.5,
          "net_pnl": 15.2
        }
    """
    await ensure_initialized()
    try:
        # Если current_price не передан, пытаемся получить из position projection
        if current_price is None:
            position = controller.position_projection.get_position(symbol)
            if position and position.avg_entry_price:
                current_price = position.avg_entry_price
            else:
                # Фоллбэк: цена из последнего fill event для этого символа
                trades = controller.pnl_projection.ledger.get_trades_for_symbol(symbol)
                if trades:
                    current_price = trades[-1]["price"]
                else:
                    current_price = 0.0
        
        # Простая price_map (в будущем — из market_state или external provider)
        price_map = {
            "BNBUSDT": 600.0,  # placeholder
            symbol: current_price
        }
        
        pnl = controller.pnl_projection.get_symbol_pnl(symbol, current_price, price_map)
        
        return pnl
    except Exception as e:
        logger.error(f"Error in get_pnl: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/system/state")
async def get_system_state():
    """
    P1 Product Layer: System State Aggregator
    
    Собирает всё состояние системы в один endpoint для Cockpit UI.
    
    Returns:
        {
            "execution_health": {...},  # Circuit breaker, latency, queue pressure, rate limiter
            "queue_metrics": {...},
            "dlq_summary": {...},
            "positions": [...],
            "open_orders": [...],
            "portfolio_stats": {...},  # Total PnL, fees, slippage
            "strategies": [...],  # Active strategies (mock for MVP)
            "audit_recent": [...],  # Last N traces
            "timestamp": str,
            "last_updated": str
        }
    """
    await ensure_initialized()
    from datetime import datetime, timezone
    
    try:
        # Execution Health (P1-A + P1-B)
        execution_health = await controller.get_execution_health()
        
        # Queue Metrics (P1.1)
        queue_metrics = {}
        dlq_summary = {"count": 0, "items": []}
        if controller.persistent_queue:
            queue_metrics = await controller.persistent_queue.get_metrics()
            
        if controller.dlq_repository:
            dlq_items = await controller.dlq_repository.list_dlq(limit=10)
            dlq_summary = {
                "count": len(dlq_items),
                "items": dlq_items
            }
        
        # Positions (from projection)
        positions_raw = controller.position_projection.list_positions()
        positions = [
            {
                "symbol": p.symbol,
                "size": p.qty,  # qty in model, size in UI
                "side": "LONG" if p.qty > 0 else "SHORT" if p.qty < 0 else "FLAT",
                "entry_price": p.avg_entry_price,
                "unrealized_pnl": 0.0,  # Needs current_price for calculation
                "realized_pnl": 0.0  # From PnL projection
            }
            for p in positions_raw
        ]
        
        # Open Orders (from projection)
        orders_raw = controller.order_projection.list_orders()
        open_orders = [
            {
                "client_order_id": o.client_order_id,
                "symbol": o.symbol,
                "side": o.side,
                "qty": o.requested_qty,  # requested_qty in model, qty in UI
                "price": o.price,
                "status": o.status,
                "order_type": o.order_type,
                "filled_qty": o.filled_qty  # filled_qty in model
            }
            for o in orders_raw
            if o.status in ["ACKNOWLEDGED", "PARTIALLY_FILLED", "PARTIAL"]
        ]
        
        # Portfolio Stats (aggregated from PnL projection)
        all_symbols = list(set([p.symbol for p in positions_raw]))
        total_realized = 0.0
        total_fees = 0.0
        
        for symbol in all_symbols:
            pnl_data = controller.pnl_projection.get_symbol_pnl(symbol, current_price=50000.0)  # Mock price
            total_realized += pnl_data.get("realized_pnl", 0.0)
            total_fees += pnl_data.get("fees_usdt", 0.0)
        
        portfolio_stats = {
            "total_realized_pnl": total_realized,
            "total_unrealized_pnl": 0.0,  # Needs live prices
            "total_pnl": total_realized,
            "total_fees": total_fees,
            "net_pnl": total_realized - total_fees,
            "open_positions": len([p for p in positions_raw if p.qty != 0]),
            "trades_count": len(controller.pnl_projection.ledger.get_all_trades())
        }
        
        # Strategies (mock for MVP - would come from TerminalStateEngine)
        strategies = [
            {
                "id": "strategy-1",
                "name": "Momentum Alpha",
                "enabled": True,
                "last_decision": datetime.now(timezone.utc).isoformat(),
                "trades_today": 5
            }
        ]
        
        # Recent Audit Traces (last 20 execution events)
        recent_events = await controller.event_store.list_last(limit=20)
        audit_recent = [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "client_order_id": e.client_order_id,
                "symbol": e.symbol,
                "trace_id": e.trace_id,
                "timestamp": e.timestamp.isoformat()
            }
            for e in recent_events
        ]
        
        return {
            "ok": True,
            "execution_health": execution_health,
            "queue_metrics": queue_metrics,
            "dlq_summary": dlq_summary,
            "positions": positions,
            "open_orders": open_orders,
            "portfolio_stats": portfolio_stats,
            "strategies": strategies,
            "audit_recent": audit_recent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.exception("Failed to fetch system state")
        raise HTTPException(status_code=500, detail=str(e))

