"""
Trading Terminal - Risk Module (TR4)
====================================

Risk Dashboard - portfolio risk monitoring and guardrails.
"""

from .risk_types import (
    RiskLevel,
    AlertType,
    AlertSeverity,
    PortfolioRiskState,
    RiskAlert,
    RiskGuardrailEvent,
    RiskMetrics,
    ExposureMetrics,
    ConcentrationMetrics,
    TailRiskMetrics
)

from .risk_metrics import (
    RiskMetricsCalculator,
    risk_metrics_calculator
)

from .risk_alert_engine import (
    RiskAlertEngine,
    risk_alert_engine
)

from .risk_guardrails import (
    RiskGuardrails,
    risk_guardrails
)

from .risk_service import (
    RiskService,
    risk_service
)

__all__ = [
    "RiskLevel", "AlertType", "AlertSeverity",
    "PortfolioRiskState", "RiskAlert", "RiskGuardrailEvent",
    "RiskMetrics", "ExposureMetrics", "ConcentrationMetrics", "TailRiskMetrics",
    "RiskMetricsCalculator", "risk_metrics_calculator",
    "RiskAlertEngine", "risk_alert_engine",
    "RiskGuardrails", "risk_guardrails",
    "RiskService", "risk_service"
]
