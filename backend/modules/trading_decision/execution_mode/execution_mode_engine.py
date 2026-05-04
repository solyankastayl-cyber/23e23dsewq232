"""
PHASE 14.6 — Execution Mode Engine
===================================
Determines HOW to execute a trade based on multiple factors.

Architecture:
    TradingDecision ──────────┐
                               │
    PositionSizingDecision ────┼── Execution Mode Engine ── ExecutionModeDecision
                               │
    ExchangeContext ───────────┤
                               │
    MarketStateMatrix ─────────┤
                               │
    MarketStructure ───────────┤  (PHASE 14.9)
                               │
    AlphaEcology ──────────────┘  (PHASE 15.7)

Output: NONE / PASSIVE / NORMAL / AGGRESSIVE / DELAYED / PARTIAL_ENTRY

PHASE 14.9: Dominance/Breadth can DOWNGRADE execution mode
PHASE 15.7: Ecology can FORBID AGGRESSIVE when CRITICAL
    
    AGGRESSIVE → NORMAL (when ecology CRITICAL)
    
But NEVER upgrades or changes direction/size.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.trading_decision.execution_mode.execution_mode_types import (
    ExecutionModeDecision,
    ExecutionMode,
    EntryStyle,
    DecisionInputSnapshot,
    SizingInputSnapshot,
    ExchangeInputSnapshot,
    MarketStateInputSnapshot,
)
from modules.trading_decision.execution_mode.execution_mode_rules import (
    BLOCKED_ACTIONS,
    AGGRESSIVE_RULES,
    NORMAL_RULES,
    PASSIVE_RULES,
    PARTIAL_ENTRY_RULES,
    DELAYED_RULES,
    URGENCY_WEIGHTS,
    URGENCY_PENALTIES,
    URGENCY_BONUSES,
    SLIPPAGE_TOLERANCE,
    ENTRY_STYLE_MAP,
)

# MongoDB
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


class ExecutionModeEngine:
    """
    Execution Mode Engine.
    
    Determines how to execute a trade based on signal quality,
    position size, market state, and exchange context.
    
    PHASE 14.9: Now includes dominance/breadth downgrade logic.
    PHASE 16.6: Now includes interaction aggregator downgrade logic.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load other engines
        self._decision_engine = None
        self._sizing_engine = None
        self._exchange_aggregator = None
        self._market_state_builder = None
        self._market_structure_engine = None  # PHASE 14.9
        self._ecology_overlay = None  # PHASE 15.7
        self._interaction_aggregator = None  # PHASE 16.6
    
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
    def interaction_aggregator(self):
        """PHASE 16.6: Interaction aggregator for combined interaction modifiers."""
        if self._interaction_aggregator is None:
            try:
                from modules.alpha_interactions.interaction_aggregator import get_interaction_aggregator
                self._interaction_aggregator = get_interaction_aggregator()
            except ImportError:
                pass
        return self._interaction_aggregator
    
    def compute(self, symbol: str) -> ExecutionModeDecision:
        """
        Compute execution mode for symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            ExecutionModeDecision with mode, urgency, slippage, etc.
            
        PHASE 15.7: Includes ecology downgrade logic (CRITICAL forbids AGGRESSIVE).
        PHASE 16.6: Includes interaction downgrade logic (RESTRICT forbids AGGRESSIVE).
        """
        now = datetime.now(timezone.utc)
        
        # Get all inputs
        decision_input = self._get_decision_input(symbol)
        sizing_input = self._get_sizing_input(symbol)
        exchange_input = self._get_exchange_input(symbol)
        market_state_input = self._get_market_state_input(symbol)
        
        # PHASE 14.9: Get dominance/breadth modifiers
        dom_modifier = self._get_dominance_modifier(symbol)
        
        # PHASE 15.7: Get ecology modifier
        ecology_modifier = self._get_ecology_modifier(symbol)
        
        # PHASE 16.6: Get interaction aggregate modifier
        interaction_modifier = self._get_interaction_modifier(symbol)
        
        # Determine execution mode
        mode, reason = self._determine_execution_mode(
            decision_input, sizing_input, exchange_input, market_state_input
        )
        
        # PHASE 14.9: Apply dominance/breadth downgrade
        mode, reason = self._apply_dominance_downgrade(
            mode, reason, dom_modifier, symbol
        )
        
        # PHASE 15.7: Apply ecology downgrade (CRITICAL forbids AGGRESSIVE)
        mode, reason = self._apply_ecology_downgrade(
            mode, reason, ecology_modifier
        )
        
        # PHASE 16.6: Apply interaction downgrade (RESTRICT forbids AGGRESSIVE)
        mode, reason = self._apply_interaction_downgrade(
            mode, reason, interaction_modifier
        )
        
        # Compute urgency
        urgency = self._compute_urgency(
            decision_input, exchange_input, market_state_input, mode
        )
        
        # Compute slippage tolerance
        slippage = self._compute_slippage(mode, urgency)
        
        # Determine entry style
        entry_style = self._determine_entry_style(mode)
        
        # Compute partial ratio
        partial_ratio = self._compute_partial_ratio(
            mode, exchange_input, sizing_input
        )
        
        # Build drivers (PHASE 16.6: extended)
        drivers = self._build_drivers(
            decision_input, sizing_input, exchange_input, market_state_input, 
            dom_modifier, ecology_modifier, interaction_modifier
        )
        
        # Build summaries
        decision_summary = {
            "action": decision_input.action,
            "direction": decision_input.direction,
            "confidence": round(decision_input.confidence, 4),
        }
        
        sizing_summary = {
            "final_size_pct": round(sizing_input.final_size_pct, 4),
            "size_bucket": sizing_input.size_bucket,
        }
        
        return ExecutionModeDecision(
            symbol=symbol,
            timestamp=now,
            execution_mode=mode,
            urgency_score=urgency,
            slippage_tolerance=slippage,
            entry_style=entry_style,
            partial_ratio=partial_ratio,
            reason=reason,
            drivers=drivers,
            decision_summary=decision_summary,
            sizing_summary=sizing_summary,
        )
    
    def compute_batch(self, symbols: List[str]) -> List[ExecutionModeDecision]:
        """Compute execution mode for multiple symbols."""
        return [self.compute(symbol) for symbol in symbols]
    
    # ═══════════════════════════════════════════════════════════════
    # INPUT GETTERS
    # ═══════════════════════════════════════════════════════════════
    
    def _get_decision_input(self, symbol: str) -> DecisionInputSnapshot:
        """Get Trading Decision as input."""
        try:
            decision = self.decision_engine.decide(symbol)
            return DecisionInputSnapshot(
                action=decision.action.value,
                direction=decision.direction.value,
                confidence=decision.confidence,
                execution_mode_hint=decision.execution_mode.value,
            )
        except Exception:
            return DecisionInputSnapshot(
                action="WAIT",
                direction="NEUTRAL",
                confidence=0.0,
                execution_mode_hint="NONE",
            )
    
    def _get_sizing_input(self, symbol: str) -> SizingInputSnapshot:
        """Get Position Sizing as input."""
        try:
            sizing = self.sizing_engine.compute(symbol)
            return SizingInputSnapshot(
                final_size_pct=sizing.final_size_pct,
                size_bucket=sizing.size_bucket.value,
                risk_multiplier=sizing.risk_multiplier,
            )
        except Exception:
            return SizingInputSnapshot(
                final_size_pct=0.0,
                size_bucket="NONE",
                risk_multiplier=0.0,
            )
    
    def _get_exchange_input(self, symbol: str) -> ExchangeInputSnapshot:
        """Get Exchange Context as input."""
        try:
            context = self.exchange_aggregator.compute(symbol)
            
            # Compute conflict ratio
            signals = []
            if context.funding_signal:
                signals.append(1 if context.funding_signal.funding_rate > 0 else -1)
            signals.append(1 if context.flow_pressure > 0 else -1)
            signals.append(1 if context.derivatives_pressure > 0 else -1)
            
            if signals:
                avg = sum(signals) / len(signals)
                conflict = sum((s - avg) ** 2 for s in signals) / len(signals)
            else:
                conflict = 0
            
            # Determine dominant signal
            driver_scores = {
                "funding": abs(context.funding_signal.funding_rate * 100) if context.funding_signal else 0,
                "flow": abs(context.flow_pressure),
                "derivatives": abs(context.derivatives_pressure),
                "liquidations": context.cascade_probability,
                "volume": context.volume_signal.anomaly_score if context.volume_signal else 0,
            }
            dominant = max(driver_scores, key=driver_scores.get)
            
            return ExchangeInputSnapshot(
                conflict_ratio=min(conflict, 1.0),
                dominant_signal=dominant,
                squeeze_probability=context.squeeze_probability,
                confidence=context.confidence,
                crowding_risk=context.crowding_risk,
            )
        except Exception:
            return ExchangeInputSnapshot(
                conflict_ratio=0.5,
                dominant_signal="none",
                squeeze_probability=0.0,
                confidence=0.5,
                crowding_risk=0.0,
            )
    
    def _get_market_state_input(self, symbol: str) -> MarketStateInputSnapshot:
        """Get Market State as input."""
        try:
            state = self.market_state_builder.build(symbol)
            return MarketStateInputSnapshot(
                volatility_state=state.volatility_state.value,
                exchange_state=state.exchange_state.value,
                derivatives_state=state.derivatives_state.value,
                combined_state=state.combined_state.value,
                risk_state=state.risk_state.value,
            )
        except Exception:
            return MarketStateInputSnapshot(
                volatility_state="NORMAL",
                exchange_state="NEUTRAL",
                derivatives_state="BALANCED",
                combined_state="UNDEFINED",
                risk_state="NEUTRAL",
            )
    
    def _get_dominance_modifier(self, symbol: str) -> Dict[str, float]:
        """
        PHASE 14.9: Get dominance/breadth modifiers for symbol.
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
    
    def _get_ecology_modifier(self, symbol: str) -> Dict[str, Any]:
        """
        PHASE 15.7: Get ecology modifiers for symbol.
        """
        try:
            return self.ecology_overlay.ecology_engine.get_modifier_for_symbol(symbol)
        except Exception:
            return {
                "ecology_confidence_modifier": 1.0,
                "ecology_size_modifier": 1.0,
                "ecology_score": 1.0,
                "ecology_state": "STABLE",
                "weakest_component": "none",
            }
    
    def _get_interaction_modifier(self, symbol: str) -> Dict[str, Any]:
        """
        PHASE 16.6: Get interaction aggregate modifiers for symbol.
        """
        if self.interaction_aggregator is None:
            return {
                "interaction_execution_modifier": "NORMAL",
                "interaction_state": "NEUTRAL",
                "interaction_score": 0.0,
                "strongest_force": "none",
                "cancellation_override": False,
            }
        
        try:
            return self.interaction_aggregator.get_aggregate_for_symbol(symbol)
        except Exception:
            return {
                "interaction_execution_modifier": "NORMAL",
                "interaction_state": "NEUTRAL",
                "interaction_score": 0.0,
                "strongest_force": "none",
                "cancellation_override": False,
            }
    
    def _apply_ecology_downgrade(
        self,
        mode: ExecutionMode,
        reason: str,
        ecology_modifier: Dict[str, Any],
    ) -> Tuple[ExecutionMode, str]:
        """
        PHASE 15.7: Apply ecology downgrade to execution mode.
        
        Rule:
            CRITICAL ecology state → AGGRESSIVE mode forbidden → downgrade to NORMAL
            
        This is the ONLY ecology rule for execution mode.
        Ecology doesn't downgrade further than NORMAL.
        """
        if mode in (ExecutionMode.NONE, ExecutionMode.DELAYED):
            return (mode, reason)
        
        ecology_state = ecology_modifier.get("ecology_state", "STABLE")
        weakest = ecology_modifier.get("weakest_component", "unknown")
        
        # Rule: CRITICAL forbids AGGRESSIVE
        if ecology_state == "CRITICAL" and mode == ExecutionMode.AGGRESSIVE:
            return (
                ExecutionMode.NORMAL, 
                f"{reason}__ecology_critical_forbid_aggressive_{weakest}"
            )
        
        return (mode, reason)
    
    def _apply_interaction_downgrade(
        self,
        mode: ExecutionMode,
        reason: str,
        interaction_modifier: Dict[str, Any],
    ) -> Tuple[ExecutionMode, str]:
        """
        PHASE 16.6: Apply interaction downgrade to execution mode.
        
        Rules:
            RESTRICT modifier → AGGRESSIVE mode forbidden → downgrade to NORMAL
            CAUTION modifier → no upgrade to AGGRESSIVE
            
        Interaction aggregator provides a RECOMMENDATION via execution_modifier:
            BOOST    → can increase aggressiveness (not implemented here)
            NORMAL   → no change
            CAUTION  → reduce aggressiveness if AGGRESSIVE
            RESTRICT → forbid AGGRESSIVE
            
        This function only DOWNGRADES, never upgrades.
        """
        if mode in (ExecutionMode.NONE, ExecutionMode.DELAYED):
            return (mode, reason)
        
        exec_modifier = interaction_modifier.get("interaction_execution_modifier", "NORMAL")
        interaction_state = interaction_modifier.get("interaction_state", "NEUTRAL")
        strongest_force = interaction_modifier.get("strongest_force", "unknown")
        cancellation_override = interaction_modifier.get("cancellation_override", False)
        
        # Rule 1: RESTRICT forbids AGGRESSIVE (downgrade to NORMAL)
        if exec_modifier == "RESTRICT" and mode == ExecutionMode.AGGRESSIVE:
            extra_reason = "cancellation_override" if cancellation_override else f"interaction_{interaction_state.lower()}"
            return (
                ExecutionMode.NORMAL, 
                f"{reason}__interaction_restrict_forbid_aggressive_{extra_reason}"
            )
        
        # Rule 2: CAUTION downgrades AGGRESSIVE to NORMAL
        if exec_modifier == "CAUTION" and mode == ExecutionMode.AGGRESSIVE:
            return (
                ExecutionMode.NORMAL, 
                f"{reason}__interaction_caution_downgrade_{strongest_force}"
            )
        
        return (mode, reason)
    
    def _apply_dominance_downgrade(
        self,
        mode: ExecutionMode,
        reason: str,
        dom_modifier: Dict[str, float],
        symbol: str,
    ) -> Tuple[ExecutionMode, str]:
        """
        PHASE 14.9: Apply dominance/breadth downgrade to execution mode.
        
        Rules:
        - AGGRESSIVE → NORMAL when BTC_DOM and ALT trade
        - NORMAL → PASSIVE when WEAK breadth
        - PASSIVE → PARTIAL_ENTRY when both hostile
        
        Never upgrades mode. Only downgrades.
        """
        if mode in (ExecutionMode.NONE, ExecutionMode.DELAYED):
            return (mode, reason)
        
        dominance_regime = dom_modifier.get("dominance_regime", "BALANCED")
        breadth_state = dom_modifier.get("breadth_state", "MIXED")
        rotation_state = dom_modifier.get("rotation_state", "STABLE")
        
        # Determine if ALT trade
        is_alt = symbol not in ("BTC", "ETH")
        is_btc_dom = dominance_regime == "BTC_DOM"
        is_weak_breadth = breadth_state == "WEAK"
        is_exiting = rotation_state == "EXITING_MARKET"
        
        new_mode = mode
        downgrade_reasons = []
        
        # Rule 1: AGGRESSIVE → NORMAL for ALT in BTC_DOM
        if mode == ExecutionMode.AGGRESSIVE:
            if is_alt and is_btc_dom:
                new_mode = ExecutionMode.NORMAL
                downgrade_reasons.append("btc_dom_alt_downgrade")
            elif is_weak_breadth:
                new_mode = ExecutionMode.NORMAL
                downgrade_reasons.append("weak_breadth_downgrade")
        
        # Rule 2: NORMAL → PASSIVE for weak breadth or exiting market
        if new_mode == ExecutionMode.NORMAL:
            if is_weak_breadth:
                new_mode = ExecutionMode.PASSIVE
                downgrade_reasons.append("weak_breadth_passive")
            elif is_exiting:
                new_mode = ExecutionMode.PASSIVE
                downgrade_reasons.append("exiting_market_passive")
        
        # Rule 3: PASSIVE → PARTIAL_ENTRY for ALT in BTC_DOM with weak breadth
        if new_mode == ExecutionMode.PASSIVE:
            if is_alt and is_btc_dom and is_weak_breadth:
                new_mode = ExecutionMode.PARTIAL_ENTRY
                downgrade_reasons.append("hostile_overlay_partial")
        
        # Build final reason
        if downgrade_reasons:
            final_reason = f"{reason}__{'+'.join(downgrade_reasons)}"
        else:
            final_reason = reason
        
        return (new_mode, final_reason)
    
    # ═══════════════════════════════════════════════════════════════
    # EXECUTION MODE DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_execution_mode(
        self,
        decision: DecisionInputSnapshot,
        sizing: SizingInputSnapshot,
        exchange: ExchangeInputSnapshot,
        market_state: MarketStateInputSnapshot,
    ) -> Tuple[ExecutionMode, str]:
        """
        Determine execution mode using hierarchical rules.
        Returns: (mode, reason)
        """
        
        # ── Rule: NONE for blocked actions ──
        if decision.action in BLOCKED_ACTIONS:
            return (ExecutionMode.NONE, f"action_{decision.action.lower()}_no_execution")
        
        # ── Rule: DELAYED for hostile conditions ──
        if self._should_delay(decision, exchange, market_state):
            return (ExecutionMode.DELAYED, "hostile_conditions_delay_entry")
        
        # ── Rule: PASSIVE for ALLOW_REDUCED (always passive) ──
        if decision.action == "ALLOW_REDUCED":
            return (ExecutionMode.PASSIVE, "reduced_action_passive_entry")
        
        # ── Rule: PARTIAL_ENTRY for squeeze/conflict with valid signal ──
        if self._should_partial_entry(decision, exchange, sizing):
            return (ExecutionMode.PARTIAL_ENTRY, "squeeze_or_conflict_staged_entry")
        
        # ── Rule: AGGRESSIVE for strong setup ──
        if self._should_be_aggressive(decision, exchange, market_state, sizing):
            return (ExecutionMode.AGGRESSIVE, "strong_setup_aggressive_entry")
        
        # ── Rule: PASSIVE for conflicted (but not reduced) ──
        if self._should_be_passive(decision, exchange):
            return (ExecutionMode.PASSIVE, "conflict_passive_entry")
        
        # ── Default: NORMAL ──
        if self._is_normal_valid(decision, exchange, market_state):
            return (ExecutionMode.NORMAL, "standard_execution")
        
        # Fallback to PASSIVE if uncertain
        return (ExecutionMode.PASSIVE, "uncertain_conditions_passive_entry")
    
    def _should_delay(
        self,
        decision: DecisionInputSnapshot,
        exchange: ExchangeInputSnapshot,
        market_state: MarketStateInputSnapshot,
    ) -> bool:
        """Check if entry should be delayed."""
        # Expanding volatility + hostile state + low confidence
        if market_state.volatility_state in DELAYED_RULES["hostile_volatility"]:
            if market_state.combined_state in DELAYED_RULES["hostile_states"]:
                return True
            if decision.confidence < DELAYED_RULES["max_confidence"]:
                return True
        
        # Hostile state + high conflict + low confidence
        if market_state.combined_state in DELAYED_RULES["hostile_states"]:
            if exchange.conflict_ratio > 0.5 and decision.confidence < 0.6:
                return True
        
        return False
    
    def _should_partial_entry(
        self,
        decision: DecisionInputSnapshot,
        exchange: ExchangeInputSnapshot,
        sizing: SizingInputSnapshot,
    ) -> bool:
        """Check if should use partial entry."""
        # Valid signal but squeeze/conflict risk
        if decision.action not in ["ALLOW", "ALLOW_AGGRESSIVE", "ALLOW_REDUCED"]:
            return False
        
        # Squeeze probability high
        if exchange.squeeze_probability >= PARTIAL_ENTRY_RULES["squeeze_probability_min"]:
            if sizing.size_bucket in PARTIAL_ENTRY_RULES["min_size_buckets"]:
                return True
        
        # High conflict but valid signal
        if exchange.conflict_ratio >= PARTIAL_ENTRY_RULES["conflict_ratio_min"]:
            if decision.confidence >= 0.5:
                return True
        
        return False
    
    def _should_be_aggressive(
        self,
        decision: DecisionInputSnapshot,
        exchange: ExchangeInputSnapshot,
        market_state: MarketStateInputSnapshot,
        sizing: SizingInputSnapshot,
    ) -> bool:
        """Check if should be aggressive."""
        if decision.action != "ALLOW_AGGRESSIVE":
            return False
        
        # Check all aggressive conditions
        if decision.confidence < AGGRESSIVE_RULES["min_confidence"]:
            return False
        
        if exchange.conflict_ratio > AGGRESSIVE_RULES["max_conflict_ratio"]:
            return False
        
        if exchange.squeeze_probability > AGGRESSIVE_RULES["max_squeeze_probability"]:
            return False
        
        if market_state.volatility_state not in AGGRESSIVE_RULES["allowed_volatility"]:
            return False
        
        if sizing.size_bucket not in AGGRESSIVE_RULES["min_size_buckets"]:
            return False
        
        return True
    
    def _should_be_passive(
        self,
        decision: DecisionInputSnapshot,
        exchange: ExchangeInputSnapshot,
    ) -> bool:
        """Check if should be passive."""
        # ALLOW_REDUCED always passive
        if decision.action == "ALLOW_REDUCED":
            return True
        
        # High conflict
        if exchange.conflict_ratio >= PASSIVE_RULES["conflict_ratio_min"]:
            return True
        
        return False
    
    def _is_normal_valid(
        self,
        decision: DecisionInputSnapshot,
        exchange: ExchangeInputSnapshot,
        market_state: MarketStateInputSnapshot,
    ) -> bool:
        """Check if normal execution is valid."""
        if decision.action not in ["ALLOW", "ALLOW_AGGRESSIVE"]:
            return False
        
        if decision.confidence < NORMAL_RULES["min_confidence"]:
            return False
        
        if exchange.conflict_ratio > NORMAL_RULES["max_conflict_ratio"]:
            return False
        
        if exchange.squeeze_probability > NORMAL_RULES["max_squeeze_probability"]:
            return False
        
        if market_state.volatility_state not in NORMAL_RULES["allowed_volatility"]:
            return False
        
        return True
    
    # ═══════════════════════════════════════════════════════════════
    # URGENCY, SLIPPAGE, PARTIAL RATIO
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_urgency(
        self,
        decision: DecisionInputSnapshot,
        exchange: ExchangeInputSnapshot,
        market_state: MarketStateInputSnapshot,
        mode: ExecutionMode,
    ) -> float:
        """Compute urgency score (0..1)."""
        if mode in (ExecutionMode.NONE, ExecutionMode.DELAYED):
            return 0.0
        
        # Base urgency from confidence
        base_urgency = decision.confidence * URGENCY_WEIGHTS["confidence"]
        
        # Agreement component (simplified)
        agreement = 0.5  # Default neutral
        if exchange.conflict_ratio < 0.3:
            agreement = 0.8
        elif exchange.conflict_ratio > 0.5:
            agreement = 0.3
        base_urgency += agreement * URGENCY_WEIGHTS["agreement"]
        
        # Timing component (from market state)
        timing = 0.5
        if market_state.combined_state in ["BREAKOUT_CONFIRMED", "BREAKDOWN_CONFIRMED"]:
            timing = 0.9
        elif market_state.combined_state in ["RANGE_ACCUMULATION", "SQUEEZE_SETUP_LONG", "SQUEEZE_SETUP_SHORT"]:
            timing = 0.7
        base_urgency += timing * URGENCY_WEIGHTS["timing"]
        
        # Apply penalties
        penalties = 0.0
        if market_state.volatility_state == "HIGH":
            penalties += URGENCY_PENALTIES["high_volatility"]
        if exchange.conflict_ratio > 0.5:
            penalties += URGENCY_PENALTIES["high_conflict"]
        if exchange.squeeze_probability > 0.5:
            penalties += URGENCY_PENALTIES["squeeze_risk"]
        if market_state.combined_state in DELAYED_RULES["hostile_states"]:
            penalties += URGENCY_PENALTIES["hostile_market"]
        
        # Apply bonuses
        bonuses = 0.0
        if exchange.conflict_ratio < 0.2 and decision.confidence > 0.7:
            bonuses += URGENCY_BONUSES["strong_agreement"]
        if market_state.volatility_state == "LOW":
            bonuses += URGENCY_BONUSES["low_volatility"]
        if "BREAKOUT" in market_state.combined_state:
            bonuses += URGENCY_BONUSES["breakout_state"]
        
        final_urgency = base_urgency - penalties + bonuses
        
        return max(0.0, min(1.0, final_urgency))
    
    def _compute_slippage(self, mode: ExecutionMode, urgency: float) -> float:
        """Compute slippage tolerance."""
        config = SLIPPAGE_TOLERANCE.get(mode.value, {"value": 0.0})
        
        if "value" in config:
            return config["value"]
        
        # Scale within range based on urgency
        min_slip = config["min"]
        max_slip = config["max"]
        
        return min_slip + (max_slip - min_slip) * urgency
    
    def _determine_entry_style(self, mode: ExecutionMode) -> EntryStyle:
        """Determine entry style from mode."""
        style = ENTRY_STYLE_MAP.get(mode.value, "LIMIT")
        return EntryStyle(style)
    
    def _compute_partial_ratio(
        self,
        mode: ExecutionMode,
        exchange: ExchangeInputSnapshot,
        sizing: SizingInputSnapshot,
    ) -> float:
        """Compute partial entry ratio."""
        if mode == ExecutionMode.PARTIAL_ENTRY:
            # Higher squeeze/conflict = lower initial entry
            risk_factor = (exchange.squeeze_probability + exchange.conflict_ratio) / 2
            ratio_range = PARTIAL_ENTRY_RULES["partial_ratio_range"]
            
            # Higher risk = lower ratio (more staged)
            ratio = ratio_range["max"] - (ratio_range["max"] - ratio_range["min"]) * risk_factor
            return max(ratio_range["min"], min(ratio_range["max"], ratio))
        
        if mode in (ExecutionMode.NONE, ExecutionMode.DELAYED):
            return 0.0
        
        return 1.0  # Full entry for other modes
    
    def _build_drivers(
        self,
        decision: DecisionInputSnapshot,
        sizing: SizingInputSnapshot,
        exchange: ExchangeInputSnapshot,
        market_state: MarketStateInputSnapshot,
        dom_modifier: Dict[str, float] = None,
        ecology_modifier: Dict[str, Any] = None,
        interaction_modifier: Dict[str, Any] = None,
    ) -> Dict[str, any]:
        """Build explainability drivers. PHASE 16.6: includes interaction."""
        drivers = {
            "decision_action": decision.action,
            "decision_confidence": decision.confidence,
            "size_bucket": sizing.size_bucket,
            "exchange_conflict_ratio": exchange.conflict_ratio,
            "squeeze_probability": exchange.squeeze_probability,
            "market_state": market_state.combined_state,
            "volatility_state": market_state.volatility_state,
            "dominant_signal": exchange.dominant_signal,
        }
        
        # PHASE 14.9: Add dominance/breadth info
        if dom_modifier:
            drivers["dominance_regime"] = dom_modifier.get("dominance_regime", "BALANCED")
            drivers["breadth_state"] = dom_modifier.get("breadth_state", "MIXED")
            drivers["rotation_state"] = dom_modifier.get("rotation_state", "STABLE")
        
        # PHASE 15.7: Add ecology info
        if ecology_modifier:
            drivers["ecology_state"] = ecology_modifier.get("ecology_state", "STABLE")
            drivers["ecology_score"] = ecology_modifier.get("ecology_score", 1.0)
            drivers["ecology_weakest"] = ecology_modifier.get("weakest_component", "none")
        
        # PHASE 16.6: Add interaction info
        if interaction_modifier:
            drivers["interaction_state"] = interaction_modifier.get("interaction_state", "NEUTRAL")
            drivers["interaction_score"] = interaction_modifier.get("interaction_score", 0.0)
            drivers["interaction_execution_modifier"] = interaction_modifier.get("interaction_execution_modifier", "NORMAL")
            drivers["interaction_strongest_force"] = interaction_modifier.get("strongest_force", "none")
            drivers["cancellation_override"] = interaction_modifier.get("cancellation_override", False)
        
        return drivers


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[ExecutionModeEngine] = None


def get_execution_mode_engine() -> ExecutionModeEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ExecutionModeEngine()
    return _engine
