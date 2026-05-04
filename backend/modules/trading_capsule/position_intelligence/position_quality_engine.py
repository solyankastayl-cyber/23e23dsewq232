"""
Position Quality Engine
=======================

Calculates Position Quality Score (0-100) (PHASE 3.1)
"""

import time
import random
from typing import Dict, List, Optional, Any

from .position_quality_types import (
    PositionQualityScore,
    SignalQualityMetrics,
    MarketContextMetrics,
    RiskMetrics,
    QualityGrade
)


class PositionQualityEngine:
    """
    Calculates Position Quality Score.
    
    Components:
    - Signal Quality (30%)
    - Market Context (25%)
    - Risk Quality (25%)
    - Timing Quality (10%)
    - Execution Quality (10%)
    
    Output: Score 0-100, Grade A+ to F
    """
    
    def __init__(self):
        # Strategy-specific baseline scores
        self._strategy_baselines = {
            "TREND_CONFIRMATION": {
                "ideal_regime": "TRENDING",
                "signal_weight": 0.30,
                "context_weight": 0.25,
                "risk_weight": 0.25
            },
            "MOMENTUM_BREAKOUT": {
                "ideal_regime": "HIGH_VOLATILITY",
                "signal_weight": 0.35,
                "context_weight": 0.20,
                "risk_weight": 0.25
            },
            "MEAN_REVERSION": {
                "ideal_regime": "RANGE",
                "signal_weight": 0.25,
                "context_weight": 0.30,
                "risk_weight": 0.25
            }
        }
        
        print("[PositionQualityEngine] Initialized (PHASE 3.1)")
    
    def calculate_quality(
        self,
        position_id: str,
        symbol: str,
        strategy: str,
        direction: str,
        regime: str,
        indicators: Dict[str, float],
        entry_price: float,
        stop_price: float,
        target_price: float,
        current_exposure_pct: float = 0.0,
        current_drawdown_pct: float = 0.0
    ) -> PositionQualityScore:
        """
        Calculate complete position quality score.
        """
        
        score = PositionQualityScore(
            position_id=position_id,
            symbol=symbol,
            strategy=strategy.upper(),
            direction=direction.upper(),
            computed_at=int(time.time() * 1000)
        )
        
        # Calculate signal quality
        signal_metrics, signal_score = self._calculate_signal_quality(
            strategy=strategy,
            regime=regime,
            indicators=indicators,
            direction=direction
        )
        score.signal_metrics = signal_metrics
        score.signal_quality = signal_score
        
        # Calculate market context
        context_metrics, context_score = self._calculate_market_context(
            strategy=strategy,
            regime=regime,
            indicators=indicators
        )
        score.context_metrics = context_metrics
        score.market_context = context_score
        
        # Calculate risk quality
        risk_metrics, risk_score = self._calculate_risk_quality(
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            direction=direction,
            current_exposure=current_exposure_pct,
            current_drawdown=current_drawdown_pct
        )
        score.risk_metrics = risk_metrics
        score.risk_quality = risk_score
        
        # Calculate timing quality
        score.timing_quality = self._calculate_timing_quality(
            regime=regime,
            indicators=indicators
        )
        
        # Calculate execution quality (placeholder - would use real execution data)
        score.execution_quality = self._calculate_execution_quality(
            entry_price=entry_price,
            indicators=indicators
        )
        
        # Calculate total score
        weights = score.weights
        score.total_score = (
            signal_score * weights["signal"] +
            context_score * weights["context"] +
            risk_score * weights["risk"] +
            score.timing_quality * weights["timing"] +
            score.execution_quality * weights["execution"]
        )
        
        # Determine grade
        score.grade = self._get_grade(score.total_score)
        
        # Generate analysis
        score.strengths, score.weaknesses = self._analyze_strengths_weaknesses(score)
        score.recommendation = self._generate_recommendation(score)
        
        return score
    
    def _calculate_signal_quality(
        self,
        strategy: str,
        regime: str,
        indicators: Dict[str, float],
        direction: str
    ) -> tuple[SignalQualityMetrics, float]:
        """Calculate signal quality component"""
        
        metrics = SignalQualityMetrics()
        
        # Confluence score - multiple indicators agreeing
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macdHist", 0)
        close = indicators.get("close", 100)
        sma20 = indicators.get("sma20", 100)
        
        confluence_count = 0
        
        if direction == "LONG":
            if rsi < 70:
                confluence_count += 1
            if macd > 0:
                confluence_count += 1
            if close > sma20:
                confluence_count += 1
        else:
            if rsi > 30:
                confluence_count += 1
            if macd < 0:
                confluence_count += 1
            if close < sma20:
                confluence_count += 1
        
        metrics.confluence_score = (confluence_count / 3) * 100
        
        # Pattern clarity (simulated)
        metrics.pattern_clarity = random.uniform(60, 95)
        
        # Volume confirmation (simulated)
        metrics.volume_confirmation = random.uniform(50, 90)
        
        # Indicator alignment
        if direction == "LONG":
            rsi_aligned = (30 < rsi < 70)
            macd_aligned = macd > 0
        else:
            rsi_aligned = (30 < rsi < 70)
            macd_aligned = macd < 0
        
        metrics.indicator_alignment = 100 if (rsi_aligned and macd_aligned) else 50 if rsi_aligned or macd_aligned else 20
        
        # Timeframe alignment (simulated)
        metrics.timeframe_alignment = random.uniform(55, 90)
        
        # Calculate total signal score
        signal_score = (
            metrics.confluence_score * 0.30 +
            metrics.pattern_clarity * 0.25 +
            metrics.volume_confirmation * 0.15 +
            metrics.indicator_alignment * 0.20 +
            metrics.timeframe_alignment * 0.10
        )
        
        return metrics, signal_score
    
    def _calculate_market_context(
        self,
        strategy: str,
        regime: str,
        indicators: Dict[str, float]
    ) -> tuple[MarketContextMetrics, float]:
        """Calculate market context component"""
        
        metrics = MarketContextMetrics()
        
        # Regime stability
        baseline = self._strategy_baselines.get(strategy.upper(), {})
        ideal_regime = baseline.get("ideal_regime", "RANGE")
        
        if regime == ideal_regime:
            metrics.regime_stability = random.uniform(80, 95)
        elif regime == "TRANSITION":
            metrics.regime_stability = random.uniform(40, 60)
        else:
            metrics.regime_stability = random.uniform(30, 50)
        
        # Trend strength
        atr = indicators.get("atr", 100)
        close = indicators.get("close", 40000)
        atr_pct = (atr / close) * 100 if close > 0 else 2
        
        if strategy.upper() == "TREND_CONFIRMATION":
            metrics.trend_strength = min(100, atr_pct * 30 + random.uniform(50, 70))
        elif strategy.upper() == "MEAN_REVERSION":
            metrics.trend_strength = max(20, 100 - atr_pct * 30 + random.uniform(30, 50))
        else:
            metrics.trend_strength = random.uniform(50, 80)
        
        # Volatility favorable
        if regime in ["HIGH_VOLATILITY"] and strategy.upper() == "MOMENTUM_BREAKOUT":
            metrics.volatility_favorable = random.uniform(75, 95)
        elif regime in ["RANGE", "LOW_VOLATILITY"] and strategy.upper() == "MEAN_REVERSION":
            metrics.volatility_favorable = random.uniform(75, 95)
        elif regime in ["TRENDING"] and strategy.upper() == "TREND_CONFIRMATION":
            metrics.volatility_favorable = random.uniform(75, 95)
        else:
            metrics.volatility_favorable = random.uniform(40, 60)
        
        # Structure intact (simulated)
        metrics.structure_intact = random.uniform(60, 95)
        
        # Momentum support (simulated based on MACD)
        macd = indicators.get("macdHist", 0)
        metrics.momentum_support = 70 + min(30, abs(macd) * 3) if macd != 0 else 50
        
        # Calculate total context score
        context_score = (
            metrics.regime_stability * 0.30 +
            metrics.trend_strength * 0.20 +
            metrics.volatility_favorable * 0.20 +
            metrics.structure_intact * 0.15 +
            metrics.momentum_support * 0.15
        )
        
        return metrics, context_score
    
    def _calculate_risk_quality(
        self,
        entry_price: float,
        stop_price: float,
        target_price: float,
        direction: str,
        current_exposure: float,
        current_drawdown: float
    ) -> tuple[RiskMetrics, float]:
        """Calculate risk quality component"""
        
        metrics = RiskMetrics()
        
        # Risk:Reward ratio
        if direction == "LONG":
            risk = entry_price - stop_price
            reward = target_price - entry_price
        else:
            risk = stop_price - entry_price
            reward = entry_price - target_price
        
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Score R:R (optimal around 2-3)
        if rr_ratio >= 3:
            metrics.risk_reward_ratio = 95
        elif rr_ratio >= 2:
            metrics.risk_reward_ratio = 85
        elif rr_ratio >= 1.5:
            metrics.risk_reward_ratio = 70
        elif rr_ratio >= 1:
            metrics.risk_reward_ratio = 50
        else:
            metrics.risk_reward_ratio = 30
        
        # Stop distance quality (simulated - would check against ATR/structure)
        metrics.stop_distance_quality = random.uniform(65, 90)
        
        # Exposure acceptable
        if current_exposure < 10:
            metrics.exposure_acceptable = 95
        elif current_exposure < 20:
            metrics.exposure_acceptable = 80
        elif current_exposure < 30:
            metrics.exposure_acceptable = 60
        else:
            metrics.exposure_acceptable = 40
        
        # Correlation safe (simulated)
        metrics.correlation_safe = random.uniform(60, 90)
        
        # Drawdown buffer
        if current_drawdown < 2:
            metrics.drawdown_buffer = 95
        elif current_drawdown < 5:
            metrics.drawdown_buffer = 80
        elif current_drawdown < 10:
            metrics.drawdown_buffer = 60
        else:
            metrics.drawdown_buffer = 40
        
        # Calculate total risk score
        risk_score = (
            metrics.risk_reward_ratio * 0.30 +
            metrics.stop_distance_quality * 0.20 +
            metrics.exposure_acceptable * 0.20 +
            metrics.correlation_safe * 0.15 +
            metrics.drawdown_buffer * 0.15
        )
        
        return metrics, risk_score
    
    def _calculate_timing_quality(
        self,
        regime: str,
        indicators: Dict[str, float]
    ) -> float:
        """Calculate timing quality"""
        
        # Session timing (simulated)
        session_score = random.uniform(60, 90)
        
        # News/event timing (simulated)
        event_score = random.uniform(70, 95)
        
        # Regime stability timing
        if regime == "TRANSITION":
            regime_timing = 40
        else:
            regime_timing = random.uniform(70, 90)
        
        return (session_score * 0.3 + event_score * 0.3 + regime_timing * 0.4)
    
    def _calculate_execution_quality(
        self,
        entry_price: float,
        indicators: Dict[str, float]
    ) -> float:
        """Calculate execution quality"""
        
        # Entry vs ideal (simulated)
        entry_accuracy = random.uniform(65, 95)
        
        # Slippage (simulated)
        slippage_score = random.uniform(80, 98)
        
        return (entry_accuracy * 0.6 + slippage_score * 0.4)
    
    def _get_grade(self, score: float) -> QualityGrade:
        """Convert score to grade"""
        if score >= 90:
            return QualityGrade.A_PLUS
        elif score >= 80:
            return QualityGrade.A
        elif score >= 70:
            return QualityGrade.B_PLUS
        elif score >= 60:
            return QualityGrade.B
        elif score >= 50:
            return QualityGrade.C
        elif score >= 40:
            return QualityGrade.D
        else:
            return QualityGrade.F
    
    def _analyze_strengths_weaknesses(
        self,
        score: PositionQualityScore
    ) -> tuple[List[str], List[str]]:
        """Identify strengths and weaknesses"""
        
        strengths = []
        weaknesses = []
        
        # Signal quality
        if score.signal_quality >= 75:
            strengths.append(f"Strong signal quality ({score.signal_quality:.0f})")
        elif score.signal_quality < 50:
            weaknesses.append(f"Weak signal quality ({score.signal_quality:.0f})")
        
        # Market context
        if score.market_context >= 75:
            strengths.append(f"Favorable market context ({score.market_context:.0f})")
        elif score.market_context < 50:
            weaknesses.append(f"Unfavorable market context ({score.market_context:.0f})")
        
        # Risk quality
        if score.risk_quality >= 75:
            strengths.append(f"Excellent risk profile ({score.risk_quality:.0f})")
        elif score.risk_quality < 50:
            weaknesses.append(f"Poor risk profile ({score.risk_quality:.0f})")
        
        # Specific metrics
        if score.risk_metrics.risk_reward_ratio >= 85:
            strengths.append("Attractive risk:reward ratio")
        
        if score.context_metrics.regime_stability >= 80:
            strengths.append("Stable market regime")
        elif score.context_metrics.regime_stability < 50:
            weaknesses.append("Unstable/transitioning regime")
        
        if score.signal_metrics.confluence_score >= 80:
            strengths.append("High indicator confluence")
        
        return strengths, weaknesses
    
    def _generate_recommendation(self, score: PositionQualityScore) -> str:
        """Generate recommendation based on score"""
        
        if score.grade in [QualityGrade.A_PLUS, QualityGrade.A]:
            return "STRONG BUY - High quality setup, consider full position"
        elif score.grade == QualityGrade.B_PLUS:
            return "BUY - Good quality setup, standard position size"
        elif score.grade == QualityGrade.B:
            return "CAUTIOUS BUY - Acceptable setup, consider reduced size"
        elif score.grade == QualityGrade.C:
            return "HOLD/SKIP - Marginal quality, consider waiting for better setup"
        elif score.grade == QualityGrade.D:
            return "AVOID - Low quality setup, not recommended"
        else:
            return "DO NOT TRADE - Poor quality, significant issues identified"
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "engine": "PositionQualityEngine",
            "status": "active",
            "version": "1.0.0",
            "components": ["signal", "context", "risk", "timing", "execution"],
            "grades": [g.value for g in QualityGrade],
            "strategies": list(self._strategy_baselines.keys()),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
position_quality_engine = PositionQualityEngine()
