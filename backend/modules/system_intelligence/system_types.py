"""
PHASE 12 - System Intelligence Types
=====================================
Core data types for system-level intelligence.

Provides unified view of:
- Global market state
- System health
- Regime management
- Autonomous decisions
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class GlobalMarketState(str, Enum):
    """Global market state classification"""
    TRENDING = "TRENDING"               # Clear directional movement
    RANGING = "RANGING"                 # Sideways consolidation
    HIGH_VOLATILITY = "HIGH_VOLATILITY" # Elevated volatility regime
    LOW_VOLATILITY = "LOW_VOLATILITY"   # Compressed volatility
    LOW_LIQUIDITY = "LOW_LIQUIDITY"     # Thin market conditions
    MACRO_DOMINANT = "MACRO_DOMINANT"   # Macro events driving price
    CRYPTO_NATIVE = "CRYPTO_NATIVE"     # Crypto-specific dynamics
    RISK_OFF = "RISK_OFF"               # Flight to safety
    RISK_ON = "RISK_ON"                 # Risk appetite high
    TRANSITION = "TRANSITION"           # Regime changing


class SystemHealthState(str, Enum):
    """System health state"""
    OPTIMAL = "OPTIMAL"                 # Everything working well
    HEALTHY = "HEALTHY"                 # Minor issues, stable
    DEGRADED = "DEGRADED"               # Some components struggling
    WARNING = "WARNING"                 # Significant issues
    CRITICAL = "CRITICAL"               # Major problems
    EMERGENCY = "EMERGENCY"             # Immediate action needed


class RegimeProfile(str, Enum):
    """Strategy regime profile"""
    AGGRESSIVE_TREND = "AGGRESSIVE_TREND"
    CONSERVATIVE_TREND = "CONSERVATIVE_TREND"
    MEAN_REVERSION = "MEAN_REVERSION"
    VOLATILITY_HARVEST = "VOLATILITY_HARVEST"
    DEFENSIVE = "DEFENSIVE"
    BALANCED = "BALANCED"
    RESEARCH_ONLY = "RESEARCH_ONLY"


class SystemAction(str, Enum):
    """System-level actions"""
    NO_ACTION = "NO_ACTION"
    REDUCE_RISK = "REDUCE_RISK"
    INCREASE_ALLOCATION = "INCREASE_ALLOCATION"
    SWITCH_REGIME = "SWITCH_REGIME"
    DISABLE_STRATEGY = "DISABLE_STRATEGY"
    ENABLE_STRATEGY = "ENABLE_STRATEGY"
    PAUSE_TRADING = "PAUSE_TRADING"
    RESUME_TRADING = "RESUME_TRADING"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"
    TRIGGER_RESEARCH = "TRIGGER_RESEARCH"


class ResearchLoopPhase(str, Enum):
    """Autonomous research loop phase"""
    IDLE = "IDLE"
    DETECTING_DECAY = "DETECTING_DECAY"
    GENERATING_HYPOTHESIS = "GENERATING_HYPOTHESIS"
    RUNNING_SCENARIOS = "RUNNING_SCENARIOS"
    RUNNING_MONTECARLO = "RUNNING_MONTECARLO"
    PROPOSING_ADAPTATION = "PROPOSING_ADAPTATION"
    SHADOW_TESTING = "SHADOW_TESTING"
    DEPLOYING = "DEPLOYING"
    COMPLETED = "COMPLETED"


@dataclass
class MarketStateSnapshot:
    """Global market state analysis"""
    timestamp: datetime
    
    # Primary state
    market_state: GlobalMarketState
    state_confidence: float           # 0-1
    
    # Contributing factors
    volatility_regime: str
    liquidity_regime: str
    correlation_regime: str
    microstructure_regime: str
    
    # Metrics
    market_volatility: float
    avg_correlation: float
    liquidity_score: float
    flow_pressure: str
    
    # Trend analysis
    trend_strength: float
    trend_direction: str
    
    # Duration
    state_duration_hours: float = 0
    previous_state: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "marketState": self.market_state.value,
            "stateConfidence": round(self.state_confidence, 3),
            "volatilityRegime": self.volatility_regime,
            "liquidityRegime": self.liquidity_regime,
            "correlationRegime": self.correlation_regime,
            "microstructureRegime": self.microstructure_regime,
            "marketVolatility": round(self.market_volatility, 4),
            "avgCorrelation": round(self.avg_correlation, 4),
            "liquidityScore": round(self.liquidity_score, 3),
            "flowPressure": self.flow_pressure,
            "trendStrength": round(self.trend_strength, 3),
            "trendDirection": self.trend_direction,
            "stateDurationHours": round(self.state_duration_hours, 1),
            "previousState": self.previous_state
        }


@dataclass
class SystemHealthSnapshot:
    """System health analysis"""
    timestamp: datetime
    
    # Overall health
    health_state: SystemHealthState
    health_score: float               # 0-1
    
    # Component health
    signal_quality: float             # 0-1
    execution_quality: float          # 0-1
    portfolio_stability: float        # 0-1
    risk_budget_usage: float          # 0-1
    edge_strength: float              # 0-1
    
    # Issues
    active_issues: List[str] = field(default_factory=list)
    critical_issues: int = 0
    
    # Recommendations
    recommended_action: SystemAction = SystemAction.NO_ACTION
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "healthState": self.health_state.value,
            "healthScore": round(self.health_score, 3),
            "signalQuality": round(self.signal_quality, 3),
            "executionQuality": round(self.execution_quality, 3),
            "portfolioStability": round(self.portfolio_stability, 3),
            "riskBudgetUsage": round(self.risk_budget_usage, 3),
            "edgeStrength": round(self.edge_strength, 3),
            "activeIssues": self.active_issues,
            "criticalIssues": self.critical_issues,
            "recommendedAction": self.recommended_action.value
        }


@dataclass
class RegimeSwitchRecommendation:
    """Regime switching recommendation"""
    timestamp: datetime
    
    # Current vs recommended
    current_profile: RegimeProfile
    recommended_profile: RegimeProfile
    
    # Reasoning
    trigger_reason: str
    supporting_signals: List[str]
    
    # Strategy adjustments
    strategy_adjustments: Dict[str, float]  # strategy -> weight change
    
    # Confidence
    confidence: float
    urgency: float
    
    # Timing
    execution_timing: str
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "currentProfile": self.current_profile.value,
            "recommendedProfile": self.recommended_profile.value,
            "triggerReason": self.trigger_reason,
            "supportingSignals": self.supporting_signals,
            "strategyAdjustments": self.strategy_adjustments,
            "confidence": round(self.confidence, 3),
            "urgency": round(self.urgency, 3),
            "executionTiming": self.execution_timing
        }


@dataclass
class ResearchLoopStatus:
    """Autonomous research loop status"""
    timestamp: datetime
    
    # Current phase
    phase: ResearchLoopPhase
    progress: float                   # 0-1
    
    # Current task
    current_task: str
    target_edge: Optional[str] = None
    
    # Results
    hypotheses_generated: int = 0
    scenarios_tested: int = 0
    montecarlo_runs: int = 0
    adaptations_proposed: int = 0
    
    # Outcome
    successful_deployments: int = 0
    failed_proposals: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "phase": self.phase.value,
            "progress": round(self.progress, 3),
            "currentTask": self.current_task,
            "targetEdge": self.target_edge,
            "hypothesesGenerated": self.hypotheses_generated,
            "scenariosTested": self.scenarios_tested,
            "montecarloRuns": self.montecarlo_runs,
            "adaptationsProposed": self.adaptations_proposed,
            "successfulDeployments": self.successful_deployments,
            "failedProposals": self.failed_proposals
        }


@dataclass
class SystemDecision:
    """System-level decision"""
    timestamp: datetime
    decision_id: str
    
    # Decision
    action: SystemAction
    target: str
    parameters: Dict
    
    # Context
    trigger: str
    evidence: Dict
    
    # Assessment
    confidence: float
    expected_impact: float
    risk_assessment: str
    
    # Status
    executed: bool = False
    execution_result: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "decision_id": self.decision_id,
            "action": self.action.value,
            "target": self.target,
            "parameters": self.parameters,
            "trigger": self.trigger,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 3),
            "expectedImpact": round(self.expected_impact, 4),
            "riskAssessment": self.risk_assessment,
            "executed": self.executed,
            "executionResult": self.execution_result
        }


@dataclass
class UnifiedSystemSnapshot:
    """Complete system state snapshot"""
    timestamp: datetime
    
    # Market state
    market_state: GlobalMarketState
    
    # System health
    system_health: float
    health_state: SystemHealthState
    
    # Portfolio
    portfolio_risk: float
    capital_deployment: float
    
    # Strategies
    active_strategies: int
    disabled_strategies: int
    
    # Edges
    edges_strengthening: int
    edges_stable: int
    edges_decaying: int
    
    # Adaptive
    pending_adaptations: int
    in_cooldown: bool
    
    # Research
    research_loop_active: bool
    
    # Actions
    pending_actions: int
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "marketState": self.market_state.value,
            "systemHealth": round(self.system_health, 3),
            "healthState": self.health_state.value,
            "portfolioRisk": round(self.portfolio_risk, 4),
            "capitalDeployment": round(self.capital_deployment, 3),
            "activeStrategies": self.active_strategies,
            "disabledStrategies": self.disabled_strategies,
            "edgesStrengthening": self.edges_strengthening,
            "edgesStable": self.edges_stable,
            "edgesDecaying": self.edges_decaying,
            "pendingAdaptations": self.pending_adaptations,
            "inCooldown": self.in_cooldown,
            "researchLoopActive": self.research_loop_active,
            "pendingActions": self.pending_actions
        }


# Default configuration
DEFAULT_SYSTEM_CONFIG = {
    # Market state thresholds
    "high_volatility_threshold": 0.25,
    "low_volatility_threshold": 0.08,
    "low_liquidity_threshold": 0.3,
    "trending_threshold": 0.6,
    
    # Health thresholds
    "health_optimal_threshold": 0.85,
    "health_healthy_threshold": 0.70,
    "health_degraded_threshold": 0.50,
    "health_warning_threshold": 0.30,
    
    # Regime switching
    "regime_switch_confidence": 0.7,
    "regime_switch_cooldown_hours": 24,
    
    # Research loop
    "research_loop_interval_hours": 4,
    "max_hypotheses_per_cycle": 5,
    "min_scenarios_for_proposal": 10,
    
    # Actions
    "pause_trading_health_threshold": 0.25,
    "emergency_exit_threshold": 0.15,
}
