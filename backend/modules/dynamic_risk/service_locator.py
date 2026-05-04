"""
Dynamic Risk Engine Service Locator
Sprint R1: Singleton accessor
"""

_dynamic_risk_engine = None


def init_dynamic_risk_engine(engine):
    """Initialize global dynamic risk engine instance."""
    global _dynamic_risk_engine
    _dynamic_risk_engine = engine


def get_dynamic_risk_engine():
    """Get dynamic risk engine instance."""
    if _dynamic_risk_engine is None:
        raise RuntimeError("DynamicRiskEngine not initialized")
    return _dynamic_risk_engine
