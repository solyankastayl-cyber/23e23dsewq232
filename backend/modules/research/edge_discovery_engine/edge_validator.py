"""
PHASE 6.4 - Edge Validator
===========================
Validates discovered edges through Hypothesis, Scenario, and Monte Carlo engines.
"""

import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .edge_types import (
    EdgeCandidate, EdgeValidation, ValidationResult,
    DiscoveredEdge, EdgeStatus, VALIDATION_THRESHOLDS
)


class EdgeValidator:
    """
    Validates edge candidates using the research layer engines.
    """
    
    def __init__(self):
        self.thresholds = VALIDATION_THRESHOLDS
    
    async def validate(
        self,
        candidate: EdgeCandidate,
        run_hypothesis: bool = True,
        run_scenario: bool = True,
        run_monte_carlo: bool = True
    ) -> EdgeValidation:
        """
        Run full validation on edge candidate.
        """
        validation = EdgeValidation(edge_id=candidate.edge_id)
        
        # Run Hypothesis validation
        if run_hypothesis:
            validation = await self._validate_hypothesis(candidate, validation)
        
        # Run Scenario validation
        if run_scenario:
            validation = await self._validate_scenario(candidate, validation)
        
        # Run Monte Carlo validation
        if run_monte_carlo:
            validation = await self._validate_monte_carlo(candidate, validation)
        
        # Calculate overall result
        validation = self._calculate_overall(validation)
        validation.validated_at = datetime.now(timezone.utc)
        
        return validation
    
    async def _validate_hypothesis(
        self,
        candidate: EdgeCandidate,
        validation: EdgeValidation
    ) -> EdgeValidation:
        """
        Validate through Hypothesis Engine.
        Simulated for now - in production, would call real engine.
        """
        # Simulate hypothesis testing
        # In production: create hypothesis from candidate and run through engine
        
        # Use candidate's estimated metrics with some variance
        base_win_rate = candidate.win_rate_estimate
        noise = random.gauss(0, 0.05)
        
        win_rate = max(0.3, min(0.9, base_win_rate + noise))
        
        # Calculate profit factor
        if win_rate > 0.5:
            avg_win = abs(candidate.avg_return_estimate) * 1.1
            avg_loss = abs(candidate.avg_return_estimate) * 0.9
            profit_factor = (win_rate * avg_win) / ((1 - win_rate) * avg_loss)
        else:
            profit_factor = 0.8 + random.random() * 0.4
        
        validation.hypothesis_win_rate = win_rate
        validation.hypothesis_profit_factor = profit_factor
        
        # Check thresholds
        thresholds = self.thresholds["hypothesis"]
        if (
            win_rate >= thresholds["min_win_rate"] and
            profit_factor >= thresholds["min_profit_factor"] and
            candidate.sample_size >= thresholds["min_sample_size"]
        ):
            validation.hypothesis_result = ValidationResult.PASSED
        elif win_rate >= thresholds["min_win_rate"] * 0.9:
            validation.hypothesis_result = ValidationResult.PARTIAL
        else:
            validation.hypothesis_result = ValidationResult.FAILED
        
        return validation
    
    async def _validate_scenario(
        self,
        candidate: EdgeCandidate,
        validation: EdgeValidation
    ) -> EdgeValidation:
        """
        Validate through Scenario Engine.
        Tests edge robustness under stress.
        """
        # Simulate scenario testing
        # In production: run candidate through stress scenarios
        
        # Base metrics on candidate quality
        base_quality = candidate.win_rate_estimate * 0.7 + 0.3
        
        survival_rate = max(0.4, min(0.95, base_quality + random.gauss(0, 0.1)))
        stability_score = max(0.3, min(0.9, base_quality * 0.9 + random.gauss(0, 0.1)))
        
        validation.scenario_survival_rate = survival_rate
        validation.scenario_stability_score = stability_score
        
        # Check thresholds
        thresholds = self.thresholds["scenario"]
        if (
            survival_rate >= thresholds["min_survival_rate"] and
            stability_score >= thresholds["min_stability_score"]
        ):
            validation.scenario_result = ValidationResult.PASSED
        elif survival_rate >= thresholds["min_survival_rate"] * 0.85:
            validation.scenario_result = ValidationResult.PARTIAL
        else:
            validation.scenario_result = ValidationResult.FAILED
        
        return validation
    
    async def _validate_monte_carlo(
        self,
        candidate: EdgeCandidate,
        validation: EdgeValidation
    ) -> EdgeValidation:
        """
        Validate through Monte Carlo Engine.
        Analyzes risk distribution.
        """
        # Simulate Monte Carlo analysis
        # In production: run 1000+ simulations
        
        base_quality = candidate.win_rate_estimate * 0.6 + 0.4
        
        profit_prob = max(0.4, min(0.85, base_quality + random.gauss(0, 0.1)))
        risk_score = max(0.15, min(0.8, 1 - base_quality + random.gauss(0, 0.1)))
        
        validation.monte_carlo_profit_prob = profit_prob
        validation.monte_carlo_risk_score = risk_score
        
        # Check thresholds
        thresholds = self.thresholds["monte_carlo"]
        if (
            profit_prob >= thresholds["min_profit_prob"] and
            risk_score <= thresholds["max_risk_score"]
        ):
            validation.monte_carlo_result = ValidationResult.PASSED
        elif profit_prob >= thresholds["min_profit_prob"] * 0.9:
            validation.monte_carlo_result = ValidationResult.PARTIAL
        else:
            validation.monte_carlo_result = ValidationResult.FAILED
        
        return validation
    
    def _calculate_overall(self, validation: EdgeValidation) -> EdgeValidation:
        """Calculate overall validation result"""
        
        # Count results
        results = [
            validation.hypothesis_result,
            validation.scenario_result,
            validation.monte_carlo_result
        ]
        
        passed = sum(1 for r in results if r == ValidationResult.PASSED)
        partial = sum(1 for r in results if r == ValidationResult.PARTIAL)
        failed = sum(1 for r in results if r == ValidationResult.FAILED)
        
        # Calculate score
        score = (
            passed * 1.0 +
            partial * 0.5
        ) / len(results)
        
        validation.overall_score = score
        
        # Determine overall result
        if passed >= 2 and failed == 0:
            validation.overall_result = ValidationResult.PASSED
            validation.validation_notes = f"Passed {passed}/3 validations"
        elif passed >= 1 and failed <= 1:
            validation.overall_result = ValidationResult.PARTIAL
            validation.validation_notes = f"Partial: {passed} passed, {partial} partial, {failed} failed"
        else:
            validation.overall_result = ValidationResult.FAILED
            validation.validation_notes = f"Failed: only {passed} passed out of 3"
        
        return validation
    
    def create_discovered_edge(
        self,
        candidate: EdgeCandidate,
        validation: EdgeValidation
    ) -> Optional[DiscoveredEdge]:
        """
        Create DiscoveredEdge from validated candidate.
        Only if validation passed.
        """
        if validation.overall_result == ValidationResult.FAILED:
            return None
        
        # Calculate final metrics
        win_rate = validation.hypothesis_win_rate
        profit_factor = validation.hypothesis_profit_factor
        
        # Estimate expectancy
        avg_return = candidate.avg_return_estimate
        expectancy = (win_rate * avg_return) - ((1 - win_rate) * avg_return * 0.8)
        
        # Estimate Sharpe (simplified)
        sharpe = (win_rate - 0.5) * 2 + profit_factor * 0.3
        
        # Risk metrics from Monte Carlo
        max_drawdown = (1 - validation.monte_carlo_profit_prob) * 0.4
        risk_of_ruin = validation.monte_carlo_risk_score * 0.3
        
        # Confidence score
        confidence = validation.overall_score * 0.8 + (candidate.sample_size / 200) * 0.2
        confidence = min(0.95, confidence)
        
        return DiscoveredEdge(
            edge_id=candidate.edge_id,
            name=candidate.name,
            description=candidate.description,
            category=candidate.category,
            pattern_types=candidate.pattern_types,
            feature_conditions=candidate.feature_conditions,
            expected_direction=candidate.expected_direction,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            risk_of_ruin=risk_of_ruin,
            risk_score=validation.monte_carlo_risk_score,
            confidence_score=confidence,
            sample_size=candidate.sample_size,
            validation=validation,
            status=EdgeStatus.VALIDATED if validation.overall_result == ValidationResult.PASSED else EdgeStatus.CANDIDATE,
            discovered_at=candidate.discovered_at,
            validated_at=validation.validated_at
        )
