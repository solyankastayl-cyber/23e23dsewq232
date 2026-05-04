"""
Setup Builder
==============
The central module that builds unified Setup objects.

Pipeline:
    Price Data → Pattern Engine → Indicator Engine → Structure Engine → Level Engine
              → Confluence Engine → Setup Builder → Setup

This module:
1. Collects signals from all engines
2. Builds confluence analysis
3. Ranks and selects best setups
4. Generates explanations
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pymongo import MongoClient, DESCENDING

from modules.ta_engine.setup.setup_types import (
    Setup,
    SetupType,
    Direction,
    DetectedPattern,
    IndicatorSignal,
    StructurePoint,
    PriceLevel,
    Confluence,
    ConflictSignal,
    SetupAnalysisResult,
    PatternType,
)
from modules.ta_engine.setup.pattern_detector import get_pattern_detector
from modules.ta_engine.setup.indicator_engine import get_indicator_engine
from modules.ta_engine.setup.level_engine import get_level_engine
from modules.ta_engine.setup.structure_engine import get_structure_engine
from modules.ta_engine.setup.market_data_service import get_market_data_service

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


class SetupBuilder:
    """
    Builds unified Setup objects from market data.
    
    This is the central coordinator that:
    1. Fetches market data
    2. Runs all analysis engines
    3. Computes confluence
    4. Builds and ranks setups
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        self.pattern_detector = get_pattern_detector()
        self.indicator_engine = get_indicator_engine()
        self.level_engine = get_level_engine()
        self.structure_engine = get_structure_engine()
        
        # Setup type mapping from patterns
        self.pattern_to_setup = {
            PatternType.ASCENDING_TRIANGLE: SetupType.ASCENDING_TRIANGLE_BREAKOUT,
            PatternType.DESCENDING_TRIANGLE: SetupType.DESCENDING_TRIANGLE_BREAKOUT,
            PatternType.SYMMETRICAL_TRIANGLE: SetupType.SYMMETRICAL_TRIANGLE_BREAKOUT,
            PatternType.ASCENDING_CHANNEL: SetupType.CHANNEL_BREAKOUT,
            PatternType.DESCENDING_CHANNEL: SetupType.CHANNEL_BREAKOUT,
            PatternType.HORIZONTAL_CHANNEL: SetupType.RANGE_BREAKOUT,
            PatternType.DOUBLE_TOP: SetupType.DOUBLE_TOP_REVERSAL,
            PatternType.DOUBLE_BOTTOM: SetupType.DOUBLE_BOTTOM_REVERSAL,
            PatternType.BULL_FLAG: SetupType.FLAG_CONTINUATION,
            PatternType.BEAR_FLAG: SetupType.FLAG_CONTINUATION,
            PatternType.COMPRESSION: SetupType.COMPRESSION_BREAKOUT,
        }
    
    def build(self, symbol: str, timeframe: str = "1d") -> SetupAnalysisResult:
        """
        Build complete setup analysis for a symbol.
        
        Returns SetupAnalysisResult with:
        - top_setup: The strongest detected setup
        - alternative_setups: Other detected setups
        - technical_bias: Overall market direction
        - bias_confidence: Confidence in the bias
        """
        # Get candle data
        candles = self._get_candles(symbol, timeframe, limit=200)
        
        if len(candles) < 50:
            return self._empty_result()
        
        # Run all analysis engines
        patterns = self.pattern_detector.detect_all(candles)
        indicators = self.indicator_engine.analyze_all(candles)
        levels = self.level_engine.analyze_all(candles)
        structure_points, structure_bias, structure_meta = self.structure_engine.analyze_all(candles)
        
        # Detect market regime
        market_regime = self._detect_regime(candles, indicators)
        
        # Get current price
        current_price = candles[-1]["close"]
        
        # Build setups from patterns
        setups = []
        for pattern in patterns:
            setup = self._build_setup_from_pattern(
                symbol=symbol,
                timeframe=timeframe,
                pattern=pattern,
                indicators=indicators,
                levels=levels,
                structure_points=structure_points,
                current_price=current_price,
                market_regime=market_regime,
            )
            if setup:
                setups.append(setup)
        
        # If no pattern-based setups, try to build from structure/indicators
        if not setups:
            structure_setup = self._build_setup_from_structure(
                symbol=symbol,
                timeframe=timeframe,
                structure_bias=structure_bias,
                structure_points=structure_points,
                indicators=indicators,
                levels=levels,
                current_price=current_price,
                market_regime=market_regime,
            )
            if structure_setup:
                setups.append(structure_setup)
        
        # Rank setups
        setups.sort(key=lambda s: s.confluence_score, reverse=True)
        
        # Calculate overall technical bias
        technical_bias, bias_confidence = self._calculate_technical_bias(
            patterns, indicators, structure_bias, setups
        )
        
        return SetupAnalysisResult(
            top_setup=setups[0] if setups else None,
            alternative_setups=setups[1:5] if len(setups) > 1 else [],
            technical_bias=technical_bias,
            bias_confidence=bias_confidence,
        )
    
    def _build_setup_from_pattern(
        self,
        symbol: str,
        timeframe: str,
        pattern: DetectedPattern,
        indicators: List[IndicatorSignal],
        levels: List[PriceLevel],
        structure_points: List[StructurePoint],
        current_price: float,
        market_regime: str,
    ) -> Optional[Setup]:
        """Build a Setup object from a detected pattern."""
        
        # Determine setup type from pattern
        setup_type = self.pattern_to_setup.get(pattern.pattern_type, SetupType.CUSTOM)
        
        # Filter relevant indicators (same direction as pattern)
        relevant_indicators = [
            ind for ind in indicators
            if ind.direction == pattern.direction or ind.direction == Direction.NEUTRAL
        ][:5]
        
        # Find relevant levels near current price
        relevant_levels = [
            lvl for lvl in levels
            if abs(lvl.price - current_price) / current_price < 0.1  # Within 10%
        ][:5]
        
        # Calculate confluence
        primary_confluence = self._compute_confluence(
            pattern=pattern,
            indicators=relevant_indicators,
            levels=relevant_levels,
            structure_points=structure_points,
        )
        
        # Find conflicting signals
        conflicts = self._find_conflicts(
            main_direction=pattern.direction,
            indicators=indicators,
            levels=levels,
        )
        
        # Calculate confidence
        confidence = self._calculate_setup_confidence(
            pattern=pattern,
            indicators=relevant_indicators,
            confluence=primary_confluence,
            conflicts=conflicts,
        )
        
        # Generate explanation
        explanation = self._generate_explanation(
            setup_type=setup_type,
            pattern=pattern,
            indicators=relevant_indicators,
            levels=relevant_levels,
            conflicts=conflicts,
        )
        
        # Build entry zone and targets
        entry_zone = None
        if pattern.breakout_level:
            entry_zone = {
                "low": pattern.breakout_level * 0.995,
                "high": pattern.breakout_level * 1.005,
            }
        
        targets = []
        if pattern.target_price:
            targets = [pattern.target_price]
            # Add additional targets
            if pattern.direction == Direction.BULLISH and pattern.breakout_level:
                move = pattern.target_price - pattern.breakout_level
                targets.append(pattern.breakout_level + move * 1.5)
            elif pattern.direction == Direction.BEARISH and pattern.breakout_level:
                move = pattern.breakout_level - pattern.target_price
                targets.append(pattern.breakout_level - move * 1.5)
        
        return Setup(
            setup_id=str(uuid.uuid4())[:8],
            asset=symbol,
            timeframe=timeframe,
            setup_type=setup_type,
            direction=pattern.direction,
            confidence=confidence,
            confluence_score=primary_confluence.score,
            patterns=[pattern],
            indicators=relevant_indicators,
            levels=relevant_levels,
            structure=structure_points[-10:],  # Last 10 structure points
            primary_confluence=primary_confluence,
            secondary_confluence=[],
            conflicts=conflicts,
            entry_zone=entry_zone,
            invalidation=pattern.invalidation,
            targets=targets,
            current_price=current_price,
            market_regime=market_regime,
            explanation=explanation,
        )
    
    def _build_setup_from_structure(
        self,
        symbol: str,
        timeframe: str,
        structure_bias: Direction,
        structure_points: List[StructurePoint],
        indicators: List[IndicatorSignal],
        levels: List[PriceLevel],
        current_price: float,
        market_regime: str,
    ) -> Optional[Setup]:
        """Build a Setup from structure analysis when no clear pattern."""
        
        if structure_bias == Direction.NEUTRAL:
            return None
        
        # Determine setup type
        if structure_bias == Direction.BULLISH:
            setup_type = SetupType.TREND_CONTINUATION
        else:
            setup_type = SetupType.TREND_CONTINUATION
        
        # Filter aligned indicators
        aligned_indicators = [
            ind for ind in indicators
            if ind.direction == structure_bias
        ][:5]
        
        # Calculate confluence score
        confluence_score = 0.3  # Base score
        for ind in aligned_indicators:
            confluence_score += ind.strength * 0.1
        confluence_score = min(confluence_score, 1.0)
        
        primary_confluence = Confluence(
            score=confluence_score,
            direction=structure_bias,
            components=[f"Structure: {structure_bias.value}"] + [ind.name for ind in aligned_indicators[:3]],
            description=f"{structure_bias.value.capitalize()} structure with indicator confirmation",
        )
        
        # Find support/resistance for targets
        support_levels = [l for l in levels if l.level_type.value == "support"]
        resistance_levels = [l for l in levels if l.level_type.value == "resistance"]
        
        targets = []
        invalidation = None
        
        if structure_bias == Direction.BULLISH:
            if resistance_levels:
                targets = [r.price for r in resistance_levels[:2]]
            if support_levels:
                invalidation = min(s.price for s in support_levels)
        else:
            if support_levels:
                targets = [s.price for s in support_levels[:2]]
            if resistance_levels:
                invalidation = max(r.price for r in resistance_levels)
        
        explanation = self._generate_structure_explanation(
            structure_bias, structure_points, aligned_indicators
        )
        
        return Setup(
            setup_id=str(uuid.uuid4())[:8],
            asset=symbol,
            timeframe=timeframe,
            setup_type=setup_type,
            direction=structure_bias,
            confidence=confluence_score * 0.8,
            confluence_score=confluence_score,
            patterns=[],
            indicators=aligned_indicators,
            levels=levels[:5],
            structure=structure_points[-10:],
            primary_confluence=primary_confluence,
            secondary_confluence=[],
            conflicts=self._find_conflicts(structure_bias, indicators, levels),
            entry_zone=None,
            invalidation=invalidation,
            targets=targets,
            current_price=current_price,
            market_regime=market_regime,
            explanation=explanation,
        )
    
    def _compute_confluence(
        self,
        pattern: DetectedPattern,
        indicators: List[IndicatorSignal],
        levels: List[PriceLevel],
        structure_points: List[StructurePoint],
    ) -> Confluence:
        """Compute confluence score for a setup."""
        
        components = []
        score = 0.0
        
        # Pattern contribution
        components.append(f"Pattern: {pattern.pattern_type.value}")
        score += pattern.confidence * 0.35
        
        # Indicator alignment
        aligned_count = sum(1 for ind in indicators if ind.direction == pattern.direction)
        if aligned_count >= 3:
            components.append(f"Indicators: {aligned_count} aligned")
            score += 0.25
        elif aligned_count >= 1:
            components.append(f"Indicators: {aligned_count} aligned")
            score += 0.15
        
        # Level support
        nearby_supports = sum(1 for lvl in levels if lvl.level_type.value == "support")
        nearby_resistances = sum(1 for lvl in levels if lvl.level_type.value == "resistance")
        
        if pattern.direction == Direction.BULLISH and nearby_supports >= 2:
            components.append("Support cluster")
            score += 0.15
        elif pattern.direction == Direction.BEARISH and nearby_resistances >= 2:
            components.append("Resistance cluster")
            score += 0.15
        
        # Structure confirmation
        recent_structure = structure_points[-5:] if structure_points else []
        bullish_structure = sum(1 for s in recent_structure if s.structure_type.value in ["HH", "HL"])
        bearish_structure = sum(1 for s in recent_structure if s.structure_type.value in ["LH", "LL"])
        
        if pattern.direction == Direction.BULLISH and bullish_structure > bearish_structure:
            components.append("Bullish structure")
            score += 0.15
        elif pattern.direction == Direction.BEARISH and bearish_structure > bullish_structure:
            components.append("Bearish structure")
            score += 0.15
        
        # Fib confluence
        fib_levels = [l for l in levels if "fib" in l.level_type.value.lower()]
        if fib_levels:
            components.append("Fibonacci confluence")
            score += 0.1
        
        score = min(score, 1.0)
        
        description = f"{pattern.direction.value.capitalize()} {pattern.pattern_type.value.replace('_', ' ')} with {len(components)-1} confirmations"
        
        return Confluence(
            score=score,
            direction=pattern.direction,
            components=components,
            description=description,
        )
    
    def _find_conflicts(
        self,
        main_direction: Direction,
        indicators: List[IndicatorSignal],
        levels: List[PriceLevel],
    ) -> List[ConflictSignal]:
        """Find signals that conflict with main thesis."""
        conflicts = []
        
        # Check for opposing indicators
        for ind in indicators:
            if ind.direction != Direction.NEUTRAL and ind.direction != main_direction:
                severity = "high" if ind.strength > 0.7 else "medium" if ind.strength > 0.5 else "low"
                conflicts.append(ConflictSignal(
                    name=ind.name,
                    description=ind.description,
                    severity=severity,
                    impact=-ind.strength * 0.3,
                ))
        
        # Check for major resistance/support in way of targets
        if main_direction == Direction.BULLISH:
            strong_resistance = [l for l in levels if l.level_type.value == "resistance" and l.strength > 0.7]
            if strong_resistance:
                conflicts.append(ConflictSignal(
                    name="Major Resistance",
                    description=f"Strong resistance level at ${strong_resistance[0].price:,.2f}",
                    severity="medium",
                    impact=-0.2,
                ))
        elif main_direction == Direction.BEARISH:
            strong_support = [l for l in levels if l.level_type.value == "support" and l.strength > 0.7]
            if strong_support:
                conflicts.append(ConflictSignal(
                    name="Major Support",
                    description=f"Strong support level at ${strong_support[0].price:,.2f}",
                    severity="medium",
                    impact=-0.2,
                ))
        
        return conflicts[:5]  # Max 5 conflicts
    
    def _calculate_setup_confidence(
        self,
        pattern: DetectedPattern,
        indicators: List[IndicatorSignal],
        confluence: Confluence,
        conflicts: List[ConflictSignal],
    ) -> float:
        """Calculate overall setup confidence."""
        confidence = confluence.score * 0.6
        confidence += pattern.confidence * 0.3
        
        # Indicator boost
        avg_indicator_strength = sum(i.strength for i in indicators) / max(len(indicators), 1)
        confidence += avg_indicator_strength * 0.1
        
        # Conflict penalty
        for conflict in conflicts:
            confidence += conflict.impact
        
        return max(min(confidence, 1.0), 0.0)
    
    def _calculate_technical_bias(
        self,
        patterns: List[DetectedPattern],
        indicators: List[IndicatorSignal],
        structure_bias: Direction,
        setups: List[Setup],
    ) -> Tuple[Direction, float]:
        """Calculate overall technical bias."""
        
        bullish_score = 0.0
        bearish_score = 0.0
        
        # Pattern contribution
        for pattern in patterns:
            weight = pattern.confidence * 0.3
            if pattern.direction == Direction.BULLISH:
                bullish_score += weight
            elif pattern.direction == Direction.BEARISH:
                bearish_score += weight
        
        # Indicator contribution
        for ind in indicators[:5]:  # Top 5 indicators
            weight = ind.strength * 0.15
            if ind.direction == Direction.BULLISH:
                bullish_score += weight
            elif ind.direction == Direction.BEARISH:
                bearish_score += weight
        
        # Structure contribution
        if structure_bias == Direction.BULLISH:
            bullish_score += 0.25
        elif structure_bias == Direction.BEARISH:
            bearish_score += 0.25
        
        # Setup contribution
        if setups:
            top_setup = setups[0]
            weight = top_setup.confluence_score * 0.3
            if top_setup.direction == Direction.BULLISH:
                bullish_score += weight
            elif top_setup.direction == Direction.BEARISH:
                bearish_score += weight
        
        total = bullish_score + bearish_score
        if total < 0.1:
            return Direction.NEUTRAL, 0.5
        
        if bullish_score > bearish_score * 1.2:
            confidence = bullish_score / total
            return Direction.BULLISH, min(confidence, 0.95)
        elif bearish_score > bullish_score * 1.2:
            confidence = bearish_score / total
            return Direction.BEARISH, min(confidence, 0.95)
        else:
            return Direction.NEUTRAL, 0.5
    
    def _generate_explanation(
        self,
        setup_type: SetupType,
        pattern: DetectedPattern,
        indicators: List[IndicatorSignal],
        levels: List[PriceLevel],
        conflicts: List[ConflictSignal],
    ) -> str:
        """Generate human-readable explanation of the setup."""
        
        lines = []
        
        # Pattern description
        pattern_name = pattern.pattern_type.value.replace("_", " ").title()
        direction_word = "bullish" if pattern.direction == Direction.BULLISH else "bearish"
        lines.append(f"Price is forming a {pattern_name} pattern suggesting {direction_word} continuation.")
        
        # Indicator confirmation
        if indicators:
            aligned = [i.name for i in indicators if i.direction == pattern.direction][:3]
            if aligned:
                lines.append(f"Confirmed by: {', '.join(aligned)}.")
        
        # Key levels
        supports = [l for l in levels if l.level_type.value == "support"]
        resistances = [l for l in levels if l.level_type.value == "resistance"]
        
        if pattern.direction == Direction.BULLISH and supports:
            lines.append(f"Support cluster at ${supports[0].price:,.2f}.")
        if pattern.direction == Direction.BEARISH and resistances:
            lines.append(f"Resistance at ${resistances[0].price:,.2f}.")
        
        # Entry/Target
        if pattern.breakout_level:
            action = "breakout above" if pattern.direction == Direction.BULLISH else "breakdown below"
            lines.append(f"Primary trigger is {action} ${pattern.breakout_level:,.2f}.")
        
        if pattern.invalidation:
            lines.append(f"Invalidation below ${pattern.invalidation:,.2f}.")
        
        # Conflicts
        if conflicts:
            lines.append(f"Watch: {conflicts[0].description}.")
        
        return " ".join(lines)
    
    def _generate_structure_explanation(
        self,
        bias: Direction,
        structure_points: List[StructurePoint],
        indicators: List[IndicatorSignal],
    ) -> str:
        """Generate explanation for structure-based setup."""
        
        direction_word = "bullish" if bias == Direction.BULLISH else "bearish"
        
        lines = [f"Market structure remains {direction_word}."]
        
        # Count structure types
        if structure_points:
            recent = structure_points[-5:]
            hh = sum(1 for s in recent if s.structure_type.value == "HH")
            hl = sum(1 for s in recent if s.structure_type.value == "HL")
            lh = sum(1 for s in recent if s.structure_type.value == "LH")
            ll = sum(1 for s in recent if s.structure_type.value == "LL")
            
            if bias == Direction.BULLISH and (hh or hl):
                lines.append(f"Recent structure shows {hh} higher highs, {hl} higher lows.")
            elif bias == Direction.BEARISH and (lh or ll):
                lines.append(f"Recent structure shows {lh} lower highs, {ll} lower lows.")
        
        if indicators:
            aligned = [i.name for i in indicators[:3]]
            lines.append(f"Indicators aligned: {', '.join(aligned)}.")
        
        return " ".join(lines)
    
    def _detect_regime(self, candles: List[Dict], indicators: List[IndicatorSignal]) -> str:
        """Detect current market regime."""
        closes = [c["close"] for c in candles]
        
        # Calculate trend strength
        sma20 = sum(closes[-20:]) / 20
        sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma20
        
        current_price = closes[-1]
        
        # ATR for volatility
        atr_signal = next((i for i in indicators if i.name == "ATR"), None)
        
        if current_price > sma20 > sma50:
            return "TREND_UP"
        elif current_price < sma20 < sma50:
            return "TREND_DOWN"
        elif atr_signal and "low_volatility" in atr_signal.signal_type:
            return "COMPRESSION"
        elif atr_signal and "high_volatility" in atr_signal.signal_type:
            return "EXPANSION"
        else:
            return "RANGE"
    
    def _get_candles(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Get candles using MarketDataService."""
        service = get_market_data_service()
        return service.get_candles(symbol, timeframe, limit)
    
    def _empty_result(self) -> SetupAnalysisResult:
        """Return empty result when data is insufficient."""
        return SetupAnalysisResult(
            top_setup=None,
            alternative_setups=[],
            technical_bias=Direction.NEUTRAL,
            bias_confidence=0.5,
        )


# Singleton
_builder: Optional[SetupBuilder] = None


def get_setup_builder() -> SetupBuilder:
    """Get singleton setup builder."""
    global _builder
    if _builder is None:
        _builder = SetupBuilder()
    return _builder
