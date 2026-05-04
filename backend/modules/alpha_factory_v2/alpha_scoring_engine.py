"""
PHASE 26.2 — Alpha Scoring Engine

Transforms FactorCandidate → AlphaFactor with scoring.

Pipeline:
candidate → backtest metrics → alpha_score

Scoring Formula:
alpha_score = 0.35 * signal_strength
            + 0.25 * sharpe_score
            + 0.20 * stability_score
            + 0.20 * drawdown_score

Bounds: 0 ≤ alpha_score ≤ 1
"""

from typing import List, Optional
from datetime import datetime
import math
import random

from .factor_types import (
    FactorCandidate,
    AlphaFactor,
    ALPHA_SCORE_WEIGHTS,
)


class AlphaScoringEngine:
    """
    Alpha Scoring Engine.
    
    Converts FactorCandidate to AlphaFactor by computing:
    - signal_strength
    - sharpe_score
    - stability_score
    - drawdown_score
    - alpha_score
    
    Weak factors (std < 0.01) are automatically deprecated.
    """
    
    # Minimum signal variance threshold
    MIN_SIGNAL_VARIANCE = 0.01
    
    # Sharpe normalization cap
    SHARPE_CAP = 3.0
    
    def __init__(self):
        self._scored_factors: List[AlphaFactor] = []
        self._last_scoring: Optional[datetime] = None
    
    # ═══════════════════════════════════════════════════════════
    # Main Scoring
    # ═══════════════════════════════════════════════════════════
    
    def score_candidates(
        self,
        candidates: List[FactorCandidate],
    ) -> List[AlphaFactor]:
        """
        Score a list of factor candidates.
        
        Args:
            candidates: List of FactorCandidate from discovery
        
        Returns:
            List of AlphaFactor with scores
        """
        scored = []
        
        for candidate in candidates:
            factor = self._score_candidate(candidate)
            scored.append(factor)
        
        self._scored_factors = scored
        self._last_scoring = datetime.utcnow()
        
        return scored
    
    def _score_candidate(
        self,
        candidate: FactorCandidate,
    ) -> AlphaFactor:
        """
        Score a single candidate.
        
        Computes all 4 metrics and final alpha_score.
        """
        # Generate simulated signal series for scoring
        signal_series = self._generate_signal_series(candidate)
        
        # Check for garbage (low variance)
        signal_std = self._compute_std(signal_series)
        
        if signal_std < self.MIN_SIGNAL_VARIANCE:
            # Weak factor - auto deprecate
            return AlphaFactor(
                factor_id=candidate.factor_id,
                name=candidate.name,
                category=candidate.category,
                lookback=candidate.lookback,
                signal_strength=0.0,
                sharpe_score=0.0,
                stability_score=0.0,
                drawdown_score=0.0,
                alpha_score=0.0,
                status="DEPRECATED",
                parameters=candidate.parameters,
                source=candidate.source,
            )
        
        # Compute metrics
        signal_strength = self._compute_signal_strength(signal_series)
        sharpe_score = self._compute_sharpe_score(candidate, signal_series)
        stability_score = self._compute_stability_score(signal_series)
        drawdown_score = self._compute_drawdown_score(candidate, signal_series)
        
        # Compute alpha score
        alpha_score = self._compute_alpha_score(
            signal_strength,
            sharpe_score,
            stability_score,
            drawdown_score,
        )
        
        return AlphaFactor(
            factor_id=candidate.factor_id,
            name=candidate.name,
            category=candidate.category,
            lookback=candidate.lookback,
            signal_strength=round(signal_strength, 4),
            sharpe_score=round(sharpe_score, 4),
            stability_score=round(stability_score, 4),
            drawdown_score=round(drawdown_score, 4),
            alpha_score=round(alpha_score, 4),
            status="CANDIDATE",
            parameters=candidate.parameters,
            source=candidate.source,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Metric Computations
    # ═══════════════════════════════════════════════════════════
    
    def _compute_signal_strength(
        self,
        signal_series: List[float],
    ) -> float:
        """
        Compute signal strength.
        
        Formula: abs(mean(signal_series))
        Bounds: [0, 1]
        """
        if not signal_series:
            return 0.0
        
        mean_signal = sum(signal_series) / len(signal_series)
        strength = abs(mean_signal)
        
        return self._clamp(strength, 0.0, 1.0)
    
    def _compute_sharpe_score(
        self,
        candidate: FactorCandidate,
        signal_series: List[float],
    ) -> float:
        """
        Compute Sharpe score.
        
        Formula: sharpe = mean(returns) / std(returns)
        Normalized: sharpe_score = min(max(sharpe / 3, 0), 1)
        """
        # Generate strategy returns from signals
        returns = self._simulate_strategy_returns(candidate, signal_series)
        
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_ret = sum(returns) / len(returns)
        std_ret = self._compute_std(returns)
        
        if std_ret < 1e-10:
            return 0.0
        
        sharpe = mean_ret / std_ret
        
        # Normalize: Sharpe 3 = max score
        sharpe_score = sharpe / self.SHARPE_CAP
        
        return self._clamp(sharpe_score, 0.0, 1.0)
    
    def _compute_stability_score(
        self,
        signal_series: List[float],
    ) -> float:
        """
        Compute stability score.
        
        Formula: 1 - std(signal_series)
        Bounds: [0, 1]
        """
        if not signal_series:
            return 0.0
        
        std_signal = self._compute_std(signal_series)
        stability = 1.0 - std_signal
        
        return self._clamp(stability, 0.0, 1.0)
    
    def _compute_drawdown_score(
        self,
        candidate: FactorCandidate,
        signal_series: List[float],
    ) -> float:
        """
        Compute drawdown score.
        
        Formula: 1 - max_drawdown(equity)
        Bounds: [0, 1]
        """
        # Simulate equity curve
        equity = self._simulate_equity_curve(candidate, signal_series)
        
        if not equity or len(equity) < 2:
            return 0.5  # Neutral
        
        max_dd = self._compute_max_drawdown(equity)
        drawdown_score = 1.0 - max_dd
        
        return self._clamp(drawdown_score, 0.0, 1.0)
    
    def _compute_alpha_score(
        self,
        signal_strength: float,
        sharpe_score: float,
        stability_score: float,
        drawdown_score: float,
    ) -> float:
        """
        Compute final alpha score.
        
        Formula:
        alpha_score = 0.35 * signal_strength
                    + 0.25 * sharpe_score
                    + 0.20 * stability_score
                    + 0.20 * drawdown_score
        """
        alpha = (
            ALPHA_SCORE_WEIGHTS["signal_strength"] * signal_strength +
            ALPHA_SCORE_WEIGHTS["sharpe_score"] * sharpe_score +
            ALPHA_SCORE_WEIGHTS["stability_score"] * stability_score +
            ALPHA_SCORE_WEIGHTS["drawdown_score"] * drawdown_score
        )
        
        return self._clamp(alpha, 0.0, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # Simulation Helpers
    # ═══════════════════════════════════════════════════════════
    
    def _generate_signal_series(
        self,
        candidate: FactorCandidate,
        length: int = 100,
    ) -> List[float]:
        """
        Generate simulated signal series for a candidate.
        
        In production, this would come from actual historical data.
        """
        # Deterministic based on factor_id for reproducibility
        seed = hash(candidate.factor_id) % 10000
        random.seed(seed)
        
        base = candidate.raw_signal
        noise_scale = 0.3
        
        series = []
        for i in range(length):
            noise = random.gauss(0, noise_scale)
            value = base + noise
            value = max(-1.0, min(1.0, value))
            series.append(value)
        
        return series
    
    def _simulate_strategy_returns(
        self,
        candidate: FactorCandidate,
        signal_series: List[float],
    ) -> List[float]:
        """
        Simulate strategy returns based on signals.
        """
        seed = hash(candidate.factor_id + "returns") % 10000
        random.seed(seed)
        
        returns = []
        for signal in signal_series:
            # Return = signal * market_move + noise
            market = random.gauss(0.001, 0.02)
            ret = signal * market + random.gauss(0, 0.005)
            returns.append(ret)
        
        return returns
    
    def _simulate_equity_curve(
        self,
        candidate: FactorCandidate,
        signal_series: List[float],
    ) -> List[float]:
        """
        Simulate equity curve for drawdown calculation.
        """
        returns = self._simulate_strategy_returns(candidate, signal_series)
        
        equity = [1.0]
        for ret in returns:
            equity.append(equity[-1] * (1 + ret))
        
        return equity
    
    # ═══════════════════════════════════════════════════════════
    # Math Helpers
    # ═══════════════════════════════════════════════════════════
    
    def _compute_std(self, values: List[float]) -> float:
        """Compute standard deviation."""
        if not values or len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)
    
    def _compute_max_drawdown(self, equity: List[float]) -> float:
        """Compute maximum drawdown from equity curve."""
        if not equity:
            return 0.0
        
        peak = equity[0]
        max_dd = 0.0
        
        for value in equity:
            if value > peak:
                peak = value
            
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_scored_factors(self) -> List[AlphaFactor]:
        """Get last scored factors."""
        return self._scored_factors
    
    def get_top_factors(self, n: int = 10) -> List[AlphaFactor]:
        """Get top N factors by alpha_score."""
        sorted_factors = sorted(
            self._scored_factors,
            key=lambda f: f.alpha_score,
            reverse=True,
        )
        return sorted_factors[:n]
    
    def get_factors_above_threshold(
        self,
        threshold: float = 0.55,
    ) -> List[AlphaFactor]:
        """Get factors with alpha_score >= threshold."""
        return [f for f in self._scored_factors if f.alpha_score >= threshold]
    
    @property
    def last_scoring(self) -> Optional[datetime]:
        """Get timestamp of last scoring run."""
        return self._last_scoring


# Singleton
_engine: Optional[AlphaScoringEngine] = None


def get_alpha_scoring_engine() -> AlphaScoringEngine:
    """Get singleton instance of AlphaScoringEngine."""
    global _engine
    if _engine is None:
        _engine = AlphaScoringEngine()
    return _engine
