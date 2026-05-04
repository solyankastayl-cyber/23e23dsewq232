"""
Liquidity Impact Engine
=======================

Анализ влияния ордера на ликвидность рынка.
"""

from typing import Dict, Any, List, Optional
from .slippage_types import LiquidityImpactResult, LiquidityImpact


class LiquidityImpactEngine:
    """
    Engine для анализа влияния на ликвидность.
    
    Метрики:
    - Size vs market depth
    - Spread impact
    - Market movement after execution
    - Execution efficiency
    """
    
    def __init__(
        self,
        negligible_impact_pct: float = 0.01,
        low_impact_pct: float = 0.05,
        moderate_impact_pct: float = 0.1,
        high_impact_pct: float = 0.5
    ):
        self.negligible = negligible_impact_pct
        self.low = low_impact_pct
        self.moderate = moderate_impact_pct
        self.high = high_impact_pct
    
    def analyze(
        self,
        order_size: float,
        executed_price: float,
        # Market data
        market_depth: float = 0.0,
        spread_before: float = 0.0,
        spread_after: float = 0.0,
        price_before: float = 0.0,
        price_after: float = 0.0,
        # Context
        side: str = "BUY",
        symbol: str = "BTCUSDT"
    ) -> LiquidityImpactResult:
        """
        Анализ влияния на ликвидность.
        
        Args:
            order_size: Размер ордера в base currency
            executed_price: Цена исполнения
            market_depth: Оценка глубины рынка (в base currency)
            spread_before: Спред до исполнения
            spread_after: Спред после исполнения
            price_before: Цена до исполнения
            price_after: Цена после исполнения
            side: BUY/SELL
            
        Returns:
            LiquidityImpactResult
        """
        # Calculate order value
        order_value = order_size * executed_price
        
        # Size vs depth ratio
        if market_depth > 0:
            size_ratio = order_value / market_depth
        else:
            # Estimate depth based on order value
            estimated_depth = order_value * 10  # Assume order is 10% of visible depth
            size_ratio = 0.1
            market_depth = estimated_depth
        
        # Spread impact
        spread_impact = 0.0
        if spread_before > 0:
            spread_impact = (spread_after - spread_before) / spread_before * 100 if spread_after else 0
        
        # Market movement
        market_move_pct = 0.0
        if price_before > 0 and price_after > 0:
            market_move_pct = abs(price_after - price_before) / price_before * 100
        elif price_before > 0:
            # Use executed price as "after"
            market_move_pct = abs(executed_price - price_before) / price_before * 100
        
        # Determine impact level
        impact_level = self._determine_impact_level(market_move_pct, size_ratio)
        
        # Liquidity score (1 = excellent liquidity, 0 = poor)
        liquidity_score = self._calculate_liquidity_score(size_ratio, spread_impact, market_move_pct)
        
        # Execution efficiency
        efficiency = self._calculate_efficiency(market_move_pct, side, size_ratio)
        
        # Notes
        notes = self._generate_notes(impact_level, market_move_pct, size_ratio)
        
        return LiquidityImpactResult(
            order_size=order_size,
            market_depth_estimate=round(market_depth, 2),
            size_vs_depth_ratio=round(size_ratio, 4),
            spread_before=spread_before,
            spread_after=spread_after,
            spread_impact=round(spread_impact, 4),
            price_before=price_before,
            price_after=price_after if price_after > 0 else executed_price,
            market_move_percent=round(market_move_pct, 4),
            impact_level=impact_level,
            liquidity_score=round(liquidity_score, 4),
            execution_efficiency=round(efficiency, 4),
            notes=notes
        )
    
    def estimate_impact(
        self,
        order_size: float,
        current_price: float,
        avg_daily_volume: float = 0.0,
        current_spread_pct: float = 0.05,
        volatility: float = 0.02
    ) -> Dict[str, Any]:
        """
        Оценить потенциальное влияние перед исполнением.
        
        Args:
            order_size: Размер ордера
            current_price: Текущая цена
            avg_daily_volume: Средний дневной объём
            current_spread_pct: Текущий спред в %
            volatility: Волатильность
            
        Returns:
            Оценка влияния
        """
        order_value = order_size * current_price
        
        # Estimate depth from daily volume
        if avg_daily_volume > 0:
            estimated_depth = avg_daily_volume * 0.01  # 1% of daily volume
        else:
            estimated_depth = order_value * 20  # Assume we're 5% of depth
        
        # Size ratio
        size_ratio = order_value / estimated_depth
        
        # Estimated market impact
        base_impact = size_ratio * 0.1 * 100  # Base impact in bps
        vol_adjustment = volatility * 50  # Volatility adds to impact
        spread_adjustment = current_spread_pct * 0.5  # Wider spread = more impact
        
        estimated_impact_bps = base_impact + vol_adjustment + spread_adjustment
        estimated_impact_pct = estimated_impact_bps / 100
        
        # Determine predicted level
        if estimated_impact_pct < self.negligible:
            predicted_level = "NEGLIGIBLE"
        elif estimated_impact_pct < self.low:
            predicted_level = "LOW"
        elif estimated_impact_pct < self.moderate:
            predicted_level = "MODERATE"
        elif estimated_impact_pct < self.high:
            predicted_level = "HIGH"
        else:
            predicted_level = "SEVERE"
        
        return {
            "order_size": order_size,
            "order_value": round(order_value, 2),
            "estimated_depth": round(estimated_depth, 2),
            "size_vs_depth": round(size_ratio, 4),
            "estimated_impact_bps": round(estimated_impact_bps, 2),
            "estimated_impact_pct": round(estimated_impact_pct, 4),
            "predicted_level": predicted_level,
            "recommendation": self._get_recommendation(predicted_level, size_ratio)
        }
    
    def _determine_impact_level(
        self,
        market_move_pct: float,
        size_ratio: float
    ) -> LiquidityImpact:
        """Определить уровень влияния"""
        # Use market move as primary indicator
        if market_move_pct < self.negligible:
            return LiquidityImpact.NEGLIGIBLE
        elif market_move_pct < self.low:
            return LiquidityImpact.LOW
        elif market_move_pct < self.moderate:
            return LiquidityImpact.MODERATE
        elif market_move_pct < self.high:
            return LiquidityImpact.HIGH
        else:
            return LiquidityImpact.SEVERE
    
    def _calculate_liquidity_score(
        self,
        size_ratio: float,
        spread_impact: float,
        market_move: float
    ) -> float:
        """Рассчитать liquidity score"""
        score = 1.0
        
        # Penalize for high size ratio
        score -= min(0.3, size_ratio * 0.3)
        
        # Penalize for spread widening
        if spread_impact > 0:
            score -= min(0.2, spread_impact / 100 * 0.2)
        
        # Penalize for market movement
        score -= min(0.4, market_move / 1.0 * 0.4)
        
        return max(0.0, score)
    
    def _calculate_efficiency(
        self,
        market_move: float,
        side: str,
        size_ratio: float
    ) -> float:
        """Рассчитать execution efficiency"""
        # Perfect efficiency = 1.0 (no market impact)
        efficiency = 1.0
        
        # Reduce based on market movement
        efficiency -= min(0.5, market_move / 1.0 * 0.5)
        
        # Reduce based on size ratio
        efficiency -= min(0.3, size_ratio * 0.3)
        
        return max(0.0, efficiency)
    
    def _generate_notes(
        self,
        impact: LiquidityImpact,
        market_move: float,
        size_ratio: float
    ) -> str:
        """Генерация заметок"""
        parts = []
        
        impact_notes = {
            LiquidityImpact.NEGLIGIBLE: "Negligible market impact",
            LiquidityImpact.LOW: "Low market impact - acceptable",
            LiquidityImpact.MODERATE: "Moderate impact - consider splitting",
            LiquidityImpact.HIGH: "High impact - recommend order splitting",
            LiquidityImpact.SEVERE: "Severe impact - review execution strategy"
        }
        
        parts.append(impact_notes.get(impact, ""))
        
        if size_ratio > 0.1:
            parts.append(f"Order size: {size_ratio:.1%} of market depth")
        
        if market_move > 0.1:
            parts.append(f"Market moved {market_move:.2f}% during execution")
        
        return " | ".join(filter(None, parts))
    
    def _get_recommendation(self, level: str, size_ratio: float) -> str:
        """Получить рекомендацию"""
        if level in ["NEGLIGIBLE", "LOW"]:
            return "Execute as single order"
        elif level == "MODERATE":
            return "Consider TWAP execution"
        elif level == "HIGH":
            return "Recommend TWAP/VWAP execution over 5-10 intervals"
        else:
            return "Recommend aggressive splitting or iceberg orders"
