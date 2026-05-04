"""
PHASE 6.3 - Monte Carlo Registry
==================================
Registry of simulation configurations and presets.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from .monte_types import MonteCarloMethod


@dataclass
class SimulationConfig:
    """Configuration preset for Monte Carlo simulation"""
    config_id: str
    name: str
    description: str
    iterations: int
    method: MonteCarloMethod
    noise_level: float
    
    def to_dict(self) -> Dict:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "description": self.description,
            "iterations": self.iterations,
            "method": self.method.value if hasattr(self.method, 'value') else self.method,
            "noise_level": self.noise_level
        }


# Default configuration presets
DEFAULT_CONFIGS: List[SimulationConfig] = [
    SimulationConfig(
        config_id="quick",
        name="Quick Analysis",
        description="Fast simulation with 1000 iterations, good for initial screening",
        iterations=1000,
        method=MonteCarloMethod.COMBINED,
        noise_level=0.1
    ),
    SimulationConfig(
        config_id="standard",
        name="Standard Analysis",
        description="Standard simulation with 5000 iterations, balanced accuracy/speed",
        iterations=5000,
        method=MonteCarloMethod.COMBINED,
        noise_level=0.1
    ),
    SimulationConfig(
        config_id="deep",
        name="Deep Analysis",
        description="Deep simulation with 10000 iterations for production decisions",
        iterations=10000,
        method=MonteCarloMethod.COMBINED,
        noise_level=0.1
    ),
    SimulationConfig(
        config_id="bootstrap_only",
        name="Bootstrap Only",
        description="Pure bootstrap resampling without shuffling or noise",
        iterations=5000,
        method=MonteCarloMethod.BOOTSTRAP,
        noise_level=0.0
    ),
    SimulationConfig(
        config_id="high_noise",
        name="High Noise Stress Test",
        description="High noise injection to test strategy robustness",
        iterations=5000,
        method=MonteCarloMethod.NOISE_INJECTION,
        noise_level=0.25
    ),
    SimulationConfig(
        config_id="conservative",
        name="Conservative Analysis",
        description="Conservative settings with low noise for production strategies",
        iterations=10000,
        method=MonteCarloMethod.COMBINED,
        noise_level=0.05
    )
]


class MonteCarloRegistry:
    """
    Registry for Monte Carlo configurations
    """
    
    def __init__(self):
        self._configs: Dict[str, SimulationConfig] = {}
        self._load_default_configs()
    
    def _load_default_configs(self):
        """Load default configurations"""
        for config in DEFAULT_CONFIGS:
            self._configs[config.config_id] = config
    
    def get(self, config_id: str) -> Optional[SimulationConfig]:
        """Get configuration by ID"""
        return self._configs.get(config_id)
    
    def get_all(self) -> List[SimulationConfig]:
        """Get all configurations"""
        return list(self._configs.values())
    
    def get_default(self) -> SimulationConfig:
        """Get default configuration"""
        return self._configs.get("standard", DEFAULT_CONFIGS[1])
    
    def add(self, config: SimulationConfig) -> bool:
        """Add new configuration"""
        if config.config_id in self._configs:
            return False
        self._configs[config.config_id] = config
        return True
    
    def delete(self, config_id: str) -> bool:
        """Delete configuration"""
        if config_id not in self._configs:
            return False
        del self._configs[config_id]
        return True
    
    def get_stats(self) -> Dict:
        """Get registry statistics"""
        configs = list(self._configs.values())
        
        method_counts = {}
        for method in MonteCarloMethod:
            method_counts[method.value] = len([c for c in configs if c.method == method])
        
        return {
            "total": len(configs),
            "by_method": method_counts,
            "avg_iterations": sum(c.iterations for c in configs) / len(configs) if configs else 0
        }


# Singleton instance
_registry_instance: Optional[MonteCarloRegistry] = None


def get_monte_registry() -> MonteCarloRegistry:
    """Get singleton registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = MonteCarloRegistry()
    return _registry_instance
