"""
Fill Quality Analyzer
====================

Анализ качества заполнения ордеров.
"""

from typing import Dict, Any, List, Optional
from .slippage_types import FillAnalysis, FillQuality


class FillQualityAnalyzer:
    """
    Analyzer для оценки качества заполнения.
    
    Метрики:
    - Fill rate: % заполнения ордера
    - Fragmentation: степень фрагментации
    - Consistency: равномерность fills
    """
    
    def __init__(
        self,
        excellent_fragmentation: float = 0.1,  # <= 10% fragmentation
        good_fragmentation: float = 0.3,       # <= 30% fragmentation
        fair_fragmentation: float = 0.6        # <= 60% fragmentation
    ):
        self.excellent_threshold = excellent_fragmentation
        self.good_threshold = good_fragmentation
        self.fair_threshold = fair_fragmentation
    
    def analyze(
        self,
        total_quantity: float,
        fills: List[Dict[str, Any]]
    ) -> FillAnalysis:
        """
        Анализ качества заполнения.
        
        Args:
            total_quantity: Запрошенное количество
            fills: Список fills [{"quantity": float, "price": float}, ...]
            
        Returns:
            FillAnalysis с метриками
        """
        if not fills or total_quantity <= 0:
            return self._empty_result(total_quantity)
        
        # Extract quantities
        fill_quantities = [f.get("quantity", 0) for f in fills]
        filled_quantity = sum(fill_quantities)
        
        # Fill rate
        fill_rate = min(1.0, filled_quantity / total_quantity)
        
        # Fragmentation score (0 = one fill, 1 = many small fills)
        fragmentation = self._calculate_fragmentation(fill_quantities, filled_quantity)
        
        # Consistency score
        consistency = self._calculate_consistency(fill_quantities)
        
        # Determine quality
        quality = self._determine_quality(fill_rate, fragmentation, len(fills))
        
        # Statistics
        avg_fill = filled_quantity / len(fills) if fills else 0
        largest = max(fill_quantities) if fill_quantities else 0
        smallest = min(fill_quantities) if fill_quantities else 0
        
        # Notes
        notes = self._generate_notes(fill_rate, fragmentation, quality, len(fills))
        
        return FillAnalysis(
            total_quantity=total_quantity,
            filled_quantity=filled_quantity,
            fill_count=len(fills),
            fills=fills,
            fill_rate=round(fill_rate, 4),
            fill_quality=quality,
            fragmentation_score=round(fragmentation, 4),
            consistency_score=round(consistency, 4),
            average_fill_size=round(avg_fill, 8),
            largest_fill=round(largest, 8),
            smallest_fill=round(smallest, 8),
            notes=notes
        )
    
    def analyze_partial(
        self,
        total_quantity: float,
        filled_quantity: float,
        fill_count: int
    ) -> FillAnalysis:
        """
        Упрощённый анализ без детальных fills.
        """
        if total_quantity <= 0:
            return self._empty_result(total_quantity)
        
        fill_rate = min(1.0, filled_quantity / total_quantity)
        
        # Estimate fragmentation from count
        if fill_count <= 1:
            fragmentation = 0.0
        elif fill_count <= 3:
            fragmentation = 0.2
        elif fill_count <= 5:
            fragmentation = 0.4
        else:
            fragmentation = min(1.0, fill_count / 10)
        
        quality = self._determine_quality(fill_rate, fragmentation, fill_count)
        
        avg_fill = filled_quantity / fill_count if fill_count > 0 else 0
        
        return FillAnalysis(
            total_quantity=total_quantity,
            filled_quantity=filled_quantity,
            fill_count=fill_count,
            fills=[],
            fill_rate=round(fill_rate, 4),
            fill_quality=quality,
            fragmentation_score=round(fragmentation, 4),
            consistency_score=1.0,  # Unknown
            average_fill_size=round(avg_fill, 8),
            largest_fill=0.0,
            smallest_fill=0.0,
            notes=f"Partial analysis: {fill_count} fills, {fill_rate:.1%} filled"
        )
    
    def _calculate_fragmentation(
        self,
        quantities: List[float],
        total: float
    ) -> float:
        """
        Рассчитать fragmentation score.
        
        0 = одно заполнение
        1 = много мелких fills
        """
        if not quantities or total <= 0:
            return 0.0
        
        n = len(quantities)
        
        if n == 1:
            return 0.0
        
        # Ideal fill = total in one
        # Fragmentation increases with number of fills and variance
        
        # Base fragmentation from count
        count_factor = min(1.0, (n - 1) / 10)  # 10+ fills = max count factor
        
        # Variance factor
        avg = total / n
        if avg > 0:
            variance_sum = sum((q - avg) ** 2 for q in quantities) / n
            std_dev = variance_sum ** 0.5
            cv = std_dev / avg  # Coefficient of variation
            variance_factor = min(1.0, cv)
        else:
            variance_factor = 0.0
        
        # Combined
        fragmentation = count_factor * 0.7 + variance_factor * 0.3
        
        return min(1.0, fragmentation)
    
    def _calculate_consistency(self, quantities: List[float]) -> float:
        """
        Рассчитать consistency score.
        
        1 = все fills одинаковые
        0 = высокая вариация
        """
        if not quantities or len(quantities) <= 1:
            return 1.0
        
        avg = sum(quantities) / len(quantities)
        if avg <= 0:
            return 1.0
        
        # Calculate coefficient of variation
        variance = sum((q - avg) ** 2 for q in quantities) / len(quantities)
        std_dev = variance ** 0.5
        cv = std_dev / avg
        
        # Invert: low CV = high consistency
        consistency = max(0.0, 1.0 - min(1.0, cv))
        
        return consistency
    
    def _determine_quality(
        self,
        fill_rate: float,
        fragmentation: float,
        fill_count: int
    ) -> FillQuality:
        """Определить качество заполнения"""
        # Not filled
        if fill_rate < 0.5:
            return FillQuality.FAILED if fill_rate < 0.1 else FillQuality.POOR
        
        # Determine based on fragmentation
        if fill_count == 1 and fill_rate >= 0.99:
            return FillQuality.EXCELLENT
        
        if fragmentation <= self.excellent_threshold:
            return FillQuality.EXCELLENT
        elif fragmentation <= self.good_threshold:
            return FillQuality.GOOD
        elif fragmentation <= self.fair_threshold:
            return FillQuality.FAIR
        else:
            return FillQuality.POOR
    
    def _generate_notes(
        self,
        fill_rate: float,
        fragmentation: float,
        quality: FillQuality,
        fill_count: int
    ) -> str:
        """Генерация заметок"""
        parts = []
        
        if fill_rate < 1.0:
            parts.append(f"Partial fill: {fill_rate:.1%}")
        
        if fill_count == 1:
            parts.append("Single fill - optimal execution")
        elif fill_count <= 3:
            parts.append(f"{fill_count} fills - low fragmentation")
        else:
            parts.append(f"{fill_count} fills - consider order splitting")
        
        quality_notes = {
            FillQuality.EXCELLENT: "Excellent fill quality",
            FillQuality.GOOD: "Good fill quality",
            FillQuality.FAIR: "Fair fill quality - acceptable",
            FillQuality.POOR: "Poor fill quality - investigate",
            FillQuality.FAILED: "Fill failed - order not executed"
        }
        
        parts.append(quality_notes.get(quality, ""))
        
        return " | ".join(filter(None, parts))
    
    def _empty_result(self, total_quantity: float) -> FillAnalysis:
        """Пустой результат"""
        return FillAnalysis(
            total_quantity=total_quantity,
            filled_quantity=0.0,
            fill_count=0,
            fills=[],
            fill_rate=0.0,
            fill_quality=FillQuality.FAILED,
            fragmentation_score=0.0,
            consistency_score=0.0,
            notes="No fills received"
        )
