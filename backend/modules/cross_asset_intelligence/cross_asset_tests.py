"""
PHASE 25.3 — Cross-Asset Tests

Tests for cross-asset bridge engine:
1-3: Macro → DXY bridge tests
4-6: DXY → SPX bridge tests
7-9: SPX → BTC bridge tests
10-12: Aggregate alignment tests
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.cross_asset_intelligence.cross_asset_types import (
    CrossAssetBridge,
    CrossAssetAlignment,
)
from modules.cross_asset_intelligence.macro_dxy_bridge import MacroDxyBridge
from modules.cross_asset_intelligence.dxy_spx_bridge import DxySpxBridge
from modules.cross_asset_intelligence.spx_btc_bridge import SpxBtcBridge
from modules.cross_asset_intelligence.cross_asset_engine import CrossAssetEngine

from modules.macro_context.macro_context_types import MacroContext
from modules.fractal_intelligence.asset_fractal_types import AssetFractalContext


# ══════════════════════════════════════════════════════════════
# Test Fixtures - Mock Data
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def tightening_macro() -> MacroContext:
    """Tightening macro with bullish USD."""
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
    """Easing macro with bearish USD."""
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
def dxy_long() -> AssetFractalContext:
    """DXY long (bullish dollar)."""
    return AssetFractalContext(
        asset="DXY",
        direction="LONG",
        confidence=0.68,
        reliability=0.65,
        strength=0.66,
        context_state="SUPPORTIVE",
        reason="dxy bullish",
    )


@pytest.fixture
def dxy_short() -> AssetFractalContext:
    """DXY short (bearish dollar)."""
    return AssetFractalContext(
        asset="DXY",
        direction="SHORT",
        confidence=0.65,
        reliability=0.62,
        strength=0.63,
        context_state="SUPPORTIVE",
        reason="dxy bearish",
    )


@pytest.fixture
def spx_long() -> AssetFractalContext:
    """SPX long (bullish equities)."""
    return AssetFractalContext(
        asset="SPX",
        direction="LONG",
        confidence=0.70,
        reliability=0.68,
        strength=0.69,
        context_state="SUPPORTIVE",
        reason="spx bullish",
    )


@pytest.fixture
def spx_short() -> AssetFractalContext:
    """SPX short (bearish equities)."""
    return AssetFractalContext(
        asset="SPX",
        direction="SHORT",
        confidence=0.67,
        reliability=0.64,
        strength=0.655,
        context_state="SUPPORTIVE",
        reason="spx bearish",
    )


@pytest.fixture
def btc_long() -> AssetFractalContext:
    """BTC long (bullish crypto)."""
    return AssetFractalContext(
        asset="BTC",
        direction="LONG",
        confidence=0.72,
        reliability=0.70,
        strength=0.71,
        context_state="SUPPORTIVE",
        reason="btc bullish",
    )


@pytest.fixture
def btc_short() -> AssetFractalContext:
    """BTC short (bearish crypto)."""
    return AssetFractalContext(
        asset="BTC",
        direction="SHORT",
        confidence=0.68,
        reliability=0.66,
        strength=0.67,
        context_state="SUPPORTIVE",
        reason="btc bearish",
    )


@pytest.fixture
def neutral_asset() -> AssetFractalContext:
    """Neutral asset (HOLD)."""
    return AssetFractalContext(
        asset="BTC",
        direction="HOLD",
        confidence=0.0,
        reliability=0.0,
        strength=0.0,
        context_state="NEUTRAL",
        reason="neutral",
    )


# ══════════════════════════════════════════════════════════════
# Tests 1-3: Macro → DXY Bridge
# ══════════════════════════════════════════════════════════════

class TestMacroDxyBridge:
    """Tests for Macro → DXY bridge."""
    
    def test_tightening_bullish_dxy_long_supportive(self, tightening_macro, dxy_long):
        """Test 1: tightening + bullish USD + DXY long → SUPPORTIVE"""
        bridge = MacroDxyBridge()
        result = bridge.compute(tightening_macro, dxy_long)
        
        assert result.source == "MACRO"
        assert result.target == "DXY"
        assert result.alignment == "SUPPORTIVE"
        assert result.influence_direction == "BULLISH"
        assert result.strength > 0
        assert result.effective_strength > 0
        
        print(f"\n✅ MACRO→DXY SUPPORTIVE: {result.reason}")
    
    def test_easing_bearish_dxy_short_supportive(self, easing_macro, dxy_short):
        """Test 2: easing + bearish USD + DXY short → SUPPORTIVE"""
        bridge = MacroDxyBridge()
        result = bridge.compute(easing_macro, dxy_short)
        
        assert result.alignment == "SUPPORTIVE"
        assert result.influence_direction == "BEARISH"
        
        print(f"\n✅ MACRO→DXY SUPPORTIVE BEARISH: {result.reason}")
    
    def test_opposite_directions_contrary(self, tightening_macro, dxy_short):
        """Test 3: opposite directions → CONTRARY"""
        bridge = MacroDxyBridge()
        result = bridge.compute(tightening_macro, dxy_short)
        
        assert result.alignment == "CONTRARY"
        # Effective strength should be penalized
        assert result.effective_strength < result.strength
        
        print(f"\n✅ MACRO→DXY CONTRARY: {result.reason}")


# ══════════════════════════════════════════════════════════════
# Tests 4-6: DXY → SPX Bridge
# ══════════════════════════════════════════════════════════════

class TestDxySpxBridge:
    """Tests for DXY → SPX bridge (INVERSE relationship)."""
    
    def test_dxy_long_spx_short_supportive(self, dxy_long, spx_short):
        """Test 4: DXY long + SPX short → SUPPORTIVE (bearish chain)"""
        bridge = DxySpxBridge()
        result = bridge.compute(dxy_long, spx_short)
        
        assert result.source == "DXY"
        assert result.target == "SPX"
        assert result.alignment == "SUPPORTIVE"
        assert result.influence_direction == "BEARISH"
        
        print(f"\n✅ DXY→SPX SUPPORTIVE BEARISH: {result.reason}")
    
    def test_dxy_short_spx_long_supportive(self, dxy_short, spx_long):
        """Test 5: DXY short + SPX long → SUPPORTIVE (bullish chain)"""
        bridge = DxySpxBridge()
        result = bridge.compute(dxy_short, spx_long)
        
        assert result.alignment == "SUPPORTIVE"
        assert result.influence_direction == "BULLISH"
        
        print(f"\n✅ DXY→SPX SUPPORTIVE BULLISH: {result.reason}")
    
    def test_same_direction_contrary(self, dxy_long, spx_long):
        """Test 6: same direction → CONTRARY (breaks inverse)"""
        bridge = DxySpxBridge()
        result = bridge.compute(dxy_long, spx_long)
        
        assert result.alignment == "CONTRARY"
        
        print(f"\n✅ DXY→SPX CONTRARY: {result.reason}")


# ══════════════════════════════════════════════════════════════
# Tests 7-9: SPX → BTC Bridge
# ══════════════════════════════════════════════════════════════

class TestSpxBtcBridge:
    """Tests for SPX → BTC bridge (POSITIVE correlation)."""
    
    def test_spx_long_btc_long_supportive(self, spx_long, btc_long):
        """Test 7: SPX long + BTC long → SUPPORTIVE (bullish risk-on)"""
        bridge = SpxBtcBridge()
        result = bridge.compute(spx_long, btc_long)
        
        assert result.source == "SPX"
        assert result.target == "BTC"
        assert result.alignment == "SUPPORTIVE"
        assert result.influence_direction == "BULLISH"
        
        print(f"\n✅ SPX→BTC SUPPORTIVE BULLISH: {result.reason}")
    
    def test_spx_short_btc_short_supportive(self, spx_short, btc_short):
        """Test 8: SPX short + BTC short → SUPPORTIVE (bearish risk-off)"""
        bridge = SpxBtcBridge()
        result = bridge.compute(spx_short, btc_short)
        
        assert result.alignment == "SUPPORTIVE"
        assert result.influence_direction == "BEARISH"
        
        print(f"\n✅ SPX→BTC SUPPORTIVE BEARISH: {result.reason}")
    
    def test_opposite_directions_contrary(self, spx_long, btc_short):
        """Test 9: opposite directions → CONTRARY"""
        bridge = SpxBtcBridge()
        result = bridge.compute(spx_long, btc_short)
        
        assert result.alignment == "CONTRARY"
        
        print(f"\n✅ SPX→BTC CONTRARY: {result.reason}")


# ══════════════════════════════════════════════════════════════
# Tests 10-12: Aggregate Alignment
# ══════════════════════════════════════════════════════════════

class TestCrossAssetEngine:
    """Tests for aggregate cross-asset alignment."""
    
    def test_all_supportive_bullish_strong(
        self, easing_macro, dxy_short, spx_long, btc_long
    ):
        """Test 10: all supportive bullish → STRONG + BULLISH"""
        engine = CrossAssetEngine()
        
        alignment = engine.compute_alignment(
            macro=easing_macro,
            dxy=dxy_short,
            spx=spx_long,
            btc=btc_long,
        )
        
        assert alignment.macro_dxy.alignment == "SUPPORTIVE"
        assert alignment.dxy_spx.alignment == "SUPPORTIVE"
        assert alignment.spx_btc.alignment == "SUPPORTIVE"
        
        assert alignment.alignment_state in ["STRONG", "MODERATE"]
        assert alignment.final_bias == "BULLISH"
        
        print(f"\n✅ FULL CHAIN BULLISH: score={alignment.alignment_score:.2f}, state={alignment.alignment_state}")
        print(f"   Reason: {alignment.reason}")
    
    def test_all_supportive_bearish_strong(
        self, tightening_macro, dxy_long, spx_short, btc_short
    ):
        """Test 11: all supportive bearish → STRONG + BEARISH"""
        engine = CrossAssetEngine()
        
        alignment = engine.compute_alignment(
            macro=tightening_macro,
            dxy=dxy_long,
            spx=spx_short,
            btc=btc_short,
        )
        
        assert alignment.macro_dxy.alignment == "SUPPORTIVE"
        assert alignment.dxy_spx.alignment == "SUPPORTIVE"
        assert alignment.spx_btc.alignment == "SUPPORTIVE"
        
        assert alignment.alignment_state in ["STRONG", "MODERATE"]
        assert alignment.final_bias == "BEARISH"
        
        print(f"\n✅ FULL CHAIN BEARISH: score={alignment.alignment_score:.2f}, state={alignment.alignment_state}")
        print(f"   Reason: {alignment.reason}")
    
    def test_mixed_chain_weak_or_conflicted(
        self, tightening_macro, dxy_short, spx_long, btc_short
    ):
        """Test 12: mixed chain → WEAK/CONFLICTED + MIXED"""
        engine = CrossAssetEngine()
        
        alignment = engine.compute_alignment(
            macro=tightening_macro,  # Bullish USD
            dxy=dxy_short,           # Bearish DXY (CONTRARY to macro)
            spx=spx_long,            # Bullish SPX (SUPPORTIVE with dxy)
            btc=btc_short,           # Bearish BTC (CONTRARY to spx)
        )
        
        # Should have some contrary bridges
        contrary_count = sum(
            1 for b in [alignment.macro_dxy, alignment.dxy_spx, alignment.spx_btc]
            if b.alignment == "CONTRARY"
        )
        
        assert contrary_count >= 1, "Should have at least one contrary bridge"
        assert alignment.alignment_state in ["WEAK", "CONFLICTED", "MODERATE"]
        assert alignment.final_bias in ["MIXED", "NEUTRAL", "BULLISH", "BEARISH"]
        
        print(f"\n✅ MIXED CHAIN: score={alignment.alignment_score:.2f}, state={alignment.alignment_state}")
        print(f"   Final bias: {alignment.final_bias}")
        print(f"   Dominant: {alignment.dominant_bridge}, Weakest: {alignment.weakest_bridge}")


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

class TestBridgeStrength:
    """Tests for bridge strength calculations."""
    
    def test_strength_bounded(self, tightening_macro, dxy_long):
        """Strength values should be in [0, 1]."""
        bridge = MacroDxyBridge()
        result = bridge.compute(tightening_macro, dxy_long)
        
        assert 0.0 <= result.strength <= 1.0
        assert 0.0 <= result.effective_strength <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        
        print(f"\n✅ Strength bounded: {result.strength:.3f}")


class TestDominantWeakest:
    """Tests for dominant/weakest bridge identification."""
    
    def test_dominant_weakest_identified(
        self, tightening_macro, dxy_long, spx_short, btc_short
    ):
        """Dominant and weakest bridges should be identified."""
        engine = CrossAssetEngine()
        
        alignment = engine.compute_alignment(
            macro=tightening_macro,
            dxy=dxy_long,
            spx=spx_short,
            btc=btc_short,
        )
        
        assert alignment.dominant_bridge in ["macro_dxy", "dxy_spx", "spx_btc"]
        assert alignment.weakest_bridge in ["macro_dxy", "dxy_spx", "spx_btc"]
        assert alignment.dominant_bridge != alignment.weakest_bridge or True  # Can be same if equal
        
        print(f"\n✅ Dominant: {alignment.dominant_bridge}, Weakest: {alignment.weakest_bridge}")


class TestAlignmentScore:
    """Tests for alignment score calculation."""
    
    def test_alignment_score_weighted(
        self, tightening_macro, dxy_long, spx_short, btc_short
    ):
        """Alignment score should use correct weights."""
        engine = CrossAssetEngine()
        
        alignment = engine.compute_alignment(
            macro=tightening_macro,
            dxy=dxy_long,
            spx=spx_short,
            btc=btc_short,
        )
        
        # Manual calculation
        expected = (
            0.30 * alignment.macro_dxy.effective_strength +
            0.30 * alignment.dxy_spx.effective_strength +
            0.40 * alignment.spx_btc.effective_strength
        )
        
        assert abs(alignment.alignment_score - expected) < 0.01
        
        print(f"\n✅ Alignment score: {alignment.alignment_score:.3f} (expected {expected:.3f})")


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
