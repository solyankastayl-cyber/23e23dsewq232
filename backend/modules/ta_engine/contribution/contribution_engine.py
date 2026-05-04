"""
Contribution Engine
===================
Unified TA Context - собирает вклад от ВСЕХ источников TA.

Принцип:
- Каждый индикатор, паттерн, fib, mechanics-слой возвращает свой вклад
- Decision строится от полного TA Context, не от selected visible layers
- GraphVisibilityEngine влияет только на отображение, но не на мозг

Критерий готовности:
1. Все индикаторы либо влияют на score, либо marked as informational
2. Pattern/Fib/Liquidity/POI/CHOCH входят в contribution model
3. API возвращает top_drivers, all_contributions, hidden_but_used
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class SignalDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class RenderType(str, Enum):
    OVERLAY = "overlay"        # На главном графике
    PANE = "pane"              # Отдельная панель
    BACKGROUND = "background"   # Фон (POI zones)
    MARKER = "marker"          # Маркеры (sweeps, CHOCH)
    LEVEL = "level"            # Уровни (fib, S/R)
    INFORMATIONAL = "informational"  # Только информация, не рисуется


class ContributionSource(str, Enum):
    INDICATOR = "indicator"
    PATTERN = "pattern"
    STRUCTURE = "structure"
    MTF = "mtf"
    LIQUIDITY = "liquidity"
    POI = "poi"
    DISPLACEMENT = "displacement"
    CHOCH = "choch"
    FIBONACCI = "fib"
    CONFLUENCE = "confluence"


@dataclass
class Contribution:
    """Single contribution from any TA source."""
    
    # Identity
    source: ContributionSource
    name: str                          # e.g., "EMA 20", "RSI", "Supply POI", "Double Bottom"
    source_id: str                     # e.g., "ema_20", "rsi", "poi_supply_1"
    
    # Signal
    signal: SignalDirection            # bullish/bearish/neutral
    score: float                       # -1.0 (full bearish) to +1.0 (full bullish)
    confidence: float                  # 0.0 to 1.0
    
    # Weight in decision
    contribution_weight: float         # Базовый вес в общем решении (0.0-1.0)
    
    # Rendering
    render_type: RenderType
    
    # Fields with defaults MUST come after non-default fields
    adjusted_weight: float = 0.0       # Финальный вес после нормализации
    visible_default: bool = True       # Показывать по умолчанию?
    used_in_decision: bool = True      # Участвует в decision?
    reason_if_not_used: str = ""       # Почему не используется (e.g., "informational only")
    raw_value: Optional[float] = None  # Сырое значение (e.g., RSI=35)
    description: str = ""              # Описание сигнала
    
    def to_dict(self) -> Dict:
        return {
            "source": self.source.value,
            "name": self.name,
            "source_id": self.source_id,
            "signal": self.signal.value,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 3),
            "contribution_weight": round(self.contribution_weight, 4),
            "adjusted_weight": round(self.adjusted_weight, 4),
            "render_type": self.render_type.value,
            "visible_default": self.visible_default,
            "used_in_decision": self.used_in_decision,
            "reason_if_not_used": self.reason_if_not_used,
            "raw_value": round(self.raw_value, 4) if self.raw_value else None,
            "description": self.description,
        }


@dataclass
class UnifiedTAContext:
    """Complete TA context with all contributions."""
    
    # Summary
    total_sources: int = 0
    active_sources: int = 0
    informational_sources: int = 0
    
    # Aggregated signals
    aggregated_score: float = 0.0      # Weighted sum of all scores
    aggregated_confidence: float = 0.0
    aggregated_bias: SignalDirection = SignalDirection.NEUTRAL
    
    # Breakdowns
    indicators_total: int = 0
    indicators_bullish: int = 0
    indicators_bearish: int = 0
    indicators_neutral: int = 0
    
    patterns_total: int = 0
    mechanics_total: int = 0
    fib_included: bool = False
    
    # Top drivers (sorted by |adjusted_weight * score|)
    top_drivers: List[Dict] = field(default_factory=list)
    
    # All contributions
    all_contributions: List[Contribution] = field(default_factory=list)
    
    # Visibility info
    rendered_default: List[str] = field(default_factory=list)    # IDs показываемых по умолчанию
    hidden_but_used: List[str] = field(default_factory=list)     # IDs скрытых, но участвующих в decision
    
    # Categories
    contributions_by_source: Dict[str, List[Contribution]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total_sources": self.total_sources,
                "active_sources": self.active_sources,
                "informational_sources": self.informational_sources,
                "aggregated_score": round(self.aggregated_score, 4),
                "aggregated_confidence": round(self.aggregated_confidence, 3),
                "aggregated_bias": self.aggregated_bias.value,
            },
            "indicators": {
                "total": self.indicators_total,
                "bullish": self.indicators_bullish,
                "bearish": self.indicators_bearish,
                "neutral": self.indicators_neutral,
            },
            "patterns_total": self.patterns_total,
            "mechanics_total": self.mechanics_total,
            "fib_included": self.fib_included,
            "top_drivers": self.top_drivers,
            "all_contributions": [c.to_dict() for c in self.all_contributions],
            "rendered_default": self.rendered_default,
            "hidden_but_used": self.hidden_but_used,
        }


class ContributionEngine:
    """
    Builds Unified TA Context from all available sources.
    
    Weight allocation (must sum to 1.0):
    - MTF Context:        0.25 (higher TF alignment)
    - Structure Context:  0.20 (regime, trend)
    - Indicators:         0.25 (all 38+ indicators)
    - Pattern:            0.10 (detected pattern)
    - Liquidity/POI:      0.10 (market mechanics)
    - Fibonacci:          0.05 (key levels)
    - CHOCH/Displacement: 0.05 (structure shifts)
    """
    
    # Weight allocation
    WEIGHTS = {
        "mtf": 0.25,
        "structure": 0.20,
        "indicators": 0.25,
        "pattern": 0.10,
        "mechanics": 0.10,  # Liquidity + POI
        "fibonacci": 0.05,
        "choch": 0.05,
    }
    
    def build(
        self,
        # Core inputs
        mtf_context: Dict[str, Any],
        structure_context: Dict[str, Any],
        confluence: Dict[str, Any],
        
        # Mechanics
        liquidity: Dict[str, Any],
        poi: Dict[str, Any],
        displacement: Dict[str, Any],
        choch_validation: Dict[str, Any],
        
        # Pattern + Fib
        primary_pattern: Optional[Dict[str, Any]] = None,
        fibonacci: Optional[Dict[str, Any]] = None,
        
        # Indicator data (from indicator_visualization)
        indicators_data: Optional[Dict[str, Any]] = None,
        
    ) -> UnifiedTAContext:
        """Build unified TA context from all sources."""
        
        contributions: List[Contribution] = []
        
        # ═══════════════════════════════════════════════════════════════
        # 1. MTF CONTEXT — Higher timeframe alignment
        # ═══════════════════════════════════════════════════════════════
        mtf_contrib = self._extract_mtf_contribution(mtf_context)
        contributions.append(mtf_contrib)
        
        # ═══════════════════════════════════════════════════════════════
        # 2. STRUCTURE CONTEXT — Regime and trend
        # ═══════════════════════════════════════════════════════════════
        structure_contrib = self._extract_structure_contribution(structure_context)
        contributions.append(structure_contrib)
        
        # ═══════════════════════════════════════════════════════════════
        # 3. INDICATORS — All 38+ indicators from confluence
        # ═══════════════════════════════════════════════════════════════
        indicator_contribs = self._extract_indicator_contributions(confluence, indicators_data)
        contributions.extend(indicator_contribs)
        
        # ═══════════════════════════════════════════════════════════════
        # 4. PATTERN — Detected chart pattern
        # ═══════════════════════════════════════════════════════════════
        if primary_pattern:
            pattern_contrib = self._extract_pattern_contribution(primary_pattern)
            contributions.append(pattern_contrib)
        
        # ═══════════════════════════════════════════════════════════════
        # 5. LIQUIDITY + POI — Market mechanics
        # ═══════════════════════════════════════════════════════════════
        mechanics_contribs = self._extract_mechanics_contributions(liquidity, poi)
        contributions.extend(mechanics_contribs)
        
        # ═══════════════════════════════════════════════════════════════
        # 6. FIBONACCI — Key levels
        # ═══════════════════════════════════════════════════════════════
        if fibonacci and fibonacci.get("fib_set"):
            fib_contrib = self._extract_fib_contribution(fibonacci)
            contributions.append(fib_contrib)
        
        # ═══════════════════════════════════════════════════════════════
        # 7. CHOCH + DISPLACEMENT — Structure shifts
        # ═══════════════════════════════════════════════════════════════
        choch_contribs = self._extract_choch_contributions(choch_validation, displacement)
        contributions.extend(choch_contribs)
        
        # ═══════════════════════════════════════════════════════════════
        # NORMALIZE WEIGHTS & COMPUTE AGGREGATES
        # ═══════════════════════════════════════════════════════════════
        context = self._compute_aggregates(contributions)
        
        return context
    
    def _extract_mtf_contribution(self, mtf_context: Dict) -> Contribution:
        """Extract contribution from MTF context."""
        global_bias = mtf_context.get("global_bias", "neutral")
        confidence = float(mtf_context.get("confidence", 0.5) or 0.5)
        alignment = mtf_context.get("alignment", "mixed")
        
        # Score based on bias and alignment
        score = 0.0
        if global_bias == "bullish":
            score = 0.8 if alignment in ["full_bullish", "aligned"] else 0.5
        elif global_bias == "bearish":
            score = -0.8 if alignment in ["full_bearish", "aligned"] else -0.5
        
        # Adjust confidence for mixed alignment
        if alignment == "mixed":
            confidence *= 0.7
        
        return Contribution(
            source=ContributionSource.MTF,
            name="MTF Context",
            source_id="mtf_context",
            signal=SignalDirection(global_bias),
            score=score,
            confidence=confidence,
            contribution_weight=self.WEIGHTS["mtf"],
            render_type=RenderType.INFORMATIONAL,
            visible_default=False,
            description=mtf_context.get("summary", ""),
        )
    
    def _extract_structure_contribution(self, structure_context: Dict) -> Contribution:
        """Extract contribution from structure context."""
        bias = structure_context.get("bias", "neutral")
        regime = structure_context.get("regime", "range")
        score_raw = float(structure_context.get("structure_score", 0.5) or 0.5)
        trend_strength = float(structure_context.get("trend_strength", 0.0) or 0.0)
        
        # Score based on bias and trend strength
        if bias == "bullish":
            score = min(1.0, 0.5 + abs(trend_strength))
        elif bias == "bearish":
            score = max(-1.0, -0.5 - abs(trend_strength))
        else:
            score = 0.0
        
        # Confidence from structure score
        confidence = score_raw
        
        return Contribution(
            source=ContributionSource.STRUCTURE,
            name="Structure Context",
            source_id="structure_context",
            signal=SignalDirection(bias),
            score=score,
            confidence=confidence,
            contribution_weight=self.WEIGHTS["structure"],
            render_type=RenderType.INFORMATIONAL,
            visible_default=False,
            description=f"Regime: {regime}, Trend strength: {round(trend_strength, 2)}",
        )
    
    def _extract_indicator_contributions(
        self,
        confluence: Dict,
        indicators_data: Optional[Dict]
    ) -> List[Contribution]:
        """Extract contributions from all indicators via confluence."""
        contributions = []
        
        # Per-indicator weight (shared among all indicators)
        total_indicators = (
            len(confluence.get("bullish", [])) +
            len(confluence.get("bearish", [])) +
            len(confluence.get("neutral", []))
        )
        if total_indicators == 0:
            return contributions
        
        per_indicator_weight = self.WEIGHTS["indicators"] / max(1, total_indicators)
        
        # Bullish indicators
        for ind in confluence.get("bullish", []):
            contributions.append(Contribution(
                source=ContributionSource.INDICATOR,
                name=ind.get("name", "Unknown"),
                source_id=ind.get("name", "").lower().replace(" ", "_"),
                signal=SignalDirection.BULLISH,
                score=float(ind.get("strength", 0.5)),
                confidence=float(ind.get("strength", 0.5)),
                contribution_weight=per_indicator_weight,
                render_type=self._get_indicator_render_type(ind.get("name", "")),
                visible_default=self._is_indicator_default_visible(ind.get("name", "")),
                raw_value=ind.get("value"),
                description=ind.get("description", ""),
            ))
        
        # Bearish indicators
        for ind in confluence.get("bearish", []):
            contributions.append(Contribution(
                source=ContributionSource.INDICATOR,
                name=ind.get("name", "Unknown"),
                source_id=ind.get("name", "").lower().replace(" ", "_"),
                signal=SignalDirection.BEARISH,
                score=-float(ind.get("strength", 0.5)),
                confidence=float(ind.get("strength", 0.5)),
                contribution_weight=per_indicator_weight,
                render_type=self._get_indicator_render_type(ind.get("name", "")),
                visible_default=self._is_indicator_default_visible(ind.get("name", "")),
                raw_value=ind.get("value"),
                description=ind.get("description", ""),
            ))
        
        # Neutral indicators (informational only, but still tracked)
        for ind in confluence.get("neutral", []):
            contributions.append(Contribution(
                source=ContributionSource.INDICATOR,
                name=ind.get("name", "Unknown"),
                source_id=ind.get("name", "").lower().replace(" ", "_"),
                signal=SignalDirection.NEUTRAL,
                score=0.0,
                confidence=float(ind.get("strength", 0.3)),
                contribution_weight=per_indicator_weight * 0.5,  # Lower weight for neutral
                render_type=self._get_indicator_render_type(ind.get("name", "")),
                visible_default=False,
                used_in_decision=False,
                reason_if_not_used="neutral signal",
                raw_value=ind.get("value"),
                description=ind.get("description", ""),
            ))
        
        return contributions
    
    def _get_indicator_render_type(self, name: str) -> RenderType:
        """Determine render type from indicator name."""
        name_lower = name.lower()
        if any(x in name_lower for x in ["ema", "sma", "bb", "vwap", "ichimoku"]):
            return RenderType.OVERLAY
        return RenderType.PANE
    
    def _is_indicator_default_visible(self, name: str) -> bool:
        """Check if indicator should be visible by default."""
        default_visible = ["ema_20", "ema_50", "rsi", "macd"]
        name_normalized = name.lower().replace(" ", "_")
        return any(x in name_normalized for x in default_visible)
    
    def _extract_pattern_contribution(self, pattern: Dict) -> Contribution:
        """Extract contribution from detected pattern."""
        direction = pattern.get("direction", "neutral")
        confidence = float(pattern.get("confidence", 0.5) or 0.5)
        pattern_type = pattern.get("type", "unknown")
        
        score = 0.0
        if direction == "bullish":
            score = confidence
        elif direction == "bearish":
            score = -confidence
        
        return Contribution(
            source=ContributionSource.PATTERN,
            name=f"Pattern: {pattern_type}",
            source_id=f"pattern_{pattern_type.lower().replace(' ', '_')}",
            signal=SignalDirection(direction),
            score=score,
            confidence=confidence,
            contribution_weight=self.WEIGHTS["pattern"],
            render_type=RenderType.OVERLAY,
            visible_default=True,
            description=f"{pattern_type} pattern with {round(confidence*100)}% confidence",
        )
    
    def _extract_mechanics_contributions(
        self,
        liquidity: Dict,
        poi: Dict
    ) -> List[Contribution]:
        """Extract contributions from liquidity and POI."""
        contributions = []
        half_weight = self.WEIGHTS["mechanics"] / 2
        
        # Liquidity pools
        pools = liquidity.get("pools", [])
        active_pools = [p for p in pools if p.get("status") == "active"]
        
        # BSL (Buy Side Liquidity) above price = potential reversal zone (bearish)
        bsl_pools = [p for p in active_pools if p.get("type") == "buy_side_liquidity"]
        # SSL (Sell Side Liquidity) below price = potential reversal zone (bullish)
        ssl_pools = [p for p in active_pools if p.get("type") == "sell_side_liquidity"]
        
        if bsl_pools:
            top_bsl = max(bsl_pools, key=lambda x: x.get("strength", 0))
            contributions.append(Contribution(
                source=ContributionSource.LIQUIDITY,
                name="BSL Pool",
                source_id="liquidity_bsl",
                signal=SignalDirection.BEARISH,  # Price tends to tap BSL then reverse
                score=-0.3 * min(1.0, float(top_bsl.get("strength", 3)) / 6),
                confidence=min(1.0, float(top_bsl.get("strength", 3)) / 6),
                contribution_weight=half_weight / 2,
                render_type=RenderType.LEVEL,
                visible_default=True,
                description=f"Buy-side liquidity at {top_bsl.get('price', 0):.0f}",
            ))
        
        if ssl_pools:
            top_ssl = max(ssl_pools, key=lambda x: x.get("strength", 0))
            contributions.append(Contribution(
                source=ContributionSource.LIQUIDITY,
                name="SSL Pool",
                source_id="liquidity_ssl",
                signal=SignalDirection.BULLISH,  # Price tends to tap SSL then reverse
                score=0.3 * min(1.0, float(top_ssl.get("strength", 3)) / 6),
                confidence=min(1.0, float(top_ssl.get("strength", 3)) / 6),
                contribution_weight=half_weight / 2,
                render_type=RenderType.LEVEL,
                visible_default=True,
                description=f"Sell-side liquidity at {top_ssl.get('price', 0):.0f}",
            ))
        
        # POI zones
        active_poi = poi.get("active_zones", []) if poi else []
        demand_zones = [z for z in active_poi if z.get("type") == "demand"]
        supply_zones = [z for z in active_poi if z.get("type") == "supply"]
        
        if demand_zones:
            top_demand = max(demand_zones, key=lambda x: x.get("strength", 0))
            contributions.append(Contribution(
                source=ContributionSource.POI,
                name="Demand Zone",
                source_id="poi_demand",
                signal=SignalDirection.BULLISH,
                score=0.4 * min(1.0, float(top_demand.get("strength", 3)) / 6),
                confidence=min(1.0, float(top_demand.get("strength", 3)) / 6),
                contribution_weight=half_weight / 2,
                render_type=RenderType.BACKGROUND,
                visible_default=True,
                description=f"Demand OB at {top_demand.get('price_mid', 0):.0f}",
            ))
        
        if supply_zones:
            top_supply = max(supply_zones, key=lambda x: x.get("strength", 0))
            contributions.append(Contribution(
                source=ContributionSource.POI,
                name="Supply Zone",
                source_id="poi_supply",
                signal=SignalDirection.BEARISH,
                score=-0.4 * min(1.0, float(top_supply.get("strength", 3)) / 6),
                confidence=min(1.0, float(top_supply.get("strength", 3)) / 6),
                contribution_weight=half_weight / 2,
                render_type=RenderType.BACKGROUND,
                visible_default=True,
                description=f"Supply OB at {top_supply.get('price_mid', 0):.0f}",
            ))
        
        return contributions
    
    def _extract_fib_contribution(self, fibonacci: Dict) -> Contribution:
        """Extract contribution from Fibonacci levels."""
        fib_set = fibonacci.get("fib_set", {})
        direction = fib_set.get("direction", "neutral")
        
        # Fib is informational — shows key levels, doesn't strongly bias direction
        score = 0.0
        if direction == "bullish":
            score = 0.2
        elif direction == "bearish":
            score = -0.2
        
        return Contribution(
            source=ContributionSource.FIBONACCI,
            name="Fibonacci Levels",
            source_id="fibonacci",
            signal=SignalDirection(direction),
            score=score,
            confidence=0.6,
            contribution_weight=self.WEIGHTS["fibonacci"],
            render_type=RenderType.LEVEL,
            visible_default=True,
            description=f"Fib from {fib_set.get('swing_low', {}).get('price', 0):.0f} to {fib_set.get('swing_high', {}).get('price', 0):.0f}",
        )
    
    def _extract_choch_contributions(
        self,
        choch_validation: Dict,
        displacement: Dict
    ) -> List[Contribution]:
        """Extract contributions from CHOCH and displacement."""
        contributions = []
        half_weight = self.WEIGHTS["choch"] / 2
        
        # CHOCH
        if choch_validation and choch_validation.get("is_valid"):
            choch_dir = choch_validation.get("direction", "neutral")
            choch_score = float(choch_validation.get("score", 0.5) or 0.5)
            
            score = 0.0
            if choch_dir == "bullish":
                score = choch_score
            elif choch_dir == "bearish":
                score = -choch_score
            
            contributions.append(Contribution(
                source=ContributionSource.CHOCH,
                name="CHOCH Validation",
                source_id="choch",
                signal=SignalDirection(choch_dir),
                score=score,
                confidence=choch_score,
                contribution_weight=half_weight,
                render_type=RenderType.MARKER,
                visible_default=True,
                description=choch_validation.get("label", ""),
            ))
        
        # Displacement
        last_impulse = displacement.get("last_impulse") if displacement else None
        if last_impulse:
            disp_dir = last_impulse.get("direction", "neutral")
            disp_strength = float(last_impulse.get("strength", 1.0) or 1.0)
            
            # Normalize strength (typical range 1-5)
            normalized_strength = min(1.0, disp_strength / 3)
            
            score = 0.0
            if disp_dir == "bullish":
                score = normalized_strength * 0.5
            elif disp_dir == "bearish":
                score = -normalized_strength * 0.5
            
            contributions.append(Contribution(
                source=ContributionSource.DISPLACEMENT,
                name="Displacement",
                source_id="displacement",
                signal=SignalDirection(disp_dir),
                score=score,
                confidence=normalized_strength,
                contribution_weight=half_weight,
                render_type=RenderType.MARKER,
                visible_default=False,
                description=last_impulse.get("label", ""),
            ))
        
        return contributions
    
    def _compute_aggregates(self, contributions: List[Contribution]) -> UnifiedTAContext:
        """Compute aggregated scores and organize context."""
        
        # Normalize weights
        total_weight = sum(c.contribution_weight for c in contributions if c.used_in_decision)
        if total_weight > 0:
            for c in contributions:
                if c.used_in_decision:
                    c.adjusted_weight = c.contribution_weight / total_weight
        
        # Compute aggregated score
        aggregated_score = sum(
            c.score * c.adjusted_weight * c.confidence
            for c in contributions
            if c.used_in_decision
        )
        
        # Compute aggregated confidence
        aggregated_confidence = sum(
            c.confidence * c.adjusted_weight
            for c in contributions
            if c.used_in_decision
        )
        
        # Determine bias
        if aggregated_score > 0.15:
            aggregated_bias = SignalDirection.BULLISH
        elif aggregated_score < -0.15:
            aggregated_bias = SignalDirection.BEARISH
        else:
            aggregated_bias = SignalDirection.NEUTRAL
        
        # Count by source type
        indicators = [c for c in contributions if c.source == ContributionSource.INDICATOR]
        patterns = [c for c in contributions if c.source == ContributionSource.PATTERN]
        mechanics = [c for c in contributions if c.source in [
            ContributionSource.LIQUIDITY, ContributionSource.POI,
            ContributionSource.DISPLACEMENT, ContributionSource.CHOCH
        ]]
        fib_exists = any(c.source == ContributionSource.FIBONACCI for c in contributions)
        
        # Top drivers (sorted by absolute contribution)
        active_contributions = [c for c in contributions if c.used_in_decision]
        sorted_by_impact = sorted(
            active_contributions,
            key=lambda c: abs(c.score * c.adjusted_weight * c.confidence),
            reverse=True
        )
        
        top_drivers = []
        for c in sorted_by_impact[:10]:
            top_drivers.append({
                "name": c.name,
                "score": round(c.score, 3),
                "signal": c.signal.value,
                "weight": round(c.adjusted_weight, 4),
                "impact": round(abs(c.score * c.adjusted_weight * c.confidence), 4),
            })
        
        # Visibility lists
        rendered_default = [c.source_id for c in contributions if c.visible_default]
        hidden_but_used = [
            c.source_id for c in contributions
            if c.used_in_decision and not c.visible_default
        ]
        
        # Group by source
        contributions_by_source = {}
        for c in contributions:
            source_key = c.source.value
            if source_key not in contributions_by_source:
                contributions_by_source[source_key] = []
            contributions_by_source[source_key].append(c)
        
        return UnifiedTAContext(
            total_sources=len(contributions),
            active_sources=len([c for c in contributions if c.used_in_decision]),
            informational_sources=len([c for c in contributions if not c.used_in_decision]),
            
            aggregated_score=aggregated_score,
            aggregated_confidence=aggregated_confidence,
            aggregated_bias=aggregated_bias,
            
            indicators_total=len(indicators),
            indicators_bullish=len([i for i in indicators if i.signal == SignalDirection.BULLISH]),
            indicators_bearish=len([i for i in indicators if i.signal == SignalDirection.BEARISH]),
            indicators_neutral=len([i for i in indicators if i.signal == SignalDirection.NEUTRAL]),
            
            patterns_total=len(patterns),
            mechanics_total=len(mechanics),
            fib_included=fib_exists,
            
            top_drivers=top_drivers,
            all_contributions=contributions,
            
            rendered_default=rendered_default,
            hidden_but_used=hidden_but_used,
            contributions_by_source=contributions_by_source,
        )


# Singleton
_contribution_engine: Optional[ContributionEngine] = None


def get_contribution_engine() -> ContributionEngine:
    global _contribution_engine
    if _contribution_engine is None:
        _contribution_engine = ContributionEngine()
    return _contribution_engine
