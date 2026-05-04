"""
PHASE 18.1 — Portfolio Exposure Engine
=======================================
Net/Gross and Asset Exposure calculations.

Calculates:
- Net exposure: longs - shorts
- Gross exposure: abs(longs) + abs(shorts)
- Asset exposure: BTC, ETH, ALT breakdown
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    Position,
    PositionDirection,
    ExposuresResponse,
)


# ══════════════════════════════════════════════════════════════
# ASSET CLASSIFICATION
# ══════════════════════════════════════════════════════════════

# Known BTC symbols
BTC_SYMBOLS = {"BTCUSDT", "BTCUSD", "XBTUSD", "BTC", "BTCPERP", "BTC-PERP"}

# Known ETH symbols
ETH_SYMBOLS = {"ETHUSDT", "ETHUSD", "ETH", "ETHPERP", "ETH-PERP"}

# Major alts (considered close to majors)
MAJOR_ALT_SYMBOLS = {"SOLUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT", "ADAUSDT", "DOGEUSDT"}


def classify_asset(symbol: str) -> str:
    """Classify symbol as BTC, ETH, or ALT."""
    symbol_upper = symbol.upper()
    
    if symbol_upper in BTC_SYMBOLS or symbol_upper.startswith("BTC"):
        return "BTC"
    elif symbol_upper in ETH_SYMBOLS or symbol_upper.startswith("ETH"):
        return "ETH"
    else:
        return "ALT"


# ══════════════════════════════════════════════════════════════
# PORTFOLIO EXPOSURE ENGINE
# ══════════════════════════════════════════════════════════════

class PortfolioExposureEngine:
    """
    Portfolio Exposure Engine - PHASE 18.1 STEP 3-4
    
    Calculates net/gross exposure and asset exposure breakdown.
    
    Example:
        BTC short 0.8
        ETH short 0.5
        SOL long 0.2
        
        net = -1.1
        gross = 1.5
        
        BTC exposure = 0.8
        ETH exposure = 0.5
        ALT exposure = 0.2
    """
    
    def calculate_exposures(self, positions: List[Position]) -> Dict:
        """
        Calculate net and gross exposure.
        
        Args:
            positions: List of portfolio positions
        
        Returns:
            Dict with exposure metrics
        """
        long_exposure = 0.0
        short_exposure = 0.0
        
        for pos in positions:
            if pos.direction == PositionDirection.LONG:
                long_exposure += pos.position_size
            else:
                short_exposure += pos.position_size
        
        net_exposure = long_exposure - short_exposure
        gross_exposure = long_exposure + short_exposure
        
        return {
            "net_exposure": net_exposure,
            "gross_exposure": gross_exposure,
            "long_exposure": long_exposure,
            "short_exposure": short_exposure,
            "long_count": sum(1 for p in positions if p.direction == PositionDirection.LONG),
            "short_count": sum(1 for p in positions if p.direction == PositionDirection.SHORT),
        }
    
    def calculate_asset_exposure(self, positions: List[Position]) -> Dict[str, float]:
        """
        Calculate exposure by asset class.
        
        Args:
            positions: List of portfolio positions
        
        Returns:
            Dict with BTC, ETH, ALT exposures
        """
        btc_exposure = 0.0
        eth_exposure = 0.0
        alt_exposure = 0.0
        
        for pos in positions:
            asset_class = classify_asset(pos.symbol)
            
            if asset_class == "BTC":
                btc_exposure += pos.position_size
            elif asset_class == "ETH":
                eth_exposure += pos.position_size
            else:
                alt_exposure += pos.position_size
        
        return {
            "btc_exposure": btc_exposure,
            "eth_exposure": eth_exposure,
            "alt_exposure": alt_exposure,
        }
    
    def calculate_asset_exposure_directional(
        self, positions: List[Position]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate directional exposure by asset class.
        
        Returns breakdown by long/short for each asset class.
        """
        result = {
            "BTC": {"long": 0.0, "short": 0.0, "net": 0.0},
            "ETH": {"long": 0.0, "short": 0.0, "net": 0.0},
            "ALT": {"long": 0.0, "short": 0.0, "net": 0.0},
        }
        
        for pos in positions:
            asset_class = classify_asset(pos.symbol)
            direction_key = "long" if pos.direction == PositionDirection.LONG else "short"
            result[asset_class][direction_key] += pos.position_size
        
        # Calculate net for each
        for asset_class in result:
            result[asset_class]["net"] = (
                result[asset_class]["long"] - result[asset_class]["short"]
            )
        
        return result
    
    def get_full_exposures(self, positions: List[Position]) -> ExposuresResponse:
        """
        Get full exposure response.
        
        Args:
            positions: List of portfolio positions
        
        Returns:
            ExposuresResponse with all exposure metrics
        """
        basic = self.calculate_exposures(positions)
        asset = self.calculate_asset_exposure(positions)
        
        return ExposuresResponse(
            net_exposure=basic["net_exposure"],
            gross_exposure=basic["gross_exposure"],
            btc_exposure=asset["btc_exposure"],
            eth_exposure=asset["eth_exposure"],
            alt_exposure=asset["alt_exposure"],
            long_exposure=basic["long_exposure"],
            short_exposure=basic["short_exposure"],
            timestamp=datetime.now(timezone.utc),
        )


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[PortfolioExposureEngine] = None


def get_portfolio_exposure_engine() -> PortfolioExposureEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = PortfolioExposureEngine()
    return _engine
