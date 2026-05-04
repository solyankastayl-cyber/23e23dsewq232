"""
PHASE 14.8 — Dominance Engine
==============================
Computes market dominance regime and rotation state.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.market_structure.breadth_dominance.dominance_types import (
    MarketDominanceState,
    DominanceRegime,
    RotationState,
)

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# DOMINANCE THRESHOLDS
# ══════════════════════════════════════════════════════════════

DOMINANCE_THRESHOLDS = {
    "btc_dom_threshold": 50.0,  # BTC > 50% = BTC_DOM
    "eth_dom_threshold": 20.0,  # ETH > 20% = ETH_DOM
    "alt_dom_threshold": 40.0,  # ALT > 40% = ALT_DOM
    "rotation_threshold": 1.5,  # Change > 1.5% in 24h = rotating
    "exit_threshold": -2.0,    # Total market down significantly
}


class DominanceEngine:
    """
    Computes market dominance and rotation.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
    
    def compute(self) -> MarketDominanceState:
        """
        Compute current market dominance state.
        """
        now = datetime.now(timezone.utc)
        
        # Get dominance data (from DB or compute from prices)
        current_dom = self._get_current_dominance()
        historical_dom = self._get_historical_dominance(hours=24)
        
        # Extract values
        btc_dom = current_dom.get("btc", 52.0)
        eth_dom = current_dom.get("eth", 17.0)
        alt_dom = 100.0 - btc_dom - eth_dom
        
        # Calculate 24h changes
        if historical_dom:
            btc_change = btc_dom - historical_dom.get("btc", btc_dom)
            eth_change = eth_dom - historical_dom.get("eth", eth_dom)
            alt_change = alt_dom - (100.0 - historical_dom.get("btc", btc_dom) - historical_dom.get("eth", eth_dom))
        else:
            btc_change = 0.0
            eth_change = 0.0
            alt_change = 0.0
        
        # Determine regime
        regime = self._determine_regime(btc_dom, eth_dom, alt_dom)
        
        # Determine rotation
        rotation, flow_strength = self._determine_rotation(
            btc_change, eth_change, alt_change
        )
        
        return MarketDominanceState(
            timestamp=now,
            btc_dominance=btc_dom,
            eth_dominance=eth_dom,
            alt_dominance=alt_dom,
            dominance_regime=regime,
            rotation_state=rotation,
            capital_flow_strength=flow_strength,
            btc_dom_change_24h=btc_change,
            eth_dom_change_24h=eth_change,
            alt_dom_change_24h=alt_change,
        )
    
    def _get_current_dominance(self) -> Dict[str, float]:
        """Get current dominance from DB or compute from market caps."""
        try:
            # Try to get from dominance collection
            doc = self.db.dominance.find_one(
                {},
                {"_id": 0},
                sort=[("timestamp", DESCENDING)]
            )
            if doc:
                return {
                    "btc": doc.get("btc_dominance", 52.0),
                    "eth": doc.get("eth_dominance", 17.0),
                }
            
            # Fallback: compute from market data
            return self._compute_from_market_data()
        except Exception:
            return {"btc": 52.0, "eth": 17.0}
    
    def _compute_from_market_data(self) -> Dict[str, float]:
        """Compute dominance from price/volume data."""
        try:
            # Get latest prices and estimate dominance
            # This is simplified - real implementation would use market caps
            btc_candle = self.db.candles.find_one(
                {"symbol": "BTC", "timeframe": "1d"},
                {"_id": 0},
                sort=[("timestamp", DESCENDING)]
            )
            eth_candle = self.db.candles.find_one(
                {"symbol": "ETH", "timeframe": "1d"},
                {"_id": 0},
                sort=[("timestamp", DESCENDING)]
            )
            
            if btc_candle and eth_candle:
                # Simplified dominance estimation
                btc_price = btc_candle.get("close", 50000)
                eth_price = eth_candle.get("close", 3000)
                
                # Rough market cap estimation (BTC ~21M supply, ETH ~120M)
                btc_cap = btc_price * 19_500_000
                eth_cap = eth_price * 120_000_000
                total_cap = btc_cap + eth_cap * 3  # Assume alts = 2x ETH cap
                
                btc_dom = (btc_cap / total_cap) * 100
                eth_dom = (eth_cap / total_cap) * 100
                
                return {"btc": min(60, max(40, btc_dom)), "eth": min(25, max(12, eth_dom))}
            
            return {"btc": 52.0, "eth": 17.0}
        except Exception:
            return {"btc": 52.0, "eth": 17.0}
    
    def _get_historical_dominance(self, hours: int = 24) -> Optional[Dict[str, float]]:
        """Get historical dominance for comparison."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            doc = self.db.dominance.find_one(
                {"timestamp": {"$lte": cutoff}},
                {"_id": 0},
                sort=[("timestamp", DESCENDING)]
            )
            if doc:
                return {
                    "btc": doc.get("btc_dominance", 52.0),
                    "eth": doc.get("eth_dominance", 17.0),
                }
            return None
        except Exception:
            return None
    
    def _determine_regime(
        self, btc_dom: float, eth_dom: float, alt_dom: float
    ) -> DominanceRegime:
        """Determine dominance regime."""
        if btc_dom >= DOMINANCE_THRESHOLDS["btc_dom_threshold"]:
            return DominanceRegime.BTC_DOM
        
        if eth_dom >= DOMINANCE_THRESHOLDS["eth_dom_threshold"]:
            return DominanceRegime.ETH_DOM
        
        if alt_dom >= DOMINANCE_THRESHOLDS["alt_dom_threshold"]:
            return DominanceRegime.ALT_DOM
        
        return DominanceRegime.BALANCED
    
    def _determine_rotation(
        self,
        btc_change: float,
        eth_change: float,
        alt_change: float,
    ) -> Tuple[RotationState, float]:
        """Determine rotation state and flow strength."""
        threshold = DOMINANCE_THRESHOLDS["rotation_threshold"]
        
        # Calculate flow strength from max absolute change
        flow_strength = max(abs(btc_change), abs(eth_change), abs(alt_change)) / 5.0
        flow_strength = min(1.0, flow_strength)
        
        # Check for market exit (all dominances falling relative to stables)
        total_change = btc_change + eth_change + alt_change
        if total_change < DOMINANCE_THRESHOLDS["exit_threshold"]:
            return (RotationState.EXITING_MARKET, flow_strength)
        
        # Check for rotation
        if btc_change >= threshold and alt_change <= -threshold:
            return (RotationState.ROTATING_TO_BTC, flow_strength)
        
        if alt_change >= threshold and btc_change <= -threshold:
            return (RotationState.ROTATING_TO_ALTS, flow_strength)
        
        if eth_change >= threshold:
            return (RotationState.ROTATING_TO_ETH, flow_strength)
        
        return (RotationState.STABLE, flow_strength)


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[DominanceEngine] = None


def get_dominance_engine() -> DominanceEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = DominanceEngine()
    return _engine
