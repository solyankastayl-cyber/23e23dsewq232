"""
Fractal Visualization API — PHASE 48.5

Provides fractal match data for visualization:
- Fractal match reference
- Matched window
- Projected path
- Similarity score
- Reference asset / date
- Path overlay points
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
import numpy as np


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class FractalMatchPoint(BaseModel):
    """Point in fractal match overlay."""
    timestamp: str
    price: float
    is_projected: bool = False


class FractalMatchVisualization(BaseModel):
    """Fractal match visualization data."""
    match_id: str
    symbol: str
    timeframe: str
    
    # Reference pattern
    reference_symbol: str
    reference_start: str
    reference_end: str
    reference_context: str = ""  # e.g., "BTC 2021 Bull Run"
    
    # Similarity
    similarity: float
    confidence: float
    
    # Current pattern overlay
    current_pattern: List[FractalMatchPoint] = Field(default_factory=list)
    
    # Historical reference overlay (normalized to current price)
    reference_pattern: List[FractalMatchPoint] = Field(default_factory=list)
    
    # Projected path (extension of reference pattern)
    projected_path: List[FractalMatchPoint] = Field(default_factory=list)
    projected_target: Optional[float] = None
    
    # Confidence bands
    upper_projection: List[float] = Field(default_factory=list)
    lower_projection: List[float] = Field(default_factory=list)
    
    # Styling
    color: str = "#8B5CF6"
    reference_color: str = "#6366F1"
    projection_color: str = "#A78BFA"
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FractalScanResult(BaseModel):
    """Result of fractal pattern scan."""
    symbol: str
    timeframe: str
    scan_timestamp: str
    
    matches: List[FractalMatchVisualization] = Field(default_factory=list)
    best_match: Optional[FractalMatchVisualization] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════

class FractalVisualizationService:
    """Service for fractal pattern visualization."""
    
    # Historical reference patterns (simplified for demo)
    REFERENCE_PATTERNS = [
        {
            "name": "BTC 2020 Pre-Halving",
            "symbol": "BTCUSDT",
            "start": "2020-01-01",
            "end": "2020-05-11",
            "pattern": [1.0, 1.05, 1.02, 1.08, 1.15, 1.12, 1.20, 1.18, 1.25, 1.30],
            "post_pattern": [1.35, 1.42, 1.38, 1.50, 1.65],
        },
        {
            "name": "BTC 2021 Bull Run",
            "symbol": "BTCUSDT",
            "start": "2021-01-01",
            "end": "2021-04-14",
            "pattern": [1.0, 1.08, 1.15, 1.12, 1.25, 1.35, 1.28, 1.45, 1.52, 1.60],
            "post_pattern": [1.55, 1.40, 1.30, 1.25, 1.20],
        },
        {
            "name": "ETH DeFi Summer",
            "symbol": "ETHUSDT",
            "start": "2020-06-01",
            "end": "2020-09-01",
            "pattern": [1.0, 1.10, 1.25, 1.20, 1.35, 1.50, 1.45, 1.60, 1.55, 1.70],
            "post_pattern": [1.65, 1.55, 1.50, 1.55, 1.60],
        },
        {
            "name": "Accumulation Pattern",
            "symbol": "BTCUSDT",
            "start": "2019-01-01",
            "end": "2019-04-01",
            "pattern": [1.0, 0.98, 1.02, 0.99, 1.01, 0.97, 1.03, 1.00, 1.05, 1.08],
            "post_pattern": [1.12, 1.18, 1.25, 1.35, 1.50],
        },
        {
            "name": "Distribution Pattern",
            "symbol": "BTCUSDT",
            "start": "2021-11-01",
            "end": "2022-01-01",
            "pattern": [1.0, 1.02, 0.98, 1.01, 0.96, 0.99, 0.94, 0.97, 0.92, 0.88],
            "post_pattern": [0.85, 0.78, 0.72, 0.68, 0.60],
        },
    ]
    
    def find_fractal_matches(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        min_similarity: float = 0.70,
        limit: int = 3
    ) -> FractalScanResult:
        """Find fractal pattern matches."""
        
        if not candles or len(candles) < 10:
            return FractalScanResult(
                symbol=symbol,
                timeframe=timeframe,
                scan_timestamp=datetime.now(timezone.utc).isoformat(),
            )
        
        # Normalize current pattern
        current_pattern = self._normalize_pattern([c["close"] for c in candles[-30:]])
        current_time = candles[-1]["timestamp"]
        current_price = candles[-1]["close"]
        
        # Find matches
        matches = []
        
        for ref in self.REFERENCE_PATTERNS:
            ref_pattern = ref["pattern"]
            
            # Calculate similarity
            similarity = self._calculate_similarity(current_pattern, ref_pattern)
            
            if similarity >= min_similarity:
                match = self._create_match_visualization(
                    candles, current_price, current_time,
                    ref, similarity, symbol, timeframe
                )
                matches.append(match)
        
        # Sort by similarity
        matches.sort(key=lambda m: m.similarity, reverse=True)
        matches = matches[:limit]
        
        return FractalScanResult(
            symbol=symbol,
            timeframe=timeframe,
            scan_timestamp=datetime.now(timezone.utc).isoformat(),
            matches=matches,
            best_match=matches[0] if matches else None,
        )
    
    def get_match_visualization(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        reference_name: str
    ) -> Optional[FractalMatchVisualization]:
        """Get visualization for a specific reference pattern."""
        
        ref = next(
            (r for r in self.REFERENCE_PATTERNS if r["name"] == reference_name),
            None
        )
        
        if not ref or not candles:
            return None
        
        current_pattern = self._normalize_pattern([c["close"] for c in candles[-30:]])
        similarity = self._calculate_similarity(current_pattern, ref["pattern"])
        
        return self._create_match_visualization(
            candles, candles[-1]["close"], candles[-1]["timestamp"],
            ref, similarity, symbol, timeframe
        )
    
    def _normalize_pattern(self, prices: List[float]) -> List[float]:
        """Normalize price pattern to start at 1.0."""
        if not prices or prices[0] == 0:
            return [1.0] * len(prices) if prices else []
        
        base = prices[0]
        return [p / base for p in prices]
    
    def _calculate_similarity(
        self,
        pattern1: List[float],
        pattern2: List[float]
    ) -> float:
        """Calculate similarity between two patterns."""
        # Resample to same length
        min_len = min(len(pattern1), len(pattern2))
        
        if min_len < 3:
            return 0.0
        
        p1 = np.array(pattern1[:min_len])
        p2 = np.array(pattern2[:min_len])
        
        # Calculate correlation
        if np.std(p1) == 0 or np.std(p2) == 0:
            return 0.0
        
        correlation = np.corrcoef(p1, p2)[0, 1]
        
        # Calculate shape similarity (DTW-like)
        shape_diff = np.mean(np.abs(p1 - p2))
        shape_similarity = max(0, 1 - shape_diff)
        
        # Combine metrics
        similarity = 0.6 * max(0, correlation) + 0.4 * shape_similarity
        
        return round(min(max(similarity, 0), 1), 3)
    
    def _create_match_visualization(
        self,
        candles: List[Dict[str, Any]],
        current_price: float,
        current_time: str,
        reference: Dict[str, Any],
        similarity: float,
        symbol: str,
        timeframe: str
    ) -> FractalMatchVisualization:
        """Create visualization for a match."""
        
        # Parse current time
        try:
            if isinstance(current_time, str):
                base_time = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
            else:
                base_time = current_time
        except:
            base_time = datetime.now(timezone.utc)
        
        # Time step estimation
        tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
        minutes = tf_minutes.get(timeframe, 60)
        
        # Current pattern points
        current_pattern_points = []
        for i, c in enumerate(candles[-30:]):
            current_pattern_points.append(FractalMatchPoint(
                timestamp=c["timestamp"],
                price=c["close"],
                is_projected=False
            ))
        
        # Reference pattern normalized to current price
        ref_pattern = reference["pattern"]
        base_price = current_price / ref_pattern[-1] if ref_pattern[-1] != 0 else current_price
        
        reference_pattern_points = []
        for i, norm_price in enumerate(ref_pattern):
            point_time = base_time - timedelta(minutes=minutes * (len(ref_pattern) - 1 - i))
            reference_pattern_points.append(FractalMatchPoint(
                timestamp=point_time.isoformat(),
                price=round(base_price * norm_price, 2),
                is_projected=False
            ))
        
        # Projected path from post_pattern
        post_pattern = reference.get("post_pattern", [])
        projected_path = []
        upper_projection = []
        lower_projection = []
        
        for i, norm_price in enumerate(post_pattern):
            point_time = base_time + timedelta(minutes=minutes * (i + 1))
            projected_price = base_price * norm_price
            
            # Confidence decreases with projection distance
            confidence = 1.0 - (i / len(post_pattern)) * 0.5
            band_width = current_price * 0.02 * (i + 1)  # Widening bands
            
            projected_path.append(FractalMatchPoint(
                timestamp=point_time.isoformat(),
                price=round(projected_price, 2),
                is_projected=True
            ))
            
            upper_projection.append(round(projected_price + band_width, 2))
            lower_projection.append(round(projected_price - band_width, 2))
        
        # Calculate projected target
        projected_target = projected_path[-1].price if projected_path else None
        
        return FractalMatchVisualization(
            match_id=f"fractal_{symbol}_{timeframe}_{reference['name'].replace(' ', '_')}",
            symbol=symbol,
            timeframe=timeframe,
            reference_symbol=reference["symbol"],
            reference_start=reference["start"],
            reference_end=reference["end"],
            reference_context=reference["name"],
            similarity=similarity,
            confidence=similarity * 0.9,  # Confidence slightly lower than similarity
            current_pattern=current_pattern_points,
            reference_pattern=reference_pattern_points,
            projected_path=projected_path,
            projected_target=projected_target,
            upper_projection=upper_projection,
            lower_projection=lower_projection,
        )


# Singleton
_fractal_viz_service: Optional[FractalVisualizationService] = None

def get_fractal_viz_service() -> FractalVisualizationService:
    global _fractal_viz_service
    if _fractal_viz_service is None:
        _fractal_viz_service = FractalVisualizationService()
    return _fractal_viz_service
