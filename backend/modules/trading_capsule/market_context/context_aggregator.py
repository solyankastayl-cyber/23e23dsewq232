"""
Context Aggregator
==================

Главный слой агрегации всех context engines.
Собирает единый context snapshot.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from .context_types import (
    FundingContext,
    OIContext,
    VolatilityContext,
    MacroContext,
    VolumeProfileContext,
    MarketContextSnapshot,
    MacroRegime,
    RiskEnvironment,
    VolatilityRegime
)
from .funding_context_engine import FundingContextEngine
from .oi_context_engine import OIContextEngine
from .volatility_context_engine import VolatilityContextEngine
from .macro_context_engine import MacroContextEngine
from .volume_profile_engine import VolumeProfileEngine


class ContextAggregator:
    """
    Aggregator для объединения всех context engines.
    
    Собирает:
    - Funding context
    - OI context
    - Volatility context
    - Macro context
    - Volume profile context
    
    И формирует единый context snapshot с:
    - Overall context score
    - Long/Short bias scores
    - Strategy confidence adjustments
    - Risk multiplier
    """
    
    def __init__(self):
        self.funding_engine = FundingContextEngine()
        self.oi_engine = OIContextEngine()
        self.volatility_engine = VolatilityContextEngine()
        self.macro_engine = MacroContextEngine()
        self.volume_profile_engine = VolumeProfileEngine()
    
    def aggregate(
        self,
        symbol: str,
        timeframe: str = "1h",
        # Funding data
        funding_rates: Optional[List[float]] = None,
        # OI data
        oi_values: Optional[List[float]] = None,
        # Price/Volume data
        highs: Optional[List[float]] = None,
        lows: Optional[List[float]] = None,
        closes: Optional[List[float]] = None,
        volumes: Optional[List[float]] = None,
        # Macro data
        spx_data: Optional[List[float]] = None,
        dxy_data: Optional[List[float]] = None,
        # Current price
        current_price: float = 0.0
    ) -> MarketContextSnapshot:
        """
        Агрегация всех контекстов.
        """
        # Generate mock data if not provided
        if funding_rates is None:
            funding_rates = self.funding_engine.generate_mock_data()
        
        if oi_values is None or closes is None:
            mock_oi, mock_prices = self.oi_engine.generate_mock_data()
            oi_values = oi_values or mock_oi
            closes = closes or mock_prices
        
        if highs is None or lows is None:
            mock_h, mock_l, mock_c = self.volatility_engine.generate_mock_data()
            highs = highs or mock_h
            lows = lows or mock_l
            if closes is None:
                closes = mock_c
        
        if volumes is None:
            _, _, _, volumes = self.volume_profile_engine.generate_mock_data()
        
        if current_price == 0 and closes:
            current_price = closes[-1]
        
        # Analyze each context
        funding_ctx = self.funding_engine.analyze(funding_rates)
        oi_ctx = self.oi_engine.analyze(oi_values, closes)
        volatility_ctx = self.volatility_engine.analyze(highs, lows, closes)
        macro_ctx = self.macro_engine.analyze(spx_data, dxy_data, closes)
        volume_profile_ctx = self.volume_profile_engine.analyze(
            highs, lows, closes, volumes, current_price
        )
        
        # Calculate aggregated scores
        context_score = self._calculate_context_score(
            funding_ctx, oi_ctx, volatility_ctx, macro_ctx, volume_profile_ctx
        )
        
        long_bias, short_bias = self._calculate_bias_scores(
            funding_ctx, oi_ctx, volatility_ctx, macro_ctx, volume_profile_ctx
        )
        
        # Determine primary bias
        if long_bias > short_bias + 0.15:
            primary_bias = "LONG"
        elif short_bias > long_bias + 0.15:
            primary_bias = "SHORT"
        else:
            primary_bias = "NEUTRAL"
        
        # Context quality
        context_quality = self._determine_quality(context_score, funding_ctx, oi_ctx)
        
        # Calculate strategy adjustments
        breakout_adj = self._calculate_breakout_adjustment(
            volatility_ctx, oi_ctx, funding_ctx
        )
        mr_adj = self._calculate_mr_adjustment(
            volatility_ctx, volume_profile_ctx, macro_ctx
        )
        trend_adj = self._calculate_trend_adjustment(
            oi_ctx, funding_ctx, macro_ctx
        )
        
        # Risk multiplier
        risk_mult = self._calculate_risk_multiplier(
            volatility_ctx, macro_ctx, funding_ctx
        )
        
        # Warnings
        warnings = self._collect_warnings(
            funding_ctx, oi_ctx, volatility_ctx, macro_ctx
        )
        
        # Notes
        notes = self._collect_notes(
            funding_ctx, oi_ctx, volatility_ctx, macro_ctx, volume_profile_ctx
        )
        
        return MarketContextSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            funding=funding_ctx,
            oi=oi_ctx,
            volatility=volatility_ctx,
            macro=macro_ctx,
            volume_profile=volume_profile_ctx,
            context_score=round(context_score, 4),
            long_bias_score=round(long_bias, 4),
            short_bias_score=round(short_bias, 4),
            primary_bias=primary_bias,
            context_quality=context_quality,
            breakout_confidence_adj=round(breakout_adj, 4),
            mean_reversion_confidence_adj=round(mr_adj, 4),
            trend_confidence_adj=round(trend_adj, 4),
            risk_multiplier=round(risk_mult, 4),
            warnings=warnings,
            notes=notes,
            computed_at=datetime.utcnow()
        )
    
    def _calculate_context_score(
        self,
        funding: FundingContext,
        oi: OIContext,
        volatility: VolatilityContext,
        macro: MacroContext,
        volume: VolumeProfileContext
    ) -> float:
        """Рассчитать общий context score"""
        score = 0.5
        
        # Good conditions boost score
        if not funding.funding_extreme:
            score += 0.1
        
        if oi.participation_quality == "STRONG":
            score += 0.1
        elif oi.participation_quality == "WEAK":
            score -= 0.1
        
        if volatility.volatility_quality == "CLEAN":
            score += 0.1
        elif volatility.volatility_quality == "CHOPPY":
            score -= 0.1
        
        if macro.risk_environment == RiskEnvironment.CRYPTO_FRIENDLY:
            score += 0.1
        elif macro.risk_environment == RiskEnvironment.CRYPTO_HOSTILE:
            score -= 0.1
        
        if volume.price_acceptance:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _calculate_bias_scores(
        self,
        funding: FundingContext,
        oi: OIContext,
        volatility: VolatilityContext,
        macro: MacroContext,
        volume: VolumeProfileContext
    ) -> tuple:
        """Рассчитать long/short bias scores"""
        long_score = 0.5
        short_score = 0.5
        
        # Funding
        long_score += funding.confidence_adjustment
        short_score -= funding.confidence_adjustment
        
        # OI
        if oi.short_covering_detected:
            long_score += 0.1
        if oi.long_liquidation_detected:
            short_score += 0.1
        
        # Macro
        long_score += macro.crypto_long_confidence_adj
        short_score += macro.crypto_short_confidence_adj
        
        # Volume profile
        if volume.volume_profile_bias.value == "BELOW_VALUE_AREA":
            long_score += 0.1  # MR potential
        elif volume.volume_profile_bias.value == "ABOVE_VALUE_AREA":
            short_score += 0.1  # MR potential
        
        return (
            max(0.0, min(1.0, long_score)),
            max(0.0, min(1.0, short_score))
        )
    
    def _determine_quality(
        self,
        context_score: float,
        funding: FundingContext,
        oi: OIContext
    ) -> str:
        """Определить качество контекста"""
        if context_score > 0.7 and oi.participation_quality == "STRONG":
            return "HIGH"
        elif context_score < 0.4 or funding.funding_extreme:
            return "LOW"
        else:
            return "MEDIUM"
    
    def _calculate_breakout_adjustment(
        self,
        volatility: VolatilityContext,
        oi: OIContext,
        funding: FundingContext
    ) -> float:
        """Adjustment для breakout strategies"""
        adj = 0.0
        
        if volatility.breakout_favorable:
            adj += 0.15
        
        if oi.participation_quality == "STRONG":
            adj += 0.1
        
        if not funding.funding_extreme:
            adj += 0.05
        
        if volatility.volatility_regime == VolatilityRegime.COMPRESSED:
            adj += 0.1
        
        return max(-0.5, min(0.5, adj))
    
    def _calculate_mr_adjustment(
        self,
        volatility: VolatilityContext,
        volume: VolumeProfileContext,
        macro: MacroContext
    ) -> float:
        """Adjustment для mean reversion strategies"""
        adj = 0.0
        
        if volatility.mean_reversion_favorable:
            adj += 0.15
        
        if volume.mean_reversion_quality > 0.6:
            adj += 0.1
        
        if macro.macro_regime == MacroRegime.RISK_OFF:
            adj -= 0.1  # Harder to MR in risk-off
        
        return max(-0.5, min(0.5, adj))
    
    def _calculate_trend_adjustment(
        self,
        oi: OIContext,
        funding: FundingContext,
        macro: MacroContext
    ) -> float:
        """Adjustment для trend strategies"""
        adj = 0.0
        
        if oi.price_oi_alignment:
            adj += 0.15
        
        if not funding.funding_extreme:
            adj += 0.1
        
        if macro.cross_market_alignment > 0.6:
            adj += 0.1
        
        return max(-0.5, min(0.5, adj))
    
    def _calculate_risk_multiplier(
        self,
        volatility: VolatilityContext,
        macro: MacroContext,
        funding: FundingContext
    ) -> float:
        """Рассчитать risk multiplier"""
        mult = 1.0
        
        # Volatility impact
        mult *= volatility.risk_multiplier
        
        # Macro impact
        if macro.risk_environment == RiskEnvironment.CRYPTO_HOSTILE:
            mult *= 0.8
        
        # Funding extreme
        if funding.funding_extreme:
            mult *= 0.85
        
        return max(0.5, min(2.0, mult))
    
    def _collect_warnings(
        self,
        funding: FundingContext,
        oi: OIContext,
        volatility: VolatilityContext,
        macro: MacroContext
    ) -> List[str]:
        """Собрать warnings"""
        warnings = []
        
        if funding.funding_extreme:
            warnings.append(f"FUNDING EXTREME: {funding.funding_state.value}")
        
        if oi.squeeze_probability > 0.6:
            warnings.append(f"HIGH SQUEEZE PROBABILITY: {oi.squeeze_probability:.0%}")
        
        if volatility.volatility_regime == VolatilityRegime.UNSTABLE:
            warnings.append("VOLATILITY UNSTABLE - reduce exposure")
        
        if macro.risk_environment == RiskEnvironment.CRYPTO_HOSTILE:
            warnings.append("CRYPTO HOSTILE ENVIRONMENT")
        
        return warnings
    
    def _collect_notes(
        self,
        funding: FundingContext,
        oi: OIContext,
        volatility: VolatilityContext,
        macro: MacroContext,
        volume: VolumeProfileContext
    ) -> List[str]:
        """Собрать notes"""
        notes = []
        
        # Top note from each context
        if funding.notes:
            notes.append(f"Funding: {funding.notes[0]}")
        if oi.notes:
            notes.append(f"OI: {oi.notes[0]}")
        if volatility.notes:
            notes.append(f"Vol: {volatility.notes[0]}")
        if macro.notes:
            notes.append(f"Macro: {macro.notes[0]}")
        if volume.notes:
            notes.append(f"VP: {volume.notes[0]}")
        
        return notes
