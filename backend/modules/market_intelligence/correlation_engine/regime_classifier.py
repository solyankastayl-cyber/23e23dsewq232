"""
PHASE 7 - Regime Classifier
=============================
Classifies market correlation regimes to understand macro conditions.

Regimes:
- MACRO_DOMINANT: BTC correlates with SPX (risk-on/risk-off driven)
- CRYPTO_NATIVE: BTC correlates with ETH but not SPX (crypto-specific moves)
- RISK_ON: High correlations, everything buys together
- RISK_OFF: High correlations, everything sells together
- DECOUPLING: Breaking from usual correlations
- TRANSITION: Regime changing between states
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from .correlation_types import (
    CorrelationRegime, RegimeState, CorrelationValue, 
    REGIME_THRESHOLDS, DEFAULT_PAIRS
)
from .correlation_matrix import CorrelationMatrixEngine


@dataclass
class RegimeHistory:
    """Tracks regime history over time"""
    regime: CorrelationRegime
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_candles: int = 0
    confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "regime": self.regime.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_candles": self.duration_candles,
            "confidence": round(self.confidence, 3)
        }


class RegimeClassifier:
    """
    Classifies market regime based on cross-asset correlations.
    """
    
    def __init__(self):
        self.matrix_engine = CorrelationMatrixEngine()
        self.regime_history: List[RegimeHistory] = []
        self.current_regime: Optional[RegimeState] = None
        
        # Thresholds for regime classification
        self.thresholds = {
            "macro_dominant_min_spx_corr": 0.5,
            "crypto_native_max_spx_corr": 0.3,
            "crypto_native_min_eth_corr": 0.7,
            "risk_off_min_avg_corr": 0.6,
            "risk_on_min_avg_corr": 0.6,
            "decoupling_max_corr": 0.2,
            "transition_unstable_std": 0.15
        }
    
    def classify_regime(
        self,
        btc_spx_corr: float,
        btc_dxy_corr: float,
        btc_eth_corr: float,
        crypto_equity_avg: float,
        btc_trend: str = "NEUTRAL",  # UP, DOWN, NEUTRAL
        correlation_volatility: float = 0.0
    ) -> RegimeState:
        """
        Classify current market regime based on correlation metrics.
        
        Args:
            btc_spx_corr: BTC-SPX correlation
            btc_dxy_corr: BTC-DXY correlation (typically negative)
            btc_eth_corr: BTC-ETH correlation
            crypto_equity_avg: Average crypto-equity correlation
            btc_trend: Current BTC price trend
            correlation_volatility: How much correlations are changing
        
        Returns:
            RegimeState with classification and details
        """
        now = datetime.now(timezone.utc)
        
        # Calculate regime scores
        scores = {
            CorrelationRegime.MACRO_DOMINANT: 0.0,
            CorrelationRegime.CRYPTO_NATIVE: 0.0,
            CorrelationRegime.RISK_ON: 0.0,
            CorrelationRegime.RISK_OFF: 0.0,
            CorrelationRegime.DECOUPLING: 0.0,
            CorrelationRegime.TRANSITIONING: 0.0
        }
        
        # MACRO_DOMINANT: High BTC-SPX correlation
        if abs(btc_spx_corr) >= self.thresholds["macro_dominant_min_spx_corr"]:
            scores[CorrelationRegime.MACRO_DOMINANT] = abs(btc_spx_corr)
        
        # CRYPTO_NATIVE: Low SPX correlation, high ETH correlation
        if abs(btc_spx_corr) <= self.thresholds["crypto_native_max_spx_corr"]:
            if btc_eth_corr >= self.thresholds["crypto_native_min_eth_corr"]:
                scores[CorrelationRegime.CRYPTO_NATIVE] = btc_eth_corr - abs(btc_spx_corr)
        
        # RISK_ON: High positive correlations + uptrend
        if crypto_equity_avg >= self.thresholds["risk_on_min_avg_corr"]:
            if btc_trend == "UP":
                scores[CorrelationRegime.RISK_ON] = crypto_equity_avg * 1.2
            elif btc_trend == "NEUTRAL":
                scores[CorrelationRegime.RISK_ON] = crypto_equity_avg * 0.8
        
        # RISK_OFF: High positive correlations + downtrend
        if crypto_equity_avg >= self.thresholds["risk_off_min_avg_corr"]:
            if btc_trend == "DOWN":
                scores[CorrelationRegime.RISK_OFF] = crypto_equity_avg * 1.2
            elif btc_trend == "NEUTRAL":
                scores[CorrelationRegime.RISK_OFF] = crypto_equity_avg * 0.5
        
        # DECOUPLING: Very low correlations across the board
        avg_corr = (abs(btc_spx_corr) + abs(btc_dxy_corr) + abs(crypto_equity_avg)) / 3
        if avg_corr <= self.thresholds["decoupling_max_corr"]:
            scores[CorrelationRegime.DECOUPLING] = 1 - avg_corr
        
        # TRANSITIONING: High correlation volatility
        if correlation_volatility >= self.thresholds["transition_unstable_std"]:
            scores[CorrelationRegime.TRANSITIONING] = min(1.0, correlation_volatility * 2)
        
        # Select regime with highest score
        regime = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[regime]
        
        # Normalize confidence
        confidence = min(0.95, max(0.1, confidence))
        
        # Build regime description and implications
        description, implications = self._get_regime_details(
            regime, btc_spx_corr, btc_dxy_corr, btc_eth_corr, btc_trend
        )
        
        # Calculate duration if continuing same regime
        duration = 0
        if self.current_regime and self.current_regime.regime == regime:
            duration = self.current_regime.duration_candles + 1
        
        state = RegimeState(
            regime=regime,
            confidence=confidence,
            btc_spx_corr=btc_spx_corr,
            btc_dxy_corr=btc_dxy_corr,
            btc_eth_corr=btc_eth_corr,
            crypto_equity_avg=crypto_equity_avg,
            description=description,
            trading_implications=implications,
            started_at=now if duration == 0 else self.current_regime.started_at,
            duration_candles=duration
        )
        
        # Track regime change
        if self.current_regime and self.current_regime.regime != regime:
            self._record_regime_change(regime, now)
        
        self.current_regime = state
        return state
    
    def _get_regime_details(
        self,
        regime: CorrelationRegime,
        btc_spx_corr: float,
        btc_dxy_corr: float,
        btc_eth_corr: float,
        btc_trend: str
    ) -> tuple:
        """Get description and trading implications for regime."""
        
        descriptions = {
            CorrelationRegime.MACRO_DOMINANT: (
                f"Market is macro-driven. BTC-SPX correlation is {btc_spx_corr:.2f}. "
                "Crypto follows traditional risk assets."
            ),
            CorrelationRegime.CRYPTO_NATIVE: (
                f"Crypto-native regime. BTC-ETH correlation is {btc_eth_corr:.2f}. "
                "Crypto moves independently of traditional markets."
            ),
            CorrelationRegime.RISK_ON: (
                "Risk-on environment. High correlations with positive bias. "
                "All risk assets rallying together."
            ),
            CorrelationRegime.RISK_OFF: (
                "Risk-off environment. High correlations with negative bias. "
                "All risk assets selling together."
            ),
            CorrelationRegime.DECOUPLING: (
                "Decoupling regime. Correlations are breaking down. "
                "Assets moving independently."
            ),
            CorrelationRegime.TRANSITIONING: (
                "Transitioning regime. Correlations are unstable. "
                "Regime change in progress."
            )
        }
        
        implications = {
            CorrelationRegime.MACRO_DOMINANT: [
                "Watch SPX/NASDAQ for BTC direction",
                "Fed decisions have high crypto impact",
                "DXY strength = crypto weakness",
                "Use macro data for crypto timing"
            ],
            CorrelationRegime.CRYPTO_NATIVE: [
                "Focus on crypto-specific catalysts",
                "ETH leads altcoin moves",
                "Macro data has lower impact",
                "On-chain metrics more relevant"
            ],
            CorrelationRegime.RISK_ON: [
                "Favor long positions",
                "Higher position sizes acceptable",
                "Altcoins likely to outperform",
                "Momentum strategies work well"
            ],
            CorrelationRegime.RISK_OFF: [
                "Favor defensive positions or cash",
                "Reduce position sizes",
                "BTC dominance likely to rise",
                "Avoid leverage"
            ],
            CorrelationRegime.DECOUPLING: [
                "Asset-specific analysis required",
                "Pair correlations unreliable",
                "Lower confidence in signals",
                "Diversification less effective"
            ],
            CorrelationRegime.TRANSITIONING: [
                "Reduce position sizes",
                "Wait for regime clarity",
                "Monitor correlation changes closely",
                "Expect increased volatility"
            ]
        }
        
        return descriptions.get(regime, "Unknown regime"), implications.get(regime, [])
    
    def _record_regime_change(self, new_regime: CorrelationRegime, timestamp: datetime):
        """Record regime change to history."""
        if self.current_regime:
            # End the previous regime
            history_entry = RegimeHistory(
                regime=self.current_regime.regime,
                started_at=self.current_regime.started_at or timestamp,
                ended_at=timestamp,
                duration_candles=self.current_regime.duration_candles,
                confidence=self.current_regime.confidence
            )
            self.regime_history.append(history_entry)
            
            # Keep only last 100 regime changes
            if len(self.regime_history) > 100:
                self.regime_history = self.regime_history[-100:]
    
    def classify_from_matrix(
        self,
        correlation_matrix: Dict[str, CorrelationValue],
        btc_trend: str = "NEUTRAL",
        correlation_volatility: float = 0.0
    ) -> RegimeState:
        """
        Classify regime from a correlation matrix.
        """
        # Extract key correlations
        btc_spx_corr = correlation_matrix.get("BTC_SPX", CorrelationValue(
            pair=DEFAULT_PAIRS[0], value=0, method="PEARSON", window_size=30,
            timestamp=datetime.now(timezone.utc)
        )).value if "BTC_SPX" in correlation_matrix else 0.0
        
        btc_dxy_corr = correlation_matrix.get("BTC_DXY", CorrelationValue(
            pair=DEFAULT_PAIRS[0], value=0, method="PEARSON", window_size=30,
            timestamp=datetime.now(timezone.utc)
        )).value if "BTC_DXY" in correlation_matrix else 0.0
        
        btc_eth_corr = correlation_matrix.get("BTC_ETH", CorrelationValue(
            pair=DEFAULT_PAIRS[0], value=0, method="PEARSON", window_size=30,
            timestamp=datetime.now(timezone.utc)
        )).value if "BTC_ETH" in correlation_matrix else 0.8
        
        # Calculate average crypto-equity correlation
        equity_corrs = []
        for pair_id, corr_val in correlation_matrix.items():
            if "SPX" in pair_id or "NASDAQ" in pair_id:
                if "BTC" in pair_id or "ETH" in pair_id:
                    equity_corrs.append(corr_val.value)
        
        crypto_equity_avg = sum(equity_corrs) / len(equity_corrs) if equity_corrs else 0.0
        
        return self.classify_regime(
            btc_spx_corr=btc_spx_corr,
            btc_dxy_corr=btc_dxy_corr,
            btc_eth_corr=btc_eth_corr,
            crypto_equity_avg=crypto_equity_avg,
            btc_trend=btc_trend,
            correlation_volatility=correlation_volatility
        )
    
    def get_regime_history(self, limit: int = 20) -> List[Dict]:
        """Get recent regime history."""
        return [h.to_dict() for h in self.regime_history[-limit:]]
    
    def get_regime_stats(self) -> Dict:
        """Get statistics about regime distribution."""
        if not self.regime_history:
            return {"total_regimes": 0}
        
        # Count regime occurrences
        regime_counts = {}
        regime_durations = {}
        
        for h in self.regime_history:
            regime_name = h.regime.value
            if regime_name not in regime_counts:
                regime_counts[regime_name] = 0
                regime_durations[regime_name] = []
            
            regime_counts[regime_name] += 1
            regime_durations[regime_name].append(h.duration_candles)
        
        # Calculate averages
        regime_avg_duration = {
            r: sum(d) / len(d) if d else 0
            for r, d in regime_durations.items()
        }
        
        total = sum(regime_counts.values())
        regime_pct = {
            r: round(c / total * 100, 1)
            for r, c in regime_counts.items()
        }
        
        return {
            "total_regimes": total,
            "regime_counts": regime_counts,
            "regime_percentages": regime_pct,
            "regime_avg_duration": {r: round(d, 1) for r, d in regime_avg_duration.items()},
            "most_common": max(regime_counts.keys(), key=lambda k: regime_counts[k]) if regime_counts else None,
            "current_regime": self.current_regime.regime.value if self.current_regime else None
        }
    
    def is_favorable_regime(self, direction: str = "LONG") -> Dict:
        """
        Check if current regime is favorable for a given direction.
        """
        if not self.current_regime:
            return {"favorable": False, "reason": "No regime classified"}
        
        regime = self.current_regime.regime
        
        favorable_long = [
            CorrelationRegime.RISK_ON,
            CorrelationRegime.CRYPTO_NATIVE
        ]
        
        favorable_short = [
            CorrelationRegime.RISK_OFF
        ]
        
        unfavorable = [
            CorrelationRegime.TRANSITIONING
        ]
        
        if direction.upper() == "LONG":
            if regime in favorable_long:
                return {
                    "favorable": True,
                    "regime": regime.value,
                    "confidence": self.current_regime.confidence,
                    "reason": f"{regime.value} regime supports long positions"
                }
            elif regime in unfavorable:
                return {
                    "favorable": False,
                    "regime": regime.value,
                    "confidence": self.current_regime.confidence,
                    "reason": "Regime is unstable, wait for clarity"
                }
            else:
                return {
                    "favorable": None,  # Neutral
                    "regime": regime.value,
                    "confidence": self.current_regime.confidence,
                    "reason": f"{regime.value} regime is neutral for longs"
                }
        else:  # SHORT
            if regime in favorable_short:
                return {
                    "favorable": True,
                    "regime": regime.value,
                    "confidence": self.current_regime.confidence,
                    "reason": f"{regime.value} regime supports short positions"
                }
            elif regime in unfavorable:
                return {
                    "favorable": False,
                    "regime": regime.value,
                    "confidence": self.current_regime.confidence,
                    "reason": "Regime is unstable, wait for clarity"
                }
            else:
                return {
                    "favorable": None,
                    "regime": regime.value,
                    "confidence": self.current_regime.confidence,
                    "reason": f"{regime.value} regime is neutral for shorts"
                }
