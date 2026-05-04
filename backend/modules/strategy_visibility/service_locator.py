"""
Strategy Visibility Service Locator
====================================
Sprint A3: Singleton access pattern
"""

_strategy_visibility_service = None


def init_strategy_visibility_service(service):
    global _strategy_visibility_service
    _strategy_visibility_service = service
    return _strategy_visibility_service


def get_strategy_visibility_service():
    if _strategy_visibility_service is None:
        raise RuntimeError("StrategyVisibilityService is not initialized")
    return _strategy_visibility_service
