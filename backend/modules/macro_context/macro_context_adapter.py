"""
PHASE 25.1 — Macro Context Adapter

Maps external macro data sources to normalized MacroInput.
Pure transformation layer with no business logic.

This adapter can work with:
- Manual input
- External macro APIs
- CSV/file-based macro data
- Database-stored macro indicators
"""

from typing import Optional, Dict, Any
from datetime import datetime

from .macro_context_types import MacroInput


class MacroContextAdapter:
    """
    Adapter that transforms raw macro data into normalized MacroInput.
    
    All outputs are normalized to [-1.0, +1.0]:
    - -1 = bearish / tightening / contraction
    -  0 = neutral
    - +1 = bullish / easing / expansion
    """
    
    @staticmethod
    def clamp(value: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))
    
    @staticmethod
    def normalize_to_range(
        value: float,
        min_input: float,
        max_input: float,
        invert: bool = False
    ) -> float:
        """
        Normalize value from [min_input, max_input] to [-1, +1].
        
        Args:
            value: Raw value
            min_input: Expected minimum
            max_input: Expected maximum
            invert: If True, flip the sign
        
        Returns:
            Normalized value in [-1, +1]
        """
        if max_input == min_input:
            return 0.0
        
        # Normalize to [0, 1]
        normalized = (value - min_input) / (max_input - min_input)
        # Convert to [-1, +1]
        result = 2 * normalized - 1
        
        if invert:
            result = -result
        
        return MacroContextAdapter.clamp(result)
    
    def adapt_from_dict(self, raw_data: Dict[str, Any]) -> MacroInput:
        """
        Transform raw macro data dict into normalized MacroInput.
        
        Expected keys (all optional):
        - inflation, inflation_yoy, cpi
        - rates, fed_rate, interest_rate
        - labor, nfp, payrolls
        - unemployment, unemployment_rate
        - housing, home_sales, permits
        - growth, gdp, gdp_growth
        - liquidity, m2, fed_balance
        - credit, credit_spread, yield_spread
        - consumer, sentiment, consumer_confidence
        """
        
        # Inflation: higher = more hawkish pressure
        inflation = self._extract_inflation(raw_data)
        
        # Rates: higher = more hawkish
        rates = self._extract_rates(raw_data)
        
        # Labor market: stronger = bullish
        labor = self._extract_labor(raw_data)
        
        # Unemployment: lower = better (we invert)
        unemployment = self._extract_unemployment(raw_data)
        
        # Housing: stronger = bullish
        housing = self._extract_housing(raw_data)
        
        # Growth: stronger = bullish
        growth = self._extract_growth(raw_data)
        
        # Liquidity: more = bullish
        liquidity = self._extract_liquidity(raw_data)
        
        # Credit: easier = bullish
        credit = self._extract_credit(raw_data)
        
        # Consumer: stronger = bullish
        consumer = self._extract_consumer(raw_data)
        
        return MacroInput(
            inflation_signal=inflation,
            rates_signal=rates,
            labor_market_signal=labor,
            unemployment_signal=unemployment,
            housing_signal=housing,
            growth_signal=growth,
            liquidity_signal=liquidity,
            credit_signal=credit,
            consumer_signal=consumer,
            timestamp=datetime.utcnow(),
            source=raw_data.get("source", "dict"),
        )
    
    def _extract_inflation(self, data: Dict[str, Any]) -> float:
        """Extract inflation signal."""
        # Try different keys
        for key in ["inflation_signal", "inflation", "cpi", "inflation_yoy"]:
            if key in data and data[key] is not None:
                val = float(data[key])
                # If raw percentage (e.g., 3.5 for 3.5%)
                if key in ["inflation", "cpi", "inflation_yoy"]:
                    # Normalize: 0% = neutral, 2% = 0, 4%+ = +1, <0 = -1
                    return self.normalize_to_range(val, 0.0, 6.0)
                return self.clamp(val)
        return 0.0
    
    def _extract_rates(self, data: Dict[str, Any]) -> float:
        """Extract rates signal."""
        for key in ["rates_signal", "rates", "fed_rate", "interest_rate"]:
            if key in data and data[key] is not None:
                val = float(data[key])
                if key in ["fed_rate", "interest_rate"]:
                    # Normalize: 0% = -1, 2.5% = 0, 5%+ = +1
                    return self.normalize_to_range(val, 0.0, 5.0)
                return self.clamp(val)
        return 0.0
    
    def _extract_labor(self, data: Dict[str, Any]) -> float:
        """Extract labor market signal."""
        for key in ["labor_market_signal", "labor", "nfp", "payrolls"]:
            if key in data and data[key] is not None:
                val = float(data[key])
                if key in ["nfp", "payrolls"]:
                    # NFP: negative = bearish, 0 = neutral, 200K+ = bullish
                    return self.normalize_to_range(val, -100000, 300000)
                return self.clamp(val)
        return 0.0
    
    def _extract_unemployment(self, data: Dict[str, Any]) -> float:
        """Extract unemployment signal (inverted: lower = better)."""
        for key in ["unemployment_signal", "unemployment", "unemployment_rate"]:
            if key in data and data[key] is not None:
                val = float(data[key])
                if key in ["unemployment", "unemployment_rate"]:
                    # 3% = +1 (good), 5% = 0 (neutral), 8%+ = -1 (bad)
                    return self.normalize_to_range(val, 8.0, 3.0)  # Inverted range
                return self.clamp(val)
        return 0.0
    
    def _extract_housing(self, data: Dict[str, Any]) -> float:
        """Extract housing signal."""
        for key in ["housing_signal", "housing", "home_sales", "permits"]:
            if key in data and data[key] is not None:
                return self.clamp(float(data[key]))
        return 0.0
    
    def _extract_growth(self, data: Dict[str, Any]) -> float:
        """Extract growth signal."""
        for key in ["growth_signal", "growth", "gdp", "gdp_growth"]:
            if key in data and data[key] is not None:
                val = float(data[key])
                if key in ["gdp", "gdp_growth"]:
                    # GDP: -2% = -1, 0% = neutral, 4%+ = +1
                    return self.normalize_to_range(val, -2.0, 4.0)
                return self.clamp(val)
        return 0.0
    
    def _extract_liquidity(self, data: Dict[str, Any]) -> float:
        """Extract liquidity signal."""
        for key in ["liquidity_signal", "liquidity", "m2_growth", "fed_balance"]:
            if key in data and data[key] is not None:
                return self.clamp(float(data[key]))
        return 0.0
    
    def _extract_credit(self, data: Dict[str, Any]) -> float:
        """Extract credit signal."""
        for key in ["credit_signal", "credit", "credit_spread", "yield_spread"]:
            if key in data and data[key] is not None:
                val = float(data[key])
                if key in ["credit_spread", "yield_spread"]:
                    # Wider spread = tighter credit = bearish
                    # 0bp = +1, 100bp = 0, 300bp+ = -1
                    return self.normalize_to_range(val, 300, 0)  # Inverted
                return self.clamp(val)
        return 0.0
    
    def _extract_consumer(self, data: Dict[str, Any]) -> float:
        """Extract consumer signal."""
        for key in ["consumer_signal", "consumer", "sentiment", "consumer_confidence"]:
            if key in data and data[key] is not None:
                val = float(data[key])
                if key in ["sentiment", "consumer_confidence"]:
                    # Michigan sentiment: 50 = -1, 75 = 0, 100+ = +1
                    return self.normalize_to_range(val, 50.0, 100.0)
                return self.clamp(val)
        return 0.0
    
    def create_manual_input(
        self,
        inflation: float = 0.0,
        rates: float = 0.0,
        labor: float = 0.0,
        unemployment: float = 0.0,
        housing: float = 0.0,
        growth: float = 0.0,
        liquidity: float = 0.0,
        credit: float = 0.0,
        consumer: float = 0.0,
    ) -> MacroInput:
        """
        Create MacroInput from direct normalized values.
        
        All values should already be in [-1.0, +1.0].
        """
        return MacroInput(
            inflation_signal=self.clamp(inflation),
            rates_signal=self.clamp(rates),
            labor_market_signal=self.clamp(labor),
            unemployment_signal=self.clamp(unemployment),
            housing_signal=self.clamp(housing),
            growth_signal=self.clamp(growth),
            liquidity_signal=self.clamp(liquidity),
            credit_signal=self.clamp(credit),
            consumer_signal=self.clamp(consumer),
            timestamp=datetime.utcnow(),
            source="manual",
        )


# ══════════════════════════════════════════════════════════════
# Default Adapter Instance
# ══════════════════════════════════════════════════════════════

_adapter: Optional[MacroContextAdapter] = None


def get_macro_adapter() -> MacroContextAdapter:
    """Get singleton adapter instance."""
    global _adapter
    if _adapter is None:
        _adapter = MacroContextAdapter()
    return _adapter
