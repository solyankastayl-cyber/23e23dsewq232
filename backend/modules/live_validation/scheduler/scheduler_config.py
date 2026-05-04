"""
Scheduler Configuration
========================
Configuration for V2 Validation Scheduler intervals and limits.
"""

# Global scheduler configuration
SCHEDULER_CONFIG = {
    # Enable/disable scheduler
    "enabled": True,
    
    # Execution intervals (seconds)
    "shadow_creation_interval_sec": 60,      # Create shadow trades every 60 sec
    "validation_interval_sec": 120,          # Run validation every 120 sec  
    "alpha_cycle_interval_sec": 300,         # Run AF3+AF4 every 300 sec (5 min)
    
    # Limits per cycle
    "max_shadow_per_cycle": 5,               # Max shadow trades to create per cycle
    "symbols_limit": 10,                     # Max symbols to process in alpha cycles
    
    # Thresholds for auto-triggers
    "wrong_early_threshold": 0.25,           # Threshold for wrong early rate alerts
    "decay_pf_threshold": 1.1,               # Profit factor decay threshold
    
    # Logging
    "verbose_logging": True,                 # Enable detailed logging
}


def get_config():
    """Get current scheduler configuration."""
    return SCHEDULER_CONFIG.copy()


def update_config(updates: dict):
    """
    Update scheduler configuration.
    
    Args:
        updates: Dictionary with config keys to update
    """
    SCHEDULER_CONFIG.update(updates)
