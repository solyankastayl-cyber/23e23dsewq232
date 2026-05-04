"""
PHASE 21.1 — Asset Capital Engine
=================================
Sub-engine for asset-level capital allocation.

Distributes capital across:
- BTC
- ETH
- ALTS
- CASH/RESERVED
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class AssetCapitalEngine:
    """
    Asset Capital Allocation Sub-Engine.
    
    Distributes capital across assets based on:
    - Dominance regime (BTC dominance)
    - Market breadth
    - Portfolio concentration
    - Current exposure
    """
    
    def __init__(self):
        """Initialize engine."""
        self._base_allocations: Dict[str, float] = {}
        self._initialize_baseline()
    
    def _initialize_baseline(self):
        """Initialize baseline asset allocations."""
        self._base_allocations = {
            "BTC": 0.40,
            "ETH": 0.25,
            "ALTS": 0.20,
            "CASH": 0.15,
        }
    
    def compute_allocations(
        self,
        btc_dominance: float = 0.55,
        market_breadth: float = 0.5,
        portfolio_concentration: float = 0.3,
        risk_off_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Compute asset allocations.
        
        Args:
            btc_dominance: BTC market dominance (0..1)
            market_breadth: Market breadth indicator (0..1)
            portfolio_concentration: Current concentration (0..1)
            risk_off_mode: Whether in risk-off mode
        
        Returns:
            {
                "allocations": {asset: allocation},
                "total": float,
                "concentration": float,
            }
        """
        allocations = {}
        
        # Start with baseline
        for asset, base_alloc in self._base_allocations.items():
            allocations[asset] = base_alloc
        
        # Adjust for BTC dominance
        if btc_dominance > 0.60:
            # High BTC dominance: shift to BTC
            allocations["BTC"] *= 1.15
            allocations["ALTS"] *= 0.75
        elif btc_dominance < 0.45:
            # Low BTC dominance: alt season
            allocations["BTC"] *= 0.90
            allocations["ETH"] *= 1.10
            allocations["ALTS"] *= 1.20
        
        # Adjust for market breadth
        if market_breadth > 0.7:
            # Wide breadth: spread across assets
            allocations["ALTS"] *= 1.10
            allocations["CASH"] *= 0.85
        elif market_breadth < 0.3:
            # Narrow breadth: concentrate
            allocations["BTC"] *= 1.10
            allocations["ALTS"] *= 0.80
        
        # Adjust for risk-off
        if risk_off_mode:
            allocations["CASH"] *= 1.50
            allocations["ALTS"] *= 0.60
            allocations["ETH"] *= 0.80
        
        # Adjust for concentration
        if portfolio_concentration > 0.5:
            # Already concentrated: increase cash
            allocations["CASH"] *= 1.20
        
        # Normalize
        total = sum(allocations.values())
        if total > 0:
            allocations = {k: v / total for k, v in allocations.items()}
        
        # Calculate concentration
        concentration = max(allocations.values()) if allocations else 0.0
        
        return {
            "allocations": allocations,
            "total": 1.0,
            "concentration": concentration,
            "btc_dominance_input": btc_dominance,
            "market_breadth_input": market_breadth,
        }
    
    def get_dominant_asset(self, allocations: Dict[str, float]) -> str:
        """Get asset with highest allocation."""
        if not allocations:
            return "none"
        return max(allocations, key=allocations.get)


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[AssetCapitalEngine] = None


def get_asset_capital_engine() -> AssetCapitalEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AssetCapitalEngine()
    return _engine
