"""
WebSocket Service Locator
Sprint WS-1: Singleton accessors for WS services
"""

_ws_manager = None
_ws_broadcaster = None


def init_ws_manager(manager):
    """Initialize global WebSocket manager instance."""
    global _ws_manager
    _ws_manager = manager
    return _ws_manager


def get_ws_manager():
    """Get WebSocket manager instance."""
    if _ws_manager is None:
        raise RuntimeError("WebSocketManager not initialized")
    return _ws_manager


def init_ws_broadcaster(broadcaster):
    """Initialize global WebSocket broadcaster instance."""
    global _ws_broadcaster
    _ws_broadcaster = broadcaster
    return _ws_broadcaster


def get_ws_broadcaster():
    """Get WebSocket broadcaster instance."""
    if _ws_broadcaster is None:
        raise RuntimeError("WebSocketBroadcaster not initialized")
    return _ws_broadcaster
