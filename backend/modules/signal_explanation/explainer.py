"""
Signal Explainer — PHASE 51

Core engine for signal explanation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

from .models import (
    SignalExplanation,
    SignalDriver,
    SignalConflict,
    ConfidenceBreakdown,
    DriverType,
    ConflictSeverity,
    MetaAlphaExplanation,
)


# ═══════════════════════════════════════════════════════════════
# Hypothesis Weights (from system_freeze_v1.md)
# ═══════════════════════════════════════════════════════════════

HYPOTHESIS_WEIGHTS = {
    "alpha": 0.33,
    "regime": 0.23,
    "microstructure": 0.18,
    "macro": 0.10,
    "fractal_market": 0.05,
    "fractal_similarity": 0.05,
    "cross_asset": 0.06,
}


class SignalExplainer:
    """Explains signals from the hypothesis engine."""
    
    def explain_hypothesis(
        self,
        hypothesis: Dict[str, Any],
        market_state: Optional[Dict[str, Any]] = None,
        patterns: Optional[List[Dict[str, Any]]] = None,
        fractal_matches: Optional[List[Dict[str, Any]]] = None,
        capital_flow: Optional[Dict[str, Any]] = None,
    ) -> SignalExplanation:
        """Generate explanation for a hypothesis signal."""
        
        signal_id = f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        direction = hypothesis.get("direction", "neutral")
        confidence = hypothesis.get("confidence", 0.5)
        
        # Build confidence breakdown
        breakdown = self._build_confidence_breakdown(hypothesis)
        
        # Identify drivers
        drivers = self._identify_drivers(hypothesis, patterns, fractal_matches, capital_flow)
        
        # Identify conflicts
        conflicts = self._identify_conflicts(hypothesis, drivers)
        
        # Generate supporting and conflicting factors
        supporting = self._get_supporting_factors(drivers, direction)
        conflicting = self._get_conflicting_factors(conflicts)
        
        # Generate narrative
        narrative = self._generate_narrative(
            direction, confidence, drivers, conflicts, 
            hypothesis.get("symbol", ""), hypothesis.get("timeframe", "")
        )
        
        # Generate summary
        summary = self._generate_summary(direction, confidence, drivers)
        
        # Risk factors
        risk_factors = self._identify_risk_factors(hypothesis, conflicts, market_state)
        
        # Chart highlights
        chart_highlights = self._get_chart_highlights(patterns, fractal_matches)
        
        # Determine strength
        if confidence >= 0.8:
            strength = "very_strong"
        elif confidence >= 0.65:
            strength = "strong"
        elif confidence >= 0.5:
            strength = "moderate"
        else:
            strength = "weak"
        
        return SignalExplanation(
            signal_id=signal_id,
            hypothesis_id=hypothesis.get("hypothesis_id"),
            symbol=hypothesis.get("symbol", ""),
            timeframe=hypothesis.get("timeframe", ""),
            timestamp=datetime.now(timezone.utc),
            direction=direction,
            confidence=confidence,
            strength=strength,
            summary=summary,
            narrative=narrative,
            drivers=drivers,
            supporting_factors=supporting,
            conflicting_factors=conflicting,
            confidence_breakdown=breakdown,
            conflicts=conflicts,
            risk_factors=risk_factors,
            chart_highlights=chart_highlights,
        )
    
    def _build_confidence_breakdown(
        self,
        hypothesis: Dict[str, Any]
    ) -> ConfidenceBreakdown:
        """Build confidence breakdown from hypothesis scores."""
        
        # Get individual scores
        alpha_score = hypothesis.get("alpha_score", 0)
        regime_score = hypothesis.get("regime_score", 0)
        micro_score = hypothesis.get("microstructure_score", 0)
        fractal_market = hypothesis.get("fractal_market_score", 0)
        fractal_sim = hypothesis.get("fractal_similarity_score", 0)
        cross_asset = hypothesis.get("cross_asset_score", 0)
        capital_flow = hypothesis.get("capital_flow_score", 0)
        reflexivity = hypothesis.get("reflexivity_score", 0)
        
        # Apply weights
        return ConfidenceBreakdown(
            alpha_contribution=alpha_score * HYPOTHESIS_WEIGHTS.get("alpha", 0.33),
            regime_contribution=regime_score * HYPOTHESIS_WEIGHTS.get("regime", 0.23),
            microstructure_contribution=micro_score * HYPOTHESIS_WEIGHTS.get("microstructure", 0.18),
            capital_flow_contribution=capital_flow * 0.05,
            fractal_market_contribution=fractal_market * HYPOTHESIS_WEIGHTS.get("fractal_market", 0.05),
            fractal_similarity_contribution=fractal_sim * HYPOTHESIS_WEIGHTS.get("fractal_similarity", 0.05),
            cross_asset_contribution=cross_asset * HYPOTHESIS_WEIGHTS.get("cross_asset", 0.06),
            reflexivity_contribution=reflexivity * 0.05,
            weights=HYPOTHESIS_WEIGHTS,
        )
    
    def _identify_drivers(
        self,
        hypothesis: Dict[str, Any],
        patterns: Optional[List[Dict[str, Any]]],
        fractal_matches: Optional[List[Dict[str, Any]]],
        capital_flow: Optional[Dict[str, Any]],
    ) -> List[SignalDriver]:
        """Identify main signal drivers."""
        drivers = []
        direction = hypothesis.get("direction", "neutral")
        
        # Alpha driver
        alpha_score = hypothesis.get("alpha_score", 0)
        if alpha_score > 0.3:
            alpha_sources = hypothesis.get("alpha_sources", [])
            drivers.append(SignalDriver(
                driver_type=DriverType.ALPHA,
                name="Alpha Signals",
                contribution=alpha_score * HYPOTHESIS_WEIGHTS["alpha"],
                description=f"Active alpha signals: {', '.join(alpha_sources[:3]) if alpha_sources else 'Multiple sources'}",
                details={"sources": alpha_sources, "score": alpha_score},
            ))
        
        # Regime driver
        regime_score = hypothesis.get("regime_score", 0)
        if regime_score > 0.3:
            drivers.append(SignalDriver(
                driver_type=DriverType.REGIME,
                name="Market Regime",
                contribution=regime_score * HYPOTHESIS_WEIGHTS["regime"],
                description=f"Regime aligned with {direction} bias",
                details={"score": regime_score},
            ))
        
        # Microstructure driver
        micro_score = hypothesis.get("microstructure_score", 0)
        if micro_score > 0.2:
            drivers.append(SignalDriver(
                driver_type=DriverType.MICROSTRUCTURE,
                name="Microstructure",
                contribution=micro_score * HYPOTHESIS_WEIGHTS["microstructure"],
                description="Orderbook and liquidity structure supportive",
                details={"score": micro_score},
            ))
        
        # Capital flow driver
        cf_score = hypothesis.get("capital_flow_score", 0)
        if capital_flow or cf_score > 0.2:
            cf_bias = capital_flow.get("bias", "neutral") if capital_flow else direction
            drivers.append(SignalDriver(
                driver_type=DriverType.CAPITAL_FLOW,
                name="Capital Flow",
                contribution=cf_score * 0.05,
                description=f"Capital flow bias: {cf_bias}",
                details={"score": cf_score, "bias": cf_bias},
            ))
        
        # Pattern driver
        if patterns:
            confirmed = [p for p in patterns if p.get("status") == "confirmed"]
            if confirmed:
                drivers.append(SignalDriver(
                    driver_type=DriverType.TECHNICAL,
                    name="Technical Patterns",
                    contribution=0.1,
                    description=f"Confirmed patterns: {', '.join(p.get('pattern_type', '') for p in confirmed[:2])}",
                    details={"patterns": [p.get("pattern_type") for p in confirmed]},
                ))
        
        # Fractal driver
        fractal_score = hypothesis.get("fractal_similarity_score", 0)
        if fractal_matches and fractal_score > 0.3:
            best_match = fractal_matches[0] if fractal_matches else {}
            drivers.append(SignalDriver(
                driver_type=DriverType.FRACTAL,
                name="Fractal Similarity",
                contribution=fractal_score * HYPOTHESIS_WEIGHTS["fractal_similarity"],
                description=f"Similar to {best_match.get('reference_context', 'historical pattern')} ({best_match.get('similarity', 0)*100:.0f}%)",
                details={
                    "reference": best_match.get("reference_context"),
                    "similarity": best_match.get("similarity"),
                },
            ))
        
        # Sort by contribution
        drivers.sort(key=lambda d: d.contribution, reverse=True)
        
        return drivers
    
    def _identify_conflicts(
        self,
        hypothesis: Dict[str, Any],
        drivers: List[SignalDriver]
    ) -> List[SignalConflict]:
        """Identify conflicting factors."""
        conflicts = []
        direction = hypothesis.get("direction", "neutral")
        
        # Check for opposing drivers
        positive_drivers = [d for d in drivers if d.contribution > 0]
        
        # Example conflicts
        micro_score = hypothesis.get("microstructure_score", 0)
        if micro_score < -0.2:
            conflicts.append(SignalConflict(
                name="Microstructure Divergence",
                severity=ConflictSeverity.MEDIUM,
                description="Orderbook structure shows opposing pressure",
                impact=-0.1,
                resolution="Monitor for orderbook alignment before entry",
            ))
        
        # Capital flow conflict
        cf_score = hypothesis.get("capital_flow_score", 0)
        if (direction == "bullish" and cf_score < -0.3) or (direction == "bearish" and cf_score > 0.3):
            conflicts.append(SignalConflict(
                name="Capital Flow Divergence",
                severity=ConflictSeverity.HIGH,
                description="Capital flow direction opposes signal",
                impact=-0.15,
                resolution="Wait for capital flow alignment",
            ))
        
        # Reflexivity conflict
        ref_score = hypothesis.get("reflexivity_score", 0)
        if ref_score < -0.2:
            conflicts.append(SignalConflict(
                name="Reflexivity Warning",
                severity=ConflictSeverity.LOW,
                description="Market reflexivity suggests possible reversal",
                impact=-0.05,
            ))
        
        return conflicts
    
    def _get_supporting_factors(
        self,
        drivers: List[SignalDriver],
        direction: str
    ) -> List[str]:
        """Get list of supporting factors."""
        factors = []
        
        for driver in drivers:
            if driver.contribution > 0:
                factors.append(driver.description)
        
        return factors[:5]
    
    def _get_conflicting_factors(
        self,
        conflicts: List[SignalConflict]
    ) -> List[str]:
        """Get list of conflicting factors."""
        return [c.description for c in conflicts]
    
    def _generate_summary(
        self,
        direction: str,
        confidence: float,
        drivers: List[SignalDriver]
    ) -> str:
        """Generate short summary."""
        if not drivers:
            return f"{direction.title()} signal with {confidence*100:.0f}% confidence"
        
        top_driver = drivers[0]
        return f"{direction.title()} signal driven by {top_driver.name} ({confidence*100:.0f}% confidence)"
    
    def _generate_narrative(
        self,
        direction: str,
        confidence: float,
        drivers: List[SignalDriver],
        conflicts: List[SignalConflict],
        symbol: str,
        timeframe: str
    ) -> str:
        """Generate human-readable narrative."""
        
        # Opening
        strength_word = "strong" if confidence >= 0.7 else "moderate" if confidence >= 0.5 else "weak"
        narrative = f"The system has identified a {strength_word} {direction} signal for {symbol} on the {timeframe} timeframe. "
        
        # Main drivers
        if drivers:
            narrative += "This signal is primarily driven by: "
            driver_texts = []
            for d in drivers[:3]:
                driver_texts.append(d.description)
            narrative += "; ".join(driver_texts) + ". "
        
        # Conflicts
        if conflicts:
            narrative += "However, there are some conflicting factors to consider: "
            conflict_texts = [c.description for c in conflicts[:2]]
            narrative += "; ".join(conflict_texts) + ". "
        
        # Recommendation
        if confidence >= 0.7 and len(conflicts) == 0:
            narrative += "The signal shows strong alignment across multiple intelligence layers."
        elif confidence >= 0.5:
            narrative += "Consider position sizing based on conflict level."
        else:
            narrative += "Caution advised due to low confidence."
        
        return narrative
    
    def _identify_risk_factors(
        self,
        hypothesis: Dict[str, Any],
        conflicts: List[SignalConflict],
        market_state: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify risk factors."""
        risks = []
        
        # From conflicts
        for conflict in conflicts:
            if conflict.severity == ConflictSeverity.HIGH:
                risks.append(f"High severity conflict: {conflict.name}")
        
        # Low confidence
        if hypothesis.get("confidence", 0) < 0.5:
            risks.append("Low overall confidence - consider reduced position size")
        
        # Market state risks
        if market_state:
            volatility = market_state.get("volatility", 0)
            if volatility > 0.03:
                risks.append("Elevated market volatility")
        
        return risks
    
    def _get_chart_highlights(
        self,
        patterns: Optional[List[Dict[str, Any]]],
        fractal_matches: Optional[List[Dict[str, Any]]]
    ) -> List[str]:
        """Get objects to highlight on chart."""
        highlights = []
        
        if patterns:
            for p in patterns[:3]:
                highlights.append(p.get("pattern_id", ""))
        
        if fractal_matches:
            for f in fractal_matches[:2]:
                highlights.append(f.get("match_id", ""))
        
        return [h for h in highlights if h]
    
    def explain_meta_alpha(
        self,
        active_family: str,
        family_stats: Dict[str, Dict[str, Any]],
        regime: str
    ) -> MetaAlphaExplanation:
        """Explain meta-alpha family selection."""
        
        stats = family_stats.get(active_family, {})
        
        # Build comparison
        comparison = []
        for family, fstats in family_stats.items():
            comparison.append({
                "family": family,
                "score": fstats.get("score", 0),
                "success_rate": fstats.get("success_rate", 0),
                "avg_pnl": fstats.get("avg_pnl", 0),
            })
        
        comparison.sort(key=lambda x: x["score"], reverse=True)
        
        # Generate reason
        reason = f"Selected {active_family} based on highest combined score in current {regime} regime. "
        reason += f"Success rate: {stats.get('success_rate', 0)*100:.1f}%, "
        reason += f"Avg PnL: {stats.get('avg_pnl', 0)*100:.2f}%"
        
        return MetaAlphaExplanation(
            active_alpha_family=active_family,
            reason=reason,
            success_rate=stats.get("success_rate", 0),
            avg_pnl=stats.get("avg_pnl", 0),
            regime_fit=stats.get("regime_fit", 0),
            comparison=comparison,
        )


# Singleton
_signal_explainer: Optional[SignalExplainer] = None

def get_signal_explainer() -> SignalExplainer:
    global _signal_explainer
    if _signal_explainer is None:
        _signal_explainer = SignalExplainer()
    return _signal_explainer
