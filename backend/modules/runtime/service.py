"""
Runtime Service — Orchestrator (Sprint 2: with Decision Trace)
"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class RuntimeService:
    """Runtime orchestrator and facade."""
    
    def __init__(
        self,
        controller,
        repository,
        signal_adapter,
        risk_manager,
        kill_switch,
        order_manager,
        exchange_service,
        execution_logger
    ):
        self.controller = controller
        self.repo = repository
        self.signal_adapter = signal_adapter
        self.risk_manager = risk_manager
        self.kill_switch = kill_switch
        self.order_manager = order_manager
        self.exchange_service = exchange_service
        self.exec_logger = execution_logger
        
        # ExecutionBridge for queue-based execution
        from modules.execution.bridge import get_execution_bridge
        self.execution_bridge = get_execution_bridge()
        
        # Sprint 2: Decision Trace
        self._trace_service = None
        try:
            from modules.runtime.decision_trace import get_decision_trace_service
            self._trace_service = get_decision_trace_service()
        except RuntimeError:
            logger.warning("[RuntimeService] DecisionTraceService not available")
        
        logger.info("[RuntimeService] Initialized with RuntimeSignalAdapter + ExecutionBridge + DecisionTrace")
    
    async def get_runtime_state(self) -> Dict[str, Any]:
        """Get current runtime state."""
        return await self.controller.get_state()
    
    async def start_runtime(self) -> Dict[str, Any]:
        """Start runtime."""
        return await self.controller.start()
    
    async def stop_runtime(self) -> Dict[str, Any]:
        """Stop runtime."""
        return await self.controller.stop()
    
    async def set_mode(self, mode: str) -> Dict[str, Any]:
        """Set runtime mode."""
        return await self.controller.set_mode(mode)
    
    async def set_symbols(self, symbols: list) -> Dict[str, Any]:
        """Set symbols universe."""
        return await self.controller.set_symbols(symbols)
    
    async def set_interval(self, interval_sec: int) -> Dict[str, Any]:
        """Set loop interval."""
        return await self.controller.set_interval(interval_sec)
    
    async def list_pending_decisions(self):
        """List pending decisions (with expiration cleanup)."""
        await self.repo.expire_old()
        pending = await self.repo.get_pending()
        return {"ok": True, "decisions": pending, "count": len(pending)}
    
    async def run_once(self) -> Dict[str, Any]:
        """
        Execute one runtime cycle.
        
        Flow:
        1. Check kill switch
        2. Check runtime enabled
        3. For each symbol:
           - Get signals
           - Evaluate risk
           - Mode gate decision
        4. Log cycle complete
        """
        state = await self.controller.get_state()
        
        await self.exec_logger.log_event({
            "type": "RUNTIME_CYCLE_START",
            "mode": state.get("mode"),
            "symbols": state.get("symbols")
        })
        
        # Check enabled
        if not state.get("enabled", False):
            await self.exec_logger.log_event({
                "type": "RUNTIME_DISABLED",
                "reason": "Runtime is not enabled"
            })
            return {"ok": False, "reason": "RUNTIME_DISABLED"}
        
        # Check kill switch
        ks_status = await self.kill_switch.get_status()
        if ks_status.get("active"):
            await self.exec_logger.log_event({
                "type": "KILL_SWITCH_ACTIVE",
                "reason": "Kill switch is active"
            })
            return {"ok": False, "reason": "KILL_SWITCH_ACTIVE"}
        
        # Sprint A2.2: STALE GUARD — block runtime if market data is stale
        from modules.market_data.service_locator import get_market_data_ingestion_service
        
        try:
            market_data_service = get_market_data_ingestion_service()
            freshness = await market_data_service.get_freshness()
            
            stale_items = []
            for symbol, by_tf in freshness["symbols"].items():
                for timeframe, item in by_tf.items():
                    if item["stale"]:
                        stale_items.append({
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "age_sec": item["age_sec"],
                            "reason": item.get("reason"),
                        })
            
            if stale_items:
                await self.exec_logger.log_event({
                    "type": "MARKET_DATA_STALE_BLOCK",
                    "details": stale_items,
                })
                return {
                    "ok": False,
                    "reason": "MARKET_DATA_STALE_BLOCK",
                    "details": stale_items,
                }
        except RuntimeError:
            # MarketDataIngestionService not initialized (e.g., during tests)
            logger.warning("MARKET_DATA_SERVICE_NOT_INITIALIZED — skipping stale guard")
        
        await self.controller.mark_running()
        
        summary = {
            "signals": 0,
            "approved": 0,
            "rejected": 0,
            "pending_created": 0,
            "executed": 0
        }
        
        try:
            symbols = state.get("symbols", [])
            mode = state.get("mode", "MANUAL")
            
            # Sprint A3: Get Strategy Visibility service
            from modules.strategy_visibility.service_locator import get_strategy_visibility_service
            try:
                strategy_visibility = get_strategy_visibility_service()
            except RuntimeError:
                strategy_visibility = None  # Not initialized (e.g., during tests)
            
            # Get signals from real TA/Prediction stack
            signals = await self.signal_adapter.get_signals(symbols)
            
            for signal in signals:
                summary["signals"] += 1
                
                # Sprint 2: Create decision trace
                from modules.runtime.decision_trace import DecisionTrace
                trace = DecisionTrace(
                    symbol=signal["symbol"],
                    side=signal["side"],
                    source=signal.get("source", "TA_ENGINE"),
                )
                trace.add_step("SIGNAL", {
                    "confidence": signal.get("confidence"),
                    "strategy": signal.get("strategy"),
                    "regime": signal.get("regime"),
                    "entry_price": signal.get("entry_price"),
                    "stop_price": signal.get("stop_price"),
                    "target_price": signal.get("target_price"),
                    "timeframe": signal.get("timeframe"),
                    "drivers": signal.get("drivers", {}),
                })
                
                await self.exec_logger.log_event({
                    "type": "SIGNAL_FROM_TA" if signal.get("source") == "TA_ENGINE" else "SIGNAL_FROM_TA_PREDICTION",
                    "symbol": signal["symbol"],
                    "side": signal["side"],
                    "strategy": signal.get("strategy"),
                    "confidence": signal.get("confidence"),
                    "source": signal.get("source"),
                    "trace_id": trace.trace_id,
                })
                
                # Sprint 1: REAL Risk Manager evaluation (no longer mock)
                try:
                    risk = await self.risk_manager.evaluate(signal)
                except Exception as e:
                    # Safety fallback: if RiskManager crashes, log and continue cautiously
                    logger.error(f"[RuntimeService] RiskManager.evaluate() failed: {e}")
                    import traceback
                    traceback.print_exc()
                    risk = {"approved": False, "reason": f"RISK_MANAGER_ERROR: {str(e)}"}
                
                if not risk["approved"]:
                    summary["rejected"] += 1
                    
                    # Sprint 2: Trace — risk rejected
                    trace.add_step("RISK_REJECTED", {
                        "approved": False,
                        "reason": risk.get("reason"),
                    })
                    trace.finalize("REJECTED", risk.get("reason"))
                    if self._trace_service:
                        await self._trace_service.save(trace)
                    
                    # Sprint A3: Record rejected signal + decision
                    if strategy_visibility:
                        await strategy_visibility.record_signal(
                            signal=signal,
                            decision_status="REJECTED",
                            runtime_mode=mode,
                            risk_reason=risk["reason"],
                        )
                        await strategy_visibility.record_decision(
                            signal=signal,
                            decision_status="REJECTED",
                            runtime_mode=mode,
                            risk_reason=risk["reason"],
                        )
                    
                    await self.exec_logger.log_event({
                        "type": "DECISION_REJECTED",
                        "symbol": signal["symbol"],
                        "reason": risk["reason"]
                    })
                    continue
                
                summary["approved"] += 1
                
                # Sprint 2: Trace — risk approved
                trace.add_step("RISK_APPROVED", {
                    "approved": True,
                })
                
                # Sprint A3: Record approved signal
                if strategy_visibility:
                    await strategy_visibility.record_signal(
                        signal=signal,
                        decision_status="APPROVED",
                        runtime_mode=mode,
                        risk_reason=None,
                    )
                
                await self.exec_logger.log_event({
                    "type": "DECISION_APPROVED",
                    "symbol": signal["symbol"],
                    "strategy": signal.get("strategy")
                })
                
                # Mode gate
                if mode == "MANUAL":
                    trace.add_step("MODE_GATE", {"mode": "MANUAL", "action": "BLOCKED"})
                    trace.finalize("BLOCKED", "MANUAL mode")
                    if self._trace_service:
                        await self._trace_service.save(trace)
                    
                    await self.exec_logger.log_event({
                        "type": "MODE_BLOCKED_MANUAL",
                        "symbol": signal["symbol"],
                        "trace_id": trace.trace_id,
                    })
                    continue
                
                if mode == "SEMI_AUTO":
                    # Create pending decision
                    decision = await self.repo.create({
                        "symbol": signal["symbol"],
                        "side": signal["side"],
                        "strategy": signal.get("strategy", "unknown"),
                        "confidence": signal.get("confidence", 0),
                        "entry_price": signal.get("entry_price"),
                        "stop_price": signal.get("stop_price"),
                        "target_price": signal.get("target_price"),
                        "size_usd": 100,  # LIVE-2b: aligned with MAX_POSITION_SIZE_USD
                        "thesis": signal.get("thesis", ""),
                        "timeframe": signal.get("timeframe", "1H"),
                        "trace_id": trace.trace_id,
                    })
                    
                    summary["pending_created"] += 1
                    
                    # Sprint 2: Trace — pending
                    trace.add_step("MODE_GATE", {"mode": "SEMI_AUTO", "action": "PENDING"})
                    trace.add_step("PENDING_CREATED", {"decision_id": decision["decision_id"]})
                    trace.finalize("PENDING", f"Awaiting approval: {decision['decision_id']}")
                    if self._trace_service:
                        await self._trace_service.save(trace)
                    
                    # Sprint A3: Record pending decision
                    if strategy_visibility:
                        await strategy_visibility.record_decision(
                            signal=signal,
                            decision_status="PENDING",
                            runtime_mode=mode,
                            risk_reason=None,
                            decision_id=decision["decision_id"],
                        )
                    
                    await self.exec_logger.log_event({
                        "type": "PENDING_DECISION_CREATED",
                        "decision_id": decision["decision_id"],
                        "symbol": decision["symbol"],
                        "side": decision["side"],
                        "confidence": decision["confidence"]
                    })
                    continue
                
                if mode == "AUTO":
                    # Sprint 2: Trace — AUTO mode entry
                    trace.add_step("MODE_GATE", {"mode": "AUTO", "action": "EXECUTE"})
                    
                    # Sprint R1: Dynamic Risk Engine (BEFORE AutoSafety)
                    from modules.dynamic_risk.service_locator import get_dynamic_risk_engine
                    
                    try:
                        dynamic_risk = get_dynamic_risk_engine()
                        
                        # DEBUG: Log portfolio state before R1 evaluation
                        from modules.portfolio.service import get_portfolio_service
                        portfolio_service = get_portfolio_service()
                        debug_summary = await portfolio_service.get_summary()
                        logger.warning(f"[Runtime] PRE-R1 portfolio state: deployment_pct={debug_summary.deployment_pct}, active_positions={debug_summary.active_positions}")
                        
                        sizing_decision = await dynamic_risk.evaluate(signal)
                        
                        # DEBUG: Log R1 decision
                        logger.warning(f"[Runtime] R1 decision: approved={sizing_decision.get('approved')}, reason={sizing_decision.get('reason')}, qty={sizing_decision.get('qty')}")
                        
                        if not sizing_decision.get("approved"):
                            # DYNAMIC RISK BLOCKED
                            block_reason = sizing_decision.get("reason", "UNKNOWN")
                            
                            await self.exec_logger.log_event({
                                "type": "DYNAMIC_RISK_BLOCKED",
                                "symbol": signal["symbol"],
                                "reason": block_reason,
                                "confidence": signal.get("confidence"),
                                "debug": sizing_decision.get("debug", {}),
                            })
                            
                            # Record blocked decision in strategy visibility
                            if strategy_visibility:
                                await strategy_visibility.record_decision(
                                    signal=signal,
                                    decision_status="REJECTED",
                                    runtime_mode=mode,
                                    risk_reason=block_reason,
                                )
                            
                            logger.warning(f"[Runtime] DYNAMIC_RISK_BLOCKED: {signal['symbol']} - {block_reason}")
                            continue
                        
                        # Store sizing decision in signal
                        signal["sizing"] = {
                            "qty": sizing_decision.get("qty"),
                            "notional_usd": sizing_decision.get("notional_usd"),
                            "size_multiplier": sizing_decision.get("size_multiplier"),
                            "symbol_exposure_usd": sizing_decision.get("symbol_exposure_usd"),
                            "portfolio_exposure_pct": sizing_decision.get("portfolio_exposure_pct"),
                            "debug": sizing_decision.get("debug", {}),
                        }
                        
                        # CRITICAL: Fallback if qty is invalid
                        qty = signal["sizing"]["qty"]
                        if not qty or qty <= 0:
                            logger.error(f"[Runtime] CRITICAL: DynamicRisk returned invalid qty={qty}, fallback to 0.001")
                            signal["sizing"]["qty"] = 0.001
                        
                        # Log R1 decision (BEFORE R2)
                        await self.exec_logger.log_event({
                            "type": "DYNAMIC_RISK_APPROVED",
                            "symbol": signal["symbol"],
                            "qty": signal["sizing"]["qty"],
                            "notional_usd": signal["sizing"]["notional_usd"],
                            "size_multiplier": signal["sizing"]["size_multiplier"],
                            "confidence": signal.get("confidence"),
                            "debug": signal["sizing"]["debug"],
                        })
                        
                        # Sprint 2: Trace — R1 sizing
                        trace.add_step("R1_SIZING", {
                            "approved": True,
                            "qty": signal["sizing"]["qty"],
                            "notional_usd": signal["sizing"]["notional_usd"],
                            "size_multiplier": signal["sizing"]["size_multiplier"],
                        })
                        
                    except RuntimeError:
                        # DynamicRiskEngine not initialized (e.g., during tests)
                        logger.warning("DYNAMIC_RISK_ENGINE_NOT_INITIALIZED — using fallback sizing")
                        signal["sizing"] = {"qty": 0.001, "notional_usd": 50, "size_multiplier": 1.0, "debug": {}}
                    
                    # Phase 5: R2 Adaptive Risk Engine (AFTER R1, BEFORE AutoSafety)
                    # STEP C: DISABLE during first 50 trades
                    adaptation_disabled = os.getenv("DISABLE_ADAPTATION", "false").lower() == "true"
                    
                    if adaptation_disabled:
                        # Lock R2: use neutral multiplier (1.0)
                        logger.info("[R2] DISABLED (first 50 trades baseline mode)")
                        signal["sizing"]["r2"] = {
                            "multiplier": 1.0,
                            "reason": "DISABLED_BASELINE_MODE",
                            "components": {},
                            "debug": {}
                        }
                        signal["sizing"]["r2_multiplier"] = 1.0
                        signal["sizing"]["final_multiplier"] = signal["sizing"]["size_multiplier"]  # R1 only
                    else:
                        # Normal R2 evaluation
                        from modules.adaptive_risk.service import get_adaptive_risk_service
                        
                        try:
                            adaptive_risk = get_adaptive_risk_service()
                            
                            # R2 evaluation (context-aware dampening)
                            r2_result = await adaptive_risk.evaluate(signal)
                            
                            # Store R2 result in signal (strict contract)
                            signal["sizing"]["r2"] = r2_result
                            signal["sizing"]["r2_multiplier"] = r2_result["multiplier"]
                            
                            # Apply R2 multiplier to R1 sizing (multiplicative layer)
                            r1_multiplier = signal["sizing"]["size_multiplier"]
                            final_multiplier = r1_multiplier * r2_result["multiplier"]
                            signal["sizing"]["final_multiplier"] = round(final_multiplier, 4)
                            
                            # Apply R2 to notional and qty
                            signal["sizing"]["notional_usd"] *= r2_result["multiplier"]
                            signal["sizing"]["qty"] *= r2_result["multiplier"]
                            
                            # Clamp qty to minimum exchange precision
                            signal["sizing"]["qty"] = max(signal["sizing"]["qty"], 0.001)
                            
                            # Log R2 application
                            await self.exec_logger.log_event({
                                "type": "ADAPTIVE_RISK_APPLIED",
                                "symbol": signal["symbol"],
                                "r2_multiplier": r2_result["multiplier"],
                                "final_multiplier": signal["sizing"]["final_multiplier"],
                                "final_qty": signal["sizing"]["qty"],
                                "final_notional_usd": signal["sizing"]["notional_usd"],
                                "r2_components": r2_result["components"],
                                "r2_debug": r2_result["debug"],
                            })
                            
                            logger.info(
                                f"[R2] Applied to {signal['symbol']}: "
                            f"R1={r1_multiplier:.2f} × R2={r2_result['multiplier']:.2f} = {final_multiplier:.2f}, "
                            f"final_qty={signal['sizing']['qty']:.4f}"
                        )
                            
                            # Sprint 2: Trace — R2 adaptive
                            trace.add_step("R2_ADAPTIVE", {
                                "r2_multiplier": r2_result["multiplier"],
                                "final_multiplier": final_multiplier,
                                "final_qty": signal["sizing"]["qty"],
                                "components": r2_result.get("components", {}),
                            })
                            
                            # Update debug dict with R2 data
                            signal["sizing"]["debug"]["r2_multiplier"] = r2_result["multiplier"]
                            signal["sizing"]["debug"]["r2_components"] = r2_result["components"]
                            signal["sizing"]["debug"]["r2_debug"] = r2_result["debug"]
                            signal["sizing"]["debug"]["final_multiplier"] = final_multiplier
                            
                        except RuntimeError as e:
                            # AdaptiveRiskService not initialized (e.g., during tests)
                            logger.warning(f"ADAPTIVE_RISK_SERVICE_NOT_INITIALIZED — skipping R2: {e}")
                            # Default: R2 = 1.0 (no adjustment)
                            signal["sizing"]["r2"] = {
                                "multiplier": 1.0,
                                "components": {"drawdown": 1.0, "loss_streak": 1.0},
                                "debug": {"drawdown_pct": 0.0, "loss_streak_count": 0}
                            }
                            signal["sizing"]["r2_multiplier"] = 1.0
                            signal["sizing"]["final_multiplier"] = signal["sizing"]["size_multiplier"]
                            
                            # Update debug
                            signal["sizing"]["debug"]["r2_multiplier"] = 1.0
                            signal["sizing"]["debug"]["r2_components"] = {"drawdown": 1.0, "loss_streak": 1.0}
                            signal["sizing"]["debug"]["r2_debug"] = {"drawdown_pct": 0.0, "loss_streak_count": 0}
                            signal["sizing"]["debug"]["final_multiplier"] = signal["sizing"]["size_multiplier"]
                            
                        except Exception as e:
                            # Catch ANY exception to prevent R2 from silently failing
                            logger.error(f"[R2] UNEXPECTED ERROR: {type(e).__name__}: {e}")
                            import traceback
                            traceback.print_exc()
                            # Default: R2 = 1.0 (no adjustment)
                            signal["sizing"]["r2"] = {
                                "multiplier": 1.0,
                                "components": {"drawdown": 1.0, "loss_streak": 1.0},
                                "debug": {"drawdown_pct": 0.0, "loss_streak_count": 0}
                            }
                            signal["sizing"]["r2_multiplier"] = 1.0
                            signal["sizing"]["final_multiplier"] = signal["sizing"]["size_multiplier"]
                            
                            # Update debug
                            signal["sizing"]["debug"]["r2_multiplier"] = 1.0
                            signal["sizing"]["debug"]["r2_components"] = {"drawdown": 1.0, "loss_streak": 1.0}
                            signal["sizing"]["debug"]["r2_debug"] = {"drawdown_pct": 0.0, "loss_streak_count": 0}
                            signal["sizing"]["debug"]["final_multiplier"] = signal["sizing"]["size_multiplier"]
                    
                    # Sprint A4: AUTO Safety Gate (AFTER R2)
                    from modules.auto_safety.service_locator import get_auto_safety_service
                    
                    try:
                        auto_safety = get_auto_safety_service()
                        permission = await auto_safety.evaluate_auto_permission(
                            signal=signal,
                            size_notional_pct=0.01,  # 1% of portfolio (Stage 1 rollout)
                        )
                        
                        if not permission.get("allowed"):
                            # AUTO BLOCKED
                            block_reason = permission.get("reason", "UNKNOWN")
                            
                            await self.exec_logger.log_event({
                                "type": "AUTO_BLOCKED",
                                "symbol": signal["symbol"],
                                "reason": block_reason,
                            })
                            
                            # Record blocked decision in strategy visibility
                            if strategy_visibility:
                                await strategy_visibility.record_decision(
                                    signal=signal,
                                    decision_status="REJECTED",
                                    runtime_mode=mode,
                                    risk_reason=block_reason,
                                )
                            
                            logger.warning(f"[Runtime] AUTO BLOCKED: {signal['symbol']} - {block_reason}")
                            continue
                        
                    except RuntimeError:
                        # AutoSafetyService not initialized (e.g., during tests)
                        logger.warning("AUTO_SAFETY_SERVICE_NOT_INITIALIZED — skipping safety gate")
                    
                    # DEBUG: Confirm we reached execution phase
                    logger.warning(f"[Runtime] DEBUG: Reached EXECUTION phase for {signal['symbol']}, about to queue execution")
                    
                    # Sprint 2: Trace — safety passed
                    trace.add_step("SAFETY", {"allowed": True})
                    
                    # Sprint A3: Fix execution event semantics (QUEUED ≠ FILLED)
                    await self.exec_logger.log_event({
                        "type": "EXECUTION_QUEUED",  # Changed from AUTO_EXECUTION_START
                        "symbol": signal["symbol"],
                        "mode": "AUTO"
                    })
                    
                    logger.warning(f"[Runtime] DEBUG: EXECUTION_QUEUED logged, calling _execute_signal")
                    
                    result = await self._execute_signal(signal, size_usd=100)  # LIVE-2b
                    
                    logger.warning(f"[Runtime] DEBUG: _execute_signal returned: {str(result)[:100]}")
                    
                    summary["executed"] += 1
                    
                    # Sprint 2: Trace — execution
                    trace.add_step("EXECUTION", {
                        "job_id": result.get("job_id") if isinstance(result, dict) else None,
                        "ok": result.get("ok") if isinstance(result, dict) else False,
                    })
                    trace.finalize("EXECUTED")
                    if self._trace_service:
                        await self._trace_service.save(trace)
                    
                    # Sprint A4: Increment safety counter AFTER successful queue submission
                    try:
                        auto_safety = get_auto_safety_service()
                        await auto_safety.increment_trades_last_hour()
                    except RuntimeError:
                        pass
                    
                    # Sprint A3: Record approved decision (execution queued, not filled)
                    if strategy_visibility:
                        await strategy_visibility.record_decision(
                            signal=signal,
                            decision_status="APPROVED",  # Changed from EXECUTED (queue ≠ fill)
                            runtime_mode=mode,
                            risk_reason=None,
                        )
                    
                    await self.exec_logger.log_event({
                        "type": "RUNTIME_HANDOFF_TO_EXECUTION",  # Changed from AUTO_EXECUTION_SUCCESS
                        "symbol": signal["symbol"],
                        "result": str(result)[:100]
                    })
            
            await self.controller.mark_idle()
            
            await self.exec_logger.log_event({
                "type": "RUNTIME_CYCLE_END",
                "summary": summary
            })
            
            logger.info(f"[RuntimeService] Cycle complete: {summary}")
            return {"ok": True, "summary": summary}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[RuntimeService] Cycle failed: {error_msg}")
            
            await self.controller.mark_error(error_msg)
            
            await self.exec_logger.log_event({
                "type": "RUNTIME_ERROR",
                "error": error_msg
            })
            
            return {"ok": False, "error": error_msg}
    
    async def approve_decision(self, decision_id: str):
        """
        Approve a pending decision and execute it.
        
        This is the KEY method for SEMI_AUTO mode.
        approve = trigger execution
        """
        decision = await self.repo.get_by_id(decision_id)
        
        if not decision:
            raise ValueError("Decision not found")
        
        if decision["status"] != "PENDING":
            raise ValueError(f"Decision is not pending: {decision['status']}")
        
        await self.repo.approve(decision_id)
        
        await self.exec_logger.log_event({
            "type": "PENDING_DECISION_APPROVED",
            "decision_id": decision_id,
            "symbol": decision["symbol"],
            "side": decision["side"]
        })
        
        # Execute the signal
        signal = {
            "symbol": decision["symbol"],
            "side": decision["side"],
            "entry_price": decision.get("entry_price"),
            "decision_id": decision_id,  # Paper Trading: передаем decision_id
            "strategy": decision.get("strategy"),
            "timeframe": decision.get("timeframe"),
            "size_usd": decision.get("size_usd", 100),  # LIVE-2b default
        }
        
        result = await self._execute_signal(signal, size_usd=decision.get("size_usd", 100))
        
        # Mark as executed
        order_id = None
        exchange_order_id = None
        
        if isinstance(result, dict):
            order_id = result.get("order_id")
            exchange_order_id = result.get("exchange_order_id")
        
        await self.repo.mark_executed(
            decision_id,
            order_id=order_id,
            exchange_order_id=exchange_order_id
        )
        
        await self.exec_logger.log_event({
            "type": "DECISION_EXECUTED",
            "decision_id": decision_id,
            "symbol": decision["symbol"],
            "order_id": order_id
        })
        
        logger.info(f"[RuntimeService] Decision {decision_id} approved and executed")
        return {"ok": True, "result": result}
    
    async def reject_decision(self, decision_id: str, reason: str = None):
        """Reject a pending decision."""
        decision = await self.repo.get_by_id(decision_id)
        
        if not decision:
            raise ValueError("Decision not found")
        
        await self.repo.reject(decision_id, reason=reason)
        
        await self.exec_logger.log_event({
            "type": "PENDING_DECISION_REJECTED",
            "decision_id": decision_id,
            "symbol": decision["symbol"],
            "reason": reason or "MANUAL_REJECT"
        })
        
        logger.info(f"[RuntimeService] Decision {decision_id} rejected")
        return {"ok": True}
    
    async def _execute_signal(self, signal: Dict[str, Any], size_usd: float):
        """
        Execute a signal via ExecutionBridge (queue-based).
        
        Sprint A2.3: Changed from direct OrderManager to ExecutionBridge.
        This ensures all execution goes through ExecutionQueueV2.
        """
        logger.info(
            "[RuntimeService] Submitting to ExecutionBridge: %s %s",
            signal['symbol'],
            signal['side']
        )
        
        # Submit через ExecutionBridge → ExecutionQueueV2 → Worker → OrderManager
        result = await self.execution_bridge.submit(signal)
        
        if result.get("ok"):
            logger.info(
                "[RuntimeService] Execution queued: job_id=%s",
                result.get("job_id")
            )
        else:
            logger.warning(
                "[RuntimeService] Execution failed to queue: %s",
                result.get("error") or result.get("reason")
            )
        
        return result

