"""
PHASE 26.1 — Factor Discovery Engine

Generates candidate alpha factors from multiple sources:
- TA signals (momentum, breakout, trend)
- Exchange microstructure (orderbook, liquidations)
- Fractal patterns (pattern alignment)
- Regime context (trend strength)

This is NOT ML/AI. This is structured alpha discovery.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

from .factor_types import (
    FactorCandidate,
    FactorCategory,
    DEFAULT_LOOKBACKS,
)


class FactorDiscoveryEngine:
    """
    Factor Discovery Engine.
    
    Generates candidate factors from multiple sources.
    Each candidate has:
    - factor_id (unique hash)
    - category (TA, EXCHANGE, FRACTAL, REGIME)
    - lookback period
    - raw signal value
    """
    
    def __init__(self):
        self._discovered_factors: List[FactorCandidate] = []
        self._last_discovery: Optional[datetime] = None
    
    # ═══════════════════════════════════════════════════════════
    # Main Discovery
    # ═══════════════════════════════════════════════════════════
    
    def discover_all(self) -> List[FactorCandidate]:
        """
        Run full factor discovery across all sources.
        
        Returns list of candidate factors.
        """
        candidates = []
        
        # Discover from each category
        candidates.extend(self.discover_ta_factors())
        candidates.extend(self.discover_exchange_factors())
        candidates.extend(self.discover_fractal_factors())
        candidates.extend(self.discover_regime_factors())
        
        self._discovered_factors = candidates
        self._last_discovery = datetime.utcnow()
        
        return candidates
    
    # ═══════════════════════════════════════════════════════════
    # TA Factor Discovery
    # ═══════════════════════════════════════════════════════════
    
    def discover_ta_factors(self) -> List[FactorCandidate]:
        """
        Discover TA-based factors.
        
        Sources:
        - Momentum signals
        - Breakout signals
        - Trend signals
        - Mean reversion signals
        """
        candidates = []
        lookbacks = DEFAULT_LOOKBACKS["TA"]
        
        # Momentum factors
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"ta_momentum_{lb}",
                category="TA",
                lookback=lb,
                raw_signal=self._simulate_signal("momentum", lb),
                source="ta_engine",
                parameters={"period": lb, "type": "momentum"},
            ))
        
        # Breakout factors
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"ta_breakout_{lb}",
                category="TA",
                lookback=lb,
                raw_signal=self._simulate_signal("breakout", lb),
                source="ta_engine",
                parameters={"period": lb, "type": "breakout"},
            ))
        
        # Trend factors
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"ta_trend_{lb}",
                category="TA",
                lookback=lb,
                raw_signal=self._simulate_signal("trend", lb),
                source="ta_engine",
                parameters={"period": lb, "type": "trend"},
            ))
        
        # Mean reversion factors
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"ta_mean_reversion_{lb}",
                category="TA",
                lookback=lb,
                raw_signal=self._simulate_signal("mean_reversion", lb),
                source="ta_engine",
                parameters={"period": lb, "type": "mean_reversion"},
            ))
        
        return candidates
    
    # ═══════════════════════════════════════════════════════════
    # Exchange Factor Discovery
    # ═══════════════════════════════════════════════════════════
    
    def discover_exchange_factors(self) -> List[FactorCandidate]:
        """
        Discover exchange microstructure factors.
        
        Sources:
        - Orderbook imbalance
        - Liquidation clusters
        - Funding rate
        - Open interest changes
        """
        candidates = []
        lookbacks = DEFAULT_LOOKBACKS["EXCHANGE"]
        
        # Orderbook imbalance
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"orderbook_imbalance_{lb}",
                category="EXCHANGE",
                lookback=lb,
                raw_signal=self._simulate_signal("orderbook", lb),
                source="exchange_intelligence",
                parameters={"period": lb, "type": "orderbook_imbalance"},
            ))
        
        # Liquidation clusters
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"liquidation_cluster_{lb}",
                category="EXCHANGE",
                lookback=lb,
                raw_signal=self._simulate_signal("liquidation", lb),
                source="exchange_intelligence",
                parameters={"period": lb, "type": "liquidation_cluster"},
            ))
        
        # Funding rate
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"funding_rate_{lb}",
                category="EXCHANGE",
                lookback=lb,
                raw_signal=self._simulate_signal("funding", lb),
                source="exchange_intelligence",
                parameters={"period": lb, "type": "funding_rate"},
            ))
        
        # Open interest delta
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"oi_delta_{lb}",
                category="EXCHANGE",
                lookback=lb,
                raw_signal=self._simulate_signal("oi", lb),
                source="exchange_intelligence",
                parameters={"period": lb, "type": "oi_delta"},
            ))
        
        return candidates
    
    # ═══════════════════════════════════════════════════════════
    # Fractal Factor Discovery
    # ═══════════════════════════════════════════════════════════
    
    def discover_fractal_factors(self) -> List[FactorCandidate]:
        """
        Discover fractal pattern factors.
        
        Sources:
        - Pattern alignment
        - Phase classification
        - Horizon consensus
        """
        candidates = []
        lookbacks = DEFAULT_LOOKBACKS["FRACTAL"]
        
        # Pattern alignment
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"fractal_pattern_alignment_{lb}",
                category="FRACTAL",
                lookback=lb,
                raw_signal=self._simulate_signal("pattern", lb),
                source="fractal_intelligence",
                parameters={"period": lb, "type": "pattern_alignment"},
            ))
        
        # Phase momentum
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"fractal_phase_momentum_{lb}",
                category="FRACTAL",
                lookback=lb,
                raw_signal=self._simulate_signal("phase", lb),
                source="fractal_intelligence",
                parameters={"period": lb, "type": "phase_momentum"},
            ))
        
        # Horizon consensus
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"fractal_horizon_consensus_{lb}",
                category="FRACTAL",
                lookback=lb,
                raw_signal=self._simulate_signal("horizon", lb),
                source="fractal_intelligence",
                parameters={"period": lb, "type": "horizon_consensus"},
            ))
        
        return candidates
    
    # ═══════════════════════════════════════════════════════════
    # Regime Factor Discovery
    # ═══════════════════════════════════════════════════════════
    
    def discover_regime_factors(self) -> List[FactorCandidate]:
        """
        Discover regime context factors.
        
        Sources:
        - Trend strength
        - Volatility regime
        - Liquidity state
        """
        candidates = []
        lookbacks = DEFAULT_LOOKBACKS["REGIME"]
        
        # Trend strength
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"regime_trend_strength_{lb}",
                category="REGIME",
                lookback=lb,
                raw_signal=self._simulate_signal("trend_regime", lb),
                source="regime_engine",
                parameters={"period": lb, "type": "trend_strength"},
            ))
        
        # Volatility regime
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"regime_volatility_{lb}",
                category="REGIME",
                lookback=lb,
                raw_signal=self._simulate_signal("volatility", lb),
                source="regime_engine",
                parameters={"period": lb, "type": "volatility_regime"},
            ))
        
        # Liquidity state
        for lb in lookbacks:
            candidates.append(self._create_candidate(
                name=f"regime_liquidity_{lb}",
                category="REGIME",
                lookback=lb,
                raw_signal=self._simulate_signal("liquidity", lb),
                source="regime_engine",
                parameters={"period": lb, "type": "liquidity_state"},
            ))
        
        return candidates
    
    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════
    
    def _create_candidate(
        self,
        name: str,
        category: FactorCategory,
        lookback: int,
        raw_signal: float,
        source: str,
        parameters: Dict[str, Any],
    ) -> FactorCandidate:
        """Create a factor candidate with unique ID."""
        factor_id = self._generate_factor_id(name, category, lookback)
        
        return FactorCandidate(
            factor_id=factor_id,
            name=name,
            category=category,
            lookback=lookback,
            raw_signal=raw_signal,
            source=source,
            parameters=parameters,
        )
    
    def _generate_factor_id(
        self,
        name: str,
        category: str,
        lookback: int,
    ) -> str:
        """Generate unique factor ID from components."""
        raw = f"{category}:{name}:{lookback}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]
    
    def _simulate_signal(self, signal_type: str, lookback: int) -> float:
        """
        Simulate raw signal value.
        
        In production, this would come from actual TA/Exchange/Fractal engines.
        For now, deterministic based on type and lookback.
        """
        # Deterministic signal based on type hash
        type_hash = hash(signal_type) % 100
        lookback_factor = (lookback % 30) / 30.0
        
        # Base signal in [-1, 1]
        base = (type_hash / 100.0) * 2 - 1
        signal = base * (0.5 + lookback_factor * 0.5)
        
        return max(-1.0, min(1.0, signal))
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_discovered_factors(self) -> List[FactorCandidate]:
        """Get last discovered factors."""
        return self._discovered_factors
    
    def get_factors_by_category(
        self,
        category: FactorCategory,
    ) -> List[FactorCandidate]:
        """Get discovered factors filtered by category."""
        return [f for f in self._discovered_factors if f.category == category]
    
    def get_discovery_count(self) -> int:
        """Get count of discovered factors."""
        return len(self._discovered_factors)
    
    @property
    def last_discovery(self) -> Optional[datetime]:
        """Get timestamp of last discovery run."""
        return self._last_discovery


# Singleton
_engine: Optional[FactorDiscoveryEngine] = None


def get_factor_discovery_engine() -> FactorDiscoveryEngine:
    """Get singleton instance of FactorDiscoveryEngine."""
    global _engine
    if _engine is None:
        _engine = FactorDiscoveryEngine()
    return _engine
