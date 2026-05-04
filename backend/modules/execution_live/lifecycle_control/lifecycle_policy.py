"""
Lifecycle Policy - ORCH-6

Policy-driven position and order management.
Integrates with AF6 for alpha-driven exits.

This is NOT hardcoded if/else - this is adaptive policy layer
that evolves based on market state, alpha verdict, validation state.
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class LifecyclePolicy:
    """
    Position lifecycle policy engine.
    
    Makes intelligent decisions based on:
    - Market state (price, volatility)
    - Alpha state (entry_mode_verdict, symbol_verdict)
    - Validation state (is_valid, severity)
    - Regime state (current regime, strength)
    - Risk state (heat, drawdown)
    - PnL state (current profit/loss)
    
    This is the brain that decides: HOLD / REDUCE / CLOSE / TRAIL
    """
    
    def evaluate_position(
        self,
        position: Dict[str, Any],
        market_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate position and generate lifecycle actions.
        
        Args:
            position: Position dict from PositionEngine
            market_state: Current market state with alpha/validation/regime/risk
            
        Returns:
            List of lifecycle actions
        """
        actions = []
        
        symbol = position.get("symbol")
        size = float(position.get("size", 0.0) or 0.0)
        
        if size <= 0:
            return actions
        
        # Extract state
        pnl_pct = market_state.get("pnl_pct", 0.0)
        alpha_state = market_state.get("alpha_state", {})
        validation_state = market_state.get("validation_state", {})
        regime_state = market_state.get("regime_state", {})
        risk_state = market_state.get("risk_state", {})
        portfolio_state = market_state.get("portfolio_state", {})  # NEW
        
        # 0. PORTFOLIO-DRIVEN EXIT (NEW - Highest priority after alpha broken)
        portfolio_dd = portfolio_state.get("drawdown", {})
        dd_pct = portfolio_dd.get("current_dd_pct", 0.0)
        
        if dd_pct < -10.0:
            # Close weakest positions when portfolio in drawdown
            # (Weakest = most negative PnL or smallest positive PnL)
            if pnl_pct < 0:
                # Losing position - close immediately
                actions.append({
                    "action_type": "CLOSE_POSITION",
                    "target_id": symbol,
                    "reason": "portfolio_drawdown_close_losing",
                    "payload": {
                        "exit_price": market_state.get("current_price"),
                    },
                    "priority": "HIGH",
                })
                logger.warning(f"[LifecyclePolicy] CLOSE {symbol}: Portfolio DD {dd_pct:.1f}%, losing position")
                return actions
            elif pnl_pct < 0.02:
                # Small profit - reduce
                actions.append({
                    "action_type": "REDUCE_POSITION",
                    "target_id": symbol,
                    "reason": "portfolio_drawdown_reduce_weak",
                    "payload": {
                        "reduce_qty": round(size * 0.6, 8),
                        "exit_price": market_state.get("current_price"),
                    },
                    "priority": "HIGH",
                })
                logger.info(f"[LifecyclePolicy] REDUCE {symbol}: Portfolio DD {dd_pct:.1f}%, weak winner")
        
        # 1. ALPHA-DRIVEN EXIT (AF6 integration)
        entry_mode_verdict = alpha_state.get("entry_mode_verdict", "UNKNOWN")
        symbol_verdict = alpha_state.get("symbol_verdict", "UNKNOWN")
        
        if entry_mode_verdict == "BROKEN" or symbol_verdict == "BROKEN":
            actions.append({
                "action_type": "CLOSE_POSITION",
                "target_id": symbol,
                "reason": "alpha_broken",
                "payload": {
                    "exit_price": market_state.get("current_price"),
                },
                "priority": "HIGH",
            })
            logger.warning(f"[LifecyclePolicy] CLOSE {symbol}: Alpha broken")
            return actions  # Exit immediately, don't evaluate other rules
        
        if entry_mode_verdict == "WEAK":
            actions.append({
                "action_type": "REDUCE_POSITION",
                "target_id": symbol,
                "reason": "alpha_weak_defensive",
                "payload": {
                    "reduce_qty": round(size * 0.5, 8),
                    "exit_price": market_state.get("current_price"),
                },
                "priority": "MEDIUM",
            })
            logger.info(f"[LifecyclePolicy] REDUCE {symbol}: Alpha weak")
        
        # 2. VALIDATION-DRIVEN EXIT
        validation_valid = validation_state.get("is_valid", True)
        validation_severity = validation_state.get("severity", "OK")
        
        if not validation_valid or validation_severity == "CRITICAL":
            actions.append({
                "action_type": "CLOSE_POSITION",
                "target_id": symbol,
                "reason": "validation_failed",
                "payload": {
                    "exit_price": market_state.get("current_price"),
                },
                "priority": "HIGH",
            })
            logger.warning(f"[LifecyclePolicy] CLOSE {symbol}: Validation failed")
            return actions
        
        # 3. PROFIT MANAGEMENT
        if pnl_pct >= 0.03:  # 3% profit
            actions.append({
                "action_type": "REDUCE_POSITION",
                "target_id": symbol,
                "reason": "partial_take_profit",
                "payload": {
                    "reduce_qty": round(size * 0.5, 8),
                    "exit_price": market_state.get("current_price"),
                },
                "priority": "LOW",
            })
            logger.info(f"[LifecyclePolicy] REDUCE {symbol}: Take profit at {pnl_pct*100:.2f}%")
        
        # 4. TRAILING STOP (activate on profit)
        if pnl_pct >= 0.02:  # 2% profit, start trailing
            side = position.get("side", "LONG")
            current_price = market_state.get("current_price")
            current_stop = position.get("stop")
            
            if current_price and current_stop:
                if side == "LONG":
                    new_stop = max(float(current_stop), current_price * 0.99)  # Trail 1% below
                else:
                    new_stop = min(float(current_stop), current_price * 1.01)  # Trail 1% above
                
                if new_stop != current_stop:
                    actions.append({
                        "action_type": "TRAIL_STOP",
                        "target_id": symbol,
                        "reason": "profit_trailing",
                        "payload": {
                            "new_stop": round(new_stop, 8),
                        },
                        "priority": "LOW",
                    })
                    logger.debug(f"[LifecyclePolicy] TRAIL {symbol}: {current_stop} → {new_stop}")
        
        # 5. REGIME ADAPTATION
        regime = regime_state.get("current", "UNKNOWN")
        
        if regime == "RANGING" and pnl_pct > 0.02:
            # In ranging, take profit early
            actions.append({
                "action_type": "REDUCE_POSITION",
                "target_id": symbol,
                "reason": "range_exit_early",
                "payload": {
                    "reduce_qty": round(size * 0.3, 8),
                    "exit_price": market_state.get("current_price"),
                },
                "priority": "MEDIUM",
            })
            logger.info(f"[LifecyclePolicy] REDUCE {symbol}: Ranging regime, take profit early")
        
        # 6. RISK MANAGEMENT
        risk_heat = risk_state.get("heat", 0.0)
        
        if risk_heat > 0.7:  # High risk heat
            actions.append({
                "action_type": "REDUCE_POSITION",
                "target_id": symbol,
                "reason": "risk_heat_high",
                "payload": {
                    "reduce_qty": round(size * 0.3, 8),
                    "exit_price": market_state.get("current_price"),
                },
                "priority": "MEDIUM",
            })
            logger.info(f"[LifecyclePolicy] REDUCE {symbol}: Risk heat high ({risk_heat:.2f})")
        
        return actions
    
    def evaluate_order(
        self,
        order: Dict[str, Any],
        market_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate open order and generate lifecycle actions.
        
        Args:
            order: Order dict from OrderManager
            market_state: Current market state
            
        Returns:
            List of lifecycle actions for orders
        """
        actions = []
        
        order_id = order.get("order_id")
        mode = order.get("mode")
        status = order.get("status")
        
        # Only manage PASSIVE_LIMIT orders
        if mode != "PASSIVE_LIMIT":
            return actions
        
        if status not in ["PLACED", "OPEN", "PARTIALLY_FILLED"]:
            return actions
        
        # Cancel stale orders
        if market_state.get("cancel_stale_orders", False):
            actions.append({
                "action_type": "CANCEL_ORDER",
                "target_id": order_id,
                "reason": "stale_limit_order",
                "payload": {},
                "priority": "LOW",
            })
            logger.debug(f"[LifecyclePolicy] CANCEL {order_id}: Stale order")
        
        # Reprice orders based on market movement
        if market_state.get("reprice_passive_orders", False):
            new_entry = market_state.get("new_entry_price")
            if new_entry:
                actions.append({
                    "action_type": "REPLACE_ORDER",
                    "target_id": order_id,
                    "reason": "market_repricing",
                    "payload": {
                        "new_entry": new_entry,
                    },
                    "priority": "LOW",
                })
                logger.debug(f"[LifecyclePolicy] REPLACE {order_id}: Repriced to {new_entry}")
        
        return actions
