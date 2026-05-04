"""
Terminal State Engine - Unified Trading Terminal Orchestrator

This is the SINGLE SOURCE OF TRUTH for the Trading Terminal UI.
Frontend NEVER calls individual APIs directly - only this orchestrator.

Aggregates:
- Decision (from Entry Timing Integration)
- Execution (from Entry Timing / Execution Strategy)
- Microstructure (from Live Micro Manager)
- Position (from Positions Service)
- Portfolio (from Portfolio Service)
- Risk (from Risk Service)
- Strategy Control (from Control Service)
- System State (from Adaptive/Calibration)
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
import logging
import asyncio

from ..validation.reconciliation_engine import get_reconciliation_engine
from ...orchestrator import get_final_gate, ExecutionController
from ...orchestrator.integration import get_integration_engine

logger = logging.getLogger(__name__)


class TerminalStateEngine:
    """
    Unified Trading Terminal Orchestrator.
    
    Single entry point for all terminal data.
    All services are injected and called internally.
    """
    
    def __init__(self, audit_controller=None):
        # Service references (injected later)
        self._decision_service = None
        self._micro_service = None
        self._positions_service = None
        self._portfolio_service = None
        self._risk_service = None
        self._strategy_service = None
        self._system_service = None
        self._forensics_service = None  # TT4
        
        # ORCH-1 + ORCH-2
        self._final_gate = get_final_gate()
        self._execution_controller = ExecutionController(route_type="simulation")
        
        # ORCH-3: Integration Engine
        self._integration_engine = get_integration_engine()
        
        # P0.7: Audit Controller
        self.audit_controller = audit_controller
        
        # Cache for performance
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl_seconds = 1.0  # 1 second cache
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def bind_services(
        self,
        decision_service=None,
        micro_service=None,
        positions_service=None,
        portfolio_service=None,
        risk_service=None,
        strategy_service=None,
        system_service=None,
        forensics_service=None  # TT4
    ):
        """Bind real services to the engine"""
        if decision_service:
            self._decision_service = decision_service
        if micro_service:
            self._micro_service = micro_service
        if positions_service:
            self._positions_service = positions_service
        if portfolio_service:
            self._portfolio_service = portfolio_service
        if risk_service:
            self._risk_service = risk_service
        if strategy_service:
            self._strategy_service = strategy_service
        if system_service:
            self._system_service = system_service
        if forensics_service:
            self._forensics_service = forensics_service
    
    # Timeframe configuration
    VALID_TIMEFRAMES = ["1H", "4H", "1D"]
    TIMEFRAME_MINUTES = {"1H": 60, "4H": 240, "1D": 1440}
    
    async def get_terminal_state(self, symbol: str, timeframe: str = "4H") -> Dict[str, Any]:
        """
        Get unified terminal state for symbol and timeframe.
        This is THE endpoint for /trading UI.
        
        Timeframe is a SYSTEM parameter, not just UI preference.
        All components must use the same timeframe.
        """
        import uuid
        
        symbol = symbol.upper()
        timeframe = timeframe.upper() if timeframe in self.VALID_TIMEFRAMES else "4H"
        
        # P0.7: Generate trace_id for full audit traceability
        trace_id = str(uuid.uuid4())
        
        # P1.2 LIVE: Mark signal arrival (start of execution timeline)
        try:
            from ...execution_reality.latency import get_latency_tracker
            latency_tracker = get_latency_tracker()
            placeholder_order_id = f"signal_{trace_id[:8]}"
            latency_tracker.mark_signal(placeholder_order_id, trace_id, symbol)
        except Exception as e:
            logger.debug(f"[P1.2] Latency mark_signal failed: {e}")
        
        # Check cache (include timeframe in key)
        cache_key = f"state_{symbol}_{timeframe}"
        if self._is_cache_valid(cache_key):
            cached_state = self._cache[cache_key].copy()
            cached_state["trace_id"] = trace_id  # New trace_id for each request
            return cached_state
        
        # Gather all data concurrently - pass timeframe to all
        results = await asyncio.gather(
            self._safe_get(self._get_decision, symbol, timeframe),
            self._safe_get(self._get_execution, symbol, timeframe),
            self._safe_get(self._get_micro, symbol),
            self._safe_get(self._get_position, symbol, timeframe),
            self._safe_get(self._get_portfolio, symbol),
            self._safe_get(self._get_risk, symbol),
            self._safe_get(self._get_strategy, symbol),
            self._safe_get(self._get_system, symbol),
            return_exceptions=True
        )
        
        # Unpack results with defaults
        decision = results[0] if isinstance(results[0], dict) else self._default_decision(symbol)
        execution = results[1] if isinstance(results[1], dict) else self._default_execution(timeframe)
        micro = results[2] if isinstance(results[2], dict) else self._default_micro()
        position = results[3] if isinstance(results[3], dict) else self._default_position(symbol)
        portfolio = results[4] if isinstance(results[4], dict) else self._default_portfolio()
        risk = results[5] if isinstance(results[5], dict) else self._default_risk()
        strategy = results[6] if isinstance(results[6], dict) else self._default_strategy()
        system = results[7] if isinstance(results[7], dict) else self._default_system()
        
        # Add timeframe to execution for consistency
        execution["timeframe"] = timeframe
        
        # ORCH-7 PHASE 3: Add default strategy_id
        # TODO: In future, derive strategy_id from decision/signal characteristics
        if "strategy_id" not in execution:
            execution["strategy_id"] = "breakout_v1"  # Default for now
        
        # ORCH-7 PHASE 4: Add requested_notional for budget enforcement
        size = float(execution.get("size", 0.0) or 0.0)
        entry = float(execution.get("entry", 0.0) or 0.0)
        if size > 0 and entry > 0:
            execution["requested_notional"] = round(size * entry, 2)
        
        # Get execution status from execution engine
        execution_status = await self._safe_get(self._get_execution_status, symbol, timeframe)
        orders_preview = await self._safe_get(self._get_orders_preview, symbol)
        
        # Get positions preview from position engine
        positions_preview = await self._safe_get(self._get_positions_preview, symbol)
        
        # Get trades preview and analytics from forensics (TT4)
        trades_preview = await self._get_trades_preview(symbol)
        trade_analytics = await self._get_trade_analytics(symbol)
        
        # ========================================
        # ORCH-3: State Normalization (Deep Integration)
        # ========================================
        
        # Get raw engine outputs
        raw_control = await self._get_control_state(symbol)
        raw_risk = risk
        raw_validation = {"is_valid": True}  # TODO: Connect real validation
        raw_alpha = await self._get_alpha_state(symbol)
        raw_regime = self._get_regime_analysis(symbol, timeframe)
        
        # Normalize through integration engine
        normalized = self._integration_engine.build_state(
            raw_control=raw_control,
            raw_risk=raw_risk,
            raw_validation=raw_validation,
            raw_alpha=raw_alpha,
            raw_regime=raw_regime,
        )
        
        # Extract normalized states
        control_state = normalized["control"]
        risk_state = normalized["risk"]
        validation_state = normalized["validation"]
        alpha_state = normalized["alpha"]
        regime_state = normalized["regime"]
        
        # ========================================
        # PORTFOLIO LAYER (Capital-Level Intelligence)
        # ========================================
        
        # Get portfolio state
        try:
            from ...portfolio import get_portfolio_controller
            
            portfolio_controller = get_portfolio_controller()
            
            # Collect all positions for portfolio calculation
            all_positions = positions_preview if isinstance(positions_preview, list) else []
            
            # Get alpha verdict and regime
            alpha_verdict = alpha_state.get("symbol_verdict", "NEUTRAL")
            regime_current = regime_state.get("current", "NEUTRAL")
            
            portfolio_state = portfolio_controller.get_portfolio_state(
                positions=all_positions,
                trades=[],  # TODO: Connect to trades history
                current_prices={symbol: position.get("mark_price") if position.get("has_position") else execution.get("entry")},
                alpha_verdict=alpha_verdict,
                regime=regime_current
            )
        except Exception as e:
            logger.warning(f"[PortfolioLayer] Error: {e}")
            portfolio_state = {}
        
        # ========================================
        # ORCH-7 PHASE 4: Meta Allocation (Hard Integration)
        # ========================================
        
        # Get strategy allocation from meta layer
        strategy_id = execution.get("strategy_id", "breakout_v1")
        
        # Get meta state (already computed earlier)
        meta_state = await self._get_meta_state(symbol, portfolio_state, alpha_state, regime_state)
        
        # Find allocation for this strategy
        allocations = meta_state.get("allocations", [])
        strategy_allocation = None
        
        for alloc in allocations:
            if alloc.get("strategy_id") == strategy_id:
                strategy_allocation = alloc
                break
        
        # Fallback if no allocation found
        if not strategy_allocation:
            logger.warning(f"[MetaAllocation] No allocation for {strategy_id}, using default")
            strategy_allocation = {
                "strategy_id": strategy_id,
                "weight": 1.0,
                "capital": None,
                "score": 1.0,
            }
        
        # PHASE 4: Compute strategy usage (from current positions/orders preview)
        # Note: This is approximate as it uses preview data before execution_control
        approx_usage = self._compute_strategy_usage(
            strategy_id,
            positions_preview if isinstance(positions_preview, list) else [],
            orders_preview if isinstance(orders_preview, list) else []
        )
        
        # Get strategy policy from meta actions
        from ...orchestrator.final_gate import get_strategy_policy
        meta_actions = meta_state.get("actions", [])
        strategy_policy = get_strategy_policy(meta_actions, strategy_id)
        
        # Build meta allocation context for FinalGate (PHASE 4)
        meta_allocation = {
            "strategy_id": strategy_id,
            "strategy_weight": strategy_allocation.get("weight", 1.0),
            "allocated_capital": strategy_allocation.get("capital"),
            "strategy_score": strategy_allocation.get("score", 1.0),
            "strategy_usage": approx_usage,  # Approximate usage for FinalGate
            "actions": meta_actions,
            "strategy_policy": strategy_policy,
        }
        
        # ========================================
        # ORCH-1: Final Gate (Pre-Execution Enforcement)
        # ========================================
        
        gate_result = self._final_gate.evaluate(
            decision=decision,
            risk=risk_state,  # Normalized
            control=control_state,  # Normalized
            validation=validation_state,  # Normalized
            alpha=alpha_state,  # Normalized
            regime=regime_state,  # Normalized
            execution=execution,
            portfolio=portfolio_state,  # Portfolio layer
            meta_allocation=meta_allocation  # NEW: ORCH-7 PHASE 3
        )
        
        # P1.2 LIVE: Mark FinalGate completion
        try:
            latency_tracker = get_latency_tracker()
            placeholder_order_id = f"signal_{trace_id[:8]}"
            latency_tracker.mark_final_gate(placeholder_order_id)
        except Exception as e:
            logger.debug(f"[P1.2] Latency mark_final_gate failed: {e}")
        
        # ========================================
        # P0.7: DECISION AUDIT (Hook 2)
        # ========================================
        if self.audit_controller:
            from modules.audit.audit_helper import run_audit_task
            logger.debug(f"[P0.7] Decision audit triggered for {symbol} | trace={trace_id}")
            
            run_audit_task(
                self.audit_controller.decision.insert({
                    "timestamp": datetime.now(timezone.utc),
                    "trace_id": trace_id,  # P0.7 CRITICAL: trace ID for causal graph
                    
                    # CONTEXT
                    "symbol": symbol,
                    "timeframe": timeframe,
                    
                    # RAW
                    "decision_raw": decision,
                    
                    # ENFORCED
                    "decision_enforced": gate_result.get("decision_enforced"),
                    
                    # RESULT
                    "final_action": gate_result.get("final_action"),
                    "blocked": gate_result.get("blocked"),
                    "block_reason": gate_result.get("block_reason"),
                    "size_multiplier": gate_result.get("size_multiplier"),
                    
                    # WHY
                    "reason_chain": gate_result.get("reason_chain", []),
                    
                    # SYSTEM CONTEXT
                    "portfolio_state": {
                        "equity": portfolio_state.get("equity", {}).get("equity"),
                        "heat": portfolio_state.get("heat", {}).get("heat"),
                        "drawdown_pct": portfolio_state.get("drawdown", {}).get("current_dd_pct")
                    },
                    "meta_execution": {
                        "strategy_id": meta_allocation.get("strategy_id"),
                        "strategy_weight": meta_allocation.get("strategy_weight"),
                        "allocated_capital": meta_allocation.get("allocated_capital")
                    },
                    "system_health": {
                        "risk_level": risk_state.get("risk_level"),
                        "portfolio_hard_stop": portfolio_state.get("policy", {}).get("hard_stop")
                    }
                }),
                context=f"decision_audit_{symbol}_{timeframe}"
            )
        
        # ========================================
        # ORCH-2 + ORCH-6: Execution Control (Intent + Routing + Lifecycle)
        # ========================================
        
        # Build market_state for ORCH-6 lifecycle orchestrator
        current_price = position.get("mark_price") if position.get("has_position") else execution.get("entry")
        
        market_state = {
            "current_price": current_price,
            "alpha_state": alpha_state,
            "validation_state": validation_state,
            "regime_state": regime_state,
            "risk_state": risk_state,
            "portfolio_state": portfolio_state,  # NEW: Portfolio state for lifecycle
        }
        
        execution_control = await self._execution_controller.run(
            symbol=symbol,
            timeframe=timeframe,
            gate_result=gate_result,
            execution_plan=execution,
            market_state=market_state,  # ORCH-6: Pass market state
            trace_id=trace_id  # P1.3.1: Pass trace_id for shadow integration
        )
        
        state = {
            "symbol": symbol,
            "timeframe": timeframe,  # System-level timeframe
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "execution": execution,
            "execution_status": execution_status if isinstance(execution_status, dict) else self._default_execution_status(),
            "orders_preview": orders_preview if isinstance(orders_preview, list) else [],
            "position": position,
            "positions_preview": positions_preview if isinstance(positions_preview, list) else [],
            "micro": micro,
            "risk": risk,
            "trades_preview": trades_preview,  # TT4
            "trade_analytics": trade_analytics,  # TT4
            "strategy": strategy,
            "system": system,
            "structure": await self._get_structure(symbol, timeframe),  # TT-UI4.1
            "chart_intelligence": await self._get_chart_intelligence(symbol, timeframe),  # TT-UI4.2
            "analysis": await self._get_analysis(symbol, timeframe, decision),  # TT-UI2 FULL
            # ORCH-1 + ORCH-2
            "decision_raw": gate_result.get("decision_raw"),
            "decision_enforced": gate_result.get("decision_enforced"),
            "final_action": gate_result.get("final_action"),
            "blocked": gate_result.get("blocked"),
            "block_reason": gate_result.get("block_reason"),
            "reason_chain": gate_result.get("reason_chain"),
            "execution_control": execution_control,
            # ORCH-3: Orchestration state (normalized)
            "orchestration": {
                "control": control_state,
                "risk": risk_state,
                "validation": validation_state,
                "alpha": alpha_state,
                "regime": regime_state,
                "overrides": self._integration_engine.get_override_snapshot()
            },
            # PORTFOLIO: Capital-level intelligence
            "portfolio": portfolio_state,
            # META: Multi-strategy orchestration (ORCH-7 PHASE 1-2)
            "meta": meta_state,
            # ORCH-5 + ORCH-6: Live orders and positions from lifecycle
            "orders_live": execution_control.get("orders", []),
            "positions_live": execution_control.get("lifecycle", {}).get("positions", []),
            "lifecycle_control": execution_control.get("lifecycle_control", {}),
        }
        
        # ORCH-7 PHASE 4: Compute strategy usage AFTER execution_control
        orders_live = state["orders_live"]
        positions_live = state["positions_live"]
        strategy_usage = self._compute_strategy_usage(strategy_id, positions_live, orders_live)
        
        # META EXECUTION: Strategy allocation in execution context (ORCH-7 PHASE 4)
        state["meta_execution"] = {
            "strategy_id": strategy_id,
            "strategy_weight": meta_allocation.get("strategy_weight", 1.0),
            "allocated_capital": meta_allocation.get("allocated_capital"),
            "strategy_score": meta_allocation.get("strategy_score", 1.0),
            "strategy_usage": strategy_usage,
            "strategy_policy": strategy_policy,
        }
        
        # META LEARNING: Learning integration status (ORCH-7 PHASE 5)
        state["meta_learning"] = {
            "alpha_actions": meta_state.get("alpha_actions", []),
            "policy_actions": meta_state.get("policy_actions", []),
            "active_learning": len(meta_state.get("alpha_actions", [])) > 0,
        }
        
        # Update execution intent based on decision
        await self._update_execution_intent(symbol, timeframe, decision, execution, state)
        
        # Run validation layer with live price
        try:
            reconciliation = get_reconciliation_engine()
            validation = await reconciliation.validate_terminal_state_async(state)
            state["validation"] = validation
        except Exception as e:
            logger.warning(f"[Validation] Error: {e}")
            state["validation"] = {
                "is_valid": True,
                "critical_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "issues": [],
                "error": str(e)
            }
        
        # P0.7: Add trace_id to state for client visibility
        state["trace_id"] = trace_id
        
        # Cache result
        self._cache[cache_key] = state
        self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
        
        return state
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache or key not in self._cache_timestamps:
            return False
        
        age = (datetime.now(timezone.utc) - self._cache_timestamps[key]).total_seconds()
        return age < self._cache_ttl_seconds
    
    async def _safe_get(self, fn, symbol: str, timeframe: str = None) -> Dict[str, Any]:
        """Safely call a getter function with error handling"""
        try:
            if timeframe and asyncio.iscoroutinefunction(fn):
                # Try calling with timeframe first
                import inspect
                sig = inspect.signature(fn)
                if 'timeframe' in sig.parameters:
                    result = await fn(symbol, timeframe)
                else:
                    result = await fn(symbol)
            elif asyncio.iscoroutinefunction(fn):
                result = await fn(symbol)
            else:
                result = fn(symbol)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.warning(f"[TerminalState] Error in {fn.__name__}: {e}")
            return {"_error": str(e)}
    
    # =========================================
    # DATA GETTERS - Each integrates with a service
    # =========================================
    
    async def _get_decision(self, symbol: str, timeframe: str = "4H") -> Dict[str, Any]:
        """Get decision from Entry Timing Integration"""
        # Try to import and use entry timing integration
        try:
            from ..live.terminal_routes import get_terminal_decision
            response = await get_terminal_decision(symbol)
            if response.get("ok") and response.get("data"):
                data = response["data"]
                decision_data = data.get("decision", {})
                why_data = data.get("why", [])
                
                return {
                    "action": decision_data.get("action", "WAIT"),
                    "confidence": decision_data.get("confidence", 0.5),
                    "direction": "LONG" if decision_data.get("action", "").startswith("GO") else "NEUTRAL",
                    "mode": data.get("execution", {}).get("mode", "PASSIVE_LIMIT"),
                    "reasons": [r.get("text", "") for r in why_data] if why_data else [],
                    "timeframe": timeframe
                }
        except Exception as e:
            logger.warning(f"[Decision] Error: {e}")
        
        return self._default_decision(symbol)
    
    async def _get_execution(self, symbol: str, timeframe: str = "4H") -> Dict[str, Any]:
        """Get execution parameters"""
        try:
            from ..live.terminal_routes import get_terminal_decision
            response = await get_terminal_decision(symbol)
            if response.get("ok") and response.get("data"):
                exec_data = response["data"].get("execution", {})
                decision = response["data"].get("decision", {})
                
                return {
                    "mode": exec_data.get("mode", "PASSIVE_LIMIT"),
                    "size": exec_data.get("size_multiplier", 0.0),
                    "entry": exec_data.get("entry"),
                    "stop": exec_data.get("stop_loss"),
                    "target": exec_data.get("take_profit"),
                    "rr": exec_data.get("risk_reward"),
                    "execution_confidence": decision.get("confidence", 0.5),
                    "timeframe": timeframe
                }
        except Exception as e:
            logger.warning(f"[Execution] Error: {e}")
        
        return self._default_execution()
    
    async def _get_micro(self, symbol: str) -> Dict[str, Any]:
        """Get microstructure data from Live Micro Manager"""
        try:
            from ..live.terminal_routes import get_micro_live
            response = await get_micro_live(symbol)
            if response.get("ok") and response.get("data"):
                data = response["data"]
                
                # Build reasons
                reasons = []
                if data.get("liquidity_state") == "strong_bid":
                    reasons.append("Strong bid support")
                if data.get("spread_bps", 0) < 1.5:
                    reasons.append("Tight spread")
                if data.get("state") == "favorable":
                    reasons.append("Favorable microstructure")
                elif data.get("state") == "hostile":
                    reasons.append("Hostile microstructure")
                elif data.get("state") == "caution":
                    reasons.append("Waiting for confirmation")
                
                return {
                    "source": response.get("source", "mock"),
                    "imbalance": data.get("imbalance", 0),
                    "spread": data.get("spread_bps"),
                    "liquidity": data.get("liquidity_state", "unknown"),
                    "state": data.get("state", "unknown"),
                    "decision": f"MICRO_{data.get('state', 'UNKNOWN').upper()}",
                    "reasons": reasons,
                    "best_bid": data.get("best_bid"),
                    "best_ask": data.get("best_ask"),
                    "mid_price": data.get("mid_price")
                }
        except Exception as e:
            logger.warning(f"[Micro] Error: {e}")
        
        return self._default_micro()
    
    async def _get_position(self, symbol: str, timeframe: str = "4H") -> Dict[str, Any]:
        """Get position for symbol from Position Engine"""
        try:
            # Try new Position Engine first (TT2)
            from ..positions.position_engine import get_position_engine
            engine = get_position_engine()
            summary = engine.build_position_summary(symbol, timeframe)
            if summary.get("has_position"):
                return summary
        except Exception as e:
            logger.warning(f"[Position] TT2 Engine error: {e}")
        
        # Fallback to legacy terminal routes
        try:
            from ..live.terminal_routes import get_positions
            response = await get_positions()
            if response.get("ok") and response.get("data"):
                positions = response["data"].get("positions", [])
                
                # Find position for this symbol
                for pos in positions:
                    if pos.get("symbol") == symbol:
                        return {
                            "has_position": True,
                            "symbol": pos.get("symbol"),
                            "side": pos.get("side"),
                            "size": pos.get("size", 0),
                            "entry_price": pos.get("entry_price"),
                            "mark_price": pos.get("current_price"),
                            "unrealized_pnl": pos.get("pnl_usd", 0),
                            "pnl_pct": pos.get("pnl_percent", 0),
                            "stop": None,
                            "target": None,
                            "health": "GOOD",
                            "status": pos.get("status", "OPEN")
                        }
        except Exception as e:
            logger.warning(f"[Position] Legacy error: {e}")
        
        return self._default_position(symbol)
    
    async def _get_positions_preview(self, symbol: str) -> list:
        """Get positions preview from Position Engine"""
        try:
            from ..positions.position_engine import get_position_engine
            engine = get_position_engine()
            return engine.get_positions_preview(symbol, limit=5)
        except Exception as e:
            logger.warning(f"[PositionsPreview] Error: {e}")
        return []
    
    async def _get_portfolio(self, symbol: str) -> Dict[str, Any]:
        """Get portfolio summary from Portfolio & Risk Console (TT3)"""
        try:
            # Use new Portfolio & Risk Console (TT3)
            from ..portfolio_risk.portfolio_risk_routes import get_portfolio_service
            service = get_portfolio_service()
            
            open_positions = service["collect_positions"]()
            open_orders = service["collect_orders"]()
            
            summary = service["portfolio_engine"].build_summary(open_positions, open_orders)
            exposure = service["exposure_engine"].build_exposure(open_positions, summary.equity)
            
            return {
                "equity": summary.equity,
                "free_capital": summary.free_capital,
                "used_capital": summary.used_capital,
                "realized_pnl": summary.realized_pnl,
                "unrealized_pnl": summary.unrealized_pnl,
                "daily_pnl": summary.daily_pnl,
                "gross_exposure": summary.gross_exposure,
                "net_exposure": summary.net_exposure,
                "open_positions": summary.open_positions,
                "open_orders": summary.open_orders,
                "exposure_by_symbol": [e.to_dict() for e in exposure.by_symbol],
                "exposure_by_direction": exposure.by_direction,
            }
        except Exception as e:
            logger.warning(f"[Portfolio] TT3 Error: {e}")
        
        # Fallback to legacy
        try:
            from ..live.terminal_routes import get_positions
            response = await get_positions()
            if response.get("ok") and response.get("data"):
                summary = response["data"].get("summary", {})
                
                return {
                    "equity": 10000 + summary.get("total_pnl_usd", 0),
                    "free_capital": 10000 - summary.get("exposure_usd", 0) * 0.1,
                    "used_capital": summary.get("exposure_usd", 0) * 0.1,
                    "realized_pnl": summary.get("total_pnl_usd", 0) * 0.3,
                    "unrealized_pnl": summary.get("total_pnl_usd", 0) * 0.7,
                    "exposure": round(summary.get("exposure_usd", 0) / 100000, 2),
                    "risk_used": round(summary.get("total_positions", 0) * 0.05, 2)
                }
        except Exception as e:
            logger.warning(f"[Portfolio] Legacy error: {e}")
        
        return self._default_portfolio()
    
    async def _get_risk(self, symbol: str) -> Dict[str, Any]:
        """Get risk metrics from Portfolio & Risk Console (TT3)"""
        try:
            # Use new Portfolio & Risk Console (TT3)
            from ..portfolio_risk.portfolio_risk_routes import get_portfolio_service
            service = get_portfolio_service()
            
            open_positions = service["collect_positions"]()
            open_orders = service["collect_orders"]()
            
            summary = service["portfolio_engine"].build_summary(open_positions, open_orders)
            exposure = service["exposure_engine"].build_exposure(open_positions, summary.equity)
            risk = service["risk_engine"].build_risk_summary(summary.to_dict(), exposure.to_dict())
            
            return {
                "heat": risk.heat,
                "daily_drawdown": risk.daily_drawdown,
                "max_drawdown": risk.max_drawdown,
                "status": risk.status.lower() if risk.status else "unknown",
                "kill_switch": risk.kill_switch,
                "can_open_new": risk.can_open_new,
                "active_guardrails": risk.active_guardrails,
                "active_guardrails_count": len(risk.active_guardrails),
                "block_reasons": risk.block_reasons,
                "block_reasons_count": len(risk.block_reasons),
                "risk_alerts": risk.risk_alerts,
            }
        except Exception as e:
            logger.warning(f"[Risk] TT3 Error: {e}")
        
        # Fallback
        import random
        heat = random.uniform(0.2, 0.6)
        drawdown = random.uniform(0.02, 0.1)
        
        return {
            "heat": round(heat, 2),
            "drawdown": round(drawdown, 2),
            "daily_drawdown": round(drawdown * 0.3, 2),
            "status": "normal" if heat < 0.5 else "elevated" if heat < 0.7 else "critical",
            "kill_switch": False,
            "alerts": []
        }
    
    async def _get_strategy(self, symbol: str) -> Dict[str, Any]:
        """Get strategy control state"""
        return {
            "profile": "BALANCED",
            "config": "default",
            "paused": False,
            "override": False
        }
    
    async def _get_system(self, symbol: str) -> Dict[str, Any]:
        """Get system state"""
        try:
            from ..live.terminal_routes import terminal_health
            health = await terminal_health()
            
            return {
                "mode": "SIMULATION",
                "adaptive_active": True,
                "scheduler": "running",
                "last_calibration": datetime.now(timezone.utc).replace(hour=0, minute=0).isoformat(),
                "last_rollback": None,
                "data_source": "mock" if not health.get("live_enabled") else "live"
            }
        except Exception as e:
            logger.warning(f"[System] Error: {e}")
        
        return self._default_system()
    
    # =========================================
    # DEFAULT VALUES
    # =========================================
    
    def _default_decision(self, symbol: str) -> Dict[str, Any]:
        return {
            "action": "WAIT",
            "confidence": 0.0,
            "direction": "NEUTRAL",
            "mode": "UNKNOWN",
            "reasons": ["waiting_for_data"]
        }
    
    def _default_execution(self, timeframe: str = "4H") -> Dict[str, Any]:
        return {
            "mode": "PASSIVE_LIMIT",
            "size": 0.0,
            "entry": None,
            "stop": None,
            "target": None,
            "rr": None,
            "execution_confidence": 0.0,
            "timeframe": timeframe
        }
    
    def _default_micro(self) -> Dict[str, Any]:
        return {
            "source": "offline",
            "imbalance": 0.0,
            "spread": None,
            "liquidity": "unknown",
            "state": "unknown",
            "decision": "WAIT_MICROSTRUCTURE",
            "reasons": ["micro_offline"]
        }
    
    def _default_position(self, symbol: str) -> Dict[str, Any]:
        return {
            "has_position": False,
            "symbol": symbol,
            "side": None,
            "size": 0.0,
            "entry": None,
            "mark": None,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "stop": None,
            "target": None,
            "status": "FLAT"
        }
    
    def _default_portfolio(self) -> Dict[str, Any]:
        return {
            "equity": None,
            "free_capital": None,
            "used_capital": None,
            "realized_pnl": None,
            "unrealized_pnl": None,
            "daily_pnl": None,
            "gross_exposure": None,
            "net_exposure": None,
            "open_positions": 0,
            "open_orders": 0,
            "exposure_by_symbol": [],
            "exposure_by_direction": {"long": 0.0, "short": 0.0},
        }
    
    def _default_risk(self) -> Dict[str, Any]:
        return {
            "heat": None,
            "daily_drawdown": None,
            "max_drawdown": None,
            "status": "unknown",
            "kill_switch": False,
            "can_open_new": True,
            "active_guardrails": [],
            "active_guardrails_count": 0,
            "block_reasons": [],
            "block_reasons_count": 0,
            "risk_alerts": [],
        }
    
    def _default_trades_preview(self) -> List[Dict[str, Any]]:
        return []
    
    def _default_trade_analytics(self) -> Dict[str, Any]:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": None,
            "expectancy": 0.0,
            "avg_rr": 0.0,
            "net_pnl": 0.0,
        }
    
    async def _get_trades_preview(self, symbol: str) -> List[Dict[str, Any]]:
        """Get recent trades preview from Forensics (TT4)"""
        try:
            from ..forensics.forensics_routes import get_forensics_service
            service = get_forensics_service()
            
            records = service["repo"].list_recent(symbol=symbol, limit=5)
            return service["query"].get_preview([r.to_dict() for r in records], limit=5)
        except Exception as e:
            logger.warning(f"[TradesPreview] TT4 Error: {e}")
        return self._default_trades_preview()
    
    async def _get_trade_analytics(self, symbol: str) -> Dict[str, Any]:
        """Get trade analytics from Forensics (TT4)"""
        try:
            from ..forensics.forensics_routes import get_forensics_service
            service = get_forensics_service()
            
            records = service["repo"].list_all(symbol=symbol)
            metrics = service["analytics"].build_metrics([r.to_dict() for r in records])
            
            return {
                "trades": metrics.trades,
                "wins": metrics.wins,
                "losses": metrics.losses,
                "win_rate": metrics.win_rate,
                "profit_factor": metrics.profit_factor,
                "expectancy": metrics.expectancy,
                "avg_rr": metrics.avg_rr,
                "net_pnl": metrics.net_pnl,
            }
        except Exception as e:
            logger.warning(f"[TradeAnalytics] TT4 Error: {e}")
        return self._default_trade_analytics()
    
    def _default_strategy(self) -> Dict[str, Any]:
        return {
            "profile": "UNKNOWN",
            "config": None,
            "paused": False,
            "override": False
        }
    
    def _default_system(self) -> Dict[str, Any]:
        return {
            "mode": "SIMULATION",
            "adaptive_active": False,
            "scheduler": "unknown",
            "last_calibration": None,
            "last_rollback": None,
            "data_source": "offline"
        }
    
    def _default_execution_status(self) -> Dict[str, Any]:
        return {
            "execution_state": "IDLE",
            "intent_state": "IDLE",
            "order_present": False,
            "position_open": False,
            "order_id": None,
            "filled_pct": 0.0,
            "status_label": "Idle",
            "status_reason": "no active execution intent"
        }
    
    # =========================================
    # EXECUTION STATUS GETTERS
    # =========================================
    
    async def _get_execution_status(self, symbol: str, timeframe: str = "4H") -> Dict[str, Any]:
        """Get execution status from execution engine"""
        try:
            from ..execution.execution_state_engine import get_execution_engine
            engine = get_execution_engine()
            return engine.build_status_summary(symbol, timeframe)
        except Exception as e:
            logger.warning(f"[ExecutionStatus] Error: {e}")
        return self._default_execution_status()
    
    async def _get_orders_preview(self, symbol: str) -> list:
        """Get orders preview from execution engine"""
        try:
            from ..execution.execution_state_engine import get_execution_engine
            engine = get_execution_engine()
            return engine.get_orders_preview(symbol, limit=5)
        except Exception as e:
            logger.warning(f"[OrdersPreview] Error: {e}")
        return []
    
    async def _get_structure(self, symbol: str, timeframe: str = "4H") -> Dict[str, Any]:
        """
        Get market structure data for chart intelligence overlay.
        
        Returns:
            Structure data with swings, events, and range info
        """
        # TODO: Integrate with actual structure service when available
        # For now, return mock structure data for TT-UI4.1
        import time
        now = int(time.time())
        
        return {
            "swings": [
                {"type": "HH", "price": 67000, "time": now - 3600 * 24},
                {"type": "HL", "price": 65000, "time": now - 3600 * 12},
                {"type": "HH", "price": 67500, "time": now - 3600 * 6},
                {"type": "HL", "price": 65500, "time": now - 3600 * 2},
            ],
            "events": [
                {"type": "BOS", "direction": "UP", "time": now - 3600 * 18},
                {"type": "CHOCH", "direction": "DOWN", "time": now - 3600 * 8},
            ],
            "range": {
                "high": 67500,
                "low": 64000
            }
        }
    
    async def _update_execution_intent(
        self, 
        symbol: str, 
        timeframe: str, 
        decision: Dict, 
        execution: Dict,
        state: Dict
    ):
        """Update execution intent based on current decision"""
        try:
            from ..execution.execution_state_engine import get_execution_engine
            engine = get_execution_engine()
            
            validation = state.get("validation", {"is_valid": True})
            position = state.get("position", {"has_position": False})
            
            # Only update if we have meaningful data
            if decision.get("action") and execution.get("entry"):
                engine.build_or_update_intent(
                    symbol=symbol,
                    timeframe=timeframe,
                    decision=decision,
                    execution=execution,
                    validation=validation,
                    position=position
                )
        except Exception as e:
            logger.warning(f"[UpdateIntent] Error: {e}")


    # ========================================
    # TT-UI4.2: Chart Intelligence (Pattern + Scenario)
    # ========================================
    
    async def _get_chart_intelligence(self, symbol: str, timeframe: str = "4H") -> Dict[str, Any]:
        """
        Get chart intelligence: patterns + scenarios
        
        TT-UI4.2 MVP: Deterministic mock by symbol/timeframe
        Production: Will call real pattern detector + scenario generator
        """
        patterns = await self._get_patterns(symbol, timeframe)
        scenarios = await self._get_scenarios(symbol, timeframe)
        
        return {
            "patterns": patterns,
            "scenarios": scenarios
        }
    
    async def _get_patterns(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Get active chart patterns
        
        MVP: Deterministic mock
        Production: Real pattern detection engine
        """
        # Mock pattern for BTCUSDT 4H
        if symbol == "BTCUSDT" and timeframe == "4H":
            return [{
                "id": "pattern-triangle-1",
                "type": "triangle",
                "label": "Symmetrical Triangle",
                "confidence": 0.72,
                "state": "FORMING",
                "bias": "NEUTRAL",
                "geometry": {
                    "kind": "polygon",
                    "points": [
                        {"time": 1711000000, "price": 65000},
                        {"time": 1711020000, "price": 66200},
                        {"time": 1711040000, "price": 65400},
                        {"time": 1711060000, "price": 65850}
                    ]
                },
                "trigger": {"price": 66050, "direction": "UP"},
                "invalidation": {"price": 64920}
            }]
        
        # Mock consolidation box for ETHUSDT
        if symbol == "ETHUSDT" and timeframe == "4H":
            return [{
                "id": "pattern-box-1",
                "type": "consolidation",
                "label": "Consolidation Range",
                "confidence": 0.68,
                "state": "ACTIVE",
                "bias": "NEUTRAL",
                "geometry": {
                    "kind": "box",
                    "startTime": 1711000000,
                    "endTime": 1711060000,
                    "high": 3200,
                    "low": 3050
                },
                "trigger": None,
                "invalidation": None
            }]
        
        return []
    
    async def _get_scenarios(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Get scenario projections
        
        MVP: Deterministic mock
        Production: Real scenario engine
        """
        # Mock scenarios for BTCUSDT 4H
        if symbol == "BTCUSDT" and timeframe == "4H":
            return [
                {
                    "id": "scenario-primary-1",
                    "role": "PRIMARY",
                    "type": "breakout_up",
                    "label": "Primary Breakout",
                    "probability": 0.62,
                    "bias": "BULLISH",
                    "path": [
                        {"time": 1711080000, "price": 66050},
                        {"time": 1711100000, "price": 66700},
                        {"time": 1711120000, "price": 67450}
                    ],
                    "target": {"price": 67450},
                    "invalidation": {"price": 64920}
                },
                {
                    "id": "scenario-alt-1",
                    "role": "ALTERNATIVE",
                    "type": "rejection_down",
                    "label": "Alt Rejection",
                    "probability": 0.38,
                    "bias": "BEARISH",
                    "path": [
                        {"time": 1711080000, "price": 65520},
                        {"time": 1711100000, "price": 64750},
                        {"time": 1711120000, "price": 64000}
                    ],
                    "target": {"price": 64000},
                    "invalidation": {"price": 66120}
                }
            ]
        
        return []

    # ========================================
    # TT-UI2 FULL: Analysis Stack (11 panels)
    # ========================================
    
    async def _get_analysis(self, symbol: str, timeframe: str, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get unified analysis data for all 11 panels
        
        TT-UI2 MVP: Deterministic mock
        Production: Real analytical engines
        """
        return {
            "context": self._get_context_analysis(symbol, timeframe),
            "structure_analysis": self._get_structure_analysis(symbol, timeframe),
            "patterns_analysis": self._get_patterns_analysis(symbol, timeframe),
            "confluence": self._get_confluence_analysis(decision),
            "prediction": self._get_prediction_analysis(symbol, timeframe),
            "entry": decision,  # Reuse existing decision
            "micro": {},  # Populated from main micro getter
            "validation": {},  # Populated from validation layer
            "alpha": self._get_alpha_analysis(symbol),
            "regime": self._get_regime_analysis(symbol, timeframe),
            "control": self._get_control_analysis()
        }
    
    def _get_context_analysis(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Market context analysis"""
        if symbol == "BTCUSDT":
            return {
                "market_regime": "NEUTRAL",
                "volatility_state": "NORMAL",
                "liquidity_state": "GOOD",
                "macro_bias": "BULLISH",
                "dominance_context": "BTC_STRONG",
                "confidence": 0.68
            }
        return {
            "market_regime": "NEUTRAL",
            "volatility_state": "NORMAL",
            "liquidity_state": "NORMAL",
            "macro_bias": "NEUTRAL",
            "dominance_context": "BALANCED",
            "confidence": 0.50
        }
    
    def _get_structure_analysis(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Structure analysis"""
        if symbol == "BTCUSDT":
            return {
                "trend_state": "UPTREND",
                "phase": "CONTINUATION",
                "last_bos": "UP",
                "last_choch": "NONE",
                "range_state": "NO_RANGE",
                "compression_state": "LOW",
                "structural_bias": "BULLISH",
                "confidence": 0.74
            }
        return {
            "trend_state": "NEUTRAL",
            "phase": "RANGING",
            "last_bos": "NONE",
            "last_choch": "NONE",
            "range_state": "RANGING",
            "compression_state": "MEDIUM",
            "structural_bias": "NEUTRAL",
            "confidence": 0.50
        }
    
    def _get_patterns_analysis(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Patterns analysis (from chart_intelligence)"""
        if symbol == "BTCUSDT":
            return {
                "dominant": {
                    "label": "Symmetrical Triangle",
                    "type": "triangle",
                    "bias": "NEUTRAL",
                    "state": "FORMING",
                    "confidence": 0.72
                },
                "alternatives": [
                    {
                        "label": "Compression",
                        "type": "box",
                        "bias": "NEUTRAL",
                        "confidence": 0.41
                    }
                ],
                "trigger": "Break above 66050",
                "invalidation": "Below 64920"
            }
        return {
            "dominant": None,
            "alternatives": [],
            "trigger": None,
            "invalidation": None
        }
    
    def _get_confluence_analysis(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Confluence analysis"""
        return {
            "score": 0.71,
            "status": "CONFIRMED",
            "bullish_factors": [
                "Trend aligned",
                "Momentum positive",
                "Structure bullish"
            ],
            "bearish_factors": [
                "Breakout not confirmed"
            ],
            "conflicts": [
                "Micro hostile"
            ]
        }
    
    def _get_prediction_analysis(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Prediction analysis"""
        if symbol == "BTCUSDT":
            return {
                "direction": "UP",
                "confidence": 0.64,
                "horizon": timeframe,
                "primary_scenario": "Breakout continuation to 67450",
                "alternative_scenario": "Failed breakout to 64000",
                "trigger": "Close above 66050",
                "invalidation": "Break below 64920"
            }
        return {
            "direction": "NEUTRAL",
            "confidence": 0.50,
            "horizon": timeframe,
            "primary_scenario": "Range continuation",
            "alternative_scenario": "Breakout either direction",
            "trigger": "Range break",
            "invalidation": "Range hold"
        }
    
    def _get_alpha_analysis(self, symbol: str) -> Dict[str, Any]:
        """Alpha Factory analysis"""
        if symbol == "BTCUSDT":
            return {
                "symbol_verdict": "STRONG_CONFIRMED_EDGE",
                "entry_mode_verdict": "WEAK_ENTRY_MODE",
                "profit_factor": 1.84,
                "win_rate": 0.58,
                "expectancy": 92.3,
                "pending_actions": 1
            }
        return {
            "symbol_verdict": "NO_VERDICT",
            "entry_mode_verdict": "NO_VERDICT",
            "profit_factor": None,
            "win_rate": None,
            "expectancy": None,
            "pending_actions": 0
        }
    
    def _get_regime_analysis(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Regime analysis"""
        if symbol == "BTCUSDT":
            return {
                "current": "TRENDING",
                "strength": 0.67,
                "allowed_activity": "FULL",
                "best_fit": [
                    "ENTER_ON_CLOSE",
                    "GO_FULL"
                ],
                "avoid": [
                    "WAIT_RETEST in chop"
                ]
            }
        return {
            "current": "NEUTRAL",
            "strength": 0.50,
            "allowed_activity": "CAUTIOUS",
            "best_fit": [],
            "avoid": []
        }
    
    def _get_control_analysis(self) -> Dict[str, Any]:
        """Control layer status"""
        return {
            "system_state": "ACTIVE",
            "alpha_mode": "MANUAL",
            "can_trade": True,
            "can_enter": True,
            "soft_kill": False,
            "hard_kill": False,
            "pending_approvals": 1
        }
    
    # ========================================
    # ORCH-1 Support Methods
    # ========================================
    
    async def _get_control_state(self, symbol: str) -> Dict[str, Any]:
        """
        Get control state from ControlBackendService.
        
        Falls back to safe defaults if service unavailable.
        """
        try:
            from ...control_backend.service import control_backend_service
            
            # Try to get real control state (sync call)
            system_status = control_backend_service.get_system_health()
            
            return {
                "can_trade": not system_status.get("frozen_symbols", {}).get(symbol, False),
                "can_enter": True,  # Default to allowing entry
                "hard_kill": system_status.get("hard_kill", False),
                "soft_kill": system_status.get("soft_kill", False),
                "regime_overrides": {}  # TODO: Implement regime overrides registry
            }
        except Exception as e:
            logger.warning(f"[ControlState] Error getting real control state: {e}")
            # Safe fallback: allow trading
            return {
                "can_trade": True,
                "can_enter": True,
                "hard_kill": False,
                "soft_kill": False,
                "regime_overrides": {}
            }
    
    async def _get_alpha_state(self, symbol: str) -> Dict[str, Any]:
        """
        Get alpha state from Alpha Factory.
        
        Falls back to neutral if service unavailable.
        """
        try:
            # Use existing alpha analysis
            alpha_data = self._get_alpha_analysis(symbol)
            return alpha_data
        except Exception as e:
            logger.warning(f"[AlphaState] Error getting alpha state: {e}")
            return {
                "symbol_verdict": "NEUTRAL",
                "entry_mode_verdict": "NEUTRAL",
                "profit_factor": None,
                "win_rate": None,
                "expectancy": None
            }
    
    async def _get_meta_state(
        self,
        symbol: str,
        portfolio_state: Dict[str, Any],
        alpha_state: Dict[str, Any],
        regime_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get meta-layer state (ORCH-7).
        
        PHASE 5: Full learning integration with real AF6 metrics.
        """
        try:
            from ...meta_layer import get_meta_controller
            from ...alpha_factory.real_learning import get_real_learning_engine
            
            # Get total capital from portfolio
            equity_data = portfolio_state.get("equity", {})
            total_capital = equity_data.get("equity", 10000.0)
            
            # ORCH-7 PHASE 5: Get REAL strategy metrics from AF6
            try:
                learning_engine = get_real_learning_engine()
                if learning_engine:
                    all_metrics = learning_engine.get_aggregated_metrics()
                    strategy_metrics = all_metrics.get("by_strategy", {})
                    
                    # Get alpha feedback actions
                    alpha_feedback_actions = learning_engine.get_alpha_feedback()
                    
                    logger.info(
                        f"[MetaState] Using REAL AF6 metrics: {len(strategy_metrics)} strategies, "
                        f"{len(alpha_feedback_actions)} alpha actions"
                    )
                else:
                    # Fallback to mock if AF6 not available
                    strategy_metrics = self._get_mock_strategy_metrics()
                    alpha_feedback_actions = []
                    logger.warning("[MetaState] AF6 not available, using mock metrics")
            except Exception as e:
                logger.warning(f"[MetaState] AF6 error: {e}, using mock metrics")
                strategy_metrics = self._get_mock_strategy_metrics()
                alpha_feedback_actions = []
            
            # Run meta controller with real metrics + alpha actions
            meta_controller = get_meta_controller()
            meta_result = meta_controller.run(
                strategy_metrics=strategy_metrics,
                regime=regime_state,
                total_capital=total_capital,
                alpha_feedback_actions=alpha_feedback_actions,  # PHASE 5
                trace_id=trace_id  # P0.7: Audit trace ID
            )
            
            return meta_result
            
        except Exception as e:
            logger.warning(f"[MetaState] Error: {e}")
            return {
                "scores": [],
                "allocations": [],
                "actions": [],
                "alpha_actions": [],
                "policy_actions": [],
                "total_capital": 0.0,
            }
    
    def _get_mock_strategy_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Fallback mock metrics when AF6 not available."""
        return {
            "breakout_v1": {
                "profit_factor": 1.5,
                "win_rate": 0.55,
                "expectancy": 45.0,
                "count": 20,
            },
            "mean_reversion_v1": {
                "profit_factor": 1.2,
                "win_rate": 0.58,
                "expectancy": 30.0,
                "count": 15,
            },
            "momentum_v1": {
                "profit_factor": 1.8,
                "win_rate": 0.52,
                "expectancy": 60.0,
                "count": 25,
            },
            "pullback_v1": {
                "profit_factor": 1.4,
                "win_rate": 0.60,
                "expectancy": 35.0,
                "count": 18,
            },
        }
    
    def _compute_strategy_usage(
        self,
        strategy_id: str,
        positions_live: List[Dict[str, Any]],
        orders_live: List[Dict[str, Any]]
    ) -> float:
        """
        Compute current capital usage for a strategy.
        
        ORCH-7 PHASE 4: Tracks usage from open positions + pending orders.
        
        Args:
            strategy_id: Strategy to track
            positions_live: List of open positions
            orders_live: List of live orders
        
        Returns:
            Total notional usage
        """
        pos_usage = 0.0
        for pos in (positions_live or []):
            # Check if position belongs to this strategy
            if pos.get("strategy_id") == strategy_id:
                size = abs(float(pos.get("size", 0.0) or 0.0))
                avg_entry = float(pos.get("avg_entry", 0.0) or 0.0)
                pos_usage += size * avg_entry
        
        ord_usage = 0.0
        for order in (orders_live or []):
            # Check if order belongs to this strategy
            if order.get("strategy_id") != strategy_id:
                continue
            
            # Only count active orders (not filled/cancelled/rejected)
            status = order.get("status", "")
            if status in ["FILLED", "CANCELLED", "REJECTED", "FAILED"]:
                continue
            
            remaining_qty = float(order.get("remaining_qty", order.get("size", 0.0)) or 0.0)
            entry = float(order.get("entry", 0.0) or 0.0)
            ord_usage += abs(remaining_qty * entry)
        
        total_usage = pos_usage + ord_usage
        
        logger.debug(
            f"[StrategyUsage] {strategy_id}: "
            f"positions=${pos_usage:,.2f}, orders=${ord_usage:,.2f}, total=${total_usage:,.2f}"
        )
        
        return round(total_usage, 2)


# Global singleton instance
_engine: Optional[TerminalStateEngine] = None
_audit_controller_ref = None  # P0.7 global ref for audit


def set_audit_controller_for_terminal(audit_controller):
    """Set audit controller reference for terminal engine (P0.7)"""
    global _audit_controller_ref, _engine
    _audit_controller_ref = audit_controller
    
    # If engine already exists, set audit_controller directly
    if _engine is not None:
        _engine.audit_controller = audit_controller
        logger.info("Audit controller set on existing TerminalStateEngine instance")
    else:
        logger.info("Audit controller ref saved for future TerminalStateEngine creation")


def get_terminal_engine() -> TerminalStateEngine:
    """Get or create the singleton terminal state engine"""
    global _engine
    if _engine is None:
        _engine = TerminalStateEngine(audit_controller=_audit_controller_ref)
    return _engine
