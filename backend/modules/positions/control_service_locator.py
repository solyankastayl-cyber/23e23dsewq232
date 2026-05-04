"""
Position Control Service Locator
Sprint A6: Singleton accessor for control service
"""

_position_control_service = None


def init_position_control_service(service):
    """Initialize global position control service instance."""
    global _position_control_service
    _position_control_service = service


def get_position_control_service():
    """Get position control service instance."""
    if _position_control_service is None:
        raise RuntimeError("PositionControlService not initialized")
    return _position_control_service
