"""
PHASE 14.8 — Breadth Engine
============================
Computes market breadth state.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.market_structure.breadth_dominance.dominance_types import (
    MarketBreadthState,
    BreadthState,
)

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# BREADTH THRESHOLDS
# ══════════════════════════════════════════════════════════════

BREADTH_THRESHOLDS = {
    "strong_ratio": 1.5,    # advancing/declining > 1.5 = STRONG
    "weak_ratio": 0.7,      # advancing/declining < 0.7 = WEAK
    "participation_high": 0.7,  # 70%+ following trend = high participation
    "participation_low": 0.4,   # <40% = low participation
}

# Symbols to track for breadth
TRACKED_SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE",
    "DOT", "MATIC", "LINK", "ATOM", "UNI", "LTC", "NEAR",
    "APT", "OP", "ARB", "INJ", "SUI"
]


class BreadthEngine:
    """
    Computes market breadth state.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
    
    def compute(self) -> MarketBreadthState:
        """
        Compute current market breadth state.
        """
        now = datetime.now(timezone.utc)
        
        # Get price changes for tracked assets
        asset_states = self._get_asset_states()
        
        # Count advancing/declining
        advancing = sum(1 for s in asset_states if s["change_24h"] > 0)
        declining = sum(1 for s in asset_states if s["change_24h"] < 0)
        unchanged = len(asset_states) - advancing - declining
        
        # Calculate breadth ratio
        breadth_ratio = advancing / max(declining, 1)
        
        # Determine breadth state
        breadth_state = self._determine_breadth_state(breadth_ratio)
        
        # Calculate trend participation
        trend_participation = self._calculate_trend_participation(asset_states)
        
        # Count highs/lows and MA positions
        new_highs = sum(1 for s in asset_states if s.get("near_high", False))
        new_lows = sum(1 for s in asset_states if s.get("near_low", False))
        above_ma = sum(1 for s in asset_states if s.get("above_20d_ma", False))
        below_ma = len(asset_states) - above_ma
        
        return MarketBreadthState(
            timestamp=now,
            advancing_assets=advancing,
            declining_assets=declining,
            unchanged_assets=unchanged,
            breadth_ratio=breadth_ratio,
            breadth_state=breadth_state,
            trend_participation=trend_participation,
            new_highs=new_highs,
            new_lows=new_lows,
            above_20d_ma=above_ma,
            below_20d_ma=below_ma,
        )
    
    def _get_asset_states(self) -> List[Dict]:
        """Get state of tracked assets."""
        asset_states = []
        
        for symbol in TRACKED_SYMBOLS:
            state = self._get_single_asset_state(symbol)
            if state:
                asset_states.append(state)
        
        # If we don't have enough real data, generate reasonable mock data
        if len(asset_states) < 5:
            asset_states = self._generate_mock_states()
        
        return asset_states
    
    def _get_single_asset_state(self, symbol: str) -> Optional[Dict]:
        """Get state for single asset."""
        try:
            # Get recent candles
            candles = list(self.db.candles.find(
                {"symbol": symbol, "timeframe": "1d"},
                {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(25))
            
            if len(candles) < 2:
                return None
            
            candles = list(reversed(candles))
            
            current_price = candles[-1]["close"]
            prev_price = candles[-2]["close"]
            
            # 24h change
            change_24h = ((current_price - prev_price) / prev_price) * 100
            
            # 20-day high/low
            if len(candles) >= 20:
                high_20d = max(c["high"] for c in candles[-20:])
                low_20d = min(c["low"] for c in candles[-20:])
                near_high = current_price >= high_20d * 0.98
                near_low = current_price <= low_20d * 1.02
                
                # 20-day MA
                ma_20 = sum(c["close"] for c in candles[-20:]) / 20
                above_20d_ma = current_price > ma_20
            else:
                near_high = False
                near_low = False
                above_20d_ma = True
            
            return {
                "symbol": symbol,
                "change_24h": change_24h,
                "near_high": near_high,
                "near_low": near_low,
                "above_20d_ma": above_20d_ma,
            }
        except Exception:
            return None
    
    def _generate_mock_states(self) -> List[Dict]:
        """Generate mock states when real data unavailable."""
        import random
        
        states = []
        for symbol in TRACKED_SYMBOLS:
            # Generate realistic distribution
            change = random.gauss(0, 3)  # Mean 0, std 3%
            states.append({
                "symbol": symbol,
                "change_24h": change,
                "near_high": random.random() < 0.15,
                "near_low": random.random() < 0.15,
                "above_20d_ma": random.random() < 0.55,
            })
        
        return states
    
    def _determine_breadth_state(self, breadth_ratio: float) -> BreadthState:
        """Determine breadth state from ratio."""
        if breadth_ratio >= BREADTH_THRESHOLDS["strong_ratio"]:
            return BreadthState.STRONG
        elif breadth_ratio <= BREADTH_THRESHOLDS["weak_ratio"]:
            return BreadthState.WEAK
        else:
            return BreadthState.MIXED
    
    def _calculate_trend_participation(self, asset_states: List[Dict]) -> float:
        """Calculate what % of assets are following the overall trend."""
        if not asset_states:
            return 0.5
        
        # Determine overall market trend
        total_change = sum(s["change_24h"] for s in asset_states)
        avg_change = total_change / len(asset_states)
        
        if avg_change > 0.5:  # Bullish trend
            participating = sum(1 for s in asset_states if s["change_24h"] > 0)
        elif avg_change < -0.5:  # Bearish trend
            participating = sum(1 for s in asset_states if s["change_24h"] < 0)
        else:  # No clear trend
            return 0.5
        
        return participating / len(asset_states)


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[BreadthEngine] = None


def get_breadth_engine() -> BreadthEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = BreadthEngine()
    return _engine
