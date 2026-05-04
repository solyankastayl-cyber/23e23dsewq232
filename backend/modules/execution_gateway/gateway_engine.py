"""
Execution Gateway Engine

PHASE 39 — Execution Gateway Layer

Main engine for unified execution pipeline.

Flow:
1. ExecutionRequest (from Execution Brain)
2. Safety Gate (Risk Budget + Portfolio + Liquidity checks)
3. Exchange Routing (symbol → exchange)
4. Order Creation (to Exchange Adapter)
5. Fill Processing (from Exchange)
6. Portfolio Update (to Portfolio Manager)

Modes:
- PAPER: Simulated fills
- LIVE: Real exchange orders
- APPROVAL: Requires human approval
"""

import os
import math
import asyncio
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone, timedelta
import random

from .gateway_types import (
    ExecutionMode,
    ExecutionRequest,
    ExecutionOrder,
    ExecutionFill,
    ExecutionResult,
    SafetyGateResult,
    SafetyCheckResult,
    SafetyCheckType,
    PortfolioUpdateEvent,
    ApprovalRequest,
    ExchangeRouteConfig,
    GatewayConfig,
    OrderSide,
    OrderType,
    OrderStatus,
)


# ══════════════════════════════════════════════════════════════
# Execution Gateway Engine
# ══════════════════════════════════════════════════════════════

class ExecutionGatewayEngine:
    """
    Execution Gateway — PHASE 39
    
    Unified pipeline from Execution Brain to Exchange.
    
    Key features:
    1. Safety Gate with Risk Budget integration
    2. Exchange routing (symbol → exchange)
    3. Paper/Live/Approval modes
    4. Order lifecycle management
    5. Portfolio sync after fills
    """
    
    def __init__(self, config: Optional[GatewayConfig] = None):
        self._config = config or GatewayConfig()
        
        # State
        self._orders: Dict[str, ExecutionOrder] = {}
        self._fills: Dict[str, ExecutionFill] = {}
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        
        # Route config
        self._routes: Dict[str, ExchangeRouteConfig] = self._init_default_routes()
        
        # Daily tracking
        self._daily_loss: float = 0.0
        self._daily_volume: float = 0.0
        self._last_reset: datetime = datetime.now(timezone.utc)
        
        # Exchange adapters cache
        self._exchange_adapters = {}
        
        # Prices cache
        self._price_cache: Dict[str, float] = {}
    
    def _init_default_routes(self) -> Dict[str, ExchangeRouteConfig]:
        """Initialize default symbol → exchange routing."""
        return {
            "BTC": ExchangeRouteConfig(
                symbol="BTC",
                preferred_exchange="BINANCE",
                fallback_exchanges=["BYBIT"],
                reason="Best liquidity"
            ),
            "ETH": ExchangeRouteConfig(
                symbol="ETH",
                preferred_exchange="BINANCE",
                fallback_exchanges=["BYBIT", "OKX"],
                reason="Best liquidity"
            ),
            "SOL": ExchangeRouteConfig(
                symbol="SOL",
                preferred_exchange="BYBIT",
                fallback_exchanges=["BINANCE"],
                reason="Good spreads"
            ),
            "AVAX": ExchangeRouteConfig(
                symbol="AVAX",
                preferred_exchange="BINANCE",
                fallback_exchanges=["BYBIT"],
                reason="Liquidity"
            ),
            # Default for unknown
            "DEFAULT": ExchangeRouteConfig(
                symbol="DEFAULT",
                preferred_exchange="BINANCE",
                fallback_exchanges=["BYBIT"],
                reason="Default exchange"
            ),
        }
    
    # ═══════════════════════════════════════════════════════════
    # 1. Main Execute Method
    # ═══════════════════════════════════════════════════════════
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Main execution pipeline.
        
        Flow:
        1. Safety Gate check
        2. Route to exchange
        3. Create order
        4. Execute (based on mode)
        5. Process fill
        6. Update portfolio
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Step 1: Safety Gate
            safety_result = await self._run_safety_gate(request)
            
            if not safety_result.approved:
                return ExecutionResult(
                    request_id=request.request_id,
                    success=False,
                    status=OrderStatus.REJECTED,
                    symbol=request.symbol,
                    side=request.side,
                    requested_size_usd=request.size_usd,
                    safety_check_passed=False,
                    failure_reason=safety_result.blocked_reason,
                    created_at=start_time,
                )
            
            # Step 2: Adjust size if needed
            approved_size_usd = safety_result.approved_size_usd
            
            # Step 3: Get current price
            current_price = await self._get_price(request.symbol)
            size_base = approved_size_usd / current_price if current_price > 0 else 0
            
            # Step 4: Route to exchange
            exchange = self._route_to_exchange(request.symbol, request.preferred_exchange)
            
            # Step 5: Create order
            order = ExecutionOrder(
                request_id=request.request_id,
                exchange=exchange,
                symbol=request.symbol,
                exchange_symbol=self._get_exchange_symbol(request.symbol, exchange),
                side=request.side,
                order_type=request.order_type,
                size_base=size_base,
                size_quote=approved_size_usd,
                limit_price=request.limit_price,
                stop_price=request.stop_price,
                expected_price=request.expected_price or current_price,
                time_in_force=request.time_in_force,
                reduce_only=request.reduce_only,
                strategy=request.strategy,
                metadata=request.metadata,
            )
            
            self._orders[order.order_id] = order
            
            # Step 6: Execute based on mode
            if self._config.execution_mode == ExecutionMode.PAPER:
                result = await self._execute_paper(order)
            elif self._config.execution_mode == ExecutionMode.APPROVAL:
                result = await self._execute_approval(order, request)
            else:  # LIVE
                result = await self._execute_live(order)
            
            # Step 7: Calculate latency
            result.latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result.completed_at = datetime.now(timezone.utc)
            
            # Step 8: Update daily tracking
            if result.success:
                self._daily_volume += result.filled_size_usd
            
            return result
            
        except Exception as e:
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                status=OrderStatus.FAILED,
                symbol=request.symbol,
                side=request.side,
                requested_size_usd=request.size_usd,
                failure_reason=str(e),
                created_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )
    
    # ═══════════════════════════════════════════════════════════
    # 2. Safety Gate
    # ═══════════════════════════════════════════════════════════
    
    async def _run_safety_gate(self, request: ExecutionRequest) -> SafetyGateResult:
        """
        Run all safety checks before execution.
        
        Integrates with:
        - Risk Budget Engine
        - Portfolio Manager
        - Liquidity Impact Engine
        """
        checks: List[SafetyCheckResult] = []
        approved_size = request.size_usd
        
        # Check 1: Max Order Size
        max_order = self._config.max_single_order_usd
        if request.size_usd > max_order:
            checks.append(SafetyCheckResult(
                check_type=SafetyCheckType.MAX_ORDER_SIZE,
                passed=False,
                reason=f"Order size ${request.size_usd:.0f} exceeds max ${max_order:.0f}",
                value=request.size_usd,
                limit=max_order,
                severity="CRITICAL"
            ))
            approved_size = max_order
        else:
            checks.append(SafetyCheckResult(
                check_type=SafetyCheckType.MAX_ORDER_SIZE,
                passed=True,
                value=request.size_usd,
                limit=max_order,
            ))
        
        # Check 2: Daily Loss Limit
        daily_limit = self._config.daily_loss_limit_usd
        if self._daily_loss >= daily_limit:
            checks.append(SafetyCheckResult(
                check_type=SafetyCheckType.DAILY_LOSS_LIMIT,
                passed=False,
                reason=f"Daily loss ${self._daily_loss:.0f} reached limit ${daily_limit:.0f}",
                value=self._daily_loss,
                limit=daily_limit,
                severity="CRITICAL"
            ))
        else:
            checks.append(SafetyCheckResult(
                check_type=SafetyCheckType.DAILY_LOSS_LIMIT,
                passed=True,
                value=self._daily_loss,
                limit=daily_limit,
            ))
        
        # Check 3: Portfolio Risk (via Risk Budget Engine)
        risk_check = await self._check_portfolio_risk(request)
        checks.append(risk_check)
        
        if not risk_check.passed and risk_check.severity == "CRITICAL":
            approved_size = 0
        
        # Check 4: Strategy Risk Budget
        strategy_check = await self._check_strategy_risk(request)
        checks.append(strategy_check)
        
        # Check 5: Liquidity Impact
        liquidity_check = await self._check_liquidity_impact(request)
        checks.append(liquidity_check)
        
        if liquidity_check.value > 100:  # > 100 bps impact
            approved_size = min(approved_size, request.size_usd * 0.5)
        
        # Determine overall result
        critical_failures = [c for c in checks if not c.passed and c.severity == "CRITICAL"]
        all_passed = len(critical_failures) == 0
        
        blocked_reason = None
        if not all_passed:
            blocked_reason = critical_failures[0].reason
        
        return SafetyGateResult(
            request_id=request.request_id,
            approved=all_passed,
            blocked_reason=blocked_reason,
            checks=checks,
            original_size_usd=request.size_usd,
            approved_size_usd=approved_size if all_passed else 0,
            size_adjusted=approved_size != request.size_usd,
            adjustment_reason="Safety limits applied" if approved_size != request.size_usd else None,
        )
    
    async def _check_portfolio_risk(self, request: ExecutionRequest) -> SafetyCheckResult:
        """Check portfolio risk via Risk Budget Engine."""
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            
            within_limit, current_risk, _ = engine.check_portfolio_risk_limit()
            max_risk = self._config.max_portfolio_risk
            
            return SafetyCheckResult(
                check_type=SafetyCheckType.PORTFOLIO_RISK,
                passed=within_limit,
                reason="" if within_limit else f"Portfolio risk {current_risk*100:.1f}% exceeds {max_risk*100:.0f}%",
                value=current_risk,
                limit=max_risk,
                severity="WARNING" if within_limit else "CRITICAL"
            )
        except Exception:
            # Default pass if engine not available
            return SafetyCheckResult(
                check_type=SafetyCheckType.PORTFOLIO_RISK,
                passed=True,
                reason="Risk engine not available",
            )
    
    async def _check_strategy_risk(self, request: ExecutionRequest) -> SafetyCheckResult:
        """Check strategy risk budget."""
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            
            budget = engine.get_strategy_risk_budget(request.strategy)
            
            if budget:
                remaining = budget.risk_target - budget.risk_used
                passed = remaining > 0.01  # At least 1% remaining
                
                return SafetyCheckResult(
                    check_type=SafetyCheckType.STRATEGY_RISK,
                    passed=passed,
                    reason="" if passed else f"Strategy {request.strategy} risk budget exhausted",
                    value=budget.risk_used,
                    limit=budget.risk_target,
                    severity="WARNING" if passed else "CRITICAL"
                )
            
            return SafetyCheckResult(
                check_type=SafetyCheckType.STRATEGY_RISK,
                passed=True,
                reason="No budget constraint",
            )
        except Exception:
            return SafetyCheckResult(
                check_type=SafetyCheckType.STRATEGY_RISK,
                passed=True,
            )
    
    async def _check_liquidity_impact(self, request: ExecutionRequest) -> SafetyCheckResult:
        """Check liquidity impact."""
        try:
            from modules.execution.slippage import get_liquidity_impact_engine
            engine = get_liquidity_impact_engine()
            
            impact = engine.estimate_impact(
                symbol=request.symbol,
                size_usd=request.size_usd,
                side=request.side.value,
            )
            
            impact_bps = impact.get("impact_bps", 0)
            max_impact = request.max_slippage_bps
            passed = impact_bps < max_impact
            
            return SafetyCheckResult(
                check_type=SafetyCheckType.LIQUIDITY_IMPACT,
                passed=passed,
                reason="" if passed else f"Impact {impact_bps:.0f} bps exceeds max {max_impact:.0f}",
                value=impact_bps,
                limit=max_impact,
                severity="WARNING" if passed else "CRITICAL"
            )
        except Exception:
            return SafetyCheckResult(
                check_type=SafetyCheckType.LIQUIDITY_IMPACT,
                passed=True,
                reason="Liquidity engine not available",
            )
    
    # ═══════════════════════════════════════════════════════════
    # 3. Exchange Routing
    # ═══════════════════════════════════════════════════════════
    
    def _route_to_exchange(
        self,
        symbol: str,
        preferred: Optional[str] = None,
    ) -> str:
        """
        Route symbol to exchange.
        
        Simple routing now, Smart Order Routing in PHASE 42.
        """
        if preferred:
            return preferred.upper()
        
        # Extract base symbol (e.g., BTCUSDT → BTC)
        base = symbol.replace("USDT", "").replace("USD", "").replace("PERP", "").upper()
        
        route = self._routes.get(base, self._routes["DEFAULT"])
        return route.preferred_exchange
    
    def _get_exchange_symbol(self, symbol: str, exchange: str) -> str:
        """Convert symbol to exchange-specific format."""
        base = symbol.upper()
        
        if exchange == "BINANCE":
            if "USDT" not in base:
                return f"{base}USDT"
            return base
        elif exchange == "BYBIT":
            if "USDT" not in base:
                return f"{base}USDT"
            return base
        elif exchange == "HYPERLIQUID":
            return base.replace("USDT", "-PERP")
        
        return base
    
    # ═══════════════════════════════════════════════════════════
    # 4. Execution Modes
    # ═══════════════════════════════════════════════════════════
    
    async def _execute_paper(self, order: ExecutionOrder) -> ExecutionResult:
        """
        Paper trading execution - simulated fills.
        """
        # Simulate fill with small slippage
        slippage_factor = random.uniform(0.9995, 1.0005)  # ±0.05%
        
        if order.order_type == OrderType.MARKET:
            fill_price = order.expected_price * slippage_factor
        else:
            fill_price = order.limit_price or order.expected_price
        
        if order.side == OrderSide.BUY:
            fill_price *= (1 + random.uniform(0, 0.001))  # Slight worse for buys
        else:
            fill_price *= (1 - random.uniform(0, 0.001))  # Slight worse for sells
        
        # Calculate slippage
        slippage_bps = ((fill_price - order.expected_price) / order.expected_price) * 10000
        if order.side == OrderSide.SELL:
            slippage_bps = -slippage_bps  # Invert for sells
        
        # Create fill
        fill = ExecutionFill(
            order_id=order.order_id,
            request_id=order.request_id,
            exchange_order_id=f"paper_{order.order_id}",
            exchange=order.exchange,
            symbol=order.symbol,
            side=order.side,
            filled_size=order.size_base,
            filled_value=order.size_quote,
            avg_price=round(fill_price, 2),
            expected_price=order.expected_price,
            slippage_bps=round(abs(slippage_bps), 2),
            fee=order.size_quote * 0.0004,  # 0.04% fee
            is_complete=True,
            strategy=order.strategy,
        )
        
        self._fills[fill.fill_id] = fill
        
        # Update order status
        order.status = OrderStatus.FILLED
        order.exchange_order_id = fill.exchange_order_id
        
        # Trigger portfolio update
        await self._update_portfolio(fill)
        
        return ExecutionResult(
            request_id=order.request_id,
            success=True,
            status=OrderStatus.FILLED,
            order_id=order.order_id,
            exchange_order_id=fill.exchange_order_id,
            exchange=order.exchange,
            symbol=order.symbol,
            side=order.side,
            requested_size_usd=order.size_quote,
            filled_size_usd=fill.filled_value,
            filled_size_base=fill.filled_size,
            avg_price=fill.avg_price,
            expected_price=order.expected_price,
            slippage_bps=fill.slippage_bps,
            fee=fill.fee,
            total_cost=fill.filled_value + fill.fee,
            safety_check_passed=True,
        )
    
    async def _execute_approval(
        self,
        order: ExecutionOrder,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        """
        Approval mode - create approval request.
        """
        # Create approval request
        approval = ApprovalRequest(
            request_id=order.request_id,
            order_id=order.order_id,
            symbol=order.symbol,
            exchange=order.exchange,
            side=order.side,
            size_usd=order.size_quote,
            size_base=order.size_base,
            order_type=order.order_type,
            strategy=order.strategy,
            hypothesis_id=request.hypothesis_id,
            portfolio_risk=0.0,  # Would be filled from actual check
            strategy_risk=0.0,
            expected_slippage_bps=0.0,
            liquidity_impact="LOW",
            system_recommendation="APPROVE",
            recommendation_reason="All safety checks passed",
            suggested_size_usd=order.size_quote,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self._config.approval_timeout_seconds),
        )
        
        self._pending_approvals[approval.approval_id] = approval
        
        # Update order status
        order.status = OrderStatus.AWAITING_APPROVAL
        
        return ExecutionResult(
            request_id=order.request_id,
            success=True,  # Request accepted, awaiting approval
            status=OrderStatus.AWAITING_APPROVAL,
            order_id=order.order_id,
            exchange=order.exchange,
            symbol=order.symbol,
            side=order.side,
            requested_size_usd=order.size_quote,
            safety_check_passed=True,
            safety_adjustments=f"Awaiting approval: {approval.approval_id}",
        )
    
    async def _execute_live(self, order: ExecutionOrder) -> ExecutionResult:
        """
        Live execution - send to exchange.
        """
        try:
            # Get exchange adapter
            adapter = await self._get_exchange_adapter(order.exchange)
            
            if not adapter:
                return ExecutionResult(
                    request_id=order.request_id,
                    success=False,
                    status=OrderStatus.FAILED,
                    symbol=order.symbol,
                    side=order.side,
                    requested_size_usd=order.size_quote,
                    failure_reason=f"Exchange adapter not available: {order.exchange}",
                )
            
            # Create order request
            from modules.exchanges.exchange_types import (
                ExchangeOrderRequest,
                OrderSide as ExOrderSide,
                OrderType as ExOrderType,
            )
            
            exchange_request = ExchangeOrderRequest(
                symbol=order.exchange_symbol,
                side=ExOrderSide(order.side.value),
                order_type=ExOrderType(order.order_type.value),
                size=order.size_base,
                price=order.limit_price,
                reduce_only=order.reduce_only,
            )
            
            # Submit order
            order.status = OrderStatus.SUBMITTED
            order.submitted_at = datetime.now(timezone.utc)
            
            response = await adapter.create_order(exchange_request)
            
            # Process response
            order.exchange_order_id = response.exchange_order_id
            
            if response.status.value == "FILLED":
                order.status = OrderStatus.FILLED
                
                # Create fill record
                fill = ExecutionFill(
                    order_id=order.order_id,
                    request_id=order.request_id,
                    exchange_order_id=response.exchange_order_id,
                    exchange=order.exchange,
                    symbol=order.symbol,
                    side=order.side,
                    filled_size=response.filled_size,
                    filled_value=response.filled_size * (response.avg_fill_price or order.expected_price),
                    avg_price=response.avg_fill_price or order.expected_price,
                    expected_price=order.expected_price,
                    slippage_bps=self._calculate_slippage(order, response.avg_fill_price),
                    is_complete=True,
                    strategy=order.strategy,
                )
                
                self._fills[fill.fill_id] = fill
                await self._update_portfolio(fill)
                
                return ExecutionResult(
                    request_id=order.request_id,
                    success=True,
                    status=OrderStatus.FILLED,
                    order_id=order.order_id,
                    exchange_order_id=response.exchange_order_id,
                    exchange=order.exchange,
                    symbol=order.symbol,
                    side=order.side,
                    requested_size_usd=order.size_quote,
                    filled_size_usd=fill.filled_value,
                    filled_size_base=fill.filled_size,
                    avg_price=fill.avg_price,
                    expected_price=order.expected_price,
                    slippage_bps=fill.slippage_bps,
                    safety_check_passed=True,
                )
            
            elif response.status.value == "NEW":
                order.status = OrderStatus.SUBMITTED
                
                return ExecutionResult(
                    request_id=order.request_id,
                    success=True,
                    status=OrderStatus.SUBMITTED,
                    order_id=order.order_id,
                    exchange_order_id=response.exchange_order_id,
                    exchange=order.exchange,
                    symbol=order.symbol,
                    side=order.side,
                    requested_size_usd=order.size_quote,
                    safety_check_passed=True,
                )
            
            else:
                return ExecutionResult(
                    request_id=order.request_id,
                    success=False,
                    status=OrderStatus(response.status.value),
                    order_id=order.order_id,
                    exchange_order_id=response.exchange_order_id,
                    exchange=order.exchange,
                    symbol=order.symbol,
                    side=order.side,
                    requested_size_usd=order.size_quote,
                    failure_reason=f"Order status: {response.status.value}",
                )
            
        except Exception as e:
            order.status = OrderStatus.FAILED
            return ExecutionResult(
                request_id=order.request_id,
                success=False,
                status=OrderStatus.FAILED,
                symbol=order.symbol,
                side=order.side,
                requested_size_usd=order.size_quote,
                failure_reason=str(e),
            )
    
    def _calculate_slippage(self, order: ExecutionOrder, fill_price: Optional[float]) -> float:
        """Calculate slippage in basis points."""
        if not fill_price or not order.expected_price:
            return 0.0
        
        diff = fill_price - order.expected_price
        if order.side == OrderSide.SELL:
            diff = -diff
        
        return abs(diff / order.expected_price * 10000)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Portfolio Update
    # ═══════════════════════════════════════════════════════════
    
    async def _update_portfolio(self, fill: ExecutionFill):
        """Update portfolio after fill."""
        try:
            # Update Risk Budget Engine
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            
            if fill.side == OrderSide.BUY:
                engine.add_position_risk(
                    symbol=fill.symbol,
                    strategy=fill.strategy,
                    position_size_usd=fill.filled_value,
                )
            else:
                engine.remove_position_risk(fill.symbol)
            
        except Exception:
            pass  # Silently fail for now
        
        # Create portfolio update event
        event = PortfolioUpdateEvent(
            fill_id=fill.fill_id,
            order_id=fill.order_id,
            symbol=fill.symbol,
            exchange=fill.exchange,
            strategy=fill.strategy,
            side=fill.side,
            size_change=fill.filled_size if fill.side == OrderSide.BUY else -fill.filled_size,
            value_change=fill.filled_value if fill.side == OrderSide.BUY else -fill.filled_value,
            avg_price=fill.avg_price,
        )
        
        # Would emit to Portfolio Manager in full implementation
        return event
    
    # ═══════════════════════════════════════════════════════════
    # 6. Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    async def _get_price(self, symbol: str) -> float:
        """Get current price for symbol."""
        if symbol in self._price_cache:
            return self._price_cache[symbol]
        
        # Default prices
        defaults = {
            "BTC": 45000.0,
            "BTCUSDT": 45000.0,
            "ETH": 2500.0,
            "ETHUSDT": 2500.0,
            "SOL": 100.0,
            "SOLUSDT": 100.0,
            "AVAX": 35.0,
            "AVAXUSDT": 35.0,
        }
        
        base = symbol.upper().replace("USDT", "")
        price = defaults.get(base, defaults.get(symbol.upper(), 100.0))
        
        self._price_cache[symbol] = price
        return price
    
    async def _get_exchange_adapter(self, exchange: str):
        """Get exchange adapter."""
        if exchange in self._exchange_adapters:
            return self._exchange_adapters[exchange]
        
        try:
            from modules.exchanges import ExchangeRouter, ExchangeId
            
            router = ExchangeRouter()
            exchange_id = ExchangeId(exchange.upper())
            
            # Use testnet by default
            adapter = router.get_or_create_adapter(
                exchange_id=exchange_id,
                testnet=self._config.testnet_mode,
            )
            
            await adapter.connect()
            self._exchange_adapters[exchange] = adapter
            
            return adapter
        except Exception:
            return None
    
    # ═══════════════════════════════════════════════════════════
    # 7. Approval Management
    # ═══════════════════════════════════════════════════════════
    
    async def approve_order(
        self,
        approval_id: str,
        approved_by: str,
        approved_size_usd: Optional[float] = None,
    ) -> ExecutionResult:
        """Approve a pending order."""
        approval = self._pending_approvals.get(approval_id)
        
        if not approval:
            return ExecutionResult(
                request_id="",
                success=False,
                status=OrderStatus.FAILED,
                symbol="",
                side=OrderSide.BUY,
                requested_size_usd=0,
                failure_reason=f"Approval {approval_id} not found",
            )
        
        if approval.status != "PENDING":
            return ExecutionResult(
                request_id=approval.request_id,
                success=False,
                status=OrderStatus.FAILED,
                symbol=approval.symbol,
                side=approval.side,
                requested_size_usd=approval.size_usd,
                failure_reason=f"Approval already processed: {approval.status}",
            )
        
        # Check expiry
        if datetime.now(timezone.utc) > approval.expires_at:
            approval.status = "EXPIRED"
            return ExecutionResult(
                request_id=approval.request_id,
                success=False,
                status=OrderStatus.EXPIRED,
                symbol=approval.symbol,
                side=approval.side,
                requested_size_usd=approval.size_usd,
                failure_reason="Approval expired",
            )
        
        # Update approval
        approval.status = "APPROVED"
        approval.approved_by = approved_by
        approval.decision_at = datetime.now(timezone.utc)
        approval.approved_size_usd = approved_size_usd or approval.size_usd
        
        # Get order and execute
        order = self._orders.get(approval.order_id)
        if not order:
            return ExecutionResult(
                request_id=approval.request_id,
                success=False,
                status=OrderStatus.FAILED,
                symbol=approval.symbol,
                side=approval.side,
                requested_size_usd=approval.size_usd,
                failure_reason="Order not found",
            )
        
        # Adjust size if modified
        if approved_size_usd and approved_size_usd != approval.size_usd:
            price = await self._get_price(order.symbol)
            order.size_quote = approved_size_usd
            order.size_base = approved_size_usd / price
        
        # Execute (paper mode for safety)
        return await self._execute_paper(order)
    
    async def reject_order(self, approval_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a pending order."""
        approval = self._pending_approvals.get(approval_id)
        
        if not approval or approval.status != "PENDING":
            return False
        
        approval.status = "REJECTED"
        approval.approved_by = rejected_by
        approval.decision_at = datetime.now(timezone.utc)
        
        # Update order
        order = self._orders.get(approval.order_id)
        if order:
            order.status = OrderStatus.REJECTED
        
        return True
    
    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """Get all pending approvals."""
        return [a for a in self._pending_approvals.values() if a.status == "PENDING"]
    
    # ═══════════════════════════════════════════════════════════
    # 8. State Management
    # ═══════════════════════════════════════════════════════════
    
    def get_order(self, order_id: str) -> Optional[ExecutionOrder]:
        """Get order by ID."""
        return self._orders.get(order_id)
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[ExecutionOrder]:
        """Get all orders, optionally filtered by status."""
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return orders
    
    def get_fill(self, fill_id: str) -> Optional[ExecutionFill]:
        """Get fill by ID."""
        return self._fills.get(fill_id)
    
    def get_fills(self, order_id: Optional[str] = None) -> List[ExecutionFill]:
        """Get all fills, optionally filtered by order."""
        fills = list(self._fills.values())
        if order_id:
            fills = [f for f in fills if f.order_id == order_id]
        return fills
    
    def get_daily_stats(self) -> Dict:
        """Get daily execution statistics."""
        return {
            "daily_volume_usd": round(self._daily_volume, 2),
            "daily_loss_usd": round(self._daily_loss, 2),
            "order_count": len(self._orders),
            "fill_count": len(self._fills),
            "pending_approvals": len(self.get_pending_approvals()),
            "last_reset": self._last_reset.isoformat(),
        }
    
    def get_config(self) -> GatewayConfig:
        """Get current config."""
        return self._config
    
    def set_execution_mode(self, mode: ExecutionMode):
        """Set execution mode."""
        self._config.execution_mode = mode


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_gateway_engine: Optional[ExecutionGatewayEngine] = None


def get_execution_gateway() -> ExecutionGatewayEngine:
    """Get singleton instance."""
    global _gateway_engine
    if _gateway_engine is None:
        _gateway_engine = ExecutionGatewayEngine()
    return _gateway_engine
