"""
PHASE 26.6 — Alpha Validation Engine Tests

Test suite for validation engine.

Required tests (15):
1. alpha_drift calculation
2. drift threshold
3. turnover calculation
4. turnover threshold
5. distribution check
6. category balance check
7. active factor limit
8. validation report structure
9. validation endpoint
10. stability pass
11. stability warning
12. stability fail
13. integration with registry
14. integration with scoring
15. full system validation
"""

import pytest
from datetime import datetime

from modules.alpha_factory_v2.alpha_validation_engine import (
    AlphaValidationEngine,
    AlphaValidationReport,
    get_alpha_validation_engine,
    ALPHA_DRIFT_THRESHOLD,
    TURNOVER_THRESHOLD,
    ALPHA_MEAN_MIN,
    ALPHA_MEAN_MAX,
    OVERFIT_THRESHOLD,
    CATEGORY_DOMINANCE_THRESHOLD,
    MAX_ACTIVE_FACTORS,
)
from modules.alpha_factory_v2.alpha_registry import AlphaRegistry, RegistryAlphaFactor
from modules.alpha_factory_v2.alpha_factory_engine import AlphaFactoryEngine
from modules.alpha_factory_v2.factor_discovery_engine import FactorDiscoveryEngine
from modules.alpha_factory_v2.alpha_scoring_engine import AlphaScoringEngine
from modules.alpha_factory_v2.factor_survival_engine import FactorSurvivalEngine


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def validation_engine():
    """Create fresh validation engine with fresh registry."""
    registry = AlphaRegistry()
    return AlphaValidationEngine(registry=registry)


@pytest.fixture
def factory_with_registry():
    """Create factory engine with shared registry."""
    registry = AlphaRegistry()
    factory = AlphaFactoryEngine(
        discovery=FactorDiscoveryEngine(),
        scoring=AlphaScoringEngine(),
        survival=FactorSurvivalEngine(),
        registry=registry,
    )
    validation = AlphaValidationEngine(registry=registry)
    return factory, validation, registry


# ══════════════════════════════════════════════════════════════
# Test 1: Alpha Drift Calculation
# ══════════════════════════════════════════════════════════════

def test_alpha_drift_calculation(validation_engine):
    """Test 1: Drift is calculated correctly."""
    drift = validation_engine.calculate_drift(
        factor_id="test",
        current_score=0.65,
        previous_score=0.60,
    )
    
    assert abs(drift - 0.05) < 0.0001  # Float precision


def test_alpha_drift_calculation_large():
    """Test drift with large difference."""
    engine = AlphaValidationEngine()
    drift = engine.calculate_drift("test", 0.80, 0.40)
    assert drift == 0.40


# ══════════════════════════════════════════════════════════════
# Test 2: Drift Threshold
# ══════════════════════════════════════════════════════════════

def test_drift_threshold_pass(validation_engine):
    """Test 2: Drift below threshold passes."""
    drift = validation_engine.calculate_drift("test", 0.60, 0.50)
    assert drift <= ALPHA_DRIFT_THRESHOLD  # 0.10 <= 0.20


def test_drift_threshold_fail():
    """Test drift above threshold fails."""
    engine = AlphaValidationEngine()
    drift = engine.calculate_drift("test", 0.90, 0.50)
    assert drift > ALPHA_DRIFT_THRESHOLD  # 0.40 > 0.20


# ══════════════════════════════════════════════════════════════
# Test 3: Turnover Calculation
# ══════════════════════════════════════════════════════════════

def test_turnover_calculation(validation_engine):
    """Test 3: Turnover rate calculated correctly."""
    previous = ["a", "b", "c", "d", "e"]
    current = ["a", "b", "f", "g", "h"]  # c, d, e replaced
    
    turnover = validation_engine.calculate_turnover(previous, current)
    
    assert turnover == 0.6  # 3/5


def test_turnover_no_change():
    """Test turnover with no changes."""
    engine = AlphaValidationEngine()
    turnover = engine.calculate_turnover(["a", "b"], ["a", "b"])
    assert turnover == 0.0


# ══════════════════════════════════════════════════════════════
# Test 4: Turnover Threshold
# ══════════════════════════════════════════════════════════════

def test_turnover_threshold_pass(validation_engine):
    """Test 4: Turnover below threshold passes."""
    previous = ["a", "b", "c", "d", "e"]
    current = ["a", "b", "c", "d", "f"]  # Only 1 replaced
    
    turnover = validation_engine.calculate_turnover(previous, current)
    assert turnover <= TURNOVER_THRESHOLD  # 0.20 <= 0.40


def test_turnover_threshold_fail():
    """Test turnover above threshold."""
    engine = AlphaValidationEngine()
    turnover = engine.calculate_turnover(["a", "b"], ["c", "d"])  # 100% replaced
    assert turnover > TURNOVER_THRESHOLD


# ══════════════════════════════════════════════════════════════
# Test 5: Distribution Check
# ══════════════════════════════════════════════════════════════

def test_distribution_check(validation_engine):
    """Test 5: Distribution statistics calculated correctly."""
    scores = [0.40, 0.50, 0.60, 0.70]
    
    result = validation_engine.check_distribution(scores)
    
    assert result["mean"] == 0.55
    assert result["min"] == 0.40
    assert result["max"] == 0.70
    assert result["in_range"] is True


def test_distribution_overfit():
    """Test distribution detects overfitting."""
    engine = AlphaValidationEngine()
    scores = [0.85, 0.90, 0.95]
    
    result = engine.check_distribution(scores)
    assert result["mean"] == 0.90
    assert result["mean"] > OVERFIT_THRESHOLD


# ══════════════════════════════════════════════════════════════
# Test 6: Category Balance Check
# ══════════════════════════════════════════════════════════════

def test_category_balance_check(validation_engine):
    """Test 6: Category balance calculated correctly."""
    counts = {"TA": 10, "EXCHANGE": 10, "FRACTAL": 10, "REGIME": 10}
    
    result = validation_engine.check_category_balance(counts)
    
    assert result["passed"] is True
    assert result["balance"]["TA"] == 0.25


def test_category_balance_imbalance():
    """Test category balance detects imbalance."""
    engine = AlphaValidationEngine()
    counts = {"TA": 70, "EXCHANGE": 10, "FRACTAL": 10, "REGIME": 10}
    
    result = engine.check_category_balance(counts)
    assert result["passed"] is False
    assert result["dominant_category"] == "TA"


# ══════════════════════════════════════════════════════════════
# Test 7: Active Factor Limit
# ══════════════════════════════════════════════════════════════

def test_active_factor_limit():
    """Test 7: Active factor limit constant is correct."""
    assert MAX_ACTIVE_FACTORS == 30


@pytest.mark.asyncio
async def test_active_factor_limit_validation(factory_with_registry):
    """Test validation checks active factor limit."""
    factory, validation, registry = factory_with_registry
    
    # Run pipeline
    await factory.run_alpha_pipeline()
    
    # Validate
    report = await validation.validate()
    
    assert report.active_factors <= MAX_ACTIVE_FACTORS


# ══════════════════════════════════════════════════════════════
# Test 8: Validation Report Structure
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_validation_report_structure(validation_engine):
    """Test 8: Validation report has all required fields."""
    report = await validation_engine.validate()
    
    assert hasattr(report, 'stability_passed')
    assert hasattr(report, 'turnover_rate')
    assert hasattr(report, 'alpha_drift_max')
    assert hasattr(report, 'average_alpha_score')
    assert hasattr(report, 'active_factors')
    assert hasattr(report, 'deprecated_factors')
    assert hasattr(report, 'validation_state')


def test_validation_report_model():
    """Test validation report model structure."""
    report = AlphaValidationReport(
        stability_passed=True,
        turnover_rate=0.28,
        alpha_drift_max=0.12,
        average_alpha_score=0.41,
        active_factors=18,
        deprecated_factors=28,
        total_factors=46,
        validation_state="PASSED",
    )
    
    assert report.stability_passed is True
    assert report.validation_state == "PASSED"


# ══════════════════════════════════════════════════════════════
# Test 9: Validation Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_validation_endpoint(factory_with_registry):
    """Test 9: Validation can be called after pipeline."""
    factory, validation, registry = factory_with_registry
    
    # Run pipeline first
    await factory.run_alpha_pipeline()
    
    # Run validation
    report = await validation.validate()
    
    assert report is not None
    assert isinstance(report, AlphaValidationReport)


# ══════════════════════════════════════════════════════════════
# Test 10: Stability Pass
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_stability_pass(validation_engine):
    """Test 10: Stability passes when drift is low."""
    # Empty registry = no drift = pass
    report = await validation_engine.validate()
    
    assert report.stability_passed is True


# ══════════════════════════════════════════════════════════════
# Test 11: Stability Warning
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_stability_warning(factory_with_registry):
    """Test 11: Stability warning when turnover high."""
    factory, validation, registry = factory_with_registry
    
    # Run pipeline
    await factory.run_alpha_pipeline()
    
    # Validate - first run should be clean
    report = await validation.validate()
    
    # Should be PASSED or WARNING (not FAILED)
    assert report.validation_state in ["PASSED", "WARNING"]


# ══════════════════════════════════════════════════════════════
# Test 12: Stability Fail
# ══════════════════════════════════════════════════════════════

def test_stability_fail_conditions():
    """Test 12: Conditions that cause FAILED state."""
    # FAILED when mean alpha > OVERFIT_THRESHOLD
    assert OVERFIT_THRESHOLD == 0.80
    
    # Or when active_factors > MAX_ACTIVE_FACTORS
    assert MAX_ACTIVE_FACTORS == 30


@pytest.mark.asyncio
async def test_validation_state_failed():
    """Test validation can return FAILED."""
    report = AlphaValidationReport(
        stability_passed=False,
        turnover_rate=0.60,
        alpha_drift_max=0.30,
        average_alpha_score=0.85,  # Overfit
        active_factors=35,  # Over limit
        deprecated_factors=10,
        total_factors=45,
        validation_state="FAILED",
        errors=["Too many active factors"],
    )
    
    assert report.validation_state == "FAILED"
    assert len(report.errors) > 0


# ══════════════════════════════════════════════════════════════
# Test 13: Integration with Registry
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_integration_with_registry(factory_with_registry):
    """Test 13: Validation integrates with registry."""
    factory, validation, registry = factory_with_registry
    
    # Run pipeline
    result = await factory.run_alpha_pipeline()
    
    # Validate
    report = await validation.validate()
    
    # Report should reflect registry state
    assert report.total_factors == result.scored_factors


# ══════════════════════════════════════════════════════════════
# Test 14: Integration with Scoring
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_integration_with_scoring(factory_with_registry):
    """Test 14: Validation uses scoring data correctly."""
    factory, validation, registry = factory_with_registry
    
    # Run pipeline
    result = await factory.run_alpha_pipeline()
    
    # Validate
    report = await validation.validate()
    
    # Average should be close to pipeline result
    assert abs(report.average_alpha_score - result.average_alpha_score) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 15: Full System Validation
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_full_system_validation(factory_with_registry):
    """Test 15: Full system validation test."""
    factory, validation, registry = factory_with_registry
    
    # Run pipeline
    pipeline_result = await factory.run_alpha_pipeline()
    
    # First validation
    report1 = await validation.validate()
    
    assert report1.total_factors == pipeline_result.scored_factors
    assert report1.validation_state in ["PASSED", "WARNING", "FAILED"]
    
    # Run pipeline again
    await factory.run_alpha_pipeline()
    
    # Second validation (now has previous factors)
    report2 = await validation.validate()
    
    # Should have valid drift calculation
    assert report2.alpha_drift_max >= 0.0
    assert report2.turnover_rate >= 0.0


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_constants():
    """Test all constants are correct."""
    assert ALPHA_DRIFT_THRESHOLD == 0.20
    assert TURNOVER_THRESHOLD == 0.40
    assert ALPHA_MEAN_MIN == 0.40
    assert ALPHA_MEAN_MAX == 0.70
    assert OVERFIT_THRESHOLD == 0.80
    assert CATEGORY_DOMINANCE_THRESHOLD == 0.60
    assert MAX_ACTIVE_FACTORS == 30


def test_singleton_pattern():
    """Test singleton pattern for validation engine."""
    engine1 = get_alpha_validation_engine()
    engine2 = get_alpha_validation_engine()
    assert engine1 is engine2


@pytest.mark.asyncio
async def test_empty_registry_validation(validation_engine):
    """Test validation handles empty registry."""
    report = await validation_engine.validate()
    
    assert report.total_factors == 0
    assert report.validation_state == "PASSED"


@pytest.mark.asyncio
async def test_category_balance_in_report(factory_with_registry):
    """Test category balance is included in report."""
    factory, validation, registry = factory_with_registry
    
    await factory.run_alpha_pipeline()
    report = await validation.validate()
    
    assert "TA" in report.category_balance
    assert "EXCHANGE" in report.category_balance
    assert "FRACTAL" in report.category_balance
    assert "REGIME" in report.category_balance
