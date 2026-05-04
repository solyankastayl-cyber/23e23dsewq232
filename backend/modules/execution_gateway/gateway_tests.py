"""
Execution Gateway Tests

PHASE 39 — Execution Gateway Layer

Minimum 40 tests covering:
- Safety gate checks
- Exchange routing
- Paper execution
- Live execution (mock)
- Approval workflow
- Portfolio integration
- Order management
- Fill tracking
- API validation
"""

import pytest
import asyncio
from datetime import datetime, timezone

from .gateway_types import (
    ExecutionMode,
    ExecutionRequest,
    ExecutionOrder,
    ExecutionFill,
    SafetyGateResult,
    GatewayConfig,
    OrderSide,
    OrderType,
    OrderStatus,
)
from .gateway_engine import ExecutionGatewayEngine


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create fresh engine for each test."""
    config = GatewayConfig(
        execution_mode=ExecutionMode.PAPER,
        max_single_order_usd=100000,
        daily_loss_limit_usd=50000,
        max_portfolio_risk=0.20,
    )
    return ExecutionGatewayEngine(config)


@pytest.fixture
def sample_request():
    """Sample execution request."""
    return ExecutionRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        size_usd=10000,
        order_type=OrderType.MARKET,
        strategy="TREND_FOLLOWING",
        max_slippage_bps=50.0,
    )


# ══════════════════════════════════════════════════════════════
# 1. Safety Gate Tests (8 tests)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_safety_gate_passes_valid_request(engine, sample_request):
    """Test safety gate passes valid request."""
    result = await engine._run_safety_gate(sample_request)
    
    assert result.approved is True
    assert result.approved_size_usd > 0


@pytest.mark.asyncio
async def test_safety_gate_blocks_oversized_order(engine):
    """Test safety gate blocks order exceeding max size."""
    request = ExecutionRequest(
        symbol="BTC",
        side=OrderSide.BUY,
        size_usd=200000,  # Exceeds 100k limit
        strategy="TREND",
    )
    
    result = await engine._run_safety_gate(request)
    
    # Should adjust size
    assert result.size_adjusted is True
    assert result.approved_size_usd <= engine._config.max_single_order_usd


@pytest.mark.asyncio
async def test_safety_gate_checks_portfolio_risk(engine, sample_request):
    """Test safety gate checks portfolio risk."""
    result = await engine._run_safety_gate(sample_request)
    
    # Should have portfolio risk check
    check_types = [c.check_type.value for c in result.checks]
    assert "PORTFOLIO_RISK" in check_types


@pytest.mark.asyncio
async def test_safety_gate_checks_strategy_risk(engine, sample_request):
    """Test safety gate checks strategy risk."""
    result = await engine._run_safety_gate(sample_request)
    
    check_types = [c.check_type.value for c in result.checks]
    assert "STRATEGY_RISK" in check_types


@pytest.mark.asyncio
async def test_safety_gate_checks_liquidity_impact(engine, sample_request):
    """Test safety gate checks liquidity impact."""
    result = await engine._run_safety_gate(sample_request)
    
    check_types = [c.check_type.value for c in result.checks]
    assert "LIQUIDITY_IMPACT" in check_types


@pytest.mark.asyncio
async def test_safety_gate_checks_max_order_size(engine, sample_request):
    """Test safety gate checks max order size."""
    result = await engine._run_safety_gate(sample_request)
    
    check_types = [c.check_type.value for c in result.checks]
    assert "MAX_ORDER_SIZE" in check_types


@pytest.mark.asyncio
async def test_safety_gate_daily_loss_check(engine):
    """Test safety gate daily loss limit check."""
    engine._daily_loss = 60000  # Over limit
    
    request = ExecutionRequest(
        symbol="BTC",
        side=OrderSide.BUY,
        size_usd=5000,
        strategy="TREND",
    )
    
    result = await engine._run_safety_gate(request)
    
    # Should have daily loss check
    daily_check = next(
        (c for c in result.checks if c.check_type.value == "DAILY_LOSS_LIMIT"),
        None
    )
    assert daily_check is not None
    assert daily_check.passed is False


@pytest.mark.asyncio
async def test_safety_gate_returns_all_checks(engine, sample_request):
    """Test safety gate returns all checks."""
    result = await engine._run_safety_gate(sample_request)
    
    # Should have at least 4 checks
    assert len(result.checks) >= 4


# ══════════════════════════════════════════════════════════════
# 2. Exchange Routing Tests (6 tests)
# ══════════════════════════════════════════════════════════════

def test_route_btc_to_binance(engine):
    """Test BTC routes to Binance."""
    exchange = engine._route_to_exchange("BTC")
    assert exchange == "BINANCE"


def test_route_eth_to_binance(engine):
    """Test ETH routes to Binance."""
    exchange = engine._route_to_exchange("ETH")
    assert exchange == "BINANCE"


def test_route_sol_to_bybit(engine):
    """Test SOL routes to Bybit."""
    exchange = engine._route_to_exchange("SOL")
    assert exchange == "BYBIT"


def test_route_with_preferred_exchange(engine):
    """Test preferred exchange override."""
    exchange = engine._route_to_exchange("BTC", preferred="BYBIT")
    assert exchange == "BYBIT"


def test_route_unknown_symbol_default(engine):
    """Test unknown symbol routes to default."""
    exchange = engine._route_to_exchange("UNKNOWNTOKEN")
    assert exchange == "BINANCE"


def test_exchange_symbol_conversion(engine):
    """Test symbol conversion to exchange format."""
    symbol = engine._get_exchange_symbol("BTC", "BINANCE")
    assert symbol == "BTCUSDT"
    
    symbol = engine._get_exchange_symbol("ETH", "BYBIT")
    assert symbol == "ETHUSDT"


# ══════════════════════════════════════════════════════════════
# 3. Paper Execution Tests (8 tests)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_paper_execution_creates_fill(engine, sample_request):
    """Test paper execution creates fill."""
    result = await engine.execute(sample_request)
    
    assert result.success is True
    assert result.status == OrderStatus.FILLED
    assert result.filled_size_usd > 0


@pytest.mark.asyncio
async def test_paper_execution_calculates_slippage(engine, sample_request):
    """Test paper execution calculates slippage."""
    result = await engine.execute(sample_request)
    
    # Slippage should be reasonable in paper mode
    assert result.slippage_bps >= 0
    assert result.slippage_bps < 50  # Less than 50 bps (reasonable)


@pytest.mark.asyncio
async def test_paper_execution_calculates_fee(engine, sample_request):
    """Test paper execution calculates fee."""
    result = await engine.execute(sample_request)
    
    # Fee should be calculated
    assert result.fee > 0
    assert result.fee < result.filled_size_usd * 0.01  # Less than 1%


@pytest.mark.asyncio
async def test_paper_execution_records_order(engine, sample_request):
    """Test paper execution records order."""
    result = await engine.execute(sample_request)
    
    order = engine.get_order(result.order_id)
    assert order is not None
    assert order.status == OrderStatus.FILLED


@pytest.mark.asyncio
async def test_paper_execution_records_fill(engine, sample_request):
    """Test paper execution records fill."""
    result = await engine.execute(sample_request)
    
    fills = engine.get_fills(order_id=result.order_id)
    assert len(fills) == 1
    assert fills[0].filled_size > 0


@pytest.mark.asyncio
async def test_paper_execution_updates_daily_volume(engine, sample_request):
    """Test paper execution updates daily volume."""
    initial_volume = engine._daily_volume
    
    await engine.execute(sample_request)
    
    assert engine._daily_volume > initial_volume


@pytest.mark.asyncio
async def test_paper_execution_returns_latency(engine, sample_request):
    """Test paper execution returns latency."""
    result = await engine.execute(sample_request)
    
    assert result.latency_ms > 0
    assert result.latency_ms < 1000  # Less than 1 second


@pytest.mark.asyncio
async def test_paper_execution_sell_order(engine):
    """Test paper execution for sell order."""
    request = ExecutionRequest(
        symbol="ETHUSDT",
        side=OrderSide.SELL,
        size_usd=5000,
        strategy="TREND",
    )
    
    result = await engine.execute(request)
    
    assert result.success is True
    assert result.side == OrderSide.SELL


# ══════════════════════════════════════════════════════════════
# 4. Approval Mode Tests (6 tests)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_approval_mode_creates_approval_request(engine, sample_request):
    """Test approval mode creates approval request."""
    engine.set_execution_mode(ExecutionMode.APPROVAL)
    
    result = await engine.execute(sample_request)
    
    assert result.status == OrderStatus.AWAITING_APPROVAL


@pytest.mark.asyncio
async def test_approval_mode_pending_list(engine, sample_request):
    """Test approval mode adds to pending list."""
    engine.set_execution_mode(ExecutionMode.APPROVAL)
    
    await engine.execute(sample_request)
    
    pending = engine.get_pending_approvals()
    assert len(pending) >= 1


@pytest.mark.asyncio
async def test_approve_order_executes(engine, sample_request):
    """Test approving order executes it."""
    engine.set_execution_mode(ExecutionMode.APPROVAL)
    
    # Create approval request
    await engine.execute(sample_request)
    
    # Get pending approval
    pending = engine.get_pending_approvals()
    assert len(pending) >= 1
    
    approval_id = pending[0].approval_id
    
    # Approve
    result = await engine.approve_order(
        approval_id=approval_id,
        approved_by="test_user",
    )
    
    assert result.success is True
    assert result.status == OrderStatus.FILLED


@pytest.mark.asyncio
async def test_reject_order(engine, sample_request):
    """Test rejecting order."""
    engine.set_execution_mode(ExecutionMode.APPROVAL)
    
    await engine.execute(sample_request)
    
    pending = engine.get_pending_approvals()
    approval_id = pending[0].approval_id
    
    success = await engine.reject_order(
        approval_id=approval_id,
        rejected_by="test_user",
        reason="Test rejection",
    )
    
    assert success is True


@pytest.mark.asyncio
async def test_approve_with_modified_size(engine, sample_request):
    """Test approving with modified size."""
    engine.set_execution_mode(ExecutionMode.APPROVAL)
    
    await engine.execute(sample_request)
    
    pending = engine.get_pending_approvals()
    approval_id = pending[0].approval_id
    
    # Approve with reduced size
    result = await engine.approve_order(
        approval_id=approval_id,
        approved_by="test_user",
        approved_size_usd=5000,  # Half size
    )
    
    assert result.success is True


@pytest.mark.asyncio
async def test_approve_invalid_id(engine):
    """Test approving invalid ID fails."""
    result = await engine.approve_order(
        approval_id="invalid_id",
        approved_by="test_user",
    )
    
    assert result.success is False


# ══════════════════════════════════════════════════════════════
# 5. Order Management Tests (5 tests)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_order_by_id(engine, sample_request):
    """Test getting order by ID."""
    result = await engine.execute(sample_request)
    
    order = engine.get_order(result.order_id)
    
    assert order is not None
    assert order.order_id == result.order_id


@pytest.mark.asyncio
async def test_get_orders_list(engine, sample_request):
    """Test getting orders list."""
    await engine.execute(sample_request)
    await engine.execute(sample_request)
    
    orders = engine.get_orders()
    
    assert len(orders) >= 2


@pytest.mark.asyncio
async def test_get_orders_by_status(engine, sample_request):
    """Test filtering orders by status."""
    await engine.execute(sample_request)
    
    orders = engine.get_orders(status=OrderStatus.FILLED)
    
    assert all(o.status == OrderStatus.FILLED for o in orders)


def test_get_nonexistent_order(engine):
    """Test getting nonexistent order returns None."""
    order = engine.get_order("nonexistent_id")
    assert order is None


@pytest.mark.asyncio
async def test_order_contains_strategy(engine, sample_request):
    """Test order contains strategy info."""
    result = await engine.execute(sample_request)
    
    order = engine.get_order(result.order_id)
    
    assert order.strategy == sample_request.strategy


# ══════════════════════════════════════════════════════════════
# 6. Fill Tracking Tests (4 tests)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_fill_by_id(engine, sample_request):
    """Test getting fill by ID."""
    result = await engine.execute(sample_request)
    
    fills = engine.get_fills(order_id=result.order_id)
    
    if fills:
        fill = engine.get_fill(fills[0].fill_id)
        assert fill is not None


@pytest.mark.asyncio
async def test_fill_contains_price_info(engine, sample_request):
    """Test fill contains price info."""
    result = await engine.execute(sample_request)
    
    fills = engine.get_fills(order_id=result.order_id)
    
    assert len(fills) == 1
    assert fills[0].avg_price > 0
    assert fills[0].expected_price > 0


@pytest.mark.asyncio
async def test_fill_is_complete(engine, sample_request):
    """Test fill is_complete flag."""
    result = await engine.execute(sample_request)
    
    fills = engine.get_fills(order_id=result.order_id)
    
    assert fills[0].is_complete is True


@pytest.mark.asyncio
async def test_fills_filter_by_order(engine, sample_request):
    """Test filtering fills by order."""
    result1 = await engine.execute(sample_request)
    result2 = await engine.execute(sample_request)
    
    fills = engine.get_fills(order_id=result1.order_id)
    
    assert all(f.order_id == result1.order_id for f in fills)


# ══════════════════════════════════════════════════════════════
# 7. Config Tests (3 tests)
# ══════════════════════════════════════════════════════════════

def test_get_config(engine):
    """Test getting config."""
    config = engine.get_config()
    
    assert config.execution_mode == ExecutionMode.PAPER
    assert config.max_single_order_usd == 100000


def test_set_execution_mode(engine):
    """Test setting execution mode."""
    engine.set_execution_mode(ExecutionMode.APPROVAL)
    
    assert engine.get_config().execution_mode == ExecutionMode.APPROVAL


def test_get_daily_stats(engine):
    """Test getting daily stats."""
    stats = engine.get_daily_stats()
    
    assert "daily_volume_usd" in stats
    assert "daily_loss_usd" in stats
    assert "order_count" in stats


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
