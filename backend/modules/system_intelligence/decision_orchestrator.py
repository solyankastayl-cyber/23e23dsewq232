"""
PHASE 12.5 - Decision Orchestrator
====================================
Central brain for system-level decisions.

Makes decisions:
- Reduce risk
- Increase allocation
- Switch regime
- Disable/enable strategies
- Pause/resume trading
- Trigger research
- Emergency exit
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone

from .system_types import (
    SystemAction, SystemDecision, GlobalMarketState,
    SystemHealthState, RegimeProfile, UnifiedSystemSnapshot,
    DEFAULT_SYSTEM_CONFIG
)
from .global_market_state_engine import GlobalMarketStateEngine
from .regime_switching_engine import RegimeSwitchingEngine
from .system_health_engine import SystemHealthEngine
from .autonomous_research_loop import AutonomousResearchLoop


class DecisionOrchestrator:
    """
    Decision Orchestrator - Central Brain
    
    Coordinates all system intelligence components
    and makes top-level decisions for the entire system.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_SYSTEM_CONFIG
        
        # Core engines
        self.market_state_engine = GlobalMarketStateEngine(config)
        self.regime_engine = RegimeSwitchingEngine(config)
        self.health_engine = SystemHealthEngine(config)
        self.research_loop = AutonomousResearchLoop(config)
        
        # Decision tracking
        self.decisions: List[SystemDecision] = []
        self.max_decisions = 200
        self._decision_counter = 0
        
        # System state
        self.trading_paused = False
        self.emergency_mode = False
    
    def evaluate_system(
        self,
        volatility_data: Optional[Dict] = None,
        liquidity_data: Optional[Dict] = None,
        correlation_data: Optional[Dict] = None,
        microstructure_data: Optional[Dict] = None,
        portfolio_data: Optional[Dict] = None,
        adaptive_data: Optional[Dict] = None
    ) -> UnifiedSystemSnapshot:
        """
        Evaluate entire system and generate unified snapshot.
        
        Args:
            Various data from different system components
            
        Returns:
            UnifiedSystemSnapshot with complete system state
        """
        now = datetime.now(timezone.utc)
        
        # Get market state
        market_snapshot = self.market_state_engine.analyze_market_state(
            volatility_data, liquidity_data, correlation_data, microstructure_data
        )
        
        # Get system health
        health_snapshot = self.health_engine.analyze_health(
            signal_metrics=adaptive_data.get("signal_quality") if adaptive_data else None,
            portfolio_metrics=portfolio_data,
            edge_metrics=adaptive_data.get("edge_metrics") if adaptive_data else None
        )
        
        # Evaluate regime switch
        regime_rec = self.regime_engine.evaluate_regime_switch(
            market_snapshot.market_state,
            market_snapshot.state_confidence,
            health_snapshot.health_score,
            health_snapshot.edge_strength
        )
        
        # Check research loop
        research_status = self.research_loop._get_current_status()
        
        # Extract portfolio metrics
        portfolio_risk = portfolio_data.get("risk_budget_used", 0.6) if portfolio_data else 0.6
        capital_deployment = portfolio_data.get("capital_deployment", 0.7) if portfolio_data else 0.7
        
        # Extract adaptive metrics
        if adaptive_data:
            edges_strengthening = adaptive_data.get("edges_strengthening", 2)
            edges_stable = adaptive_data.get("edges_stable", 2)
            edges_decaying = adaptive_data.get("edges_decaying", 1)
            pending_adaptations = adaptive_data.get("pending_adaptations", 0)
            in_cooldown = adaptive_data.get("in_cooldown", False)
            active_strategies = adaptive_data.get("active_strategies", 4)
            disabled_strategies = adaptive_data.get("disabled_strategies", 0)
        else:
            edges_strengthening = 2
            edges_stable = 2
            edges_decaying = 1
            pending_adaptations = 0
            in_cooldown = False
            active_strategies = 4
            disabled_strategies = 0
        
        # Generate any necessary decisions
        pending_actions = self._generate_decisions(
            market_snapshot, health_snapshot, regime_rec
        )
        
        return UnifiedSystemSnapshot(
            timestamp=now,
            market_state=market_snapshot.market_state,
            system_health=health_snapshot.health_score,
            health_state=health_snapshot.health_state,
            portfolio_risk=portfolio_risk,
            capital_deployment=capital_deployment,
            active_strategies=active_strategies,
            disabled_strategies=disabled_strategies,
            edges_strengthening=edges_strengthening,
            edges_stable=edges_stable,
            edges_decaying=edges_decaying,
            pending_adaptations=pending_adaptations,
            in_cooldown=in_cooldown,
            research_loop_active=self.research_loop.loop_running,
            pending_actions=pending_actions
        )
    
    def _generate_decisions(
        self,
        market_snapshot,
        health_snapshot,
        regime_rec
    ) -> int:
        """Generate decisions based on current state."""
        now = datetime.now(timezone.utc)
        pending = 0
        
        # Emergency exit check
        if health_snapshot.health_score < self.config["emergency_exit_threshold"]:
            decision = self._create_decision(
                SystemAction.EMERGENCY_EXIT,
                "ALL_POSITIONS",
                {"reason": "Health below emergency threshold"},
                f"Health score {health_snapshot.health_score:.2%}",
                {"health_score": health_snapshot.health_score},
                confidence=0.95,
                impact=-0.5,
                risk="HIGH"
            )
            self.decisions.append(decision)
            self.emergency_mode = True
            pending += 1
        
        # Pause trading check
        elif health_snapshot.health_score < self.config["pause_trading_health_threshold"]:
            decision = self._create_decision(
                SystemAction.PAUSE_TRADING,
                "SYSTEM",
                {"reason": "Health below trading threshold"},
                f"Health score {health_snapshot.health_score:.2%}",
                {"health_score": health_snapshot.health_score},
                confidence=0.85,
                impact=-0.2,
                risk="MEDIUM"
            )
            self.decisions.append(decision)
            self.trading_paused = True
            pending += 1
        
        # Regime switch check
        elif regime_rec.recommended_profile != regime_rec.current_profile:
            if regime_rec.execution_timing not in ["BLOCKED_COOLDOWN", "N/A"]:
                decision = self._create_decision(
                    SystemAction.SWITCH_REGIME,
                    regime_rec.recommended_profile.value,
                    {"from": regime_rec.current_profile.value, "to": regime_rec.recommended_profile.value},
                    regime_rec.trigger_reason,
                    {"confidence": regime_rec.confidence, "adjustments": regime_rec.strategy_adjustments},
                    confidence=regime_rec.confidence,
                    impact=0.1,
                    risk="LOW"
                )
                self.decisions.append(decision)
                pending += 1
        
        # Risk reduction check
        if health_snapshot.recommended_action == SystemAction.REDUCE_RISK:
            decision = self._create_decision(
                SystemAction.REDUCE_RISK,
                "PORTFOLIO",
                {"reduction_pct": 0.2},
                "Health degradation",
                {"issues": health_snapshot.active_issues[:3]},
                confidence=0.75,
                impact=-0.1,
                risk="LOW"
            )
            self.decisions.append(decision)
            pending += 1
        
        # Research trigger check
        if self.research_loop.should_start_new_cycle():
            decision = self._create_decision(
                SystemAction.TRIGGER_RESEARCH,
                "RESEARCH_LOOP",
                {"cycle_type": "scheduled"},
                "Research interval elapsed",
                {},
                confidence=0.9,
                impact=0.05,
                risk="NONE"
            )
            self.decisions.append(decision)
            pending += 1
        
        # Trim decisions list
        if len(self.decisions) > self.max_decisions:
            self.decisions = self.decisions[-self.max_decisions:]
        
        return pending
    
    def _create_decision(
        self,
        action: SystemAction,
        target: str,
        parameters: Dict,
        trigger: str,
        evidence: Dict,
        confidence: float,
        impact: float,
        risk: str
    ) -> SystemDecision:
        """Create a system decision."""
        self._decision_counter += 1
        
        return SystemDecision(
            timestamp=datetime.now(timezone.utc),
            decision_id=f"decision_{self._decision_counter}",
            action=action,
            target=target,
            parameters=parameters,
            trigger=trigger,
            evidence=evidence,
            confidence=confidence,
            expected_impact=impact,
            risk_assessment=risk,
            executed=False
        )
    
    def execute_decision(self, decision_id: str) -> Dict:
        """Execute a pending decision."""
        for decision in self.decisions:
            if decision.decision_id == decision_id and not decision.executed:
                # Execute based on action type
                if decision.action == SystemAction.SWITCH_REGIME:
                    profile = RegimeProfile(decision.target)
                    self.regime_engine.apply_switch(profile)
                    decision.executed = True
                    decision.execution_result = "Regime switched successfully"
                
                elif decision.action == SystemAction.TRIGGER_RESEARCH:
                    self.research_loop.start_research_cycle([], {})
                    decision.executed = True
                    decision.execution_result = "Research cycle started"
                
                elif decision.action == SystemAction.PAUSE_TRADING:
                    self.trading_paused = True
                    decision.executed = True
                    decision.execution_result = "Trading paused"
                
                elif decision.action == SystemAction.RESUME_TRADING:
                    self.trading_paused = False
                    decision.executed = True
                    decision.execution_result = "Trading resumed"
                
                else:
                    decision.executed = True
                    decision.execution_result = "Executed (simulated)"
                
                return {
                    "executed": True,
                    "decision_id": decision_id,
                    "action": decision.action.value,
                    "result": decision.execution_result
                }
        
        return {"executed": False, "reason": "Decision not found or already executed"}
    
    def get_pending_decisions(self) -> List[Dict]:
        """Get all pending decisions."""
        return [
            d.to_dict() for d in self.decisions
            if not d.executed
        ]
    
    def get_orchestrator_summary(self) -> Dict:
        """Get summary of orchestrator state."""
        return {
            "trading_paused": self.trading_paused,
            "emergency_mode": self.emergency_mode,
            "current_regime": self.regime_engine.current_profile.value,
            "pending_decisions": len([d for d in self.decisions if not d.executed]),
            "total_decisions": len(self.decisions),
            "market_state": self.market_state_engine.get_state_summary(),
            "health": self.health_engine.get_health_summary(),
            "regime": self.regime_engine.get_regime_summary(),
            "research_loop": self.research_loop.get_loop_summary()
        }
