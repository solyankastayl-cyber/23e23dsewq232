"""
Imbalance Detector
==================

Детектор зон дисбаланса (FVG - Fair Value Gap) и Order Blocks.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .structure_types import (
    Imbalance,
    ImbalanceType
)


class ImbalanceDetector:
    """
    Детектор зон дисбаланса.
    
    Fair Value Gap (FVG):
    - Bullish FVG: gap между high[i-1] и low[i+1]
    - Bearish FVG: gap между low[i-1] и high[i+1]
    
    Order Block:
    - Bullish OB: последняя медвежья свеча перед импульсом вверх
    - Bearish OB: последняя бычья свеча перед импульсом вниз
    """
    
    def __init__(
        self,
        min_gap_pct: float = 0.1,    # Минимальный % для FVG
        min_impulse_pct: float = 1.0, # Минимальный % для импульса
        ob_lookback: int = 3          # Lookback для Order Block
    ):
        self.min_gap_pct = min_gap_pct
        self.min_impulse_pct = min_impulse_pct
        self.ob_lookback = ob_lookback
    
    def detect(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        Детектирование зон дисбаланса.
        """
        if len(highs) < 10:
            return self._empty_result()
        
        if timestamps is None:
            timestamps = [datetime.utcnow() for _ in range(len(highs))]
        
        imbalances = []
        
        # Detect FVG
        fvg_zones = self._detect_fvg(opens, highs, lows, closes, timestamps)
        imbalances.extend(fvg_zones)
        
        # Detect Order Blocks
        ob_zones = self._detect_order_blocks(opens, highs, lows, closes, timestamps)
        imbalances.extend(ob_zones)
        
        # Check which imbalances are filled
        self._check_filled(imbalances, highs, lows)
        
        return {
            "imbalances": imbalances,
            "active_imbalances": sum(1 for i in imbalances if i.active)
        }
    
    def _detect_fvg(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        timestamps: List[datetime]
    ) -> List[Imbalance]:
        """Детектировать Fair Value Gaps"""
        fvg_zones = []
        
        for i in range(1, len(highs) - 1):
            # Bullish FVG: gap up
            # high[i-1] < low[i+1] - there's a gap
            if highs[i-1] < lows[i+1]:
                gap_size = lows[i+1] - highs[i-1]
                gap_pct = gap_size / highs[i-1] * 100
                
                if gap_pct >= self.min_gap_pct:
                    # Check if middle candle is impulse
                    candle_size = abs(closes[i] - opens[i])
                    if candle_size / opens[i] * 100 >= self.min_impulse_pct * 0.5:
                        fvg_zones.append(Imbalance(
                            imbalance_type=ImbalanceType.BULLISH_FVG,
                            high=lows[i+1],
                            low=highs[i-1],
                            midpoint=(lows[i+1] + highs[i-1]) / 2,
                            strength=min(1.0, gap_pct / 1.0),
                            timestamp=timestamps[i] if i < len(timestamps) else datetime.utcnow(),
                            candle_index=i,
                            notes=f"Bullish FVG: {gap_pct:.2f}% gap"
                        ))
            
            # Bearish FVG: gap down
            # low[i-1] > high[i+1] - there's a gap
            if lows[i-1] > highs[i+1]:
                gap_size = lows[i-1] - highs[i+1]
                gap_pct = gap_size / lows[i-1] * 100
                
                if gap_pct >= self.min_gap_pct:
                    candle_size = abs(closes[i] - opens[i])
                    if candle_size / opens[i] * 100 >= self.min_impulse_pct * 0.5:
                        fvg_zones.append(Imbalance(
                            imbalance_type=ImbalanceType.BEARISH_FVG,
                            high=lows[i-1],
                            low=highs[i+1],
                            midpoint=(lows[i-1] + highs[i+1]) / 2,
                            strength=min(1.0, gap_pct / 1.0),
                            timestamp=timestamps[i] if i < len(timestamps) else datetime.utcnow(),
                            candle_index=i,
                            notes=f"Bearish FVG: {gap_pct:.2f}% gap"
                        ))
        
        return fvg_zones
    
    def _detect_order_blocks(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        timestamps: List[datetime]
    ) -> List[Imbalance]:
        """Детектировать Order Blocks"""
        ob_zones = []
        
        for i in range(self.ob_lookback, len(highs) - 1):
            # Check for impulse move
            impulse_size = abs(closes[i] - opens[i])
            impulse_pct = impulse_size / opens[i] * 100
            
            if impulse_pct < self.min_impulse_pct:
                continue
            
            # Bullish impulse - look for bearish candle before
            if closes[i] > opens[i]:
                # Find last bearish candle in lookback
                for j in range(i-1, max(0, i-self.ob_lookback-1), -1):
                    if closes[j] < opens[j]:
                        # Found bearish candle - this is potential OB
                        ob_zones.append(Imbalance(
                            imbalance_type=ImbalanceType.BULLISH_OB,
                            high=highs[j],
                            low=lows[j],
                            midpoint=(highs[j] + lows[j]) / 2,
                            strength=min(1.0, impulse_pct / 2.0),
                            timestamp=timestamps[j] if j < len(timestamps) else datetime.utcnow(),
                            candle_index=j,
                            notes=f"Bullish OB before {impulse_pct:.2f}% impulse"
                        ))
                        break
            
            # Bearish impulse - look for bullish candle before
            elif closes[i] < opens[i]:
                for j in range(i-1, max(0, i-self.ob_lookback-1), -1):
                    if closes[j] > opens[j]:
                        ob_zones.append(Imbalance(
                            imbalance_type=ImbalanceType.BEARISH_OB,
                            high=highs[j],
                            low=lows[j],
                            midpoint=(highs[j] + lows[j]) / 2,
                            strength=min(1.0, impulse_pct / 2.0),
                            timestamp=timestamps[j] if j < len(timestamps) else datetime.utcnow(),
                            candle_index=j,
                            notes=f"Bearish OB before {impulse_pct:.2f}% impulse"
                        ))
                        break
        
        return ob_zones
    
    def _check_filled(
        self,
        imbalances: List[Imbalance],
        highs: List[float],
        lows: List[float]
    ):
        """Проверить заполненность зон"""
        for imb in imbalances:
            if imb.candle_index >= len(highs) - 1:
                continue
            
            # Check candles after the imbalance
            for i in range(imb.candle_index + 1, len(highs)):
                filled = False
                fill_pct = 0.0
                
                if imb.imbalance_type in [ImbalanceType.BULLISH_FVG, ImbalanceType.BULLISH_OB]:
                    # Price needs to come down to fill
                    if lows[i] <= imb.midpoint:
                        filled = True
                        fill_pct = min(100.0, (imb.high - lows[i]) / (imb.high - imb.low) * 100)
                elif imb.imbalance_type in [ImbalanceType.BEARISH_FVG, ImbalanceType.BEARISH_OB]:
                    # Price needs to come up to fill
                    if highs[i] >= imb.midpoint:
                        filled = True
                        fill_pct = min(100.0, (highs[i] - imb.low) / (imb.high - imb.low) * 100)
                
                if filled:
                    imb.filled_pct = fill_pct
                    if fill_pct >= 50:
                        imb.active = False
                    break
    
    def _empty_result(self) -> Dict[str, Any]:
        """Пустой результат"""
        return {
            "imbalances": [],
            "active_imbalances": 0
        }
