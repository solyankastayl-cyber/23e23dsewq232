"""
PHASE 12.4 - Autonomous Research Loop
======================================
Continuous research machine that completes the learning cycle.

Loop phases:
1. Detect edge decay
2. Generate hypothesis
3. Run scenario tests
4. Run Monte Carlo
5. Propose adaptation
6. Shadow test
7. Deploy
"""

import random
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta
from enum import Enum

from .system_types import (
    ResearchLoopPhase, ResearchLoopStatus, DEFAULT_SYSTEM_CONFIG
)


class AutonomousResearchLoop:
    """
    Autonomous Research Loop
    
    Continuously runs the research cycle to discover,
    validate, and deploy new trading edges.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_SYSTEM_CONFIG
        
        # Loop state
        self.current_phase = ResearchLoopPhase.IDLE
        self.phase_progress = 0.0
        self.current_task = "Idle"
        self.target_edge: Optional[str] = None
        
        # Counters
        self.hypotheses_generated = 0
        self.scenarios_tested = 0
        self.montecarlo_runs = 0
        self.adaptations_proposed = 0
        self.successful_deployments = 0
        self.failed_proposals = 0
        
        # History
        self.loop_history: List[ResearchLoopStatus] = []
        self.max_history = 100
        
        # Last run tracking
        self.last_loop_start: Optional[datetime] = None
        self.loop_running = False
    
    def start_research_cycle(
        self,
        decaying_edges: List[str],
        edge_metrics: Dict[str, Dict]
    ) -> ResearchLoopStatus:
        """
        Start a new research cycle.
        
        Args:
            decaying_edges: List of edges showing decay
            edge_metrics: Metrics for each edge
            
        Returns:
            ResearchLoopStatus
        """
        now = datetime.now(timezone.utc)
        
        if self.loop_running:
            return self._get_current_status()
        
        # Select target edge
        if decaying_edges:
            self.target_edge = decaying_edges[0]  # Prioritize first
        else:
            self.target_edge = "exploratory_research"
        
        self.loop_running = True
        self.last_loop_start = now
        self.current_phase = ResearchLoopPhase.DETECTING_DECAY
        self.phase_progress = 0.0
        self.current_task = f"Analyzing edge: {self.target_edge}"
        
        return self._get_current_status()
    
    def advance_loop(self) -> ResearchLoopStatus:
        """
        Advance the research loop to next phase.
        
        Returns:
            ResearchLoopStatus after advancement
        """
        if not self.loop_running:
            return self._get_current_status()
        
        # Phase transitions
        transitions = {
            ResearchLoopPhase.DETECTING_DECAY: self._phase_generate_hypothesis,
            ResearchLoopPhase.GENERATING_HYPOTHESIS: self._phase_run_scenarios,
            ResearchLoopPhase.RUNNING_SCENARIOS: self._phase_run_montecarlo,
            ResearchLoopPhase.RUNNING_MONTECARLO: self._phase_propose_adaptation,
            ResearchLoopPhase.PROPOSING_ADAPTATION: self._phase_shadow_test,
            ResearchLoopPhase.SHADOW_TESTING: self._phase_deploy,
            ResearchLoopPhase.DEPLOYING: self._phase_complete,
            ResearchLoopPhase.COMPLETED: self._phase_idle,
        }
        
        handler = transitions.get(self.current_phase, self._phase_idle)
        handler()
        
        return self._get_current_status()
    
    def _phase_generate_hypothesis(self):
        """Generate hypotheses for improvement."""
        self.current_phase = ResearchLoopPhase.GENERATING_HYPOTHESIS
        self.current_task = "Generating improvement hypotheses"
        self.phase_progress = 0.2
        
        # Simulate hypothesis generation
        num_hypotheses = random.randint(2, self.config["max_hypotheses_per_cycle"])
        self.hypotheses_generated += num_hypotheses
    
    def _phase_run_scenarios(self):
        """Run scenario tests."""
        self.current_phase = ResearchLoopPhase.RUNNING_SCENARIOS
        self.current_task = "Testing hypotheses against scenarios"
        self.phase_progress = 0.4
        
        # Simulate scenario testing
        num_scenarios = random.randint(
            self.config["min_scenarios_for_proposal"],
            self.config["min_scenarios_for_proposal"] * 2
        )
        self.scenarios_tested += num_scenarios
    
    def _phase_run_montecarlo(self):
        """Run Monte Carlo simulations."""
        self.current_phase = ResearchLoopPhase.RUNNING_MONTECARLO
        self.current_task = "Running Monte Carlo simulations"
        self.phase_progress = 0.55
        
        # Simulate Monte Carlo
        num_runs = random.randint(100, 500)
        self.montecarlo_runs += num_runs
    
    def _phase_propose_adaptation(self):
        """Propose adaptation based on research."""
        self.current_phase = ResearchLoopPhase.PROPOSING_ADAPTATION
        self.current_task = "Evaluating research results"
        self.phase_progress = 0.7
        
        # Decide if we have a viable proposal
        # In real system: based on scenario + MC results
        if random.random() > 0.3:  # 70% chance of viable proposal
            self.adaptations_proposed += 1
        else:
            self.failed_proposals += 1
            self.current_phase = ResearchLoopPhase.COMPLETED
            self.current_task = "Research cycle completed - no viable adaptation"
            self.phase_progress = 1.0
    
    def _phase_shadow_test(self):
        """Run shadow testing."""
        if self.current_phase == ResearchLoopPhase.COMPLETED:
            return  # Already completed without proposal
        
        self.current_phase = ResearchLoopPhase.SHADOW_TESTING
        self.current_task = "Shadow testing proposed adaptation"
        self.phase_progress = 0.85
    
    def _phase_deploy(self):
        """Deploy successful adaptation."""
        self.current_phase = ResearchLoopPhase.DEPLOYING
        self.current_task = "Deploying validated adaptation"
        self.phase_progress = 0.95
        
        # Simulate deployment success
        if random.random() > 0.2:  # 80% success rate
            self.successful_deployments += 1
        else:
            self.failed_proposals += 1
    
    def _phase_complete(self):
        """Complete the loop."""
        self.current_phase = ResearchLoopPhase.COMPLETED
        self.current_task = "Research cycle completed"
        self.phase_progress = 1.0
        
        # Save to history
        self.loop_history.append(self._get_current_status())
        if len(self.loop_history) > self.max_history:
            self.loop_history = self.loop_history[-self.max_history:]
    
    def _phase_idle(self):
        """Return to idle state."""
        self.current_phase = ResearchLoopPhase.IDLE
        self.current_task = "Idle - awaiting next cycle"
        self.phase_progress = 0.0
        self.target_edge = None
        self.loop_running = False
    
    def _get_current_status(self) -> ResearchLoopStatus:
        """Get current loop status."""
        return ResearchLoopStatus(
            timestamp=datetime.now(timezone.utc),
            phase=self.current_phase,
            progress=self.phase_progress,
            current_task=self.current_task,
            target_edge=self.target_edge,
            hypotheses_generated=self.hypotheses_generated,
            scenarios_tested=self.scenarios_tested,
            montecarlo_runs=self.montecarlo_runs,
            adaptations_proposed=self.adaptations_proposed,
            successful_deployments=self.successful_deployments,
            failed_proposals=self.failed_proposals
        )
    
    def should_start_new_cycle(self) -> bool:
        """Check if new research cycle should start."""
        if self.loop_running:
            return False
        
        if self.last_loop_start is None:
            return True
        
        hours_since = (datetime.now(timezone.utc) - self.last_loop_start).total_seconds() / 3600
        interval = self.config["research_loop_interval_hours"]
        
        return hours_since >= interval
    
    def get_loop_summary(self) -> Dict:
        """Get summary of research loop."""
        return {
            "current_phase": self.current_phase.value,
            "progress": round(self.phase_progress, 3),
            "target_edge": self.target_edge,
            "loop_running": self.loop_running,
            "stats": {
                "hypotheses_generated": self.hypotheses_generated,
                "scenarios_tested": self.scenarios_tested,
                "montecarlo_runs": self.montecarlo_runs,
                "adaptations_proposed": self.adaptations_proposed,
                "successful_deployments": self.successful_deployments,
                "failed_proposals": self.failed_proposals
            },
            "success_rate": round(
                self.successful_deployments / max(1, self.adaptations_proposed), 3
            )
        }
