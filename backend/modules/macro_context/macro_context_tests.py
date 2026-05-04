"""
PHASE 25.1 — Macro Context Tests

Minimum 12 tests as specified:
1. risk-on macro → RISK_ON
2. tightening macro → TIGHTENING
3. stagflation case → STAGFLATION
4. usd bias classified correctly
5. equity bias classified correctly
6. liquidity state classified correctly
7. macro_strength computed correctly
8. SUPPORTIVE state classified correctly
9. CONFLICTED state classified correctly
10. BLOCKED on missing inputs
11. summary endpoint valid
12. health endpoint valid
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.macro_context.macro_context_types import MacroInput, MacroContext
from modules.macro_context.macro_context_engine import MacroContextEngine
from modules.macro_context.macro_context_adapter import MacroContextAdapter


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create fresh engine instance."""
    return MacroContextEngine()


@pytest.fixture
def adapter():
    """Create fresh adapter instance."""
    return MacroContextAdapter()


# ══════════════════════════════════════════════════════════════
# Test 1: RISK_ON macro state
# ══════════════════════════════════════════════════════════════

class TestMacroStateClassification:
    """Tests for macro state classification."""
    
    def test_risk_on_macro(self, engine, adapter):
        """Test 1: risk-on macro → RISK_ON"""
        input = adapter.create_manual_input(
            inflation=-0.1,   # Low inflation (not triggering EASING)
            rates=0.1,        # Neutral-ish rates (not triggering EASING)
            labor=0.5,        # Strong labor
            unemployment=0.4, # Low unemployment
            housing=0.3,      # Strong housing
            growth=0.6,       # Strong growth
            liquidity=0.3,    # Expanding liquidity
            credit=0.4,       # Easy credit
            consumer=0.5,     # Strong consumer
        )
        
        context = engine.build_context(input)
        
        assert context.macro_state == "RISK_ON"
        assert context.equity_bias == "BULLISH"
        assert context.liquidity_state in ["EXPANDING", "STABLE"]
        print(f"\n✅ RISK_ON: {context.reason}")
    
    def test_tightening_macro(self, engine, adapter):
        """Test 2: tightening macro → TIGHTENING"""
        input = adapter.create_manual_input(
            inflation=0.6,    # High inflation
            rates=0.6,        # Very hawkish rates
            labor=0.3,        # OK labor
            unemployment=0.2, # OK unemployment
            housing=-0.2,     # Weakening housing
            growth=0.1,       # Slowing growth
            liquidity=-0.4,   # Contracting liquidity
            credit=-0.3,      # Tightening credit
            consumer=-0.1,    # Weakening consumer
        )
        
        context = engine.build_context(input)
        
        assert context.macro_state == "TIGHTENING"
        assert context.usd_bias == "BULLISH"
        assert context.liquidity_state == "CONTRACTING"
        print(f"\n✅ TIGHTENING: {context.reason}")
    
    def test_stagflation_macro(self, engine, adapter):
        """Test 3: stagflation case → STAGFLATION"""
        input = adapter.create_manual_input(
            inflation=0.7,    # Very high inflation
            rates=0.3,        # Elevated rates
            labor=-0.2,       # Weakening labor
            unemployment=-0.3,# Rising unemployment
            housing=-0.4,     # Weak housing
            growth=-0.4,      # Negative growth
            liquidity=-0.1,   # Stable/slight contraction
            credit=-0.2,      # Tighter credit
            consumer=-0.4,    # Weak consumer
        )
        
        context = engine.build_context(input)
        
        assert context.macro_state == "STAGFLATION"
        assert context.equity_bias == "BEARISH"
        print(f"\n✅ STAGFLATION: {context.reason}")
    
    def test_risk_off_macro(self, engine, adapter):
        """Test: risk-off macro → RISK_OFF"""
        input = adapter.create_manual_input(
            inflation=0.3,    # Moderate inflation (not stagflation level)
            rates=0.5,        # Hawkish rates
            labor=0.2,        # OK labor
            unemployment=-0.2,# Rising unemployment
            housing=-0.3,     # Weak housing
            growth=-0.2,      # Weak growth (not stagflation level)
            liquidity=-0.2,   # Contracting liquidity
            credit=-0.4,      # Tight credit
            consumer=-0.3,    # Weak consumer
        )
        
        context = engine.build_context(input)
        
        assert context.macro_state == "RISK_OFF"
        assert context.usd_bias == "BULLISH"
        assert context.equity_bias == "BEARISH"
        print(f"\n✅ RISK_OFF: {context.reason}")


# ══════════════════════════════════════════════════════════════
# Tests 4-6: Bias Classification
# ══════════════════════════════════════════════════════════════

class TestBiasClassification:
    """Tests for bias classification."""
    
    def test_usd_bias_bullish(self, engine, adapter):
        """Test 4: USD bias classified correctly - BULLISH"""
        input = adapter.create_manual_input(
            inflation=0.5,    # High inflation → bullish USD
            rates=0.6,        # High rates → bullish USD
            labor=0.4,        # Strong labor → bullish USD
            credit=-0.3,      # Tight credit → bullish USD
        )
        
        context = engine.build_context(input)
        
        assert context.usd_bias == "BULLISH"
        print(f"\n✅ USD BULLISH: score driven by high rates + inflation")
    
    def test_usd_bias_bearish(self, engine, adapter):
        """Test 4b: USD bias classified correctly - BEARISH"""
        input = adapter.create_manual_input(
            inflation=-0.5,   # Low inflation → bearish USD
            rates=-0.6,       # Low rates → bearish USD
            labor=-0.2,       # Weak labor → bearish USD
            credit=0.4,       # Easy credit → bearish USD
        )
        
        context = engine.build_context(input)
        
        assert context.usd_bias == "BEARISH"
        print(f"\n✅ USD BEARISH: score driven by low rates + inflation")
    
    def test_equity_bias_bullish(self, engine, adapter):
        """Test 5: Equity bias classified correctly - BULLISH"""
        input = adapter.create_manual_input(
            growth=0.6,       # Strong growth → bullish equities
            liquidity=0.5,    # Expanding liquidity → bullish
            consumer=0.4,     # Strong consumer → bullish
            inflation=-0.2,   # Low inflation → less drag
            rates=-0.3,       # Low rates → bullish
        )
        
        context = engine.build_context(input)
        
        assert context.equity_bias == "BULLISH"
        print(f"\n✅ EQUITY BULLISH: score driven by growth + liquidity")
    
    def test_equity_bias_bearish(self, engine, adapter):
        """Test 5b: Equity bias classified correctly - BEARISH"""
        input = adapter.create_manual_input(
            growth=-0.5,      # Weak growth → bearish equities
            liquidity=-0.3,   # Contracting liquidity → bearish
            consumer=-0.3,    # Weak consumer → bearish
            inflation=0.5,    # High inflation → drag
            rates=0.4,        # High rates → bearish
        )
        
        context = engine.build_context(input)
        
        assert context.equity_bias == "BEARISH"
        print(f"\n✅ EQUITY BEARISH: score driven by weak growth + high inflation")
    
    def test_liquidity_state_expanding(self, engine, adapter):
        """Test 6: Liquidity state classified correctly - EXPANDING"""
        input = adapter.create_manual_input(
            liquidity=0.6,    # Expanding liquidity
            rates=-0.3,       # Low rates → more liquidity
            credit=0.3,       # Easy credit → more liquidity
            inflation=-0.2,   # Low inflation → no drain
        )
        
        context = engine.build_context(input)
        
        assert context.liquidity_state == "EXPANDING"
        print(f"\n✅ LIQUIDITY EXPANDING: driven by liquidity signal + low rates")
    
    def test_liquidity_state_contracting(self, engine, adapter):
        """Test 6b: Liquidity state classified correctly - CONTRACTING"""
        input = adapter.create_manual_input(
            liquidity=-0.4,   # Contracting liquidity
            rates=0.5,        # High rates → drains liquidity
            credit=-0.4,      # Tight credit → less liquidity
            inflation=0.4,    # High inflation → Fed tightening
        )
        
        context = engine.build_context(input)
        
        assert context.liquidity_state == "CONTRACTING"
        print(f"\n✅ LIQUIDITY CONTRACTING: driven by high rates + tight credit")


# ══════════════════════════════════════════════════════════════
# Test 7: Macro Strength
# ══════════════════════════════════════════════════════════════

class TestMacroStrength:
    """Tests for macro_strength computation."""
    
    def test_macro_strength_computed(self, engine, adapter):
        """Test 7: macro_strength computed correctly"""
        input = adapter.create_manual_input(
            inflation=0.5,
            rates=0.5,
            labor=0.5,
            unemployment=0.5,
            housing=0.5,
            growth=0.5,
            liquidity=0.5,
            credit=0.5,
            consumer=0.5,
        )
        
        context = engine.build_context(input)
        
        # Confidence should be high (avg of abs = 0.5)
        assert 0.4 <= context.confidence <= 0.6
        
        # Reliability should be high (all same direction → low stddev)
        assert context.reliability >= 0.7
        
        # Macro strength = 0.5 * confidence + 0.5 * reliability
        expected_strength = 0.5 * context.confidence + 0.5 * context.reliability
        assert abs(context.macro_strength - expected_strength) < 0.01
        
        print(f"\n✅ MACRO_STRENGTH: conf={context.confidence:.3f}, rel={context.reliability:.3f}, strength={context.macro_strength:.3f}")
    
    def test_macro_strength_low_on_conflicting_signals(self, engine, adapter):
        """Test: macro_strength lower when signals conflict"""
        input = adapter.create_manual_input(
            inflation=0.8,    # Very high
            rates=-0.8,       # Very low (conflicting with inflation)
            labor=0.5,
            unemployment=-0.5,  # Conflicting (bad)
            growth=0.6,
            liquidity=-0.6,   # Conflicting
            consumer=0.4,
        )
        
        context = engine.build_context(input)
        
        # High confidence (strong signals)
        assert context.confidence >= 0.4
        
        # Lower reliability (conflicting signals)
        assert context.reliability <= 0.7
        
        print(f"\n✅ CONFLICTING: conf={context.confidence:.3f}, rel={context.reliability:.3f}")


# ══════════════════════════════════════════════════════════════
# Tests 8-10: Context State
# ══════════════════════════════════════════════════════════════

class TestContextState:
    """Tests for context_state classification."""
    
    def test_supportive_state(self, engine, adapter):
        """Test 8: SUPPORTIVE state classified correctly"""
        # Create inputs that lead to a clear macro state (e.g., TIGHTENING)
        input = adapter.create_manual_input(
            inflation=0.6,    # High inflation
            rates=0.6,        # High rates
            labor=0.4,        # OK labor
            unemployment=0.3, # OK unemployment
            housing=0.2,      # Weakening housing
            growth=0.2,       # Slowing growth
            liquidity=-0.4,   # Contracting liquidity
            credit=-0.2,      # Tighter credit
            consumer=0.3,     # OK consumer
        )
        
        context = engine.build_context(input)
        
        # Should be TIGHTENING (clear macro state) with good reliability → SUPPORTIVE
        assert context.macro_state == "TIGHTENING"
        assert context.context_state == "SUPPORTIVE"
        assert context.confidence >= 0.30
        assert context.reliability >= 0.55
        print(f"\n✅ SUPPORTIVE: state={context.macro_state}, conf={context.confidence:.3f}, rel={context.reliability:.3f}")
    
    def test_conflicted_state(self, engine, adapter):
        """Test 9: CONFLICTED state classified correctly"""
        input = adapter.create_manual_input(
            inflation=0.8,    # Very high
            rates=-0.8,       # Very low (conflicting!)
            labor=0.7,        # Strong
            unemployment=-0.7,# Bad (conflicting with labor!)
            housing=0.6,
            growth=-0.7,      # Weak (conflicting with labor!)
            liquidity=0.7,
            credit=-0.7,      # Tight (conflicting with liquidity!)
            consumer=0.5,
        )
        
        context = engine.build_context(input)
        
        # Strong signals but inconsistent → CONFLICTED
        assert context.context_state == "CONFLICTED"
        assert context.confidence >= 0.50
        assert context.reliability < 0.45
        print(f"\n✅ CONFLICTED: conf={context.confidence:.3f}, rel={context.reliability:.3f}")
    
    def test_blocked_on_missing_inputs(self, engine, adapter):
        """Test 10: BLOCKED on missing inputs"""
        input = adapter.create_manual_input(
            inflation=0.0,
            rates=0.0,
            labor=0.0,
            unemployment=0.0,
            housing=0.0,
            growth=0.1,       # Only one tiny signal
            liquidity=0.0,
            credit=0.0,
            consumer=0.0,
        )
        
        context = engine.build_context(input)
        
        # Too few non-zero inputs → BLOCKED
        assert context.context_state == "BLOCKED"
        assert context.macro_state == "UNKNOWN"
        print(f"\n✅ BLOCKED: insufficient inputs, macro_state={context.macro_state}")


# ══════════════════════════════════════════════════════════════
# Tests 11-12: Endpoint Validation
# ══════════════════════════════════════════════════════════════

class TestEndpointValidation:
    """Tests for endpoint response validation."""
    
    def test_summary_endpoint_valid(self, engine, adapter):
        """Test 11: summary endpoint valid"""
        input = adapter.create_manual_input(
            inflation=0.3,
            rates=0.4,
            labor=0.3,
            unemployment=0.2,
            growth=0.3,
            liquidity=0.2,
            consumer=0.3,
        )
        
        context = engine.build_context(input)
        summary = engine.get_summary(context)
        
        # Verify all required fields
        assert summary.macro_state is not None
        assert summary.usd_bias in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert summary.equity_bias in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert summary.liquidity_state in ["EXPANDING", "STABLE", "CONTRACTING", "UNKNOWN"]
        assert 0.0 <= summary.confidence <= 1.0
        assert 0.0 <= summary.reliability <= 1.0
        assert summary.context_state in ["SUPPORTIVE", "MIXED", "CONFLICTED", "BLOCKED"]
        
        print(f"\n✅ SUMMARY: {summary.model_dump()}")
    
    def test_health_endpoint_valid(self, engine, adapter):
        """Test 12: health endpoint valid"""
        input = adapter.create_manual_input(
            inflation=0.3,
            rates=0.4,
            labor=0.3,
            growth=0.3,
        )
        
        engine.build_context(input)
        health = engine.get_health()
        
        # Verify all required fields
        assert health.status in ["OK", "DEGRADED", "ERROR"]
        assert isinstance(health.has_inputs, bool)
        assert isinstance(health.input_count, int)
        assert health.context_state in ["SUPPORTIVE", "MIXED", "CONFLICTED", "BLOCKED"]
        
        print(f"\n✅ HEALTH: status={health.status}, has_inputs={health.has_inputs}, count={health.input_count}")


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

class TestAdapter:
    """Tests for MacroContextAdapter."""
    
    def test_adapt_from_raw_dict(self, adapter):
        """Test adapter with raw macro values."""
        raw_data = {
            "inflation": 3.5,     # 3.5% inflation
            "fed_rate": 4.5,      # 4.5% fed rate
            "unemployment": 4.0,  # 4.0% unemployment
            "gdp_growth": 2.5,    # 2.5% GDP growth
        }
        
        input = adapter.adapt_from_dict(raw_data)
        
        # All values should be normalized to [-1, +1]
        assert -1.0 <= input.inflation_signal <= 1.0
        assert -1.0 <= input.rates_signal <= 1.0
        assert -1.0 <= input.unemployment_signal <= 1.0
        assert -1.0 <= input.growth_signal <= 1.0
        
        print(f"\n✅ ADAPTER: inflation={input.inflation_signal:.3f}, rates={input.rates_signal:.3f}")
    
    def test_adapter_clamps_values(self, adapter):
        """Test adapter clamps extreme values."""
        raw_data = {
            "inflation_signal": 2.5,   # Too high
            "rates_signal": -3.0,      # Too low
        }
        
        input = adapter.adapt_from_dict(raw_data)
        
        assert input.inflation_signal == 1.0
        assert input.rates_signal == -1.0
        print(f"\n✅ CLAMP: inflation clamped to 1.0, rates clamped to -1.0")


class TestReasonGeneration:
    """Tests for reason string generation."""
    
    def test_reason_generated(self, engine, adapter):
        """Test that reason is always generated."""
        input = adapter.create_manual_input(
            inflation=0.3,
            rates=0.3,
            growth=0.4,
            liquidity=0.3,
        )
        
        context = engine.build_context(input)
        
        assert context.reason is not None
        assert len(context.reason) > 10
        assert any(word in context.reason.lower() for word in 
                   ["macro", "risk", "tightening", "easing", "liquidity", "equity", "dollar", "mixed", "insufficient"])
        
        print(f"\n✅ REASON: {context.reason}")


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
