"""
PHASE 26.5 — Alpha Factory Engine Tests

Test suite for unified pipeline.

Required tests (20):
1. pipeline runs
2. discovery called
3. scoring called
4. survival called
5. registry update called
6. result contract correct
7. candidate count correct
8. scoring output correct
9. survival filtering correct
10. registry storage correct
11. strongest factor detection
12. weakest factor detection
13. average alpha score correct
14. scheduler works
15. api run endpoint
16. api status endpoint
17. api summary endpoint
18. pipeline empty case
19. max_active_factors protection
20. full integration test
"""

import pytest
from datetime import datetime, timedelta

from modules.alpha_factory_v2.alpha_factory_engine import (
    AlphaFactoryEngine,
    get_alpha_factory_engine,
    AlphaFactoryResult,
    AlphaFactoryStatus,
    MAX_ACTIVE_FACTORS,
    SCHEDULE_INTERVAL_HOURS,
)
from modules.alpha_factory_v2.factor_discovery_engine import FactorDiscoveryEngine
from modules.alpha_factory_v2.alpha_scoring_engine import AlphaScoringEngine
from modules.alpha_factory_v2.factor_survival_engine import FactorSurvivalEngine
from modules.alpha_factory_v2.alpha_registry import AlphaRegistry
from modules.alpha_factory_v2.factor_types import AlphaFactor


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def factory_engine():
    """Create fresh factory engine with fresh components."""
    return AlphaFactoryEngine(
        discovery=FactorDiscoveryEngine(),
        scoring=AlphaScoringEngine(),
        survival=FactorSurvivalEngine(),
        registry=AlphaRegistry(),
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Pipeline Runs
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pipeline_runs(factory_engine):
    """Test 1: Pipeline executes without error."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert result is not None
    assert isinstance(result, AlphaFactoryResult)


# ══════════════════════════════════════════════════════════════
# Test 2: Discovery Called
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_discovery_called(factory_engine):
    """Test 2: Discovery engine is called during pipeline."""
    result = await factory_engine.run_alpha_pipeline()
    
    # Discovery should generate candidates
    assert result.candidates_generated > 0


# ══════════════════════════════════════════════════════════════
# Test 3: Scoring Called
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_scoring_called(factory_engine):
    """Test 3: Scoring engine is called during pipeline."""
    result = await factory_engine.run_alpha_pipeline()
    
    # All candidates should be scored
    assert result.scored_factors == result.candidates_generated


# ══════════════════════════════════════════════════════════════
# Test 4: Survival Called
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_survival_called(factory_engine):
    """Test 4: Survival engine is called during pipeline."""
    result = await factory_engine.run_alpha_pipeline()
    
    # Total should equal scored
    total = result.active_factors + result.deprecated_factors
    assert total == result.scored_factors


# ══════════════════════════════════════════════════════════════
# Test 5: Registry Update Called
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_update_called(factory_engine):
    """Test 5: Registry is updated during pipeline."""
    await factory_engine.run_alpha_pipeline()
    
    # Registry should have factors
    status = await factory_engine.get_status()
    assert status.total_factors > 0


# ══════════════════════════════════════════════════════════════
# Test 6: Result Contract Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_result_contract_correct(factory_engine):
    """Test 6: Result has all required fields."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert hasattr(result, 'candidates_generated')
    assert hasattr(result, 'scored_factors')
    assert hasattr(result, 'active_factors')
    assert hasattr(result, 'deprecated_factors')
    assert hasattr(result, 'strongest_factor')
    assert hasattr(result, 'weakest_factor')
    assert hasattr(result, 'average_alpha_score')


# ══════════════════════════════════════════════════════════════
# Test 7: Candidate Count Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_candidate_count_correct(factory_engine):
    """Test 7: Candidate count matches discovery output."""
    result = await factory_engine.run_alpha_pipeline()
    
    # Expected ~46 candidates based on discovery engine
    assert 40 <= result.candidates_generated <= 50


# ══════════════════════════════════════════════════════════════
# Test 8: Scoring Output Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_scoring_output_correct(factory_engine):
    """Test 8: Scoring produces valid output."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert result.scored_factors == result.candidates_generated
    assert result.average_alpha_score >= 0.0
    assert result.average_alpha_score <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 9: Survival Filtering Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_survival_filtering_correct(factory_engine):
    """Test 9: Survival correctly filters factors."""
    result = await factory_engine.run_alpha_pipeline()
    
    # Should have both active and deprecated
    assert result.active_factors >= 0
    assert result.deprecated_factors >= 0
    assert result.active_factors + result.deprecated_factors == result.scored_factors


# ══════════════════════════════════════════════════════════════
# Test 10: Registry Storage Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_storage_correct(factory_engine):
    """Test 10: Registry stores all survived factors."""
    result = await factory_engine.run_alpha_pipeline()
    
    status = await factory_engine.get_status()
    assert status.total_factors == result.scored_factors


# ══════════════════════════════════════════════════════════════
# Test 11: Strongest Factor Detection
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_strongest_factor_detection(factory_engine):
    """Test 11: Strongest factor is detected."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert result.strongest_factor is not None
    assert isinstance(result.strongest_factor, str)


# ══════════════════════════════════════════════════════════════
# Test 12: Weakest Factor Detection
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_weakest_factor_detection(factory_engine):
    """Test 12: Weakest factor is detected."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert result.weakest_factor is not None
    assert isinstance(result.weakest_factor, str)


# ══════════════════════════════════════════════════════════════
# Test 13: Average Alpha Score Correct
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_average_alpha_score_correct(factory_engine):
    """Test 13: Average alpha score is calculated correctly."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert 0.0 <= result.average_alpha_score <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 14: Scheduler Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_scheduler_works(factory_engine):
    """Test 14: Scheduler respects interval."""
    # First run should execute
    result1 = await factory_engine.run_scheduled()
    assert result1 is not None
    
    # Second run should be skipped (too soon)
    result2 = await factory_engine.run_scheduled()
    assert result2 is None


# ══════════════════════════════════════════════════════════════
# Test 15: API Run Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_run_endpoint(factory_engine):
    """Test 15: Pipeline can be triggered."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert result.candidates_generated > 0
    assert factory_engine.pipeline_state == "READY"


# ══════════════════════════════════════════════════════════════
# Test 16: API Status Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_status_endpoint(factory_engine):
    """Test 16: Status endpoint returns correct data."""
    await factory_engine.run_alpha_pipeline()
    
    status = await factory_engine.get_status()
    
    assert isinstance(status, AlphaFactoryStatus)
    assert status.pipeline_state == "READY"
    assert status.last_run is not None


# ══════════════════════════════════════════════════════════════
# Test 17: API Summary Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_summary_endpoint(factory_engine):
    """Test 17: Summary endpoint returns correct data."""
    await factory_engine.run_alpha_pipeline()
    
    summary = await factory_engine.get_summary()
    
    assert "total_factors" in summary
    assert "active_factors" in summary
    assert "deprecated_factors" in summary
    assert "average_alpha_score" in summary


# ══════════════════════════════════════════════════════════════
# Test 18: Pipeline Empty Case
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pipeline_empty_case():
    """Test 18: Pipeline handles empty discovery gracefully."""
    # Create engine with mock discovery that returns empty
    class EmptyDiscovery:
        def discover_all(self):
            return []
    
    engine = AlphaFactoryEngine(
        discovery=EmptyDiscovery(),
        scoring=AlphaScoringEngine(),
        survival=FactorSurvivalEngine(),
        registry=AlphaRegistry(),
    )
    
    result = await engine.run_alpha_pipeline()
    
    assert result.candidates_generated == 0
    assert result.scored_factors == 0


# ══════════════════════════════════════════════════════════════
# Test 19: Max Active Factors Protection
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_max_active_factors_protection(factory_engine):
    """Test 19: Max active factors limit is enforced."""
    result = await factory_engine.run_alpha_pipeline()
    
    # Active factors should not exceed limit
    assert result.active_factors <= MAX_ACTIVE_FACTORS


# ══════════════════════════════════════════════════════════════
# Test 20: Full Integration Test
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_full_integration(factory_engine):
    """Test 20: Full pipeline integration test."""
    # Run pipeline
    result = await factory_engine.run_alpha_pipeline()
    
    # Verify all stages completed
    assert result.candidates_generated > 0
    assert result.scored_factors > 0
    assert result.active_factors + result.deprecated_factors == result.scored_factors
    
    # Verify registry state
    status = await factory_engine.get_status()
    assert status.total_factors == result.scored_factors
    
    # Verify summary
    summary = await factory_engine.get_summary()
    assert summary["total_factors"] == result.scored_factors
    
    # Verify active factors retrievable
    active = await factory_engine.get_active_factors()
    assert len(active) == result.active_factors


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_singleton_pattern():
    """Test singleton pattern for factory engine."""
    engine1 = get_alpha_factory_engine()
    engine2 = get_alpha_factory_engine()
    assert engine1 is engine2


def test_constants():
    """Test constants are correct."""
    assert MAX_ACTIVE_FACTORS == 30
    assert SCHEDULE_INTERVAL_HOURS == 6


@pytest.mark.asyncio
async def test_pipeline_duration_tracked(factory_engine):
    """Test pipeline duration is tracked."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert result.pipeline_duration_ms >= 0


@pytest.mark.asyncio
async def test_last_result_stored(factory_engine):
    """Test last result is stored."""
    result = await factory_engine.run_alpha_pipeline()
    
    assert factory_engine.last_result is not None
    assert factory_engine.last_result == result


@pytest.mark.asyncio
async def test_should_run_scheduled(factory_engine):
    """Test should_run_scheduled works."""
    # Before first run
    assert factory_engine.should_run_scheduled() is True
    
    # After run
    await factory_engine.run_alpha_pipeline()
    assert factory_engine.should_run_scheduled() is False
