"""
Final Gate - ORCH-1
===================

Pre-execution gate that enforces all constraints from:
- Control Layer (hard kill, can_enter)
- Validation Layer (critical issues)
- Regime Layer (mode restrictions)
- Risk Layer (size limits)
- Alpha Layer (mode quality)

Priority order (highest to lowest):
1. Control (hard kill, system-level blocks)
2. Validation (critical data issues)
3. Regime (market mode restrictions)
4. Risk (size constraints)
5. Alpha (adaptive suggestions)
6. Entry Timing (raw input)
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def get_strategy_policy(meta_actions: List[Dict[str, Any]], strategy_id: str) -> Dict[str, bool]:
    """
    Extract strategy policy from meta actions.
    
    Args:
        meta_actions: List of meta-level policy actions
        strategy_id: Strategy to check
    
    Returns:
        Policy flags: disabled, capped, boosted
    """
    policy = {
        "disabled": False,
        "capped": False,
        "boosted": False,
    }
    
    for action in (meta_actions or []):
        if action.get("strategy_id") != strategy_id:
            continue
        
        action_type = action.get("type")
        if action_type == "DISABLE_STRATEGY":
            policy["disabled"] = True
        elif action_type == "CAP_STRATEGY":
            policy["capped"] = True
        elif action_type == "BOOST_STRATEGY":
            policy["boosted"] = True
    
    return policy


class FinalGate:
    """
    Final Gate - Pre-Execution Enforcement Layer
    
    Combines all system constraints into single go/no-go decision.
    """
    
    def __init__(self):
        """Initialize Final Gate."""
        pass
    
    def evaluate(
        self,
        decision: Dict[str, Any],
        risk: Dict[str, Any],
        control: Dict[str, Any],
        validation: Dict[str, Any],
        alpha: Dict[str, Any],
        regime: Dict[str, Any],
        execution: Dict[str, Any],
        portfolio: Dict[str, Any] = None,  # Portfolio state
        meta_allocation: Dict[str, Any] = None,  # NEW: ORCH-7 PHASE 3
        context: Dict[str, Any] = None  # NEW: P0.6 Risk Guard context
    ) -> Dict[str, Any]:
        """
        Evaluate all constraints and return enforced decision.
        
        Args:
            decision: Raw decision from Entry Timing
            risk: Risk state from RiskEngine
            control: Control state from ControlBackend
            validation: Validation state from Validation Layer
            alpha: Alpha state from Alpha Factory
            regime: Regime state from Regime Analysis
            execution: Raw execution plan
            portfolio: Portfolio state (heat, drawdown, allocator)
            meta_allocation: Meta allocation state (ORCH-7)
            context: Risk Guard context (system_health, guard_actions, health_metrics)
        
        Returns:
            Dict with:
                - final_action: ALLOW, ALLOW_REDUCED, ALLOW_MODIFIED, BLOCK
                - blocked: bool
                - block_reason: Optional[str]
                - size_multiplier: float
                - forced_execution_mode: Optional[str]
                - decision_raw: original decision
                - decision_enforced: modified decision
                - reason_chain: List[str]
                - risk_guard_triggered: bool (P0.6 kill switch signal)
        """
        result = {
            "final_action": "ALLOW",
            "blocked": False,
            "block_reason": None,
            "size_multiplier": 1.0,
            "forced_execution_mode": None,
            "reason_chain": [],
            "decision_raw": decision.copy() if decision else {},
            "decision_enforced": None,
            "risk_guard_triggered": False  # P0.6 kill switch signal
        }
        
        portfolio = portfolio or {}
        meta_allocation = meta_allocation or {}  # ORCH-7
        context = context or {}  # P0.6
        
        # -------------------------
        # 0.6 META LAYER (ORCH-7 PHASE 4 - Hard Integration)
        # -------------------------
        strategy_id = meta_allocation.get("strategy_id")
        strategy_weight = meta_allocation.get("strategy_weight", 1.0)
        allocated_capital = meta_allocation.get("allocated_capital")
        strategy_usage = meta_allocation.get("strategy_usage", 0.0)
        meta_actions = meta_allocation.get("actions", [])
        
        # Extract strategy policy from meta actions
        strategy_policy = get_strategy_policy(meta_actions, strategy_id) if strategy_id else {
            "disabled": False, "capped": False, "boosted": False
        }
        
        # 1. DISABLE_STRATEGY → BLOCK (highest priority)
        if strategy_policy["disabled"]:
            logger.warning(f"[FinalGate] ORCH-7 PHASE 4: Strategy {strategy_id} DISABLED")
            return self._block(result, f"strategy_{strategy_id}_disabled")
        
        # 2. BUDGET ENFORCEMENT (hard block)
        requested_notional = execution.get("requested_notional")
        
        if allocated_capital is not None and strategy_usage is not None and requested_notional is not None:
            remaining = allocated_capital - strategy_usage
            
            # Budget exhausted → BLOCK
            if remaining <= 0:
                logger.warning(
                    f"[FinalGate] ORCH-7 PHASE 4: Strategy {strategy_id} budget EXHAUSTED "
                    f"(used=${strategy_usage:,.2f}, allocated=${allocated_capital:,.2f})"
                )
                return self._block(result, f"strategy_{strategy_id}_budget_exhausted")
            
            # Budget overflow → CLAMP
            if requested_notional > remaining:
                ratio = remaining / requested_notional
                result["size_multiplier"] *= max(0.0, ratio)
                result["reason_chain"].append(f"strategy_{strategy_id}_budget_clamp")
                logger.warning(
                    f"[FinalGate] ORCH-7 PHASE 4: Strategy {strategy_id} budget CLAMP "
                    f"(requested=${requested_notional:,.2f}, remaining=${remaining:,.2f}, ratio={ratio:.2%})"
                )
        
        # 3. CAP_STRATEGY → stronger reduction
        if strategy_policy["capped"]:
            result["size_multiplier"] *= 0.5
            result["reason_chain"].append(f"strategy_{strategy_id}_capped")
            logger.info(f"[FinalGate] ORCH-7 PHASE 4: Strategy {strategy_id} CAPPED (size × 0.5)")
        
        # 4. BOOST_STRATEGY → soft boost
        if strategy_policy["boosted"]:
            result["size_multiplier"] *= 1.15
            result["reason_chain"].append(f"strategy_{strategy_id}_boosted")
            logger.info(f"[FinalGate] ORCH-7 PHASE 4: Strategy {strategy_id} BOOSTED (size × 1.15)")
        
        # 5. Strategy weight (PHASE 3 - soft adjustment)
        if strategy_weight < 1.0:
            result["size_multiplier"] *= strategy_weight
            result["reason_chain"].append(f"meta_strategy_weight_{strategy_weight:.2f}")
        elif strategy_weight > 1.0:
            boost = min(strategy_weight, 1.5)
            result["size_multiplier"] *= boost
            result["reason_chain"].append(f"meta_strategy_boost_{boost:.2f}")
        
        # -------------------------
        # 0.6 RISK GUARD LAYER (P0.6 - Execution Reality Protection)
        # -------------------------
        system_health = context.get("system_health")
        guard_actions = context.get("guard_actions", [])
        health_metrics = context.get("health_metrics", {})
        
        # CRITICAL health → BLOCK all new trades
        if system_health == "CRITICAL":
            logger.critical(
                f"[FinalGate] P0.6 RISK GUARD: System CRITICAL "
                f"(drawdown={health_metrics.get('drawdown_pct', 0):.2%}, "
                f"recon_critical={health_metrics.get('reconciliation_critical', 0)})"
            )
            result["risk_guard_triggered"] = True
            return self._block(result, "system_health_critical")
        
        # REDUCE_SIZE action → reduce size by 50%
        if "REDUCE_SIZE" in guard_actions:
            result["size_multiplier"] *= 0.5
            result["reason_chain"].append("risk_guard_reduce_size")
            logger.warning(
                f"[FinalGate] P0.6 RISK GUARD: REDUCE_SIZE active "
                f"(health={system_health}, size × 0.5)"
            )
        
        # -------------------------
        # P1.2 LATENCY GUARD (Execution Quality Control)
        # -------------------------
        try:
            from ..execution_reality.latency import get_latency_tracker
            latency_tracker = get_latency_tracker()
            latency_health = latency_tracker.get_health_status()
            
            latency_status = latency_health.get("status")
            p95_ms = latency_health.get("p95_ms", 0)
            p99_ms = latency_health.get("p99_ms", 0)
            
            # CRITICAL latency → BLOCK (execution unreliable)
            if latency_status == "CRITICAL":
                logger.critical(
                    f"[FinalGate] P1.2 LATENCY GUARD: CRITICAL latency "
                    f"(p95={p95_ms:.0f}ms, p99={p99_ms:.0f}ms) → BLOCK"
                )
                return self._block(result, "latency_critical")
            
            # WARNING latency → reduce size 30%
            if latency_status == "WARNING":
                result["size_multiplier"] *= 0.7
                result["reason_chain"].append("latency_warning_reduce")
                logger.warning(
                    f"[FinalGate] P1.2 LATENCY GUARD: WARNING latency "
                    f"(p95={p95_ms:.0f}ms) → size × 0.7"
                )
            
            # Execution delay penalty (p95 > 1000ms → soft penalty)
            if p95_ms and p95_ms > 1000:
                result["size_multiplier"] *= 0.85
                result["reason_chain"].append("latency_slow_penalty")
                logger.info(
                    f"[FinalGate] P1.2 LATENCY GUARD: Slow execution "
                    f"(p95={p95_ms:.0f}ms > 1000ms) → size × 0.85"
                )
        
        except Exception as e:
            logger.debug(f"[P1.2] Latency guard check failed: {e}")
        
        # -------------------------
        # 0. PORTFOLIO LAYER (HIGHEST PRIORITY AFTER CONTROL)
        # -------------------------
        portfolio_policy = portfolio.get("policy", {})
        
        # Hard stop from portfolio
        if portfolio_policy.get("hard_stop"):
            return self._block(result, "portfolio_hard_stop")
        
        # Block new entries from portfolio
        if not portfolio_policy.get("can_open_new", True):
            return self._block(result, "portfolio_block_new_entries")
        
        # Apply capital allocator multiplier
        allocator = portfolio.get("allocator", {})
        capital_multiplier = allocator.get("multiplier", 1.0)
        
        if capital_multiplier < 1.0:
            result["size_multiplier"] *= capital_multiplier
            reasons = allocator.get("reason_chain", [])
            result["reason_chain"].extend([f"capital_{r}" for r in reasons[:2]])
        
        # Portfolio heat check
        heat_data = portfolio.get("heat", {})
        heat = heat_data.get("heat", 0.0)
        
        if heat > 0.4:
            return self._block(result, "portfolio_heat_limit")
        elif heat > 0.35:
            result["size_multiplier"] *= 0.5
            result["reason_chain"].append("portfolio_heat_elevated")
        
        # Drawdown check
        dd_data = portfolio.get("drawdown", {})
        dd_pct = dd_data.get("current_dd_pct", 0.0)
        
        if dd_pct < -15.0:
            return self._block(result, "portfolio_drawdown_critical")
        elif dd_pct < -10.0:
            result["size_multiplier"] *= 0.5
            result["reason_chain"].append("portfolio_drawdown_high")
        
        # -------------------------
        # 1. HARD CONTROL (TOP PRIORITY)
        # -------------------------
        if control.get("hard_kill"):
            return self._block(result, "hard_kill_active")
        
        if control.get("soft_kill"):
            result["reason_chain"].append("soft_kill_warning")
            result["size_multiplier"] *= 0.5
        
        if not control.get("can_enter", True):
            return self._block(result, "control_blocked_entry")
        
        if not control.get("can_trade", True):
            return self._block(result, "control_blocked_trading")
        
        # -------------------------
        # 2. VALIDATION (CRITICAL)
        # -------------------------
        if not validation.get("is_valid", True):
            return self._block(result, "validation_failed")
        
        critical_count = validation.get("critical_count", 0)
        if critical_count > 0:
            return self._block(result, f"validation_critical_{critical_count}_issues")
        
        warning_count = validation.get("warning_count", 0)
        if warning_count > 0:
            result["reason_chain"].append(f"validation_{warning_count}_warnings")
            result["size_multiplier"] *= 0.7
        
        # -------------------------
        # 3. REGIME RULES
        # -------------------------
        entry_mode = decision.get("mode") or decision.get("action") or "UNKNOWN"
        current_regime = regime.get("current", "NEUTRAL")
        
        # Check regime overrides from control
        regime_overrides = control.get("regime_overrides", {})
        regime_mode_state = regime_overrides.get(entry_mode)
        
        if regime_mode_state == "DISABLED":
            return self._block(result, f"{entry_mode}_disabled_in_{current_regime}")
        
        # Regime-based adjustments
        if current_regime == "RANGING":
            result["reason_chain"].append("regime_ranging")
            
            # Aggressive modes should be downgraded in ranging
            if entry_mode in ["GO_FULL", "ENTER_NOW", "GO_AGGRESSIVE"]:
                result["forced_execution_mode"] = "PASSIVE"
                result["size_multiplier"] *= 0.5
                result["reason_chain"].append("ranging_downgrade_aggressive")
        
        elif current_regime == "TRENDING":
            result["reason_chain"].append("regime_trending")
            # Boost in trending
            result["size_multiplier"] *= 1.2
        
        elif current_regime == "HIGH_VOLATILITY":
            result["reason_chain"].append("regime_high_vol")
            result["size_multiplier"] *= 0.6
        
        # -------------------------
        # 4. RISK CLAMP
        # -------------------------
        max_allowed_position = risk.get("max_allowed_position")
        current_utilization = risk.get("current_utilization", 0.0)
        
        # Size clamp based on risk limits
        if max_allowed_position is not None:
            requested_size = execution.get("size", 1.0)
            
            if requested_size > max_allowed_position:
                ratio = max_allowed_position / requested_size
                result["size_multiplier"] *= ratio
                result["reason_chain"].append(f"risk_clamp_{round(ratio, 2)}")
        
        # Utilization check
        if current_utilization > 0.8:
            result["size_multiplier"] *= 0.5
            result["reason_chain"].append("risk_high_utilization")
        
        # Risk level check
        risk_level = risk.get("risk_level", "NORMAL")
        if risk_level == "HIGH":
            result["size_multiplier"] *= 0.6
            result["reason_chain"].append("risk_level_high")
        elif risk_level == "CRITICAL":
            return self._block(result, "risk_level_critical")
        
        # -------------------------
        # 5. ALPHA ADJUSTMENTS
        # -------------------------
        symbol_verdict = alpha.get("symbol_verdict")
        entry_mode_verdict = alpha.get("entry_mode_verdict")
        
        # Block broken modes
        if entry_mode_verdict == "BROKEN_ENTRY_MODE":
            return self._block(result, "alpha_broken_mode")
        
        # Reduce weak modes
        if entry_mode_verdict == "WEAK_ENTRY_MODE":
            result["size_multiplier"] *= 0.5
            result["reason_chain"].append("alpha_weak_mode_reduce")
        
        # Boost strong modes
        if entry_mode_verdict == "STRONG_CONFIRMED_EDGE":
            result["size_multiplier"] *= 1.1
            result["reason_chain"].append("alpha_strong_mode_boost")
        
        # Symbol-level block
        if symbol_verdict == "NO_EDGE" or symbol_verdict == "BROKEN":
            return self._block(result, "alpha_no_edge_symbol")
        
        # -------------------------
        # 6. FINAL DECISION BUILD
        # -------------------------
        
        # Clamp size_multiplier to reasonable bounds
        result["size_multiplier"] = max(0.1, min(2.0, result["size_multiplier"]))
        
        # Build enforced decision
        result["decision_enforced"] = {
            **decision,
            "size_multiplier": result["size_multiplier"],
            "forced_mode": result["forced_execution_mode"]
        }
        
        # Set final action
        if result["size_multiplier"] < 1.0:
            result["final_action"] = "ALLOW_REDUCED"
        elif result["forced_execution_mode"]:
            result["final_action"] = "ALLOW_MODIFIED"
        
        return result
    
    def _block(self, result: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Block execution with reason."""
        result["final_action"] = "BLOCK"
        result["blocked"] = True
        result["block_reason"] = reason
        result["reason_chain"].append(reason)
        result["decision_enforced"] = None
        result["size_multiplier"] = 0.0
        return result


# Singleton instance
_final_gate: Optional[FinalGate] = None


def get_final_gate() -> FinalGate:
    """Get or create singleton Final Gate instance."""
    global _final_gate
    if _final_gate is None:
        _final_gate = FinalGate()
    return _final_gate
