"""
Macro Context Engine
====================

Анализ макро среды для определения:
- Risk-on / Risk-off
- SPX / DXY context
- Crypto-friendly backdrop
- Cross-market alignment
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import random

from .context_types import MacroRegime, RiskEnvironment, MacroContext


class MacroContextEngine:
    """
    Engine для анализа макро контекста.
    
    Внутренний анализ на основе:
    - SPX proxy (risk appetite)
    - DXY proxy (dollar strength)
    - Cross-market correlations
    """
    
    def __init__(
        self,
        risk_on_threshold: float = 0.6,
        risk_off_threshold: float = 0.4
    ):
        self.risk_on_threshold = risk_on_threshold
        self.risk_off_threshold = risk_off_threshold
    
    def analyze(
        self,
        spx_data: Optional[List[float]] = None,
        dxy_data: Optional[List[float]] = None,
        btc_data: Optional[List[float]] = None,
        timestamps: Optional[List[datetime]] = None
    ) -> MacroContext:
        """
        Анализ макро контекста.
        
        Args:
            spx_data: S&P 500 proxy data (or mock)
            dxy_data: DXY proxy data (or mock)
            btc_data: BTC price for correlation
            
        Returns:
            MacroContext
        """
        # Generate mock if not provided
        if spx_data is None:
            spx_data = self._generate_mock_index(100, base=4500, volatility=0.01)
        if dxy_data is None:
            dxy_data = self._generate_mock_index(100, base=104, volatility=0.005)
        if btc_data is None:
            btc_data = self._generate_mock_index(100, base=45000, volatility=0.02)
        
        # Analyze SPX
        spx_context, spx_score = self._analyze_index(spx_data, "SPX")
        
        # Analyze DXY (inverse relationship with crypto)
        dxy_context, dxy_score = self._analyze_index(dxy_data, "DXY")
        
        # Determine macro regime
        regime = self._determine_regime(spx_score, dxy_score)
        
        # Determine bias
        macro_bias = self._determine_bias(spx_context, dxy_context)
        
        # Risk environment
        risk_env = self._determine_risk_environment(spx_context, dxy_context, regime)
        
        # Cross-market alignment
        alignment = self._calculate_alignment(spx_data, dxy_data, btc_data)
        
        # Confidence adjustments
        long_adj, short_adj = self._calculate_confidence_adjustments(
            regime, risk_env, spx_context, dxy_context
        )
        
        # Notes
        notes = self._generate_notes(regime, risk_env, spx_context, dxy_context)
        
        return MacroContext(
            macro_regime=regime,
            macro_bias=macro_bias,
            risk_environment=risk_env,
            spx_context=spx_context,
            dxy_context=dxy_context,
            cross_market_alignment=round(alignment, 4),
            crypto_long_confidence_adj=round(long_adj, 4),
            crypto_short_confidence_adj=round(short_adj, 4),
            notes=notes
        )
    
    def _generate_mock_index(
        self,
        count: int,
        base: float,
        volatility: float
    ) -> List[float]:
        """Генерация mock index data"""
        values = []
        price = base
        
        for _ in range(count):
            change = random.uniform(-volatility, volatility)
            price *= (1 + change)
            values.append(price)
        
        return values
    
    def _analyze_index(self, data: List[float], index_name: str) -> tuple:
        """Анализ индекса"""
        if len(data) < 20:
            return "NEUTRAL", 0.5
        
        # Recent trend
        recent_change = (data[-1] - data[-10]) / data[-10] * 100
        longer_change = (data[-1] - data[-20]) / data[-20] * 100
        
        # Determine context
        if recent_change > 1 and longer_change > 2:
            context = "STRONG"
            score = 0.7 + min(0.3, longer_change / 10)
        elif recent_change < -1 and longer_change < -2:
            context = "WEAK"
            score = 0.3 - min(0.2, abs(longer_change) / 10)
        else:
            context = "NEUTRAL"
            score = 0.5
        
        return context, max(0.0, min(1.0, score))
    
    def _determine_regime(self, spx_score: float, dxy_score: float) -> MacroRegime:
        """Определить макро режим"""
        # Risk-on: SPX strong, DXY weak
        # Risk-off: SPX weak, DXY strong
        
        risk_score = spx_score * 0.6 + (1 - dxy_score) * 0.4
        
        if risk_score > self.risk_on_threshold:
            return MacroRegime.RISK_ON
        elif risk_score < self.risk_off_threshold:
            return MacroRegime.RISK_OFF
        elif abs(risk_score - 0.5) < 0.1:
            return MacroRegime.TRANSITIONING
        else:
            return MacroRegime.NEUTRAL
    
    def _determine_bias(self, spx_context: str, dxy_context: str) -> str:
        """Определить макро bias"""
        if spx_context == "STRONG" and dxy_context != "STRONG":
            return "BULLISH"
        elif spx_context == "WEAK" or dxy_context == "STRONG":
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def _determine_risk_environment(
        self,
        spx_context: str,
        dxy_context: str,
        regime: MacroRegime
    ) -> RiskEnvironment:
        """Определить риск среду"""
        if regime == MacroRegime.RISK_ON and spx_context == "STRONG":
            return RiskEnvironment.CRYPTO_FRIENDLY
        elif regime == MacroRegime.RISK_OFF and dxy_context == "STRONG":
            return RiskEnvironment.CRYPTO_HOSTILE
        else:
            return RiskEnvironment.NEUTRAL
    
    def _calculate_alignment(
        self,
        spx_data: List[float],
        dxy_data: List[float],
        btc_data: List[float]
    ) -> float:
        """Рассчитать cross-market alignment"""
        if len(spx_data) < 10 or len(dxy_data) < 10 or len(btc_data) < 10:
            return 0.5
        
        # Simple correlation proxy
        spx_changes = [(spx_data[i] - spx_data[i-1]) / spx_data[i-1] for i in range(-10, 0)]
        btc_changes = [(btc_data[i] - btc_data[i-1]) / btc_data[i-1] for i in range(-10, 0)]
        
        # Count aligned moves
        aligned = sum(1 for s, b in zip(spx_changes, btc_changes) if (s > 0) == (b > 0))
        alignment = aligned / len(spx_changes)
        
        return alignment
    
    def _calculate_confidence_adjustments(
        self,
        regime: MacroRegime,
        risk_env: RiskEnvironment,
        spx_context: str,
        dxy_context: str
    ) -> tuple:
        """Рассчитать adjustments для confidence"""
        long_adj = 0.0
        short_adj = 0.0
        
        if risk_env == RiskEnvironment.CRYPTO_FRIENDLY:
            long_adj = 0.15
            short_adj = -0.1
        elif risk_env == RiskEnvironment.CRYPTO_HOSTILE:
            long_adj = -0.15
            short_adj = 0.1
        
        # DXY strong = bad for crypto longs
        if dxy_context == "STRONG":
            long_adj -= 0.1
            short_adj += 0.05
        elif dxy_context == "WEAK":
            long_adj += 0.05
        
        return (
            max(-0.5, min(0.5, long_adj)),
            max(-0.5, min(0.5, short_adj))
        )
    
    def _generate_notes(
        self,
        regime: MacroRegime,
        risk_env: RiskEnvironment,
        spx_context: str,
        dxy_context: str
    ) -> List[str]:
        """Генерация заметок"""
        notes = []
        
        notes.append(f"Macro regime: {regime.value}")
        notes.append(f"SPX: {spx_context}, DXY: {dxy_context}")
        
        if risk_env == RiskEnvironment.CRYPTO_HOSTILE:
            notes.append("WARNING: Crypto-hostile backdrop - reduce long exposure")
        elif risk_env == RiskEnvironment.CRYPTO_FRIENDLY:
            notes.append("Crypto-friendly environment - favorable for longs")
        
        if spx_context == "WEAK" and dxy_context == "STRONG":
            notes.append("Risk-off environment: DXY strong + SPX weak")
        
        return notes
