"""
PHASE 25.1 — Macro Context Engine

Core engine that:
1. Computes USD bias from inflation, rates, labor, credit
2. Computes Equity bias from growth, liquidity, consumer
3. Computes Liquidity state
4. Classifies overall Macro state
5. Computes confidence and reliability
6. Determines context_state
7. Generates human-readable reason

This module is INDEPENDENT from TA / Exchange / Fractal.
"""

from typing import Optional, Dict, List
from datetime import datetime
import math

from .macro_context_types import (
    MacroInput,
    MacroContext,
    MacroContextSummary,
    MacroHealthStatus,
    MacroStateType,
    BiasType,
    LiquidityStateType,
    ContextStateType,
)
from .macro_context_adapter import MacroContextAdapter, get_macro_adapter


class MacroContextEngine:
    """
    Engine that computes MacroContext from MacroInput.
    
    Formulas (from spec):
    - usd_score = 0.35*inflation + 0.35*rates + 0.15*labor + 0.15*credit
    - equity_score = 0.30*growth + 0.20*liquidity + 0.15*consumer - 0.20*inflation - 0.15*rates
    - liquidity_score = 0.45*liquidity - 0.25*rates - 0.15*credit - 0.15*inflation
    - confidence = avg(abs(all 9 inputs))
    - reliability = 1 - stddev(inputs)
    - macro_strength = 0.5 * confidence + 0.5 * reliability
    """
    
    # Thresholds for bias classification
    BIAS_THRESHOLD_BULLISH = 0.20
    BIAS_THRESHOLD_BEARISH = -0.20
    
    # Thresholds for context state
    BLOCKED_RELIABILITY_THRESHOLD = 0.15
    SUPPORTIVE_CONFIDENCE_THRESHOLD = 0.35  # Lowered from 0.55
    SUPPORTIVE_RELIABILITY_THRESHOLD = 0.55
    CONFLICTED_RELIABILITY_THRESHOLD = 0.40
    
    # Minimum inputs for non-BLOCKED state
    MIN_INPUTS_FOR_SIGNAL = 3
    
    def __init__(self, adapter: Optional[MacroContextAdapter] = None):
        """
        Initialize engine with optional custom adapter.
        
        Args:
            adapter: MacroContextAdapter instance. If None, creates default.
        """
        self.adapter = adapter or get_macro_adapter()
        self._last_input: Optional[MacroInput] = None
        self._last_context: Optional[MacroContext] = None
    
    # ═══════════════════════════════════════════════════════════
    # Core Bias Calculations
    # ═══════════════════════════════════════════════════════════
    
    def compute_usd_score(self, input: MacroInput) -> float:
        """
        Compute USD bias score.
        
        Formula: 0.35*inflation + 0.35*rates + 0.15*labor + 0.15*credit
        
        Logic:
        - High inflation → hawkish Fed → stronger USD
        - High rates → stronger USD
        - Strong labor → hawkish Fed → stronger USD
        - Tight credit → risk-off → stronger USD
        """
        score = (
            0.35 * input.inflation_signal +
            0.35 * input.rates_signal +
            0.15 * input.labor_market_signal +
            0.15 * (-input.credit_signal)  # Tight credit (negative) = bullish USD
        )
        return self._clamp(score)
    
    def compute_equity_score(self, input: MacroInput) -> float:
        """
        Compute Equity bias score.
        
        Formula: 0.30*growth + 0.20*liquidity + 0.15*consumer - 0.20*inflation - 0.15*rates
        
        Logic:
        - Strong growth → bullish equities
        - Expanding liquidity → bullish equities
        - Strong consumer → bullish equities
        - High inflation → bearish pressure
        - High rates → bearish pressure
        """
        score = (
            0.30 * input.growth_signal +
            0.20 * input.liquidity_signal +
            0.15 * input.consumer_signal -
            0.20 * input.inflation_signal -
            0.15 * input.rates_signal
        )
        return self._clamp(score)
    
    def compute_liquidity_score(self, input: MacroInput) -> float:
        """
        Compute Liquidity state score.
        
        Formula: 0.45*liquidity - 0.25*rates - 0.15*credit - 0.15*inflation
        
        Logic:
        - Expanding liquidity → positive
        - High rates → drains liquidity
        - Tight credit → less liquidity
        - High inflation → Fed tightening → less liquidity
        """
        score = (
            0.45 * input.liquidity_signal -
            0.25 * input.rates_signal -
            0.15 * (-input.credit_signal) -  # Tight credit reduces liquidity
            0.15 * input.inflation_signal
        )
        return self._clamp(score)
    
    # ═══════════════════════════════════════════════════════════
    # Bias Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_usd_bias(self, score: float) -> BiasType:
        """Classify USD bias from score."""
        if score > self.BIAS_THRESHOLD_BULLISH:
            return "BULLISH"
        elif score < self.BIAS_THRESHOLD_BEARISH:
            return "BEARISH"
        return "NEUTRAL"
    
    def classify_equity_bias(self, score: float) -> BiasType:
        """Classify Equity bias from score."""
        if score > self.BIAS_THRESHOLD_BULLISH:
            return "BULLISH"
        elif score < self.BIAS_THRESHOLD_BEARISH:
            return "BEARISH"
        return "NEUTRAL"
    
    def classify_liquidity_state(self, score: float) -> LiquidityStateType:
        """Classify Liquidity state from score."""
        if score > self.BIAS_THRESHOLD_BULLISH:
            return "EXPANDING"
        elif score < self.BIAS_THRESHOLD_BEARISH:
            return "CONTRACTING"
        return "STABLE"
    
    # ═══════════════════════════════════════════════════════════
    # Macro State Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_macro_state(
        self,
        input: MacroInput,
        usd_bias: BiasType,
        equity_bias: BiasType,
        liquidity_state: LiquidityStateType,
    ) -> MacroStateType:
        """
        Classify overall macro state using rule-based logic.
        
        Priority order:
        1. UNKNOWN if insufficient data
        2. STAGFLATION if high inflation + weak growth + weak equity
        3. TIGHTENING if high rates + high inflation + contracting liquidity
        4. EASING if low rates + expanding liquidity + bullish equity
        5. RISK_ON if bullish equity + expanding/stable liquidity + not bullish USD
        6. RISK_OFF if bearish equity + bullish USD
        7. NEUTRAL otherwise
        """
        
        # Check data sufficiency
        if input.count_non_zero() < self.MIN_INPUTS_FOR_SIGNAL:
            return "UNKNOWN"
        
        # STAGFLATION: high inflation + weak growth + weak equity
        # Must have BOTH high inflation AND weak growth
        if (
            input.inflation_signal > 0.4 and
            input.growth_signal < -0.3 and
            equity_bias == "BEARISH"
        ):
            return "STAGFLATION"
        
        # TIGHTENING: high rates + high inflation + contracting liquidity
        if (
            input.rates_signal > 0.4 and
            input.inflation_signal > 0.3 and
            liquidity_state == "CONTRACTING"
        ):
            return "TIGHTENING"
        
        # RISK_OFF: bearish equity + bullish USD (check BEFORE EASING)
        if (
            equity_bias == "BEARISH" and
            usd_bias == "BULLISH"
        ):
            return "RISK_OFF"
        
        # EASING: low/falling rates + expanding liquidity + bullish equity
        if (
            input.rates_signal < -0.2 and
            liquidity_state == "EXPANDING" and
            equity_bias == "BULLISH"
        ):
            return "EASING"
        
        # RISK_ON: bullish equity + expanding/stable liquidity + not bullish USD
        if (
            equity_bias == "BULLISH" and
            liquidity_state in ["EXPANDING", "STABLE"] and
            usd_bias != "BULLISH"
        ):
            return "RISK_ON"
        
        return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # Confidence & Reliability
    # ═══════════════════════════════════════════════════════════
    
    def compute_confidence(self, input: MacroInput) -> float:
        """
        Compute confidence as average of abs(all inputs).
        
        If all signals are weak → low confidence
        If signals are strong → high confidence
        """
        signals = input.get_all_signals()
        values = list(signals.values())
        
        if not values:
            return 0.0
        
        # Average of absolute values
        avg_abs = sum(abs(v) for v in values) / len(values)
        return self._clamp(avg_abs, 0.0, 1.0)
    
    def compute_reliability(self, input: MacroInput) -> float:
        """
        Compute reliability as 1 - stddev(inputs).
        
        If all signals point same direction → high reliability
        If signals conflict → low reliability
        """
        signals = input.get_all_signals()
        values = list(signals.values())
        
        if len(values) < 2:
            return 0.5  # Not enough data
        
        # Compute stddev
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        stddev = math.sqrt(variance)
        
        # Normalize: stddev of [-1, 1] range is max ~1.0
        # So reliability = 1 - stddev, clamped
        reliability = 1.0 - stddev
        return self._clamp(reliability, 0.0, 1.0)
    
    def compute_macro_strength(self, confidence: float, reliability: float) -> float:
        """
        Compute macro_strength = 0.5 * confidence + 0.5 * reliability
        """
        return self._clamp(0.5 * confidence + 0.5 * reliability, 0.0, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # Context State
    # ═══════════════════════════════════════════════════════════
    
    def determine_context_state(
        self,
        input: MacroInput,
        macro_state: MacroStateType,
        confidence: float,
        reliability: float,
    ) -> ContextStateType:
        """
        Determine context state based on signal quality.
        
        Returns: SUPPORTIVE, MIXED, CONFLICTED, or BLOCKED
        """
        
        # BLOCKED: insufficient data or very low reliability
        if input.count_non_zero() < self.MIN_INPUTS_FOR_SIGNAL:
            return "BLOCKED"
        if reliability < self.BLOCKED_RELIABILITY_THRESHOLD:
            return "BLOCKED"
        
        # If macro state is UNKNOWN → BLOCKED
        if macro_state == "UNKNOWN":
            return "BLOCKED"
        
        # SUPPORTIVE: clear macro state with good confidence and reliability
        if (
            macro_state in ["RISK_ON", "RISK_OFF", "TIGHTENING", "EASING"] and
            confidence >= self.SUPPORTIVE_CONFIDENCE_THRESHOLD and
            reliability >= self.SUPPORTIVE_RELIABILITY_THRESHOLD
        ):
            return "SUPPORTIVE"
        
        # CONFLICTED: decent confidence but low reliability
        if (
            confidence >= 0.50 and
            reliability < self.CONFLICTED_RELIABILITY_THRESHOLD
        ):
            return "CONFLICTED"
        
        # Default: MIXED
        return "MIXED"
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        macro_state: MacroStateType,
        usd_bias: BiasType,
        equity_bias: BiasType,
        liquidity_state: LiquidityStateType,
        context_state: ContextStateType,
        confidence: float,
    ) -> str:
        """Generate human-readable explanation."""
        
        if context_state == "BLOCKED":
            return "insufficient macro inputs or reliability too low for directional signal"
        
        # Build descriptive parts
        usd_str = f"{'stronger' if usd_bias == 'BULLISH' else 'weaker' if usd_bias == 'BEARISH' else 'stable'} dollar"
        equity_str = f"{'bullish' if equity_bias == 'BULLISH' else 'bearish' if equity_bias == 'BEARISH' else 'neutral'} equity"
        liquidity_str = f"{'expanding' if liquidity_state == 'EXPANDING' else 'contracting' if liquidity_state == 'CONTRACTING' else 'stable'} liquidity"
        
        if macro_state == "RISK_ON":
            return f"macro indicates risk-on environment with {liquidity_str} and {equity_str} backdrop"
        
        if macro_state == "RISK_OFF":
            return f"macro indicates risk-off environment with {usd_str} pressure and {equity_str} backdrop"
        
        if macro_state == "TIGHTENING":
            return f"macro indicates tightening regime with {usd_str} and {liquidity_str}"
        
        if macro_state == "EASING":
            return f"macro indicates easing regime with {liquidity_str} and {equity_str} support"
        
        if macro_state == "STAGFLATION":
            return f"macro indicates stagflation risk with high inflation and {equity_str} weakness"
        
        if context_state == "CONFLICTED":
            return f"macro inputs are directional but internally inconsistent across indicators"
        
        # NEUTRAL / MIXED
        return f"macro environment is mixed with {equity_str} and {liquidity_str}"
    
    # ═══════════════════════════════════════════════════════════
    # Main Build Method
    # ═══════════════════════════════════════════════════════════
    
    def build_context(self, input: MacroInput) -> MacroContext:
        """
        Build complete MacroContext from MacroInput.
        
        Args:
            input: Normalized macro input
            
        Returns:
            MacroContext with all computed fields
        """
        
        # Compute scores
        usd_score = self.compute_usd_score(input)
        equity_score = self.compute_equity_score(input)
        liquidity_score = self.compute_liquidity_score(input)
        
        # Classify biases
        usd_bias = self.classify_usd_bias(usd_score)
        equity_bias = self.classify_equity_bias(equity_score)
        liquidity_state = self.classify_liquidity_state(liquidity_score)
        
        # Classify macro state
        macro_state = self.classify_macro_state(
            input, usd_bias, equity_bias, liquidity_state
        )
        
        # Compute quality metrics
        confidence = self.compute_confidence(input)
        reliability = self.compute_reliability(input)
        macro_strength = self.compute_macro_strength(confidence, reliability)
        
        # Determine context state
        context_state = self.determine_context_state(
            input, macro_state, confidence, reliability
        )
        
        # Generate reason
        reason = self.generate_reason(
            macro_state, usd_bias, equity_bias, liquidity_state,
            context_state, confidence
        )
        
        # Store for caching
        self._last_input = input
        
        context = MacroContext(
            macro_state=macro_state,
            usd_bias=usd_bias,
            equity_bias=equity_bias,
            liquidity_state=liquidity_state,
            confidence=round(confidence, 4),
            reliability=round(reliability, 4),
            macro_strength=round(macro_strength, 4),
            context_state=context_state,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        
        self._last_context = context
        return context
    
    def build_context_from_dict(self, raw_data: Dict) -> MacroContext:
        """
        Convenience method: build context directly from raw dict.
        """
        input = self.adapter.adapt_from_dict(raw_data)
        return self.build_context(input)
    
    def get_summary(self, context: MacroContext) -> MacroContextSummary:
        """Extract compact summary from full context."""
        return MacroContextSummary(
            macro_state=context.macro_state,
            usd_bias=context.usd_bias,
            equity_bias=context.equity_bias,
            liquidity_state=context.liquidity_state,
            confidence=context.confidence,
            reliability=context.reliability,
            context_state=context.context_state,
        )
    
    def get_health(self) -> MacroHealthStatus:
        """Get health status of macro context module."""
        input_count = 0
        context_state: ContextStateType = "BLOCKED"
        last_update = None
        
        if self._last_input:
            input_count = self._last_input.count_non_zero()
            last_update = self._last_input.timestamp
        
        if self._last_context:
            context_state = self._last_context.context_state
        
        has_inputs = input_count >= self.MIN_INPUTS_FOR_SIGNAL
        
        if not has_inputs:
            status = "ERROR"
        elif context_state == "BLOCKED":
            status = "DEGRADED"
        else:
            status = "OK"
        
        return MacroHealthStatus(
            status=status,
            has_inputs=has_inputs,
            input_count=input_count,
            context_state=context_state,
            last_update=last_update,
        )
    
    @staticmethod
    def _clamp(value: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))


# ══════════════════════════════════════════════════════════════
# Singleton Instance
# ══════════════════════════════════════════════════════════════

_engine: Optional[MacroContextEngine] = None


def get_macro_context_engine() -> MacroContextEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = MacroContextEngine()
    return _engine
