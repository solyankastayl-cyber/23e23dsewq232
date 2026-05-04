"""
Alpha Signal Builder
====================

Собирает alpha results в aggregated alpha context.
Предоставляет данные для strategy selection и risk management.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .alpha_types import (
    AlphaResult,
    AlphaSummary,
    AlphaDirection,
    AlphaSnapshot,
    AlphaConfig
)
from .alpha_scoring_engine import AlphaScoringEngine


class AlphaSignalBuilder:
    """
    Builder для создания aggregated alpha context.
    
    Использует AlphaScoringEngine для расчётов и
    формирует финальный контекст для торговых решений.
    """
    
    def __init__(self, config: Optional[AlphaConfig] = None):
        self.config = config or AlphaConfig()
        self.scoring_engine = AlphaScoringEngine(config)
    
    def build_signals(
        self, 
        symbol: str,
        timeframe: str,
        market_data: Dict[str, Any]
    ) -> AlphaSummary:
        """
        Построение alpha сигналов из market data.
        
        Args:
            symbol: Торговый символ (BTCUSDT, etc)
            timeframe: Таймфрейм (1h, 4h, 1d)
            market_data: Dict с ключами close, high, low, volume
            
        Returns:
            AlphaSummary с агрегированными результатами
        """
        return self.scoring_engine.score(symbol, timeframe, market_data)
    
    def build_context(
        self,
        symbol: str,
        timeframe: str,
        market_data: Dict[str, Any],
        current_price: float = 0.0,
        regime: str = "UNKNOWN"
    ) -> Dict[str, Any]:
        """
        Построение полного alpha context для торговых решений.
        
        Returns:
            Dict с:
            - summary: AlphaSummary
            - decision_factors: факторы для решений
            - risk_adjustment: рекомендации по риску
        """
        summary = self.build_signals(symbol, timeframe, market_data)
        
        # Build decision factors
        decision_factors = self._build_decision_factors(summary)
        
        # Build risk adjustment
        risk_adjustment = self._build_risk_adjustment(summary)
        
        # Build strategy hints
        strategy_hints = self._build_strategy_hints(summary)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "regime": regime,
            "summary": summary.model_dump(),
            "decision_factors": decision_factors,
            "risk_adjustment": risk_adjustment,
            "strategy_hints": strategy_hints,
            "computed_at": datetime.utcnow().isoformat()
        }
    
    def _build_decision_factors(self, summary: AlphaSummary) -> Dict[str, Any]:
        """
        Построение факторов для торговых решений.
        """
        # Trend factors
        trend_score = (
            summary.trend_strength * 0.4 +
            summary.trend_acceleration * 0.3 +
            (1 - summary.trend_exhaustion) * 0.3
        )
        
        # Breakout factors
        breakout_score = (
            summary.breakout_pressure * 0.5 +
            summary.volatility_compression * 0.3 +
            summary.volume_confirmation * 0.2
        )
        
        # Reversal factors
        reversal_score = (
            summary.reversal_pressure * 0.4 +
            summary.trend_exhaustion * 0.3 +
            summary.liquidity_sweep * 0.3
        )
        
        # Volume factors
        volume_score = (
            summary.volume_confirmation * 0.6 +
            summary.volume_anomaly * 0.4
        )
        
        # Determine primary signal type
        scores = {
            "trend_continuation": trend_score,
            "breakout": breakout_score,
            "reversal": reversal_score
        }
        primary_type = max(scores, key=scores.get)
        
        return {
            "primary_signal_type": primary_type,
            "trend_score": round(trend_score, 4),
            "breakout_score": round(breakout_score, 4),
            "reversal_score": round(reversal_score, 4),
            "volume_score": round(volume_score, 4),
            "signal_clarity": round(max(scores.values()) - sorted(scores.values())[-2], 4),
            "recommendation": self._get_recommendation(summary, primary_type)
        }
    
    def _get_recommendation(self, summary: AlphaSummary, signal_type: str) -> str:
        """Генерация рекомендации"""
        if summary.alpha_confidence < 0.4:
            return "WAIT - low confidence"
        
        if signal_type == "trend_continuation" and summary.alpha_bias != AlphaDirection.NEUTRAL:
            return f"TREND_{summary.alpha_bias.value} - follow trend"
        
        if signal_type == "breakout" and summary.breakout_pressure > 0.6:
            return f"BREAKOUT_{summary.alpha_bias.value} - prepare for breakout"
        
        if signal_type == "reversal" and summary.reversal_pressure > 0.6:
            return f"REVERSAL_WATCH - potential reversal"
        
        return "NEUTRAL - no clear signal"
    
    def _build_risk_adjustment(self, summary: AlphaSummary) -> Dict[str, Any]:
        """
        Построение рекомендаций по риску.
        """
        # Base risk multiplier
        risk_multiplier = 1.0
        
        # Adjust based on confidence
        if summary.alpha_confidence > 0.7:
            risk_multiplier *= 1.2
        elif summary.alpha_confidence < 0.4:
            risk_multiplier *= 0.7
        
        # Adjust based on signal agreement
        agreement = summary.long_signals / max(1, summary.alphas_count) if summary.alpha_bias == AlphaDirection.LONG else \
                   summary.short_signals / max(1, summary.alphas_count) if summary.alpha_bias == AlphaDirection.SHORT else 0.5
        
        if agreement > 0.7:
            risk_multiplier *= 1.1
        elif agreement < 0.4:
            risk_multiplier *= 0.8
        
        # Adjust based on volatility
        if summary.volatility_expansion > 0.7:
            risk_multiplier *= 0.85  # Reduce risk in high vol
        
        # Clamp
        risk_multiplier = max(0.5, min(1.5, risk_multiplier))
        
        # Position sizing suggestion
        if risk_multiplier > 1.2:
            size_suggestion = "FULL"
        elif risk_multiplier > 0.9:
            size_suggestion = "STANDARD"
        elif risk_multiplier > 0.7:
            size_suggestion = "REDUCED"
        else:
            size_suggestion = "MINIMAL"
        
        return {
            "risk_multiplier": round(risk_multiplier, 4),
            "size_suggestion": size_suggestion,
            "confidence_factor": round(summary.alpha_confidence, 4),
            "agreement_factor": round(agreement, 4),
            "volatility_factor": round(1 - summary.volatility_expansion * 0.15, 4),
            "notes": self._get_risk_notes(summary, risk_multiplier)
        }
    
    def _get_risk_notes(self, summary: AlphaSummary, multiplier: float) -> List[str]:
        """Генерация заметок по риску"""
        notes = []
        
        if multiplier > 1.1:
            notes.append("High conviction setup - consider full position")
        elif multiplier < 0.8:
            notes.append("Low conviction - reduce position size")
        
        if summary.volatility_expansion > 0.7:
            notes.append("High volatility - tighter stops recommended")
        
        if summary.alpha_confidence > 0.7 and summary.alpha_strength > 0.7:
            notes.append("Strong alpha signal - favorable R:R expected")
        
        return notes
    
    def _build_strategy_hints(self, summary: AlphaSummary) -> Dict[str, Any]:
        """
        Построение подсказок для выбора стратегии.
        """
        hints = {
            "preferred_strategies": [],
            "avoid_strategies": [],
            "regime_alignment": []
        }
        
        # Trend strategies
        if summary.trend_strength > 0.6 and summary.trend_exhaustion < 0.4:
            hints["preferred_strategies"].extend([
                "MOMENTUM_CONTINUATION",
                "TREND_FOLLOWING",
                "MTF_BREAKOUT"
            ])
        
        # Breakout strategies
        if summary.volatility_compression > 0.6:
            hints["preferred_strategies"].extend([
                "CHANNEL_BREAKOUT",
                "COMPRESSION_BREAKOUT"
            ])
        
        # Reversal strategies
        if summary.reversal_pressure > 0.6 or summary.liquidity_sweep > 0.5:
            hints["preferred_strategies"].extend([
                "DOUBLE_BOTTOM" if summary.alpha_bias == AlphaDirection.LONG else "DOUBLE_TOP",
                "REVERSAL_PATTERN"
            ])
            hints["avoid_strategies"].extend([
                "MOMENTUM_CONTINUATION",
                "TREND_FOLLOWING"
            ])
        
        # Exhaustion - avoid trend strategies
        if summary.trend_exhaustion > 0.7:
            hints["avoid_strategies"].extend([
                "MOMENTUM_CONTINUATION",
                "TREND_FOLLOWING"
            ])
        
        # Regime alignment
        if summary.alpha_bias == AlphaDirection.LONG:
            hints["regime_alignment"] = ["TREND_UP", "EXPANSION"]
        elif summary.alpha_bias == AlphaDirection.SHORT:
            hints["regime_alignment"] = ["TREND_DOWN", "EXPANSION"]
        else:
            hints["regime_alignment"] = ["RANGE", "COMPRESSION"]
        
        # Remove duplicates
        hints["preferred_strategies"] = list(set(hints["preferred_strategies"]))
        hints["avoid_strategies"] = list(set(hints["avoid_strategies"]))
        
        return hints
    
    def create_snapshot(
        self,
        symbol: str,
        timeframe: str,
        summary: AlphaSummary,
        current_price: float = 0.0,
        regime: str = "UNKNOWN"
    ) -> AlphaSnapshot:
        """
        Создание snapshot для хранения.
        """
        import uuid
        
        return AlphaSnapshot(
            id=str(uuid.uuid4()),
            symbol=symbol,
            timeframe=timeframe,
            summary=summary,
            market_price=current_price,
            regime=regime,
            created_at=datetime.utcnow()
        )
