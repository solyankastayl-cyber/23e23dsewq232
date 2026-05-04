"""
Portfolio Engine - Capital allocation and position sizing

Answers: "HOW MUCH CAPITAL FOR EACH TRADE?"

Factors:
- Kelly criterion (optimal sizing)
- Portfolio correlation (reduce correlated bets)
- Concentration limits (max % per symbol)
- Risk budget (total portfolio risk)
- Volatility adjustment
"""

from typing import Dict, List, Any
import math


class PortfolioEngine:
    """Portfolio-level capital allocation and sizing"""
    
    def __init__(
        self,
        max_portfolio_risk: float = 0.30,  # 30% max portfolio risk
        max_symbol_concentration: float = 0.20,  # 20% max per symbol
        max_correlation_exposure: float = 0.40,  # 40% max to correlated group
        base_risk_per_trade: float = 0.02,  # 2% base risk per trade
    ):
        self.max_portfolio_risk = max_portfolio_risk
        self.max_symbol_concentration = max_symbol_concentration
        self.max_correlation_exposure = max_correlation_exposure
        self.base_risk_per_trade = base_risk_per_trade
    
    def calculate_position_size(
        self,
        signal: Dict[str, Any],
        portfolio: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        risk_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size for a signal
        
        Args:
            signal: {symbol, entry, stop, target, confidence, kelly_fraction, ...}
            portfolio: {equity, balance, risk_heat, ...}
            open_positions: List of current positions
            risk_multiplier: From risk engine (0.0 - 1.0)
        
        Returns:
            {size_usd, size_units, risk_amount, justification}
        """
        equity = portfolio.get("equity", 10000)
        current_heat = portfolio.get("risk_heat", 0)
        
        symbol = signal.get("symbol")
        entry = signal.get("entry", 0)
        stop = signal.get("stop", 0)
        kelly = signal.get("kelly_fraction", 0.02)
        
        # 1. BASE SIZING (Kelly adjusted)
        base_size = equity * self.base_risk_per_trade * kelly
        
        # 2. RISK ENGINE ADJUSTMENT
        base_size *= risk_multiplier
        
        # 3. PORTFOLIO HEAT ADJUSTMENT
        # Reduce size if portfolio is already hot
        remaining_heat = self.max_portfolio_risk - current_heat
        if remaining_heat < 0.05:  # Less than 5% heat budget left
            base_size *= 0.5
        
        # 4. CONCENTRATION CHECK
        # Check if we already have position on this symbol
        existing_exposure = sum(
            p.get("size_usd", 0) 
            for p in open_positions 
            if p.get("symbol") == symbol and p.get("status") == "OPEN"
        )
        
        max_symbol_size = equity * self.max_symbol_concentration
        if existing_exposure > 0:
            # Already have position - reduce new size
            available_for_symbol = max_symbol_size - existing_exposure
            if available_for_symbol <= 0:
                return {
                    "size_usd": 0,
                    "size_units": 0,
                    "risk_amount": 0,
                    "justification": "concentration_limit_reached",
                    "rejected": True,
                }
            base_size = min(base_size, available_for_symbol)
        
        # 5. CORRELATION PENALTY
        # Reduce size if portfolio has correlated positions
        correlation_penalty = self._calculate_correlation_penalty(
            symbol, open_positions
        )
        base_size *= correlation_penalty
        
        # 6. STOP DISTANCE SIZING
        # Calculate actual units based on stop distance
        if entry > 0 and stop > 0:
            stop_distance_pct = abs(entry - stop) / entry
            if stop_distance_pct > 0:
                # Risk amount is percentage of equity willing to lose
                risk_amount = base_size * stop_distance_pct
                # Position size in USD
                size_usd = base_size
                # Position size in units (for crypto)
                size_units = size_usd / entry if entry > 0 else 0
            else:
                return {
                    "size_usd": 0,
                    "size_units": 0,
                    "risk_amount": 0,
                    "justification": "invalid_stop_distance",
                    "rejected": True,
                }
        else:
            return {
                "size_usd": 0,
                "size_units": 0,
                "risk_amount": 0,
                "justification": "missing_entry_or_stop",
                "rejected": True,
            }
        
        # 7. FINAL SIZE CAP (sanity check)
        max_size_per_trade = equity * 0.15  # Never more than 15% per trade
        size_usd = min(size_usd, max_size_per_trade)
        size_units = size_usd / entry if entry > 0 else 0
        
        return {
            "size_usd": round(size_usd, 2),
            "size_units": round(size_units, 6),
            "risk_amount": round(risk_amount, 2),
            "justification": "normal_sizing",
            "rejected": False,
            "sizing_factors": {
                "kelly": kelly,
                "risk_multiplier": risk_multiplier,
                "correlation_penalty": correlation_penalty,
                "stop_distance_pct": stop_distance_pct,
            }
        }
    
    def _calculate_correlation_penalty(
        self,
        symbol: str,
        open_positions: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate penalty for correlated positions
        
        Simple heuristic:
        - BTC vs other crypto: 0.8 (20% penalty)
        - Same category (e.g., all ALTs): 0.7 (30% penalty)
        - Different categories: 1.0 (no penalty)
        """
        if not open_positions:
            return 1.0
        
        # Count BTC exposure
        has_btc = any(p.get("symbol") == "BTCUSDT" for p in open_positions)
        
        # If adding BTC and already have alts (or vice versa)
        if symbol == "BTCUSDT" and len(open_positions) > 0:
            return 0.8  # Reduce 20%
        
        if symbol != "BTCUSDT" and has_btc:
            return 0.8  # Reduce 20%
        
        # If adding another alt when already have alts
        if symbol != "BTCUSDT" and len([p for p in open_positions if p.get("symbol") != "BTCUSDT"]) > 0:
            return 0.7  # Reduce 30%
        
        return 1.0  # No penalty


# Global instance
_portfolio_engine = None

def get_portfolio_engine() -> PortfolioEngine:
    """Get global portfolio engine instance"""
    global _portfolio_engine
    if _portfolio_engine is None:
        _portfolio_engine = PortfolioEngine()
    return _portfolio_engine
