"""
Slippage Calculator
===================

Расчёт проскальзывания между ожидаемой и фактической ценой.
"""

from typing import Dict, Any, Optional
from .slippage_types import SlippageResult, SlippageDirection


class SlippageCalculator:
    """
    Calculator для расчёта проскальзывания.
    
    Slippage = (Executed Price - Expected Price) / Expected Price
    
    Для BUY:
    - Favorable: executed < expected (купили дешевле)
    - Unfavorable: executed > expected (купили дороже)
    
    Для SELL:
    - Favorable: executed > expected (продали дороже)
    - Unfavorable: executed < expected (продали дешевле)
    """
    
    def __init__(self, zero_threshold_bps: float = 0.5):
        """
        Args:
            zero_threshold_bps: Порог для считания slippage нулевым (в bps)
        """
        self.zero_threshold_bps = zero_threshold_bps
    
    def calculate(
        self,
        expected_price: float,
        executed_price: float,
        side: str = "BUY",
        quantity: float = 0.0
    ) -> SlippageResult:
        """
        Рассчитать проскальзывание.
        
        Args:
            expected_price: Ожидаемая цена исполнения
            executed_price: Фактическая цена исполнения
            side: BUY или SELL
            quantity: Количество (для информации)
            
        Returns:
            SlippageResult с расчётами
        """
        if expected_price <= 0:
            return self._zero_result(expected_price, executed_price, side)
        
        # Calculate slippage
        slippage_absolute = executed_price - expected_price
        slippage_percent = (slippage_absolute / expected_price) * 100
        slippage_bps = slippage_percent * 100  # 1% = 100 bps
        
        # Determine direction and favorability
        direction, is_favorable = self._determine_direction(
            slippage_bps, side
        )
        
        # Generate notes
        notes = self._generate_notes(
            slippage_percent, direction, is_favorable, side
        )
        
        return SlippageResult(
            expected_price=expected_price,
            executed_price=executed_price,
            slippage_absolute=round(slippage_absolute, 8),
            slippage_bps=round(slippage_bps, 4),
            slippage_percent=round(slippage_percent, 6),
            direction=direction,
            side=side,
            is_favorable=is_favorable,
            notes=notes
        )
    
    def calculate_from_fills(
        self,
        expected_price: float,
        fills: list,
        side: str = "BUY"
    ) -> SlippageResult:
        """
        Рассчитать проскальзывание из множественных fills.
        
        Args:
            expected_price: Ожидаемая цена
            fills: Список fills [{"price": float, "quantity": float}, ...]
            side: BUY или SELL
            
        Returns:
            SlippageResult с VWAP executed price
        """
        if not fills:
            return self._zero_result(expected_price, expected_price, side)
        
        # Calculate VWAP
        total_value = sum(f.get("price", 0) * f.get("quantity", 0) for f in fills)
        total_quantity = sum(f.get("quantity", 0) for f in fills)
        
        if total_quantity <= 0:
            return self._zero_result(expected_price, expected_price, side)
        
        vwap_price = total_value / total_quantity
        
        result = self.calculate(expected_price, vwap_price, side, total_quantity)
        result.notes += f" | VWAP from {len(fills)} fills"
        
        return result
    
    def _determine_direction(
        self,
        slippage_bps: float,
        side: str
    ) -> tuple:
        """Определить направление и благоприятность"""
        abs_slippage = abs(slippage_bps)
        
        # Check if effectively zero
        if abs_slippage < self.zero_threshold_bps:
            return SlippageDirection.ZERO, True
        
        # Determine direction based on side
        if side == "BUY":
            if slippage_bps < 0:
                # Bought cheaper than expected
                return SlippageDirection.FAVORABLE, True
            else:
                # Bought more expensive
                return SlippageDirection.UNFAVORABLE, False
        else:  # SELL
            if slippage_bps > 0:
                # Sold higher than expected
                return SlippageDirection.FAVORABLE, True
            else:
                # Sold lower
                return SlippageDirection.UNFAVORABLE, False
    
    def _generate_notes(
        self,
        slippage_percent: float,
        direction: SlippageDirection,
        is_favorable: bool,
        side: str
    ) -> str:
        """Генерация заметок"""
        if direction == SlippageDirection.ZERO:
            return "Minimal slippage - excellent execution"
        
        abs_slip = abs(slippage_percent)
        
        if abs_slip > 0.5:
            severity = "HIGH"
        elif abs_slip > 0.1:
            severity = "MODERATE"
        else:
            severity = "LOW"
        
        favor_text = "favorable" if is_favorable else "unfavorable"
        
        return f"{severity} {favor_text} slippage ({abs_slip:.4f}%) for {side} order"
    
    def _zero_result(
        self,
        expected: float,
        executed: float,
        side: str
    ) -> SlippageResult:
        """Нулевой результат"""
        return SlippageResult(
            expected_price=expected,
            executed_price=executed,
            slippage_absolute=0.0,
            slippage_bps=0.0,
            slippage_percent=0.0,
            direction=SlippageDirection.ZERO,
            side=side,
            is_favorable=True,
            notes="Zero slippage"
        )
    
    def estimate_slippage(
        self,
        symbol: str,
        side: str,
        quantity: float,
        current_price: float,
        volatility: float = 0.01,
        liquidity_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Оценить ожидаемое проскальзывание.
        
        Args:
            symbol: Символ
            side: BUY/SELL
            quantity: Размер ордера
            current_price: Текущая цена
            volatility: Волатильность (0-1)
            liquidity_factor: Фактор ликвидности (0-1, где 1 = высокая)
            
        Returns:
            Оценка ожидаемого slippage
        """
        # Base slippage estimate
        base_slippage_bps = 2.0  # 2 bps base
        
        # Adjust for volatility
        vol_adjustment = volatility * 50  # High vol = more slippage
        
        # Adjust for liquidity
        liq_adjustment = (1 - liquidity_factor) * 30  # Low liq = more slippage
        
        # Adjust for size (simplified)
        size_factor = min(1.0, quantity * current_price / 100000)  # $100k threshold
        size_adjustment = size_factor * 20
        
        estimated_bps = base_slippage_bps + vol_adjustment + liq_adjustment + size_adjustment
        estimated_percent = estimated_bps / 100
        
        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "current_price": current_price,
            "estimated_slippage_bps": round(estimated_bps, 2),
            "estimated_slippage_percent": round(estimated_percent, 4),
            "estimated_executed_price": round(
                current_price * (1 + estimated_percent / 100) if side == "BUY" 
                else current_price * (1 - estimated_percent / 100), 2
            ),
            "factors": {
                "base": base_slippage_bps,
                "volatility_adj": round(vol_adjustment, 2),
                "liquidity_adj": round(liq_adjustment, 2),
                "size_adj": round(size_adjustment, 2)
            }
        }
