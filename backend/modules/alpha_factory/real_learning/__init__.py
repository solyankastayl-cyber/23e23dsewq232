"""
Real Learning Module - AF6

Intelligence loop for self-improving trading system.
"""

from .outcome_registry import OutcomeRegistry
from .trade_outcome_engine import TradeOutcomeEngine
from .outcome_classifier import OutcomeClassifier
from .learning_metrics_engine import LearningMetricsEngine
from .alpha_feedback_engine import AlphaFeedbackEngine
from .learning_policy_bridge import LearningPolicyBridge
from .learning_engine import RealLearningEngine
from .learning_routes import router as learning_router, init_learning

__all__ = [
    "OutcomeRegistry",
    "TradeOutcomeEngine",
    "OutcomeClassifier",
    "LearningMetricsEngine",
    "AlphaFeedbackEngine",
    "LearningPolicyBridge",
    "RealLearningEngine",
    "learning_router",
    "init_learning",
]
