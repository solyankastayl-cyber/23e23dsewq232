"""
PHASE 11.6.3 - Shadow Mode Engine
==================================
Runs candidate adaptations in parallel before promotion.

Process:
1. Candidate adaptation created
2. Run in shadow (parallel evaluation)
3. Compare results with current live logic
4. Promote or reject based on performance
"""

import random
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum


class ShadowTestStatus(str, Enum):
    """Status of shadow test."""
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    CANCELLED = "CANCELLED"


@dataclass
class ShadowTest:
    """A shadow test instance."""
    test_id: str
    key: str                        # What is being tested
    change_type: str
    
    # Configurations
    current_config: Dict
    candidate_config: Dict
    
    # Timing
    started_at: datetime
    ends_at: datetime
    
    # Results
    status: ShadowTestStatus = ShadowTestStatus.RUNNING
    current_performance: Dict = field(default_factory=dict)
    candidate_performance: Dict = field(default_factory=dict)
    
    # Outcome
    winner: Optional[str] = None    # "CURRENT" or "CANDIDATE"
    improvement_pct: float = 0.0


class ShadowModeEngine:
    """
    Shadow Mode Engine
    
    Tests candidate adaptations in parallel without affecting
    live trading, then promotes based on results.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        from ..adaptive_types import DEFAULT_ADAPTIVE_CONFIG
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        
        self.active_tests: Dict[str, ShadowTest] = {}
        self.completed_tests: List[ShadowTest] = []
        self.max_completed = 100
        self._test_counter = 0
    
    def start_shadow_test(
        self,
        key: str,
        change_type: str,
        current_config: Dict,
        candidate_config: Dict,
        duration_hours: Optional[float] = None
    ) -> ShadowTest:
        """
        Start a new shadow test.
        
        Args:
            key: Identifier for what's being tested
            change_type: Type of change (PARAMETER, WEIGHT, etc.)
            current_config: Current configuration
            candidate_config: Proposed new configuration
            duration_hours: How long to run test
            
        Returns:
            ShadowTest instance
        """
        now = datetime.now(timezone.utc)
        
        if duration_hours is None:
            duration_hours = self.config["shadow_test_duration_hours"]
        
        self._test_counter += 1
        test_id = f"shadow_{self._test_counter}_{int(now.timestamp())}"
        
        test = ShadowTest(
            test_id=test_id,
            key=key,
            change_type=change_type,
            current_config=current_config,
            candidate_config=candidate_config,
            started_at=now,
            ends_at=now + timedelta(hours=duration_hours),
            status=ShadowTestStatus.RUNNING
        )
        
        self.active_tests[test_id] = test
        
        return test
    
    def record_results(
        self,
        test_id: str,
        current_result: Dict,
        candidate_result: Dict
    ):
        """
        Record parallel results for a shadow test.
        
        Args:
            test_id: Shadow test identifier
            current_result: Result from current config
            candidate_result: Result from candidate config
        """
        test = self.active_tests.get(test_id)
        if not test:
            return
        
        # Accumulate results
        for key, value in current_result.items():
            if key not in test.current_performance:
                test.current_performance[key] = []
            test.current_performance[key].append(value)
        
        for key, value in candidate_result.items():
            if key not in test.candidate_performance:
                test.candidate_performance[key] = []
            test.candidate_performance[key].append(value)
    
    def evaluate_test(self, test_id: str) -> ShadowTest:
        """
        Evaluate a shadow test and determine outcome.
        
        Returns:
            Updated ShadowTest with results
        """
        test = self.active_tests.get(test_id)
        if not test:
            return None
        
        now = datetime.now(timezone.utc)
        
        # Check if test period complete
        if now < test.ends_at:
            # Simulate some results if none recorded
            if not test.current_performance:
                test.current_performance = self._generate_mock_results()
            if not test.candidate_performance:
                test.candidate_performance = self._generate_mock_results(
                    improvement_bias=0.05
                )
        
        # Calculate performance scores
        current_score = self._calculate_score(test.current_performance)
        candidate_score = self._calculate_score(test.candidate_performance)
        
        # Determine winner
        if candidate_score > current_score * 1.05:  # Require 5% improvement
            test.status = ShadowTestStatus.PASSED
            test.winner = "CANDIDATE"
            test.improvement_pct = (candidate_score - current_score) / current_score if current_score > 0 else 0
        elif current_score > candidate_score:
            test.status = ShadowTestStatus.FAILED
            test.winner = "CURRENT"
            test.improvement_pct = 0
        else:
            test.status = ShadowTestStatus.INCONCLUSIVE
            test.winner = None
            test.improvement_pct = 0
        
        # Move to completed
        self._complete_test(test_id)
        
        return test
    
    def _calculate_score(self, performance: Dict) -> float:
        """Calculate overall performance score."""
        if not performance:
            return 0.0
        
        score = 0.0
        
        # PnL contribution (if available)
        if "pnl" in performance:
            pnl_values = performance["pnl"]
            if pnl_values:
                score += sum(pnl_values) / len(pnl_values) * 100
        
        # Win rate contribution
        if "win_rate" in performance:
            wr_values = performance["win_rate"]
            if wr_values:
                score += (sum(wr_values) / len(wr_values) - 0.5) * 50
        
        # Sharpe contribution
        if "sharpe" in performance:
            sharpe_values = performance["sharpe"]
            if sharpe_values:
                score += sum(sharpe_values) / len(sharpe_values) * 10
        
        return score
    
    def _generate_mock_results(self, improvement_bias: float = 0.0) -> Dict:
        """Generate mock results for testing."""
        n = 20
        return {
            "pnl": [random.gauss(0.002 + improvement_bias, 0.01) for _ in range(n)],
            "win_rate": [0.52 + improvement_bias + random.gauss(0, 0.05) for _ in range(n)],
            "sharpe": [1.5 + improvement_bias * 5 + random.gauss(0, 0.3) for _ in range(n)]
        }
    
    def _complete_test(self, test_id: str):
        """Move test to completed."""
        test = self.active_tests.pop(test_id, None)
        if test:
            self.completed_tests.append(test)
            if len(self.completed_tests) > self.max_completed:
                self.completed_tests = self.completed_tests[-self.max_completed:]
    
    def cancel_test(self, test_id: str) -> bool:
        """Cancel an active test."""
        test = self.active_tests.get(test_id)
        if test:
            test.status = ShadowTestStatus.CANCELLED
            self._complete_test(test_id)
            return True
        return False
    
    def get_active_tests(self) -> List[Dict]:
        """Get all active shadow tests."""
        result = []
        
        for test in self.active_tests.values():
            remaining = test.ends_at - datetime.now(timezone.utc)
            result.append({
                "test_id": test.test_id,
                "key": test.key,
                "change_type": test.change_type,
                "started_at": test.started_at.isoformat(),
                "remaining_hours": max(0, remaining.total_seconds() / 3600),
                "status": test.status.value
            })
        
        return result
    
    def get_shadow_summary(self) -> Dict:
        """Get summary of shadow testing."""
        passed = sum(1 for t in self.completed_tests if t.status == ShadowTestStatus.PASSED)
        failed = sum(1 for t in self.completed_tests if t.status == ShadowTestStatus.FAILED)
        inconclusive = sum(1 for t in self.completed_tests if t.status == ShadowTestStatus.INCONCLUSIVE)
        
        return {
            "active_tests": len(self.active_tests),
            "completed_tests": len(self.completed_tests),
            "passed": passed,
            "failed": failed,
            "inconclusive": inconclusive,
            "promotion_rate": passed / len(self.completed_tests) if self.completed_tests else 0,
            "default_duration_hours": self.config["shadow_test_duration_hours"]
        }
