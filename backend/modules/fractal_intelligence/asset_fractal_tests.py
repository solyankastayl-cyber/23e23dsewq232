"""
PHASE 25.2 — Asset Fractal Tests

Tests for unified asset fractal contracts:
1. BTC adapter returns correct contract
2. SPX adapter returns correct contract
3. DXY adapter returns correct contract
4. Direction mapping works
5. Phase mapping works
6. Strength in range
7. Confidence bounds
8. Fallback works
9. Endpoint schema correct
10. Contexts don't conflict
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.fractal_intelligence.asset_fractal_types import (
    AssetFractalContext,
    MultiAssetFractalContext,
)
from modules.fractal_intelligence.btc_fractal_adapter import BTCFractalAdapter
from modules.fractal_intelligence.spx_fractal_adapter import SPXFractalAdapter
from modules.fractal_intelligence.dxy_fractal_adapter import DXYFractalAdapter
from modules.fractal_intelligence.asset_fractal_service import AssetFractalService


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def btc_adapter():
    return BTCFractalAdapter()


@pytest.fixture
def spx_adapter():
    return SPXFractalAdapter()


@pytest.fixture
def dxy_adapter():
    return DXYFractalAdapter()


@pytest.fixture
def service():
    return AssetFractalService()


# ══════════════════════════════════════════════════════════════
# Test 1-3: Adapter Returns Correct Contract
# ══════════════════════════════════════════════════════════════

class TestAdapterContracts:
    """Tests for adapter contract compliance."""
    
    def test_btc_adapter_returns_contract(self, btc_adapter):
        """Test 1: BTC adapter returns correct contract"""
        ctx = btc_adapter.build_context_sync()
        
        assert isinstance(ctx, AssetFractalContext)
        assert ctx.asset == "BTC"
        assert ctx.direction in ["LONG", "SHORT", "HOLD"]
        assert 0.0 <= ctx.confidence <= 1.0
        assert 0.0 <= ctx.reliability <= 1.0
        assert 0.0 <= ctx.strength <= 1.0
        assert ctx.context_state in ["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]
        assert ctx.reason is not None and len(ctx.reason) > 0
        
        print(f"\n✅ BTC: dir={ctx.direction}, conf={ctx.confidence}, state={ctx.context_state}")
    
    def test_spx_adapter_returns_contract(self, spx_adapter):
        """Test 2: SPX adapter returns correct contract"""
        ctx = spx_adapter.build_context_sync()
        
        assert isinstance(ctx, AssetFractalContext)
        assert ctx.asset == "SPX"
        assert ctx.direction in ["LONG", "SHORT", "HOLD"]
        assert 0.0 <= ctx.confidence <= 1.0
        assert 0.0 <= ctx.reliability <= 1.0
        assert 0.0 <= ctx.strength <= 1.0
        assert ctx.context_state in ["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]
        assert ctx.reason is not None
        
        print(f"\n✅ SPX: dir={ctx.direction}, conf={ctx.confidence}, state={ctx.context_state}")
    
    def test_dxy_adapter_returns_contract(self, dxy_adapter):
        """Test 3: DXY adapter returns correct contract"""
        ctx = dxy_adapter.build_context_sync()
        
        assert isinstance(ctx, AssetFractalContext)
        assert ctx.asset == "DXY"
        assert ctx.direction in ["LONG", "SHORT", "HOLD"]
        assert 0.0 <= ctx.confidence <= 1.0
        assert 0.0 <= ctx.reliability <= 1.0
        assert 0.0 <= ctx.strength <= 1.0
        assert ctx.context_state in ["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]
        assert ctx.reason is not None
        
        print(f"\n✅ DXY: dir={ctx.direction}, conf={ctx.confidence}, state={ctx.context_state}")


# ══════════════════════════════════════════════════════════════
# Test 4-5: Mapping Functions
# ══════════════════════════════════════════════════════════════

class TestMappingFunctions:
    """Tests for direction and phase mapping."""
    
    def test_direction_mapping(self, btc_adapter, spx_adapter, dxy_adapter):
        """Test 4: Direction mapping works for all adapters"""
        # BTC
        assert btc_adapter._map_direction("LONG") == "LONG"
        assert btc_adapter._map_direction("SHORT") == "SHORT"
        assert btc_adapter._map_direction("HOLD") == "HOLD"
        assert btc_adapter._map_direction("INVALID") == "HOLD"
        
        # SPX
        assert spx_adapter._map_direction("BUY") == "LONG"
        assert spx_adapter._map_direction("SELL") == "SHORT"
        assert spx_adapter._map_direction("HOLD") == "HOLD"
        
        # DXY
        assert dxy_adapter._map_direction("BULLISH") == "LONG"
        assert dxy_adapter._map_direction("BEARISH") == "SHORT"
        assert dxy_adapter._map_direction("NEUTRAL") == "HOLD"
        
        print("\n✅ Direction mapping works for all adapters")
    
    def test_phase_mapping(self, btc_adapter, spx_adapter, dxy_adapter):
        """Test 5: Phase mapping works for all adapters"""
        # BTC
        assert btc_adapter._map_phase("MARKUP") == "MARKUP"
        assert btc_adapter._map_phase("MARKDOWN") == "MARKDOWN"
        assert btc_adapter._map_phase("ACCUMULATION") == "ACCUMULATION"
        assert btc_adapter._map_phase(None) is None
        
        # SPX
        assert spx_adapter._map_phase("DISTRIBUTION") == "DISTRIBUTION"
        assert spx_adapter._map_phase("invalid") == "UNKNOWN"
        
        # DXY
        assert dxy_adapter._map_phase("RECOVERY") == "RECOVERY"
        assert dxy_adapter._map_phase("CAPITULATION") == "CAPITULATION"
        
        print("\n✅ Phase mapping works for all adapters")


# ══════════════════════════════════════════════════════════════
# Test 6-7: Value Bounds
# ══════════════════════════════════════════════════════════════

class TestValueBounds:
    """Tests for value bounds."""
    
    def test_strength_in_range(self, service):
        """Test 6: Strength values are in valid range"""
        contexts = service.get_all_contexts_sync()
        
        for ctx in [contexts.btc, contexts.spx, contexts.dxy]:
            assert 0.0 <= ctx.strength <= 1.0, f"{ctx.asset} strength out of bounds"
        
        print("\n✅ All strength values in [0, 1]")
    
    def test_confidence_bounds(self, service):
        """Test 7: Confidence values are bounded"""
        contexts = service.get_all_contexts_sync()
        
        for ctx in [contexts.btc, contexts.spx, contexts.dxy]:
            assert 0.0 <= ctx.confidence <= 1.0, f"{ctx.asset} confidence out of bounds"
            assert 0.0 <= ctx.reliability <= 1.0, f"{ctx.asset} reliability out of bounds"
            assert 0.0 <= ctx.phase_confidence <= 1.0, f"{ctx.asset} phase_confidence out of bounds"
        
        print("\n✅ All confidence values bounded [0, 1]")


# ══════════════════════════════════════════════════════════════
# Test 8: Fallback
# ══════════════════════════════════════════════════════════════

class TestFallback:
    """Tests for fallback behavior."""
    
    def test_fallback_works(self, dxy_adapter):
        """Test 8: Fallback works when service unavailable"""
        # DXY fallback from macro
        ctx = dxy_adapter.build_from_macro_context(
            macro_usd_bias="BULLISH",
            macro_confidence=0.7
        )
        
        assert ctx.asset == "DXY"
        assert ctx.direction == "LONG"  # BULLISH USD = LONG DXY
        assert ctx.confidence > 0
        assert "macro" in ctx.reason.lower()
        
        print(f"\n✅ DXY fallback: dir={ctx.direction}, reason={ctx.reason}")
    
    def test_blocked_fallback(self, spx_adapter):
        """Test: SPX returns neutral when service unavailable"""
        ctx = spx_adapter.build_context_sync()
        
        # Sync should return neutral fallback
        assert ctx.asset == "SPX"
        assert ctx.direction == "HOLD"
        assert ctx.context_state in ["NEUTRAL", "BLOCKED"]
        
        print(f"\n✅ SPX fallback: state={ctx.context_state}")


# ══════════════════════════════════════════════════════════════
# Test 9: Endpoint Schema
# ══════════════════════════════════════════════════════════════

class TestEndpointSchema:
    """Tests for endpoint schema validation."""
    
    def test_endpoint_schema_correct(self, service):
        """Test 9: Endpoint schema is correct"""
        contexts = service.get_all_contexts_sync()
        
        # Verify MultiAssetFractalContext structure
        assert isinstance(contexts, MultiAssetFractalContext)
        assert contexts.btc is not None
        assert contexts.spx is not None
        assert contexts.dxy is not None
        assert contexts.timestamp is not None
        
        # Verify can serialize to dict
        btc_dict = contexts.btc.model_dump()
        assert "asset" in btc_dict
        assert "direction" in btc_dict
        assert "confidence" in btc_dict
        assert "reliability" in btc_dict
        assert "strength" in btc_dict
        assert "context_state" in btc_dict
        assert "reason" in btc_dict
        
        print("\n✅ Endpoint schema is correct")


# ══════════════════════════════════════════════════════════════
# Test 10: No Conflicts
# ══════════════════════════════════════════════════════════════

class TestNoConflicts:
    """Tests for context consistency."""
    
    def test_contexts_dont_conflict(self, service):
        """Test 10: Contexts don't have conflicting states"""
        contexts = service.get_all_contexts_sync()
        
        # Each asset should have its own identity
        assert contexts.btc.asset == "BTC"
        assert contexts.spx.asset == "SPX"
        assert contexts.dxy.asset == "DXY"
        
        # All timestamps should be recent (within last minute)
        now = datetime.utcnow()
        for ctx in [contexts.btc, contexts.spx, contexts.dxy]:
            delta = (now - ctx.timestamp).total_seconds()
            assert delta < 60, f"{ctx.asset} timestamp too old: {delta}s"
        
        # Context states should be valid
        valid_states = {"SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"}
        for ctx in [contexts.btc, contexts.spx, contexts.dxy]:
            assert ctx.context_state in valid_states, f"{ctx.asset} has invalid state"
        
        print("\n✅ No conflicts in contexts")


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

class TestHealthStatus:
    """Tests for health status."""
    
    def test_health_status(self, service):
        """Health status returns valid response"""
        # First get contexts to populate state
        service.get_all_contexts_sync()
        
        health = service.get_health()
        
        assert health.status in ["OK", "DEGRADED", "ERROR"]
        assert isinstance(health.btc_available, bool)
        assert isinstance(health.spx_available, bool)
        assert isinstance(health.dxy_available, bool)
        
        print(f"\n✅ Health: status={health.status}, btc={health.btc_available}, spx={health.spx_available}, dxy={health.dxy_available}")


class TestMultiAssetContext:
    """Tests for multi-asset context."""
    
    def test_multi_asset_context_structure(self, service):
        """Multi-asset context has correct structure"""
        contexts = service.get_all_contexts_sync()
        
        # Should have all three assets
        assert hasattr(contexts, 'btc')
        assert hasattr(contexts, 'spx')
        assert hasattr(contexts, 'dxy')
        assert hasattr(contexts, 'timestamp')
        
        # Each should be AssetFractalContext
        assert isinstance(contexts.btc, AssetFractalContext)
        assert isinstance(contexts.spx, AssetFractalContext)
        assert isinstance(contexts.dxy, AssetFractalContext)
        
        print("\n✅ Multi-asset context structure valid")


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
