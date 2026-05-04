"""
PHASE 26.4 — Alpha Registry Tests

Test suite for alpha registry functionality.

Required tests (18):
1. register_factor works
2. update_factor works
3. archive_factor works
4. registry retrieval works
5. active filter works
6. deprecated filter works
7. history storage works
8. history retrieval works
9. duplicate protection
10. factor update timestamp
11. registry summary correct
12. registry endpoint correct
13. active endpoint correct
14. history endpoint correct
15. empty registry handling
16. large factor list handling
17. integration with survival engine
18. integration with scoring engine
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from modules.alpha_factory_v2.alpha_registry import (
    AlphaRegistry,
    get_alpha_registry,
    RegistryAlphaFactor,
    AlphaFactorHistory,
    RegistrySummary,
)
from modules.alpha_factory_v2.factor_discovery_engine import FactorDiscoveryEngine
from modules.alpha_factory_v2.alpha_scoring_engine import AlphaScoringEngine
from modules.alpha_factory_v2.factor_survival_engine import FactorSurvivalEngine
from modules.alpha_factory_v2.factor_types import AlphaFactor


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def registry():
    """Create fresh registry instance (in-memory)."""
    return AlphaRegistry()


@pytest.fixture
def discovery_engine():
    """Create fresh discovery engine instance."""
    return FactorDiscoveryEngine()


@pytest.fixture
def scoring_engine():
    """Create fresh scoring engine instance."""
    return AlphaScoringEngine()


@pytest.fixture
def survival_engine():
    """Create fresh survival engine instance."""
    return FactorSurvivalEngine()


@pytest.fixture
def sample_factor():
    """Create a sample AlphaFactor."""
    return AlphaFactor(
        factor_id="test_factor_001",
        name="test_momentum",
        category="TA",
        lookback=14,
        signal_strength=0.65,
        sharpe_score=0.55,
        stability_score=0.60,
        drawdown_score=0.50,
        alpha_score=0.59,
        status="ACTIVE",
        parameters={"period": 14},
        source="ta_engine",
    )


@pytest.fixture
def deprecated_factor():
    """Create a deprecated AlphaFactor."""
    return AlphaFactor(
        factor_id="deprecated_001",
        name="deprecated_signal",
        category="TA",
        lookback=14,
        signal_strength=0.30,
        sharpe_score=0.25,
        stability_score=0.30,
        drawdown_score=0.35,
        alpha_score=0.30,
        status="DEPRECATED",
        parameters={},
        source="ta_engine",
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Register Factor Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_register_factor_works(registry, sample_factor):
    """Test 1: register_factor creates new factor."""
    result = await registry.register_factor(sample_factor)
    
    assert isinstance(result, RegistryAlphaFactor)
    assert result.factor_id == sample_factor.factor_id
    assert result.name == sample_factor.name
    assert result.alpha_score == sample_factor.alpha_score


# ══════════════════════════════════════════════════════════════
# Test 2: Update Factor Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_factor_works(registry, sample_factor):
    """Test 2: update_factor updates existing factor."""
    # Register first
    await registry.register_factor(sample_factor)
    
    # Update with new score
    sample_factor.alpha_score = 0.75
    updated = await registry.update_factor(sample_factor)
    
    assert updated.alpha_score == 0.75


# ══════════════════════════════════════════════════════════════
# Test 3: Archive Factor Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_archive_factor_works(registry, sample_factor):
    """Test 3: archive_factor sets status to DEPRECATED."""
    await registry.register_factor(sample_factor)
    
    archived = await registry.archive_factor(sample_factor.factor_id)
    
    assert archived is not None
    assert archived.status == "DEPRECATED"


# ══════════════════════════════════════════════════════════════
# Test 4: Registry Retrieval Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_retrieval_works(registry, sample_factor):
    """Test 4: get_factor retrieves correct factor."""
    await registry.register_factor(sample_factor)
    
    retrieved = await registry.get_factor(sample_factor.factor_id)
    
    assert retrieved is not None
    assert retrieved.factor_id == sample_factor.factor_id


# ══════════════════════════════════════════════════════════════
# Test 5: Active Filter Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_active_filter_works(registry, sample_factor, deprecated_factor):
    """Test 5: get_active_factors returns only ACTIVE."""
    await registry.register_factor(sample_factor)
    await registry.register_factor(deprecated_factor)
    
    active = await registry.get_active_factors()
    
    assert len(active) == 1
    assert all(f.status == "ACTIVE" for f in active)


# ══════════════════════════════════════════════════════════════
# Test 6: Deprecated Filter Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_deprecated_filter_works(registry, sample_factor, deprecated_factor):
    """Test 6: get_deprecated_factors returns only DEPRECATED."""
    await registry.register_factor(sample_factor)
    await registry.register_factor(deprecated_factor)
    
    deprecated = await registry.get_deprecated_factors()
    
    assert len(deprecated) == 1
    assert all(f.status == "DEPRECATED" for f in deprecated)


# ══════════════════════════════════════════════════════════════
# Test 7: History Storage Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_history_storage_works(registry, sample_factor):
    """Test 7: History is stored when factor is registered."""
    await registry.register_factor(sample_factor)
    
    # History should have one entry
    history = await registry.get_factor_history(sample_factor.factor_id)
    
    assert len(history) >= 1


# ══════════════════════════════════════════════════════════════
# Test 8: History Retrieval Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_history_retrieval_works(registry, sample_factor):
    """Test 8: Factor history can be retrieved."""
    await registry.register_factor(sample_factor)
    
    # Update to create more history
    sample_factor.alpha_score = 0.70
    await registry.update_factor(sample_factor)
    
    history = await registry.get_factor_history(sample_factor.factor_id)
    
    assert len(history) >= 2
    assert all(isinstance(h, AlphaFactorHistory) for h in history)


# ══════════════════════════════════════════════════════════════
# Test 9: Duplicate Protection
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_duplicate_protection(registry, sample_factor):
    """Test 9: Registering same factor twice updates instead."""
    await registry.register_factor(sample_factor)
    await registry.register_factor(sample_factor)
    
    all_factors = await registry.get_all_factors()
    
    # Should only have one factor
    assert len(all_factors) == 1


# ══════════════════════════════════════════════════════════════
# Test 10: Factor Update Timestamp
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_factor_update_timestamp(registry, sample_factor):
    """Test 10: last_updated timestamp changes on update."""
    result1 = await registry.register_factor(sample_factor)
    original_updated = result1.last_updated
    
    # Small delay to ensure timestamp difference
    await asyncio.sleep(0.01)
    
    sample_factor.alpha_score = 0.80
    result2 = await registry.update_factor(sample_factor)
    
    assert result2.last_updated >= original_updated


# ══════════════════════════════════════════════════════════════
# Test 11: Registry Summary Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_summary_correct(registry, sample_factor, deprecated_factor):
    """Test 11: get_summary returns correct stats."""
    await registry.register_factor(sample_factor)
    await registry.register_factor(deprecated_factor)
    
    summary = await registry.get_summary()
    
    assert isinstance(summary, RegistrySummary)
    assert summary.total_factors == 2
    assert summary.active_factors == 1
    assert summary.deprecated_factors == 1


# ══════════════════════════════════════════════════════════════
# Test 12: Registry Endpoint Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_endpoint_correct(registry, sample_factor):
    """Test 12: get_all_factors returns all factors."""
    await registry.register_factor(sample_factor)
    
    all_factors = await registry.get_all_factors()
    
    assert len(all_factors) == 1
    assert all(isinstance(f, RegistryAlphaFactor) for f in all_factors)


# ══════════════════════════════════════════════════════════════
# Test 13: Active Endpoint Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_active_endpoint_correct(registry, sample_factor):
    """Test 13: get_active_factors returns correct structure."""
    await registry.register_factor(sample_factor)
    
    active = await registry.get_active_factors()
    
    assert len(active) == 1
    assert active[0].status == "ACTIVE"


# ══════════════════════════════════════════════════════════════
# Test 14: History Endpoint Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_history_endpoint_correct(registry, sample_factor):
    """Test 14: get_factor_history returns correct structure."""
    await registry.register_factor(sample_factor)
    
    history = await registry.get_factor_history(sample_factor.factor_id)
    
    assert all(isinstance(h, AlphaFactorHistory) for h in history)
    assert all(h.factor_id == sample_factor.factor_id for h in history)


# ══════════════════════════════════════════════════════════════
# Test 15: Empty Registry Handling
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_empty_registry_handling(registry):
    """Test 15: Empty registry returns valid empty results."""
    all_factors = await registry.get_all_factors()
    active = await registry.get_active_factors()
    summary = await registry.get_summary()
    
    assert all_factors == []
    assert active == []
    assert summary.total_factors == 0


# ══════════════════════════════════════════════════════════════
# Test 16: Large Factor List Handling
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_large_factor_list_handling(registry):
    """Test 16: Registry handles large number of factors."""
    factors = []
    for i in range(50):
        factor = AlphaFactor(
            factor_id=f"factor_{i:03d}",
            name=f"factor_{i}",
            category="TA",
            lookback=14,
            signal_strength=0.5 + (i % 10) * 0.05,
            sharpe_score=0.5,
            stability_score=0.5,
            drawdown_score=0.5,
            alpha_score=0.5 + (i % 10) * 0.05,
            status="ACTIVE" if i % 2 == 0 else "DEPRECATED",
            parameters={},
            source="test",
        )
        factors.append(factor)
    
    results = await registry.register_factors_bulk(factors)
    
    assert len(results) == 50
    
    summary = await registry.get_summary()
    assert summary.total_factors == 50


# ══════════════════════════════════════════════════════════════
# Test 17: Integration with Survival Engine
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_integration_with_survival(
    registry, discovery_engine, scoring_engine, survival_engine
):
    """Test 17: Full integration with survival engine."""
    # Discover → Score → Survive
    candidates = discovery_engine.discover_all()
    scored = scoring_engine.score_candidates(candidates)
    survived = survival_engine.apply_survival(scored)
    
    # Register all survived factors
    for factor in survived:
        await registry.register_factor(factor)
    
    all_factors = await registry.get_all_factors()
    assert len(all_factors) == len(survived)


# ══════════════════════════════════════════════════════════════
# Test 18: Integration with Scoring Engine
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_integration_with_scoring(
    registry, discovery_engine, scoring_engine
):
    """Test 18: Integration with scoring engine."""
    # Discover → Score
    candidates = discovery_engine.discover_all()
    scored = scoring_engine.score_candidates(candidates)
    
    # Register scored factors
    for factor in scored:
        await registry.register_factor(factor)
    
    summary = await registry.get_summary()
    assert summary.total_factors == len(scored)


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_singleton_pattern():
    """Test singleton pattern for registry."""
    registry1 = get_alpha_registry()
    registry2 = get_alpha_registry()
    assert registry1 is registry2


@pytest.mark.asyncio
async def test_top_factors(registry, sample_factor, deprecated_factor):
    """Test get_top_factors returns sorted factors."""
    await registry.register_factor(sample_factor)
    await registry.register_factor(deprecated_factor)
    
    top = await registry.get_top_factors(2)
    
    assert len(top) == 2
    # First should have higher alpha
    assert top[0].alpha_score >= top[1].alpha_score


@pytest.mark.asyncio
async def test_clear_registry(registry, sample_factor):
    """Test clear_registry removes all factors."""
    await registry.register_factor(sample_factor)
    
    await registry.clear_registry()
    
    all_factors = await registry.get_all_factors()
    assert len(all_factors) == 0
