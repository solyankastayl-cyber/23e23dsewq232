"""
PHASE 14.7 — Trading Product Engine
====================================
Unified orchestration engine that calls all modules in sequence
and produces a single trading product snapshot.

Pipeline:
    TAHypothesis → ExchangeContext → MarketStateMatrix 
        → TradingDecision → PositionSizing → ExecutionMode
        → TradingProductSnapshot

PHASE 14.9: Now integrates Dominance/Breadth overlay into final output.
PHASE 15.7: Now integrates Alpha Ecology layer into final output.
PHASE 18.4: Now integrates Meta Portfolio layer into final output.
PHASE 24.4: Now integrates Fractal Intelligence into final output.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.trading_product.trading_product_types import (
    TradingProductSnapshot,
    ProductStatus,
    OverlayEffect,
    PortfolioOverlayEffect,
)

# MongoDB
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


class TradingProductEngine:
    """
    Unified Trading Product Engine.
    
    Orchestrates all modules into a single product output.
    
    PHASE 14.9: Now includes dominance/breadth overlay integration.
    PHASE 15.7: Now includes alpha ecology integration.
    PHASE 18.4: Now includes meta portfolio integration.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load all engines
        self._ta_builder = None
        self._exchange_aggregator = None
        self._market_state_builder = None
        self._decision_engine = None
        self._sizing_engine = None
        self._execution_engine = None
        self._market_structure_engine = None  # PHASE 14.9
        self._ecology_overlay = None  # PHASE 15.7
        self._meta_portfolio_engine = None  # PHASE 18.4
    
    # ═══════════════════════════════════════════════════════════════
    # LAZY LOADERS
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def ta_builder(self):
        if self._ta_builder is None:
            from modules.ta_engine.hypothesis.ta_hypothesis_builder import get_hypothesis_builder
            self._ta_builder = get_hypothesis_builder()
        return self._ta_builder
    
    @property
    def exchange_aggregator(self):
        if self._exchange_aggregator is None:
            from modules.exchange_intelligence.exchange_context_aggregator import ExchangeContextAggregator
            self._exchange_aggregator = ExchangeContextAggregator()
        return self._exchange_aggregator
    
    @property
    def market_state_builder(self):
        if self._market_state_builder is None:
            from modules.trading_decision.market_state.market_state_builder import get_market_state_builder
            self._market_state_builder = get_market_state_builder()
        return self._market_state_builder
    
    @property
    def decision_engine(self):
        if self._decision_engine is None:
            from modules.trading_decision.decision_layer.decision_engine import get_decision_engine
            self._decision_engine = get_decision_engine()
        return self._decision_engine
    
    @property
    def sizing_engine(self):
        if self._sizing_engine is None:
            from modules.trading_decision.position_sizing.position_sizing_engine import get_position_sizing_engine
            self._sizing_engine = get_position_sizing_engine()
        return self._sizing_engine
    
    @property
    def execution_engine(self):
        if self._execution_engine is None:
            from modules.trading_decision.execution_mode.execution_mode_engine import get_execution_mode_engine
            self._execution_engine = get_execution_mode_engine()
        return self._execution_engine
    
    @property
    def market_structure_engine(self):
        """PHASE 14.9: Market structure for dominance/breadth."""
        if self._market_structure_engine is None:
            from modules.market_structure.breadth_dominance.market_structure_engine import get_market_structure_engine
            self._market_structure_engine = get_market_structure_engine()
        return self._market_structure_engine
    
    @property
    def ecology_overlay(self):
        """PHASE 15.7: Ecology overlay for alpha health."""
        if self._ecology_overlay is None:
            from modules.trading.ecology_overlay import get_ecology_overlay
            self._ecology_overlay = get_ecology_overlay()
        return self._ecology_overlay
    
    @property
    def meta_portfolio_engine(self):
        """PHASE 18.4: Meta Portfolio for portfolio-level risk management."""
        if self._meta_portfolio_engine is None:
            try:
                from modules.portfolio.meta_portfolio.meta_portfolio_engine import get_meta_portfolio_engine
                self._meta_portfolio_engine = get_meta_portfolio_engine()
            except ImportError:
                pass
        return self._meta_portfolio_engine
    
    @property
    def fractal_context_engine(self):
        """PHASE 24.4: Fractal Intelligence for historical analog signals."""
        if not hasattr(self, '_fractal_context_engine'):
            self._fractal_context_engine = None
        if self._fractal_context_engine is None:
            try:
                from modules.fractal_intelligence.fractal_context_engine import FractalContextEngine
                self._fractal_context_engine = FractalContextEngine()
            except ImportError:
                pass
        return self._fractal_context_engine
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════════
    
    def compute(self, symbol: str) -> TradingProductSnapshot:
        """
        Compute full trading product snapshot for symbol.
        
        Calls all modules in sequence and assembles unified output.
        
        PHASE 14.9: Now includes dominance/breadth overlay.
        PHASE 15.7: Now includes alpha ecology.
        PHASE 18.4: Now includes meta portfolio layer.
        """
        now = datetime.now(timezone.utc)
        
        # ── Step 1: TA Hypothesis ──
        ta_output = self._get_ta_hypothesis(symbol)
        
        # ── Step 2: Exchange Context ──
        exchange_output = self._get_exchange_context(symbol)
        
        # ── Step 3: Market State ──
        market_state_output = self._get_market_state(symbol)
        
        # ── Step 4: Trading Decision ──
        decision_output = self._get_trading_decision(symbol)
        
        # ── Step 5: Position Sizing ──
        sizing_output = self._get_position_sizing(symbol)
        
        # ── Step 6: Execution Mode ──
        execution_output = self._get_execution_mode(symbol)
        
        # ── PHASE 14.9: Step 7: Get Dominance/Breadth Overlay ──
        overlay_data = self._get_overlay_data(symbol)
        
        # ── PHASE 15.7: Step 8: Get Ecology Data ──
        ecology_data = self._get_ecology_data(symbol)
        
        # ── PHASE 18.4: Step 9: Get Meta Portfolio Data ──
        meta_portfolio_data = self._get_meta_portfolio_data(symbol)
        
        # ── PHASE 24.4: Step 10: Get Fractal Intelligence Data ──
        fractal_data = self._get_fractal_data(symbol)
        
        # ── Aggregate final outputs ──
        final_action = decision_output.get("action", "WAIT")
        final_direction = decision_output.get("direction", "NEUTRAL")
        final_confidence = decision_output.get("confidence", 0.0)
        final_size_pct = sizing_output.get("final_size_pct", 0.0)
        final_execution_mode = execution_output.get("execution_mode", "NONE")
        
        # ── PHASE 18.4: Apply meta portfolio modifiers ──
        portfolio_allowed = meta_portfolio_data.get("allowed", True)
        portfolio_state = meta_portfolio_data.get("portfolio_state", "BALANCED")
        portfolio_confidence_modifier = meta_portfolio_data.get("confidence_modifier", 1.0)
        portfolio_capital_modifier = meta_portfolio_data.get("capital_modifier", 1.0)
        
        # Apply portfolio confidence modifier to final_confidence
        final_confidence = final_confidence * portfolio_confidence_modifier
        
        # Apply portfolio capital modifier to final_size
        final_size_pct = final_size_pct * portfolio_capital_modifier
        
        # PHASE 18.4: Override if portfolio blocks
        if not portfolio_allowed:
            final_action = "BLOCK"
            final_execution_mode = "NONE"
            final_size_pct = 0.0
        
        # PHASE 18.4: Restrict execution mode based on portfolio state
        final_execution_mode = self._apply_portfolio_execution_restriction(
            final_execution_mode, portfolio_state, portfolio_allowed
        )
        
        # ── Determine product status (PHASE 18.4: portfolio-aware) ──
        product_status, reason = self._determine_product_status(
            final_action, final_execution_mode, 
            decision_output, execution_output, exchange_output,
            portfolio_allowed, portfolio_state
        )
        
        # ── PHASE 14.9: Determine overlay effect ──
        overlay_effect = self._determine_overlay_effect(
            symbol, overlay_data, final_action
        )
        
        # ── PHASE 18.4: Determine portfolio overlay effect ──
        portfolio_overlay_effect = self._determine_portfolio_overlay_effect(
            portfolio_state, portfolio_allowed
        )
        
        # Build meta_portfolio block for output
        meta_portfolio_block = {
            "portfolio_state": portfolio_state,
            "allowed": portfolio_allowed,
            "confidence_modifier": round(portfolio_confidence_modifier, 4),
            "capital_modifier": round(portfolio_capital_modifier, 4),
            "recommended_action": meta_portfolio_data.get("recommended_action", "HOLD"),
        }
        
        return TradingProductSnapshot(
            symbol=symbol,
            timestamp=now,
            final_action=final_action,
            final_direction=final_direction,
            final_confidence=final_confidence,
            final_size_pct=final_size_pct,
            final_execution_mode=final_execution_mode,
            product_status=product_status,
            reason=reason,
            # PHASE 14.9
            dominance_state=overlay_data.get("dominance_regime", "BALANCED"),
            breadth_state=overlay_data.get("breadth_state", "MIXED"),
            dominance_modifier=overlay_data.get("confidence_modifier", 1.0),
            breadth_modifier=overlay_data.get("size_modifier", 1.0),
            overlay_effect=overlay_effect,
            # PHASE 15.7
            ecology_state=ecology_data.get("state", "STABLE"),
            ecology_score=ecology_data.get("score", 1.0),
            ecology_modifier=ecology_data.get("size_modifier", 1.0),
            ecology_weakest=ecology_data.get("weakest", "none"),
            # PHASE 18.4
            portfolio_state=portfolio_state,
            portfolio_allowed=portfolio_allowed,
            portfolio_confidence_modifier=portfolio_confidence_modifier,
            portfolio_capital_modifier=portfolio_capital_modifier,
            portfolio_overlay_effect=portfolio_overlay_effect,
            meta_portfolio=meta_portfolio_block,
            # Module outputs
            ta_hypothesis=ta_output,
            exchange_context=exchange_output,
            market_state=market_state_output,
            trading_decision=decision_output,
            position_sizing=sizing_output,
            execution_mode=execution_output,
            ecology=ecology_data,  # PHASE 15.7
            # PHASE 24.4
            fractal=fractal_data,
        )
    
    def compute_batch(self, symbols: List[str]) -> List[TradingProductSnapshot]:
        """Compute product snapshots for multiple symbols."""
        return [self.compute(symbol) for symbol in symbols]
    
    # ═══════════════════════════════════════════════════════════════
    # MODULE GETTERS
    # ═══════════════════════════════════════════════════════════════
    
    def _get_ta_hypothesis(self, symbol: str) -> Dict[str, Any]:
        """Get TA Hypothesis output."""
        try:
            hypothesis = self.ta_builder.build(symbol)
            return {
                "direction": hypothesis.direction.value,
                "regime": hypothesis.regime.value,
                "setup_type": hypothesis.setup_type.value,
                "setup_quality": round(hypothesis.setup_quality, 4),
                "trend_strength": round(hypothesis.trend_strength, 4),
                "conviction": round(hypothesis.conviction, 4),
                "entry_quality": round(hypothesis.entry_quality, 4),
            }
        except Exception as e:
            return {"error": str(e), "direction": "NEUTRAL", "conviction": 0.0}
    
    def _get_exchange_context(self, symbol: str) -> Dict[str, Any]:
        """Get Exchange Context output."""
        try:
            context = self.exchange_aggregator.compute(symbol)
            return {
                "bias": context.exchange_bias.value,
                "confidence": round(context.confidence, 4),
                "crowding_risk": round(context.crowding_risk, 4),
                "squeeze_probability": round(context.squeeze_probability, 4),
                "cascade_probability": round(context.cascade_probability, 4),
                "flow_pressure": round(context.flow_pressure, 4),
                "derivatives_pressure": round(context.derivatives_pressure, 4),
            }
        except Exception as e:
            return {"error": str(e), "bias": "NEUTRAL", "confidence": 0.5}
    
    def _get_market_state(self, symbol: str) -> Dict[str, Any]:
        """Get Market State output."""
        try:
            state = self.market_state_builder.build(symbol)
            return {
                "trend_state": state.trend_state.value,
                "volatility_state": state.volatility_state.value,
                "exchange_state": state.exchange_state.value,
                "derivatives_state": state.derivatives_state.value,
                "risk_state": state.risk_state.value,
                "combined_state": state.combined_state.value,
                "confidence": round(state.confidence, 4),
            }
        except Exception as e:
            return {"error": str(e), "combined_state": "UNDEFINED", "confidence": 0.5}
    
    def _get_trading_decision(self, symbol: str) -> Dict[str, Any]:
        """Get Trading Decision output."""
        try:
            decision = self.decision_engine.decide(symbol)
            return {
                "action": decision.action.value,
                "direction": decision.direction.value,
                "confidence": round(decision.confidence, 4),
                "position_multiplier": round(decision.position_multiplier, 4),
                "execution_mode": decision.execution_mode.value,
                "decision_rule": decision.decision_rule.value,
                "reason": decision.reason,
            }
        except Exception as e:
            return {"error": str(e), "action": "WAIT", "direction": "NEUTRAL", "confidence": 0.0}
    
    def _get_position_sizing(self, symbol: str) -> Dict[str, Any]:
        """Get Position Sizing output. PHASE 14.9: includes dom/breadth adjustments."""
        try:
            sizing = self.sizing_engine.compute(symbol)
            return {
                "base_risk": round(sizing.base_risk, 4),
                "risk_multiplier": round(sizing.risk_multiplier, 4),
                "volatility_adjustment": round(sizing.volatility_adjustment, 4),
                "exchange_adjustment": round(sizing.exchange_adjustment, 4),
                "market_adjustment": round(sizing.market_adjustment, 4),
                # PHASE 14.9
                "dominance_adjustment": round(sizing.dominance_adjustment, 4),
                "breadth_adjustment": round(sizing.breadth_adjustment, 4),
                "final_size_pct": round(sizing.final_size_pct, 4),
                "size_bucket": sizing.size_bucket.value,
            }
        except Exception as e:
            return {"error": str(e), "final_size_pct": 0.0, "size_bucket": "NONE"}
    
    def _get_execution_mode(self, symbol: str) -> Dict[str, Any]:
        """Get Execution Mode output."""
        try:
            mode = self.execution_engine.compute(symbol)
            return {
                "execution_mode": mode.execution_mode.value,
                "urgency_score": round(mode.urgency_score, 4),
                "slippage_tolerance": round(mode.slippage_tolerance, 4),
                "entry_style": mode.entry_style.value,
                "partial_ratio": round(mode.partial_ratio, 4),
                "reason": mode.reason,
            }
        except Exception as e:
            return {"error": str(e), "execution_mode": "NONE", "urgency_score": 0.0}
    
    def _get_overlay_data(self, symbol: str) -> Dict[str, Any]:
        """
        PHASE 14.9: Get dominance/breadth overlay data.
        """
        try:
            return self.market_structure_engine.get_modifier_for_symbol(symbol)
        except Exception:
            return {
                "confidence_modifier": 1.0,
                "size_modifier": 1.0,
                "dominance_regime": "BALANCED",
                "breadth_state": "MIXED",
                "rotation_state": "STABLE",
            }
    
    def _get_ecology_data(self, symbol: str) -> Dict[str, Any]:
        """
        PHASE 15.7: Get alpha ecology data for trading product.
        
        Returns ecology state formatted for TradingProductSnapshot.
        """
        try:
            return self.ecology_overlay.get_trading_product_ecology(symbol)
        except Exception:
            return {
                "state": "STABLE",
                "score": 1.0,
                "confidence_modifier": 1.0,
                "size_modifier": 1.0,
                "weakest": "none",
                "strongest": "none",
                "components": {},
            }
    
    def _get_meta_portfolio_data(self, symbol: str) -> Dict[str, Any]:
        """
        PHASE 18.4: Get meta portfolio data for trading product.
        
        Returns portfolio state with modifiers.
        """
        if self.meta_portfolio_engine is None:
            return {
                "portfolio_state": "BALANCED",
                "allowed": True,
                "confidence_modifier": 1.0,
                "capital_modifier": 1.0,
                "recommended_action": "HOLD",
            }
        
        try:
            # Use default portfolio for now (can be extended per symbol)
            result = self.meta_portfolio_engine.analyze_portfolio("default")
            return {
                "portfolio_state": result.portfolio_state.value,
                "allowed": result.allowed,
                "confidence_modifier": result.confidence_modifier,
                "capital_modifier": result.capital_modifier,
                "recommended_action": result.recommended_action,
                "intelligence_state": result.intelligence_state,
                "constraint_state": result.constraint_state,
                "net_exposure": result.net_exposure,
                "gross_exposure": result.gross_exposure,
                "concentration_score": result.concentration_score,
            }
        except Exception:
            return {
                "portfolio_state": "BALANCED",
                "allowed": True,
                "confidence_modifier": 1.0,
                "capital_modifier": 1.0,
                "recommended_action": "HOLD",
            }
    
    def _get_fractal_data(self, symbol: str) -> Dict[str, Any]:
        """
        PHASE 24.4: Get fractal intelligence data for trading product.
        
        Returns fractal context formatted for TradingProductSnapshot.
        This is purely observability/explainability - does NOT affect decisions.
        """
        # Default inactive fractal
        default_fractal = {
            "is_active": False,
            "direction": "HOLD",
            "confidence": 0.0,
            "reliability": 0.0,
            "phase": "UNKNOWN",
            "dominant_horizon": None,
            "context_state": "BLOCKED",
            "strength": 0.0,
        }
        
        if self.fractal_context_engine is None:
            return default_fractal
        
        try:
            import asyncio
            
            loop = asyncio.new_event_loop()
            try:
                context = loop.run_until_complete(
                    self.fractal_context_engine.build_context(symbol)
                )
            finally:
                loop.close()
            
            is_active = context.context_state not in ["BLOCKED"] and context.direction != "HOLD"
            
            return {
                "is_active": is_active,
                "direction": context.direction,
                "confidence": round(context.confidence, 4),
                "reliability": round(context.reliability, 4),
                "phase": context.phase or "UNKNOWN",
                "dominant_horizon": context.dominant_horizon,
                "context_state": context.context_state,
                "strength": round(context.fractal_strength, 4),
            }
        except Exception:
            return default_fractal
    
    def _apply_portfolio_execution_restriction(
        self,
        execution_mode: str,
        portfolio_state: str,
        portfolio_allowed: bool,
    ) -> str:
        """
        PHASE 18.4: Apply portfolio-based execution mode restrictions.
        
        Rules:
        - RISK_OFF: execution_mode = NONE
        - CONSTRAINED: AGGRESSIVE forbidden, prefer PASSIVE/PARTIAL
        - BALANCED: No restrictions
        """
        if not portfolio_allowed or portfolio_state == "RISK_OFF":
            return "NONE"
        
        if portfolio_state == "CONSTRAINED":
            # Forbid AGGRESSIVE
            if execution_mode == "AGGRESSIVE":
                return "NORMAL"
        
        return execution_mode
    
    def _determine_portfolio_overlay_effect(
        self,
        portfolio_state: str,
        portfolio_allowed: bool,
    ) -> PortfolioOverlayEffect:
        """
        PHASE 18.4: Determine portfolio overlay effect.
        
        Returns: SUPPORTIVE / NEUTRAL / RESTRICTIVE / BLOCKING
        """
        if not portfolio_allowed:
            return PortfolioOverlayEffect.BLOCKING
        
        if portfolio_state == "RISK_OFF":
            return PortfolioOverlayEffect.BLOCKING
        
        if portfolio_state == "CONSTRAINED":
            return PortfolioOverlayEffect.RESTRICTIVE
        
        if portfolio_state == "BALANCED":
            return PortfolioOverlayEffect.SUPPORTIVE
        
        return PortfolioOverlayEffect.NEUTRAL
    
    def _determine_overlay_effect(
        self,
        symbol: str,
        overlay_data: Dict[str, Any],
        action: str,
    ) -> OverlayEffect:
        """
        PHASE 14.9: Determine overlay effect (SUPPORTIVE/NEUTRAL/HOSTILE).
        
        Based on:
        - Dominance regime vs symbol type
        - Breadth state
        - Rotation state
        """
        if action in ("BLOCK", "WAIT"):
            return OverlayEffect.NEUTRAL
        
        dominance_regime = overlay_data.get("dominance_regime", "BALANCED")
        breadth_state = overlay_data.get("breadth_state", "MIXED")
        rotation_state = overlay_data.get("rotation_state", "STABLE")
        
        # Determine asset class
        is_btc = symbol == "BTC"
        is_eth = symbol == "ETH"
        is_alt = symbol not in ("BTC", "ETH")
        
        score = 0
        
        # Dominance regime impact
        if is_btc:
            if dominance_regime == "BTC_DOM":
                score += 2
            elif dominance_regime == "ALT_DOM":
                score -= 1
        elif is_eth:
            if dominance_regime == "ETH_DOM":
                score += 2
            elif dominance_regime == "BTC_DOM":
                score -= 1
        else:  # ALT
            if dominance_regime == "ALT_DOM":
                score += 2
            elif dominance_regime == "BTC_DOM":
                score -= 2
        
        # Breadth state impact
        if breadth_state == "STRONG":
            score += 1
        elif breadth_state == "WEAK":
            score -= 2
        
        # Rotation state impact
        if rotation_state == "EXITING_MARKET":
            score -= 3
        elif rotation_state == "ROTATING_TO_BTC" and is_btc:
            score += 1
        elif rotation_state == "ROTATING_TO_ALTS" and is_alt:
            score += 1
        
        # Determine effect
        if score >= 2:
            return OverlayEffect.SUPPORTIVE
        elif score <= -2:
            return OverlayEffect.HOSTILE
        else:
            return OverlayEffect.NEUTRAL
    
    # ═══════════════════════════════════════════════════════════════
    # PRODUCT STATUS DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_product_status(
        self,
        action: str,
        execution_mode: str,
        decision_output: Dict,
        execution_output: Dict,
        exchange_output: Dict,
        portfolio_allowed: bool = True,
        portfolio_state: str = "BALANCED",
    ) -> tuple:
        """
        Determine final product status.
        
        Returns: (ProductStatus, reason)
        
        PHASE 18.4: Now considers portfolio state.
        """
        
        # PHASE 18.4: BLOCKED if portfolio forbids
        if not portfolio_allowed or portfolio_state == "RISK_OFF":
            return (ProductStatus.BLOCKED, "portfolio_risk_off_no_new_positions")
        
        # BLOCKED: action is BLOCK or size is 0
        if action == "BLOCK":
            return (ProductStatus.BLOCKED, "trading_blocked_by_decision_layer")
        
        # WAIT: action is WAIT or execution is DELAYED/NONE
        if action == "WAIT":
            return (ProductStatus.WAIT, "waiting_for_valid_setup")
        
        if execution_mode in ("NONE", "DELAYED"):
            if action == "REVERSE_CANDIDATE":
                return (ProductStatus.WAIT, "reverse_candidate_waiting")
            return (ProductStatus.WAIT, "execution_delayed_due_to_conditions")
        
        # CONFLICTED: ALLOW_REDUCED with high conflict and passive/partial execution
        if action == "ALLOW_REDUCED":
            # Check if we computed conflict somewhere
            if execution_mode in ("PASSIVE", "PARTIAL_ENTRY"):
                return (ProductStatus.CONFLICTED, "valid_but_conflicted_reduced_execution")
        
        # Check for conflict in ALLOW with PARTIAL_ENTRY
        if action == "ALLOW" and execution_mode == "PARTIAL_ENTRY":
            return (ProductStatus.CONFLICTED, "valid_but_partial_due_to_uncertainty")
        
        # PHASE 18.4: CONSTRAINED portfolio triggers CONFLICTED status
        if portfolio_state == "CONSTRAINED":
            if action in ("ALLOW", "ALLOW_AGGRESSIVE", "ALLOW_REDUCED"):
                return (ProductStatus.CONFLICTED, "valid_but_portfolio_constrained")
        
        # READY: action is ALLOW/ALLOW_AGGRESSIVE and execution is not blocked
        if action in ("ALLOW", "ALLOW_AGGRESSIVE", "ALLOW_REDUCED"):
            if execution_mode in ("NORMAL", "AGGRESSIVE", "PASSIVE"):
                if action == "ALLOW_AGGRESSIVE":
                    return (ProductStatus.READY, "strong_setup_ready_for_aggressive_execution")
                elif action == "ALLOW":
                    return (ProductStatus.READY, "valid_setup_ready_for_execution")
                else:
                    return (ProductStatus.READY, "reduced_setup_ready_for_passive_execution")
        
        # Default fallback
        return (ProductStatus.WAIT, "unknown_conditions_defaulting_to_wait")


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[TradingProductEngine] = None


def get_trading_product_engine() -> TradingProductEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = TradingProductEngine()
    return _engine
