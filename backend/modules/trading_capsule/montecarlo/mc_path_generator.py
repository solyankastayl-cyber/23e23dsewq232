"""
Monte Carlo Path Generator (S5)
===============================

Generates random market paths for Monte Carlo simulation.

Methods:
- Bootstrap: Shuffle historical returns
- Noise Injection: Add random noise to prices
- Crash Injection: Add artificial market crashes
- Regime Switch: Simulate regime changes
"""

import random
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .mc_types import PathGeneratorType, CrashType


# ===========================================
# Market Path Data Structures
# ===========================================

@dataclass
class MarketPath:
    """Generated market path with returns and prices"""
    path_id: str
    returns: List[float]              # Daily returns
    prices: List[float]               # Price series
    had_crash: bool = False
    crash_magnitude: float = 0.0
    crash_day: int = -1
    recovery_day: int = -1


# ===========================================
# Path Generator
# ===========================================

class MonteCarloPathGenerator:
    """
    Generates random market paths for Monte Carlo simulation.
    
    Supports multiple generation methods:
    - Bootstrap: Shuffle historical returns
    - Noise Injection: Add random noise
    - Crash Injection: Add market crashes
    """
    
    def __init__(
        self,
        base_returns: List[float],
        initial_price: float = 100.0
    ):
        """
        Initialize path generator.
        
        Args:
            base_returns: Historical daily returns
            initial_price: Starting price for paths
        """
        self.base_returns = base_returns
        self.initial_price = initial_price
        
        # Calculate base statistics
        self.mean_return = sum(base_returns) / len(base_returns) if base_returns else 0
        self.std_return = self._calculate_std(base_returns) if base_returns else 0.01
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.01
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    # ===========================================
    # Bootstrap Method
    # ===========================================
    
    def generate_bootstrap_path(
        self,
        horizon_days: int,
        path_id: str = ""
    ) -> MarketPath:
        """
        Generate path by shuffling historical returns.
        
        This is the safest method - preserves return distribution.
        """
        # Sample with replacement
        returns = [random.choice(self.base_returns) for _ in range(horizon_days)]
        
        # Generate price series
        prices = self._returns_to_prices(returns)
        
        return MarketPath(
            path_id=path_id,
            returns=returns,
            prices=prices
        )
    
    # ===========================================
    # Noise Injection Method
    # ===========================================
    
    def generate_noise_path(
        self,
        horizon_days: int,
        noise_std: float = 0.02,
        path_id: str = ""
    ) -> MarketPath:
        """
        Generate path by adding noise to base returns.
        
        price = price * (1 + base_return + noise)
        """
        returns = []
        
        for i in range(horizon_days):
            base_return = random.choice(self.base_returns)
            noise = random.gauss(0, noise_std)
            returns.append(base_return + noise)
        
        prices = self._returns_to_prices(returns)
        
        return MarketPath(
            path_id=path_id,
            returns=returns,
            prices=prices
        )
    
    # ===========================================
    # Crash Injection Method
    # ===========================================
    
    def generate_crash_path(
        self,
        horizon_days: int,
        crash_probability: float = 0.05,
        crash_severity_min: float = -0.20,
        crash_severity_max: float = -0.50,
        path_id: str = ""
    ) -> MarketPath:
        """
        Generate path with potential crash injection.
        
        Simulates sudden market crashes with recovery.
        """
        # Start with bootstrap path
        returns = [random.choice(self.base_returns) for _ in range(horizon_days)]
        
        # Decide if crash happens
        had_crash = random.random() < crash_probability
        crash_magnitude = 0.0
        crash_day = -1
        recovery_day = -1
        
        if had_crash:
            # Determine crash parameters
            crash_day = random.randint(int(horizon_days * 0.1), int(horizon_days * 0.8))
            crash_magnitude = random.uniform(crash_severity_max, crash_severity_min)
            
            # Determine crash type and duration
            crash_duration = random.randint(1, 5)
            
            # Inject crash returns
            daily_crash = crash_magnitude / crash_duration
            for i in range(crash_day, min(crash_day + crash_duration, horizon_days)):
                returns[i] = daily_crash + random.gauss(0, 0.02)
            
            # Recovery period (if applicable)
            recovery_start = crash_day + crash_duration
            recovery_duration = random.randint(10, 50)
            recovery_return = abs(crash_magnitude) * 0.6 / recovery_duration
            
            for i in range(recovery_start, min(recovery_start + recovery_duration, horizon_days)):
                returns[i] = recovery_return + random.gauss(0, 0.01)
            
            recovery_day = min(recovery_start + recovery_duration, horizon_days)
        
        prices = self._returns_to_prices(returns)
        
        return MarketPath(
            path_id=path_id,
            returns=returns,
            prices=prices,
            had_crash=had_crash,
            crash_magnitude=crash_magnitude,
            crash_day=crash_day,
            recovery_day=recovery_day
        )
    
    # ===========================================
    # Regime Switch Method
    # ===========================================
    
    def generate_regime_path(
        self,
        horizon_days: int,
        bull_prob: float = 0.6,
        bear_prob: float = 0.3,
        path_id: str = ""
    ) -> MarketPath:
        """
        Generate path with regime switching.
        
        Alternates between bull, bear, and sideways regimes.
        """
        returns = []
        
        # Regime parameters
        bull_return = self.mean_return * 1.5
        bear_return = self.mean_return * -0.5
        sideways_return = self.mean_return * 0.1
        
        regime_volatility = {
            "bull": self.std_return * 0.8,
            "bear": self.std_return * 1.5,
            "sideways": self.std_return * 0.5
        }
        
        # Start with random regime
        current_regime = "bull" if random.random() < bull_prob else ("bear" if random.random() < bear_prob else "sideways")
        regime_duration = 0
        
        for day in range(horizon_days):
            # Check for regime change
            if regime_duration > random.randint(20, 60):
                roll = random.random()
                if roll < 0.4:
                    current_regime = "bull"
                elif roll < 0.7:
                    current_regime = "bear"
                else:
                    current_regime = "sideways"
                regime_duration = 0
            
            # Generate return based on regime
            if current_regime == "bull":
                base = bull_return
            elif current_regime == "bear":
                base = bear_return
            else:
                base = sideways_return
            
            vol = regime_volatility[current_regime]
            daily_return = random.gauss(base, vol)
            returns.append(daily_return)
            
            regime_duration += 1
        
        prices = self._returns_to_prices(returns)
        
        return MarketPath(
            path_id=path_id,
            returns=returns,
            prices=prices
        )
    
    # ===========================================
    # Mixed Method
    # ===========================================
    
    def generate_mixed_path(
        self,
        horizon_days: int,
        noise_std: float = 0.01,
        crash_probability: float = 0.03,
        crash_severity_min: float = -0.15,
        crash_severity_max: float = -0.40,
        path_id: str = ""
    ) -> MarketPath:
        """
        Generate path using combination of methods.
        
        Bootstrap + Noise + Possible Crash
        """
        # Start with bootstrap
        returns = [random.choice(self.base_returns) for _ in range(horizon_days)]
        
        # Add noise
        returns = [r + random.gauss(0, noise_std) for r in returns]
        
        # Possibly inject crash
        had_crash = random.random() < crash_probability
        crash_magnitude = 0.0
        crash_day = -1
        recovery_day = -1
        
        if had_crash:
            crash_day = random.randint(int(horizon_days * 0.1), int(horizon_days * 0.8))
            crash_magnitude = random.uniform(crash_severity_max, crash_severity_min)
            
            crash_duration = random.randint(1, 3)
            daily_crash = crash_magnitude / crash_duration
            
            for i in range(crash_day, min(crash_day + crash_duration, horizon_days)):
                returns[i] = daily_crash
            
            recovery_day = crash_day + crash_duration + random.randint(10, 30)
        
        prices = self._returns_to_prices(returns)
        
        return MarketPath(
            path_id=path_id,
            returns=returns,
            prices=prices,
            had_crash=had_crash,
            crash_magnitude=crash_magnitude,
            crash_day=crash_day,
            recovery_day=recovery_day
        )
    
    # ===========================================
    # Generate Path (Main Entry)
    # ===========================================
    
    def generate_path(
        self,
        horizon_days: int,
        generator_type: PathGeneratorType,
        path_id: str = "",
        **kwargs
    ) -> MarketPath:
        """
        Generate market path using specified method.
        """
        if generator_type == PathGeneratorType.BOOTSTRAP:
            return self.generate_bootstrap_path(horizon_days, path_id)
        
        elif generator_type == PathGeneratorType.NOISE_INJECTION:
            return self.generate_noise_path(
                horizon_days,
                kwargs.get("noise_std", 0.02),
                path_id
            )
        
        elif generator_type == PathGeneratorType.CRASH_INJECTION:
            return self.generate_crash_path(
                horizon_days,
                kwargs.get("crash_probability", 0.05),
                kwargs.get("crash_severity_min", -0.20),
                kwargs.get("crash_severity_max", -0.50),
                path_id
            )
        
        elif generator_type == PathGeneratorType.REGIME_SWITCH:
            return self.generate_regime_path(
                horizon_days,
                kwargs.get("bull_prob", 0.6),
                kwargs.get("bear_prob", 0.3),
                path_id
            )
        
        elif generator_type == PathGeneratorType.MIXED:
            return self.generate_mixed_path(
                horizon_days,
                kwargs.get("noise_std", 0.01),
                kwargs.get("crash_probability", 0.03),
                kwargs.get("crash_severity_min", -0.15),
                kwargs.get("crash_severity_max", -0.40),
                path_id
            )
        
        # Default to bootstrap
        return self.generate_bootstrap_path(horizon_days, path_id)
    
    # ===========================================
    # Utilities
    # ===========================================
    
    def _returns_to_prices(self, returns: List[float]) -> List[float]:
        """Convert returns to price series"""
        prices = [self.initial_price]
        
        for r in returns:
            new_price = prices[-1] * (1 + r)
            prices.append(max(0.01, new_price))  # Prevent negative prices
        
        return prices
    
    @staticmethod
    def create_synthetic_returns(
        mean: float = 0.0005,      # 0.05% daily
        std: float = 0.02,         # 2% daily volatility
        num_days: int = 252
    ) -> List[float]:
        """Create synthetic historical returns for testing"""
        return [random.gauss(mean, std) for _ in range(num_days)]
