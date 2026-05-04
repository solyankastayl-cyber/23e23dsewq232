"""
Final Analysis Resolver
========================

ГЛАВНЫЙ ПРИНЦИП:
На любом таймфрейме система ОБЯЗАНА вернуть один из трёх типов ответа:
1. FIGURE - есть чистая фигура
2. STRUCTURE - нет фигуры, но есть структура (HH/HL/LH/LL)
3. CONTEXT - нет локальной структуры, показываем контекст ТФ

ПУСТОГО СОСТОЯНИЯ БЫТЬ НЕ ДОЛЖНО НИКОГДА.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class StructureResult:
    """Structure Layer result - ALWAYS meaningful."""
    trend: str  # up, down, neutral
    phase: str  # impulse, correction, transition, compression, expansion
    swing_state: str  # "HH-HL sequence intact", "LH-LL breakdown", etc.
    bias: str  # bullish, bearish, neutral
    is_meaningful: bool = True
    swings: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "trend": self.trend,
            "phase": self.phase,
            "swing_state": self.swing_state,
            "bias": self.bias,
            "is_meaningful": self.is_meaningful,
        }


@dataclass
class ContextResult:
    """Context Layer result - macro view."""
    regime: str  # macro uptrend, macro downtrend, range, transition
    volatility: str  # low, normal, high, extreme
    location: str  # near support, near resistance, mid-range, breakout zone
    range_position: str  # upper_half, lower_half, middle
    
    def to_dict(self) -> Dict:
        return {
            "regime": self.regime,
            "volatility": self.volatility,
            "location": self.location,
            "range_position": self.range_position,
        }


@dataclass
class AnalysisResult:
    """Complete analysis result - NEVER empty."""
    timeframe: str
    analysis_mode: str  # figure, structure, context
    
    figure: Optional[Dict] = None
    structure: Optional[Dict] = None
    context: Optional[Dict] = None
    summary: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        result = {
            "timeframe": self.timeframe,
            "analysis_mode": self.analysis_mode,
            "figure": self.figure,
            "structure": self.structure,
            "context": self.context,
            "summary": self.summary,
        }
        # Validation
        assert self.analysis_mode in ["figure", "structure", "context"]
        assert self.summary.get("title", "") != ""
        assert self.summary.get("text", "") != ""
        return result


class StructureLayer:
    """
    Structure Layer - железобетонный fallback.
    Работает ВСЕГДА. Возвращает HH/HL/LH/LL + bias + phase.
    """
    
    def run(self, candles: List[Dict], swings: List[Dict] = None) -> StructureResult:
        """
        Build structure state from swings.
        ALWAYS returns meaningful result.
        """
        if not candles or len(candles) < 20:
            return self._default_structure()
        
        # Find swings if not provided
        if not swings:
            swings = self._find_swings(candles)
        
        if len(swings) < 4:
            return self._default_structure()
        
        # Count swing types
        hh_count = sum(1 for s in swings if s.get("type") == "HH")
        hl_count = sum(1 for s in swings if s.get("type") == "HL")
        lh_count = sum(1 for s in swings if s.get("type") == "LH")
        ll_count = sum(1 for s in swings if s.get("type") == "LL")
        
        # Determine trend and bias
        bullish_score = hh_count + hl_count
        bearish_score = lh_count + ll_count
        
        if bullish_score > bearish_score + 1:
            trend = "up"
            bias = "bullish"
        elif bearish_score > bullish_score + 1:
            trend = "down"
            bias = "bearish"
        else:
            trend = "neutral"
            bias = "neutral"
        
        # Determine phase
        phase = self._detect_phase(candles, swings, trend)
        
        # Build swing state description
        swing_state = self._summarize_swings(swings, hh_count, hl_count, lh_count, ll_count)
        
        return StructureResult(
            trend=trend,
            phase=phase,
            swing_state=swing_state,
            bias=bias,
            is_meaningful=True,
            swings=swings,
        )
    
    def _find_swings(self, candles: List[Dict], window: int = 3) -> List[Dict]:
        """Find swing highs and lows with type classification."""
        swings = []
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        
        prev_high = None
        prev_low = None
        
        for i in range(window, len(candles) - window):
            # Swing high
            if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] >= highs[i+j] for j in range(1, window+1)):
                swing_type = "HH" if prev_high is None or highs[i] > prev_high else "LH"
                swings.append({
                    "index": i,
                    "price": highs[i],
                    "swing": "high",
                    "type": swing_type,
                    "time": candles[i].get("time", 0),
                })
                prev_high = highs[i]
            
            # Swing low
            if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] <= lows[i+j] for j in range(1, window+1)):
                swing_type = "HL" if prev_low is None or lows[i] > prev_low else "LL"
                swings.append({
                    "index": i,
                    "price": lows[i],
                    "swing": "low",
                    "type": swing_type,
                    "time": candles[i].get("time", 0),
                })
                prev_low = lows[i]
        
        return sorted(swings, key=lambda x: x["index"])
    
    def _detect_phase(self, candles: List[Dict], swings: List[Dict], trend: str) -> str:
        """Detect market phase."""
        if len(candles) < 10:
            return "unknown"
        
        # Check recent price action
        recent = candles[-10:]
        start_price = recent[0].get("close", 0)
        end_price = recent[-1].get("close", 0)
        
        if start_price == 0:
            return "unknown"
        
        change_pct = (end_price - start_price) / start_price
        
        # Check volatility (range compression/expansion)
        ranges = [c.get("high", 0) - c.get("low", 0) for c in recent]
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        recent_range = ranges[-1] if ranges else 0
        
        is_compressing = recent_range < avg_range * 0.7
        is_expanding = recent_range > avg_range * 1.3
        
        if trend == "up":
            if change_pct > 0.02:
                return "impulse"
            elif change_pct < -0.01:
                return "correction"
            elif is_compressing:
                return "compression"
            else:
                return "consolidation"
        elif trend == "down":
            if change_pct < -0.02:
                return "impulse"
            elif change_pct > 0.01:
                return "correction"
            elif is_compressing:
                return "compression"
            else:
                return "consolidation"
        else:
            if is_compressing:
                return "compression"
            elif is_expanding:
                return "expansion"
            else:
                return "transition"
    
    def _summarize_swings(self, swings: List[Dict], hh: int, hl: int, lh: int, ll: int) -> str:
        """Generate human-readable swing state."""
        if hh + hl > lh + ll:
            if hh > 0 and hl > 0:
                return f"HH-HL sequence intact ({hh} HH, {hl} HL)"
            elif hh > 0:
                return f"Higher highs forming ({hh} HH)"
            else:
                return f"Higher lows holding ({hl} HL)"
        elif lh + ll > hh + hl:
            if lh > 0 and ll > 0:
                return f"LH-LL sequence active ({lh} LH, {ll} LL)"
            elif ll > 0:
                return f"Lower lows forming ({ll} LL)"
            else:
                return f"Lower highs capping ({lh} LH)"
        else:
            return f"Mixed structure ({hh}HH {hl}HL {lh}LH {ll}LL)"
    
    def _default_structure(self) -> StructureResult:
        """Return default structure when data is insufficient."""
        return StructureResult(
            trend="neutral",
            phase="unknown",
            swing_state="Insufficient data for swing analysis",
            bias="neutral",
            is_meaningful=False,
        )


class ContextLayer:
    """
    Context Layer - macro view for HTF.
    Provides regime, volatility, location.
    """
    
    def run(self, candles: List[Dict], timeframe: str) -> ContextResult:
        """Build context from candles."""
        if not candles or len(candles) < 20:
            return self._default_context()
        
        # Calculate regime
        regime = self._detect_regime(candles)
        
        # Calculate volatility
        volatility = self._detect_volatility(candles)
        
        # Calculate location
        location, range_position = self._detect_location(candles)
        
        return ContextResult(
            regime=regime,
            volatility=volatility,
            location=location,
            range_position=range_position,
        )
    
    def _detect_regime(self, candles: List[Dict]) -> str:
        """Detect macro regime."""
        if len(candles) < 50:
            return "unknown"
        
        # Compare start, middle, end
        start_price = sum(c.get("close", 0) for c in candles[:10]) / 10
        mid_price = sum(c.get("close", 0) for c in candles[len(candles)//2-5:len(candles)//2+5]) / 10
        end_price = sum(c.get("close", 0) for c in candles[-10:]) / 10
        
        if start_price == 0:
            return "unknown"
        
        total_change = (end_price - start_price) / start_price
        
        if total_change > 0.15:
            return "macro uptrend"
        elif total_change < -0.15:
            return "macro downtrend"
        elif abs(total_change) < 0.05:
            return "range"
        else:
            return "transition"
    
    def _detect_volatility(self, candles: List[Dict]) -> str:
        """Detect volatility level."""
        if len(candles) < 20:
            return "normal"
        
        # Calculate ATR-like measure
        ranges = []
        for i in range(1, len(candles)):
            h = candles[i].get("high", 0)
            l = candles[i].get("low", 0)
            pc = candles[i-1].get("close", 0)
            if pc > 0:
                tr = max(h - l, abs(h - pc), abs(l - pc))
                ranges.append(tr / pc)  # Normalized
        
        if not ranges:
            return "normal"
        
        avg_range = sum(ranges) / len(ranges)
        
        if avg_range < 0.01:
            return "low"
        elif avg_range < 0.03:
            return "normal"
        elif avg_range < 0.05:
            return "high"
        else:
            return "extreme"
    
    def _detect_location(self, candles: List[Dict]) -> tuple:
        """Detect price location relative to range."""
        if len(candles) < 20:
            return "unknown", "middle"
        
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        current = candles[-1].get("close", 0)
        
        range_high = max(highs)
        range_low = min(lows)
        range_size = range_high - range_low
        
        if range_size == 0:
            return "unknown", "middle"
        
        position = (current - range_low) / range_size
        
        # Range position
        if position > 0.7:
            range_position = "upper_half"
        elif position < 0.3:
            range_position = "lower_half"
        else:
            range_position = "middle"
        
        # Location description
        if position > 0.9:
            location = "near resistance"
        elif position < 0.1:
            location = "near support"
        elif position > 0.7:
            location = "upper range"
        elif position < 0.3:
            location = "lower range"
        else:
            location = "mid-range"
        
        return location, range_position
    
    def _default_context(self) -> ContextResult:
        """Return default context."""
        return ContextResult(
            regime="unknown",
            volatility="normal",
            location="unknown",
            range_position="middle",
        )


class SummaryBuilder:
    """
    Builds human-readable summary from analysis.
    NEVER returns empty title or text.
    """
    
    def build(
        self,
        mode: str,
        figure: Optional[Dict],
        structure: Dict,
        context: Dict,
        timeframe: str,
    ) -> Dict:
        """Build summary based on analysis mode."""
        
        if mode == "figure" and figure:
            return self._figure_summary(figure, structure)
        elif mode == "structure":
            return self._structure_summary(structure, context)
        else:
            return self._context_summary(context, structure, timeframe)
    
    def _figure_summary(self, figure: Dict, structure: Dict) -> Dict:
        """Build figure mode summary."""
        fig_type = figure.get("type", "pattern").replace("_", " ").title()
        state = figure.get("state", "forming")
        bias = figure.get("bias", structure.get("bias", "neutral"))
        confidence = figure.get("confidence", 0.5)
        
        # Title
        bias_adj = "Bullish" if bias == "bullish" else "Bearish" if bias == "bearish" else ""
        title = f"{bias_adj} {fig_type} {state}".strip()
        
        # Text
        if state == "forming":
            text = f"Price is forming a {fig_type.lower()} pattern. "
        elif state == "maturing":
            text = f"{fig_type} is maturing and approaching a decision point. "
        elif state == "breakout":
            text = f"{fig_type} has broken out. "
        else:
            text = f"{fig_type} detected. "
        
        # Add structure context
        struct_bias = structure.get("bias", "neutral")
        if struct_bias == bias:
            text += f"The broader structure supports this {bias} bias."
        else:
            text += f"Note: broader structure shows {struct_bias} tendency."
        
        return {"title": title, "text": text}
    
    def _structure_summary(self, structure: Dict, context: Dict) -> Dict:
        """Build structure mode summary."""
        trend = structure.get("trend", "neutral")
        phase = structure.get("phase", "unknown")
        bias = structure.get("bias", "neutral")
        swing_state = structure.get("swing_state", "")
        
        # Title
        if trend == "up":
            title = f"Bullish structure in {phase}"
        elif trend == "down":
            title = f"Bearish structure in {phase}"
        else:
            title = f"Neutral structure - {phase}"
        
        # Text
        text = f"No clean figure is active. "
        
        if swing_state:
            text += f"{swing_state}. "
        
        if trend == "up":
            text += "Higher highs and higher lows define the broader bullish structure."
        elif trend == "down":
            text += "Lower highs and lower lows define the broader bearish structure."
        else:
            text += "Price is in a transitional phase without clear directional bias."
        
        return {"title": title, "text": text}
    
    def _context_summary(self, context: Dict, structure: Dict, timeframe: str) -> Dict:
        """Build context mode summary."""
        regime = context.get("regime", "unknown")
        location = context.get("location", "mid-range")
        volatility = context.get("volatility", "normal")
        
        # Title
        if "uptrend" in regime:
            title = f"Macro bullish trend - {location}"
        elif "downtrend" in regime:
            title = f"Macro bearish trend - {location}"
        elif regime == "range":
            title = f"Range-bound market - {location}"
        else:
            title = f"Market in transition - {location}"
        
        # Text
        text = f"On {timeframe}, "
        
        if "uptrend" in regime:
            text += "the macro trend remains bullish. "
        elif "downtrend" in regime:
            text += "the macro trend remains bearish. "
        else:
            text += "price is consolidating without clear macro direction. "
        
        text += f"Volatility is {volatility}. "
        text += f"Price is currently {location}."
        
        return {"title": title, "text": text}


class FinalAnalysisResolver:
    """
    Main orchestrator - sits above all layers.
    NEVER returns empty analysis.
    """
    
    def __init__(self):
        self.structure_layer = StructureLayer()
        self.context_layer = ContextLayer()
        self.summary_builder = SummaryBuilder()
    
    def resolve(
        self,
        timeframe: str,
        candles: List[Dict],
        figure_result: Optional[Dict] = None,
        swings: List[Dict] = None,
    ) -> AnalysisResult:
        """
        Resolve final analysis for timeframe.
        
        Priority:
        - LTF (4H, 1D): figure > structure > context
        - HTF (1M+): context > structure > figure
        """
        # Build structure (ALWAYS)
        structure = self.structure_layer.run(candles, swings)
        
        # Build context (ALWAYS)
        context = self.context_layer.run(candles, timeframe)
        
        # Determine TF role
        tf_role = self._get_tf_role(timeframe)
        
        # Apply display gate to figure
        displayable_figure = self._apply_display_gate(figure_result)
        
        # Resolve analysis mode
        mode = self._resolve_mode(displayable_figure, structure, context, tf_role)
        
        # Build summary
        summary = self.summary_builder.build(
            mode=mode,
            figure=displayable_figure,
            structure=structure.to_dict(),
            context=context.to_dict(),
            timeframe=timeframe,
        )
        
        return AnalysisResult(
            timeframe=timeframe,
            analysis_mode=mode,
            figure=displayable_figure,
            structure=structure.to_dict(),
            context=context.to_dict(),
            summary=summary,
        )
    
    def _get_tf_role(self, timeframe: str) -> str:
        """Determine timeframe role."""
        tf_upper = timeframe.upper()
        
        if tf_upper in ["1H", "4H"]:
            return "execution"  # LTF, figure priority
        elif tf_upper in ["1D", "7D"]:
            return "pattern"  # Main pattern layer
        elif tf_upper in ["1M", "3M", "6M", "1Y"]:
            return "macro"  # HTF, context priority
        else:
            return "pattern"
    
    def _apply_display_gate(self, figure: Optional[Dict]) -> Optional[Dict]:
        """Apply display gate to figure."""
        if not figure:
            return None
        
        # Check if figure is displayable
        confidence = figure.get("confidence", 0)
        state = figure.get("state", "")
        
        # Minimum thresholds
        if confidence < 0.5:
            return None
        
        if state == "invalidated":
            return None
        
        figure["is_displayable"] = True
        return figure
    
    def _resolve_mode(
        self,
        figure: Optional[Dict],
        structure: StructureResult,
        context: ContextResult,
        tf_role: str,
    ) -> str:
        """
        Resolve analysis mode based on available data and TF role.
        
        Rules:
        - figure wins only if it's clean and displayable
        - else structure if meaningful
        - else context
        
        For HTF: context takes priority.
        """
        # HTF prioritizes context
        if tf_role == "macro":
            if structure.is_meaningful:
                return "structure"  # Still show structure for meaning
            return "context"
        
        # LTF/Pattern TF: figure > structure > context
        if figure and figure.get("is_displayable"):
            return "figure"
        
        if structure.is_meaningful:
            return "structure"
        
        return "context"


# Factory function
def get_final_analysis_resolver() -> FinalAnalysisResolver:
    """Get resolver instance."""
    return FinalAnalysisResolver()
