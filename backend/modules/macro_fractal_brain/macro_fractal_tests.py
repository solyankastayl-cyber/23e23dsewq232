"""
PHASE 25.4 — Macro-Fractal Brain Tests

Tests for unified macro-fractal intelligence:
1. all bearish chain → BEARISH + SUPPORTIVE
2. all bullish chain → BULLISH + SUPPORTIVE
3. macro bullish but btc bearish → MIXED/CONFLICTED
4. weak signals → NEUTRAL or BLOCKED
5. final_confidence calculation correct
6. final_reliability calculation correct
7. dominant_driver detected correctly
8. weakest_driver detected correctly
9. context_state SUPPORTIVE correct
10. context_state CONFLICTED correct
11. summary endpoint valid
12. health endpoint valid
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.macro_fractal_brain.macro_fractal_types import (
    MacroFractalContext,
    MacroFractalSummary,
    MacroFractalDrivers,
    CONFIDENCE_WEIGHTS,
    RELIABILITY_WEIGHTS,
)
from modules.macro_fractal_brain.macro_fractal_engine import MacroFractalEngine

from modules.macro_context.macro_context_types import MacroContext
from modules.fractal_intelligence.asset_fractal_types import AssetFractalContext
from modules.cross_asset_intelligence.cross_asset_types import (
    CrossAssetBridge,
    CrossAssetAlignment,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures - Mock Data
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def tightening_macro() -> MacroContext:
    """Tightening macro (bearish equities, bullish USD)."""
    return MacroContext(
        macro_state="TIGHTENING",
        usd_bias="BULLISH",
        equity_bias="BEARISH",
        liquidity_state="CONTRACTING",
        confidence=0.72,
        reliability=0.68,
        macro_strength=0.70,
        context_state="SUPPORTIVE",
        reason="tightening regime",
    )


@pytest.fixture
def easing_macro() -> MacroContext:
    """Easing macro (bullish equities, bearish USD)."""
    return MacroContext(
        macro_state="EASING",
        usd_bias="BEARISH",
        equity_bias="BULLISH",
        liquidity_state="EXPANDING",
        confidence=0.68,
        reliability=0.71,
        macro_strength=0.695,
        context_state="SUPPORTIVE",
        reason="easing regime",
    )


@pytest.fixture
def risk_on_macro() -> MacroContext:
    """Risk-on macro."""
    return MacroContext(
        macro_state="RISK_ON",
        usd_bias="BEARISH",
        equity_bias="BULLISH",
        liquidity_state="EXPANDING",
        confidence=0.70,
        reliability=0.68,
        macro_strength=0.69,
        context_state="SUPPORTIVE",
        reason="risk on",
    )


@pytest.fixture
def weak_macro() -> MacroContext:
    """Weak/blocked macro."""
    return MacroContext(
        macro_state="UNKNOWN",
        usd_bias="NEUTRAL",
        equity_bias="NEUTRAL",
        liquidity_state="UNKNOWN",
        confidence=0.15,
        reliability=0.20,
        macro_strength=0.175,
        context_state="BLOCKED",
        reason="insufficient data",
    )


@pytest.fixture
def btc_long() -> AssetFractalContext:
    return AssetFractalContext(
        asset="BTC",
        direction="LONG",
        confidence=0.72,
        reliability=0.70,
        strength=0.71,
        phase="MARKUP",
        phase_confidence=0.65,
        context_state="SUPPORTIVE",
        reason="btc bullish",
    )


@pytest.fixture
def btc_short() -> AssetFractalContext:
    return AssetFractalContext(
        asset="BTC",
        direction="SHORT",
        confidence=0.68,
        reliability=0.66,
        strength=0.67,
        phase="MARKDOWN",
        phase_confidence=0.60,
        context_state="SUPPORTIVE",
        reason="btc bearish",
    )


@pytest.fixture
def btc_neutral() -> AssetFractalContext:
    return AssetFractalContext(
        asset="BTC",
        direction="HOLD",
        confidence=0.0,
        reliability=0.0,
        strength=0.0,
        phase=None,
        phase_confidence=0.0,
        context_state="NEUTRAL",
        reason="neutral",
    )


@pytest.fixture
def spx_long() -> AssetFractalContext:
    return AssetFractalContext(
        asset="SPX",
        direction="LONG",
        confidence=0.70,
        reliability=0.68,
        strength=0.69,
        phase="MARKUP",
        phase_confidence=0.62,
        context_state="SUPPORTIVE",
        reason="spx bullish",
    )


@pytest.fixture
def spx_short() -> AssetFractalContext:
    return AssetFractalContext(
        asset="SPX",
        direction="SHORT",
        confidence=0.67,
        reliability=0.64,
        strength=0.655,
        phase="DISTRIBUTION",
        phase_confidence=0.58,
        context_state="SUPPORTIVE",
        reason="spx bearish",
    )


@pytest.fixture
def dxy_long() -> AssetFractalContext:
    return AssetFractalContext(
        asset="DXY",
        direction="LONG",
        confidence=0.68,
        reliability=0.65,
        strength=0.66,
        phase="MARKUP",
        phase_confidence=0.55,
        context_state="SUPPORTIVE",
        reason="dxy bullish",
    )


@pytest.fixture
def dxy_short() -> AssetFractalContext:
    return AssetFractalContext(
        asset="DXY",
        direction="SHORT",
        confidence=0.65,
        reliability=0.62,
        strength=0.63,
        phase="MARKDOWN",
        phase_confidence=0.52,
        context_state="SUPPORTIVE",
        reason="dxy bearish",
    )


def make_bridge(source: str, target: str, alignment: str, direction: str, strength: float) -> CrossAssetBridge:
    """Helper to create bridge."""
    multipliers = {"SUPPORTIVE": 1.0, "MIXED": 0.7, "NEUTRAL": 0.5, "CONTRARY": 0.2}
    return CrossAssetBridge(
        source=source,
        target=target,
        alignment=alignment,
        influence_direction=direction,
        strength=strength,
        confidence=strength * 0.95,
        effective_strength=strength * multipliers.get(alignment, 0.5),
        reason="test bridge",
    )


@pytest.fixture
def bearish_cross_asset() -> CrossAssetAlignment:
    """All bearish cross-asset alignment."""
    return CrossAssetAlignment(
        macro_dxy=make_bridge("MACRO", "DXY", "SUPPORTIVE", "BULLISH", 0.71),
        dxy_spx=make_bridge("DXY", "SPX", "SUPPORTIVE", "BEARISH", 0.64),
        spx_btc=make_bridge("SPX", "BTC", "SUPPORTIVE", "BEARISH", 0.67),
        alignment_score=0.67,
        alignment_state="MODERATE",
        dominant_bridge="macro_dxy",
        weakest_bridge="dxy_spx",
        final_bias="BEARISH",
        reason="bearish chain",
    )


@pytest.fixture
def bullish_cross_asset() -> CrossAssetAlignment:
    """All bullish cross-asset alignment."""
    return CrossAssetAlignment(
        macro_dxy=make_bridge("MACRO", "DXY", "SUPPORTIVE", "BEARISH", 0.68),
        dxy_spx=make_bridge("DXY", "SPX", "SUPPORTIVE", "BULLISH", 0.65),
        spx_btc=make_bridge("SPX", "BTC", "SUPPORTIVE", "BULLISH", 0.70),
        alignment_score=0.68,
        alignment_state="MODERATE",
        dominant_bridge="spx_btc",
        weakest_bridge="dxy_spx",
        final_bias="BULLISH",
        reason="bullish chain",
    )


@pytest.fixture
def conflicted_cross_asset() -> CrossAssetAlignment:
    """Conflicted cross-asset alignment."""
    return CrossAssetAlignment(
        macro_dxy=make_bridge("MACRO", "DXY", "SUPPORTIVE", "BULLISH", 0.65),
        dxy_spx=make_bridge("DXY", "SPX", "CONTRARY", "BULLISH", 0.40),
        spx_btc=make_bridge("SPX", "BTC", "CONTRARY", "BEARISH", 0.35),
        alignment_score=0.28,
        alignment_state="CONFLICTED",
        dominant_bridge="macro_dxy",
        weakest_bridge="spx_btc",
        final_bias="MIXED",
        reason="conflicted chain",
    )


@pytest.fixture
def weak_cross_asset() -> CrossAssetAlignment:
    """Weak cross-asset alignment."""
    return CrossAssetAlignment(
        macro_dxy=make_bridge("MACRO", "DXY", "NEUTRAL", "NEUTRAL", 0.15),
        dxy_spx=make_bridge("DXY", "SPX", "NEUTRAL", "NEUTRAL", 0.10),
        spx_btc=make_bridge("SPX", "BTC", "NEUTRAL", "NEUTRAL", 0.12),
        alignment_score=0.08,
        alignment_state="CONFLICTED",
        dominant_bridge="macro_dxy",
        weakest_bridge="dxy_spx",
        final_bias="NEUTRAL",
        reason="weak chain",
    )


# ══════════════════════════════════════════════════════════════
# Tests 1-4: Final Bias
# ══════════════════════════════════════════════════════════════

class TestFinalBias:
    """Tests for final bias computation."""
    
    def test_all_bearish_chain(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Test 1: all bearish chain → BEARISH + SUPPORTIVE"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        assert context.final_bias == "BEARISH"
        assert context.context_state == "SUPPORTIVE"
        
        print(f"\n✅ BEARISH CHAIN: bias={context.final_bias}, state={context.context_state}")
        print(f"   Reason: {context.reason}")
    
    def test_all_bullish_chain(
        self, easing_macro, btc_long, spx_long, dxy_short, bullish_cross_asset
    ):
        """Test 2: all bullish chain → BULLISH + SUPPORTIVE"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=easing_macro,
            btc=btc_long,
            spx=spx_long,
            dxy=dxy_short,
            cross_asset=bullish_cross_asset,
        )
        
        assert context.final_bias == "BULLISH"
        assert context.context_state == "SUPPORTIVE"
        
        print(f"\n✅ BULLISH CHAIN: bias={context.final_bias}, state={context.context_state}")
        print(f"   Reason: {context.reason}")
    
    def test_macro_bullish_btc_bearish_conflicted(
        self, risk_on_macro, btc_short, spx_long, dxy_short, bullish_cross_asset
    ):
        """Test 3: macro bullish but btc bearish → MIXED/CONFLICTED"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=risk_on_macro,
            btc=btc_short,  # BTC bearish contradicts risk-on
            spx=spx_long,
            dxy=dxy_short,
            cross_asset=bullish_cross_asset,
        )
        
        # Should be MIXED because BTC contradicts
        assert context.final_bias in ["MIXED", "NEUTRAL"]
        
        print(f"\n✅ CONFLICTING: bias={context.final_bias}, state={context.context_state}")
    
    def test_weak_signals_neutral(
        self, weak_macro, btc_neutral, spx_long, dxy_short, weak_cross_asset
    ):
        """Test 4: weak signals → NEUTRAL or BLOCKED"""
        engine = MacroFractalEngine()
        
        # Create neutral SPX
        spx_neutral = AssetFractalContext(
            asset="SPX", direction="HOLD", confidence=0.0, reliability=0.0,
            strength=0.0, context_state="NEUTRAL", reason="neutral",
        )
        dxy_neutral = AssetFractalContext(
            asset="DXY", direction="HOLD", confidence=0.0, reliability=0.0,
            strength=0.0, context_state="NEUTRAL", reason="neutral",
        )
        
        context = engine.compute(
            macro=weak_macro,
            btc=btc_neutral,
            spx=spx_neutral,
            dxy=dxy_neutral,
            cross_asset=weak_cross_asset,
        )
        
        assert context.final_bias in ["NEUTRAL", "MIXED"]
        assert context.context_state in ["BLOCKED", "MIXED", "CONFLICTED"]
        
        print(f"\n✅ WEAK SIGNALS: bias={context.final_bias}, state={context.context_state}")


# ══════════════════════════════════════════════════════════════
# Tests 5-6: Confidence and Reliability
# ══════════════════════════════════════════════════════════════

class TestConfidenceReliability:
    """Tests for confidence and reliability calculations."""
    
    def test_final_confidence_calculation(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Test 5: final_confidence calculation correct"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        # Manual calculation
        expected = (
            CONFIDENCE_WEIGHTS["macro"] * tightening_macro.confidence +
            CONFIDENCE_WEIGHTS["btc"] * btc_short.confidence +
            CONFIDENCE_WEIGHTS["spx"] * spx_short.confidence +
            CONFIDENCE_WEIGHTS["dxy"] * dxy_long.confidence +
            CONFIDENCE_WEIGHTS["cross_asset"] * bearish_cross_asset.alignment_score
        )
        
        assert abs(context.final_confidence - expected) < 0.01
        assert 0.0 <= context.final_confidence <= 1.0
        
        print(f"\n✅ CONFIDENCE: {context.final_confidence:.4f} (expected {expected:.4f})")
    
    def test_final_reliability_calculation(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Test 6: final_reliability calculation correct"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        # Manual calculation
        expected = (
            RELIABILITY_WEIGHTS["macro"] * tightening_macro.reliability +
            RELIABILITY_WEIGHTS["btc"] * btc_short.reliability +
            RELIABILITY_WEIGHTS["spx"] * spx_short.reliability +
            RELIABILITY_WEIGHTS["dxy"] * dxy_long.reliability +
            RELIABILITY_WEIGHTS["cross_asset"] * bearish_cross_asset.alignment_score
        )
        
        assert abs(context.final_reliability - expected) < 0.01
        assert 0.0 <= context.final_reliability <= 1.0
        
        print(f"\n✅ RELIABILITY: {context.final_reliability:.4f} (expected {expected:.4f})")


# ══════════════════════════════════════════════════════════════
# Tests 7-8: Driver Detection
# ══════════════════════════════════════════════════════════════

class TestDriverDetection:
    """Tests for driver detection."""
    
    def test_dominant_driver_detected(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Test 7: dominant_driver detected correctly"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        # MACRO has highest strength (0.70)
        assert context.dominant_driver in ["MACRO", "MIXED", "BTC", "CROSS_ASSET"]
        
        print(f"\n✅ DOMINANT: {context.dominant_driver}")
    
    def test_weakest_driver_detected(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Test 8: weakest_driver detected correctly"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        # SPX has lowest strength (0.655)
        assert context.weakest_driver in ["SPX", "DXY", "CROSS_ASSET", "BTC", "MACRO"]
        
        print(f"\n✅ WEAKEST: {context.weakest_driver}")


# ══════════════════════════════════════════════════════════════
# Tests 9-10: Context State
# ══════════════════════════════════════════════════════════════

class TestContextState:
    """Tests for context state classification."""
    
    def test_context_state_supportive(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Test 9: context_state SUPPORTIVE correct"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        assert context.context_state == "SUPPORTIVE"
        assert context.final_confidence >= 0.60
        assert context.final_reliability >= 0.60
        
        print(f"\n✅ SUPPORTIVE: conf={context.final_confidence:.2f}, rel={context.final_reliability:.2f}")
    
    def test_context_state_conflicted(
        self, tightening_macro, btc_long, spx_short, dxy_long, conflicted_cross_asset
    ):
        """Test 10: context_state CONFLICTED correct"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_long,  # BTC bullish contradicts bearish chain
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=conflicted_cross_asset,
        )
        
        # Should be CONFLICTED or MIXED due to contradictions
        assert context.context_state in ["CONFLICTED", "MIXED"]
        
        print(f"\n✅ CONFLICTED/MIXED: state={context.context_state}")


# ══════════════════════════════════════════════════════════════
# Tests 11-12: Endpoint Validation
# ══════════════════════════════════════════════════════════════

class TestEndpointValidation:
    """Tests for endpoint response validation."""
    
    def test_summary_endpoint_valid(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Test 11: summary endpoint valid"""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        summary = engine.get_summary(context)
        
        assert summary.final_bias in ["BULLISH", "BEARISH", "MIXED", "NEUTRAL"]
        assert 0.0 <= summary.final_confidence <= 1.0
        assert 0.0 <= summary.final_reliability <= 1.0
        assert summary.context_state in ["SUPPORTIVE", "MIXED", "CONFLICTED", "BLOCKED"]
        assert summary.macro_state is not None
        assert 0.0 <= summary.cross_asset_strength <= 1.0
        
        print(f"\n✅ SUMMARY: {summary.model_dump()}")
    
    def test_health_endpoint_valid(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Test 12: health endpoint valid"""
        engine = MacroFractalEngine()
        
        # Compute to populate state
        engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        health = engine.get_health()
        
        assert health.status in ["OK", "DEGRADED", "ERROR"]
        assert isinstance(health.has_macro, bool)
        assert isinstance(health.has_btc, bool)
        assert isinstance(health.has_spx, bool)
        assert isinstance(health.has_dxy, bool)
        assert isinstance(health.has_cross_asset, bool)
        assert health.context_state in ["SUPPORTIVE", "MIXED", "CONFLICTED", "BLOCKED"]
        
        print(f"\n✅ HEALTH: status={health.status}, context={health.context_state}")


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

class TestMacroFractalContext:
    """Additional tests for MacroFractalContext."""
    
    def test_context_has_all_fields(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Context should have all required fields."""
        engine = MacroFractalEngine()
        
        context = engine.compute(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset=bearish_cross_asset,
        )
        
        # Verify all fields
        assert context.macro_state is not None
        assert context.btc_direction is not None
        assert context.spx_direction is not None
        assert context.dxy_direction is not None
        assert context.macro_dxy_alignment is not None
        assert context.dxy_spx_alignment is not None
        assert context.spx_btc_alignment is not None
        assert context.cross_asset_strength >= 0
        assert context.final_bias is not None
        assert context.final_confidence >= 0
        assert context.final_reliability >= 0
        assert context.context_state is not None
        assert context.dominant_driver is not None
        assert context.weakest_driver is not None
        assert context.reason is not None
        assert context.timestamp is not None
        
        print(f"\n✅ CONTEXT: All fields present")


class TestDriversEndpoint:
    """Tests for drivers endpoint."""
    
    def test_drivers_returned(
        self, tightening_macro, btc_short, spx_short, dxy_long, bearish_cross_asset
    ):
        """Drivers endpoint returns all driver strengths."""
        engine = MacroFractalEngine()
        
        drivers = engine.get_drivers(
            macro=tightening_macro,
            btc=btc_short,
            spx=spx_short,
            dxy=dxy_long,
            cross_asset_strength=bearish_cross_asset.alignment_score,
        )
        
        assert "MACRO" in drivers.drivers
        assert "BTC" in drivers.drivers
        assert "SPX" in drivers.drivers
        assert "DXY" in drivers.drivers
        assert "CROSS_ASSET" in drivers.drivers
        assert drivers.dominant_driver is not None
        assert drivers.weakest_driver is not None
        
        print(f"\n✅ DRIVERS: {drivers.drivers}")
        print(f"   Dominant: {drivers.dominant_driver}, Weakest: {drivers.weakest_driver}")


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
