"""
POI Engine — Order Blocks / Supply / Demand Zones
==================================================

POI = Point of Interest = откуда начался импульс

Не "рисуем зоны где красиво", а:
- находим displacement
- ищем последнюю противоположную свечу перед импульсом
- это = Order Block = POI

Output:
{
    "zones": [
        {
            "type": "demand",
            "subtype": "order_block",
            "price_low": 68200,
            "price_high": 69500,
            "origin_index": 120,
            "direction": "bullish",
            "strength": 8.2,
            "mitigated": false,
            "displacement_strength": 2.4
        }
    ]
}

Rules:
- Каждая зона связана с displacement
- Максимум 3-5 зон (без мусора)
- strength score на основе displacement + body ratio + freshness
- mitigated = цена вернулась в зону
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class POIEngine:
    """
    POI Engine — builds demand/supply zones from displacement origins.
    
    Order Block = последняя противоположная свеча перед импульсом:
    - Bullish OB: последняя красная свеча перед сильным ростом
    - Bearish OB: последняя зелёная свеча перед сливом
    """

    def __init__(
        self,
        lookback: int = 160,
        max_zones: int = 5,
        mitigation_tolerance: float = 0.0015,  # 0.15% tolerance for mitigation check
        min_displacement_strength: float = 1.5,  # minimum displacement to create POI
    ):
        self.lookback = lookback
        self.max_zones = max_zones
        self.mitigation_tolerance = mitigation_tolerance
        self.min_displacement_strength = min_displacement_strength

    def build(
        self,
        candles: List[Dict[str, Any]],
        displacement: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build POI zones from displacement events.
        
        Returns:
            {
                "zones": [...],
                "demand_zones": [...],  # filtered
                "supply_zones": [...],  # filtered
                "active_zones": [...],  # unmitigated only
            }
        """
        if not candles:
            return self._empty_result()

        scope = candles[-self.lookback:] if len(candles) > self.lookback else candles
        events = displacement.get("events", []) if displacement else []

        # Only process strong displacements
        strong_events = [
            e for e in events 
            if float(e.get("strength", 0) or 0) >= self.min_displacement_strength
        ]

        zones: List[Dict[str, Any]] = []

        for event in strong_events:
            zone = self._build_zone_from_displacement(scope, event)
            if zone:
                zones.append(zone)

        # Deduplicate overlapping zones
        zones = self._dedupe_zones(zones)
        
        # Mark mitigation
        zones = self._mark_mitigation(scope, zones)
        
        # Sort by strength (strongest first)
        zones.sort(key=lambda z: z["strength"], reverse=True)
        
        # Limit to max zones
        zones = zones[:self.max_zones]

        # Filter views
        demand_zones = [z for z in zones if z["type"] == "demand"]
        supply_zones = [z for z in zones if z["type"] == "supply"]
        active_zones = [z for z in zones if not z["mitigated"]]

        return {
            "zones": zones,
            "demand_zones": demand_zones,
            "supply_zones": supply_zones,
            "active_zones": active_zones,
            "total_count": len(zones),
            "active_count": len(active_zones),
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "zones": [],
            "demand_zones": [],
            "supply_zones": [],
            "active_zones": [],
            "total_count": 0,
            "active_count": 0,
        }

    # ---------------------------------------------------------
    # BUILD ZONE FROM DISPLACEMENT
    # ---------------------------------------------------------
    def _build_zone_from_displacement(
        self,
        candles: List[Dict[str, Any]],
        event: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Find the order block (last opposite candle) before displacement.
        """
        direction = event.get("direction")
        start_index = int(event.get("start_index", -1))
        end_index = int(event.get("end_index", -1))
        disp_strength = float(event.get("strength", 0.0) or 0.0)
        disp_range_pct = float(event.get("range_pct", 0.0) or 0.0)

        if start_index < 1 or start_index >= len(candles):
            return None

        # Bullish displacement -> find last bearish candle before impulse (demand zone)
        if direction == "bullish":
            ob_index = self._find_last_opposite_candle(
                candles=candles,
                start_index=start_index,
                looking_for_bearish=True,
            )
            if ob_index is None:
                return None

            c = candles[ob_index]
            zone = self._create_zone(
                candle=c,
                zone_type="demand",
                direction="bullish",
                ob_index=ob_index,
                start_index=start_index,
                end_index=end_index,
                disp_strength=disp_strength,
                disp_range_pct=disp_range_pct,
                candles=candles,
            )
            return zone

        # Bearish displacement -> find last bullish candle before impulse (supply zone)
        if direction == "bearish":
            ob_index = self._find_last_opposite_candle(
                candles=candles,
                start_index=start_index,
                looking_for_bearish=False,
            )
            if ob_index is None:
                return None

            c = candles[ob_index]
            zone = self._create_zone(
                candle=c,
                zone_type="supply",
                direction="bearish",
                ob_index=ob_index,
                start_index=start_index,
                end_index=end_index,
                disp_strength=disp_strength,
                disp_range_pct=disp_range_pct,
                candles=candles,
            )
            return zone

        return None

    def _find_last_opposite_candle(
        self,
        candles: List[Dict[str, Any]],
        start_index: int,
        looking_for_bearish: bool,
        search_back: int = 10,
    ) -> Optional[int]:
        """
        Search backwards from displacement start to find the last opposite candle.
        """
        left = max(0, start_index - search_back)

        for i in range(start_index - 1, left - 1, -1):
            o = float(candles[i]["open"])
            c = float(candles[i]["close"])

            # Looking for bearish candle (close < open)
            if looking_for_bearish and c < o:
                return i

            # Looking for bullish candle (close > open)
            if not looking_for_bearish and c > o:
                return i

        return None

    def _create_zone(
        self,
        candle: Dict[str, Any],
        zone_type: str,
        direction: str,
        ob_index: int,
        start_index: int,
        end_index: int,
        disp_strength: float,
        disp_range_pct: float,
        candles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create zone object with all properties."""
        low = float(candle["low"])
        high = float(candle["high"])
        open_p = float(candle["open"])
        close = float(candle["close"])
        
        # Calculate zone properties
        body = abs(close - open_p)
        full_range = high - low
        
        # Strength score
        strength = self._score_zone(
            candle=candle,
            disp_strength=disp_strength,
            candles=candles,
            idx=ob_index,
            direction=direction,
        )

        return {
            "type": zone_type,
            "subtype": "order_block",
            "direction": direction,
            "price_low": round(low, 2),
            "price_high": round(high, 2),
            "price_mid": round((low + high) / 2, 2),
            "zone_size": round(high - low, 2),
            "zone_size_pct": round(((high - low) / close) * 100, 3) if close > 0 else 0,
            "origin_index": ob_index,
            "origin_time": candle.get("time", candle.get("timestamp", 0)),
            "displacement_start_index": start_index,
            "displacement_end_index": end_index,
            "displacement_strength": round(disp_strength, 2),
            "displacement_range_pct": round(disp_range_pct, 2),
            "strength": round(strength, 2),
            "body_ratio": round(body / full_range, 2) if full_range > 0 else 0,
            "mitigated": False,
            "label": f"{zone_type.upper()} OB @ {round((low + high) / 2, 0)}",
        }

    # ---------------------------------------------------------
    # STRENGTH SCORING
    # ---------------------------------------------------------
    def _score_zone(
        self,
        candle: Dict[str, Any],
        disp_strength: float,
        candles: List[Dict[str, Any]],
        idx: int,
        direction: str,
    ) -> float:
        """
        Score zone strength based on:
        - Displacement strength (most important)
        - Body ratio of OB candle
        - Freshness (more recent = higher score)
        - Compactness (tighter zone = better)
        """
        body = abs(float(candle["close"]) - float(candle["open"]))
        full_range = max(float(candle["high"]) - float(candle["low"]), 1e-9)
        body_ratio = body / full_range

        # Freshness: newer zones are more relevant
        freshness = self._freshness_score(candles, idx)
        
        # Impulse bonus from displacement
        impulse_bonus = min(disp_strength, 4.0)  # cap at 4

        # Compact zone is better (smaller % of price)
        price = max(float(candle["close"]), 1e-9)
        compactness = 1.0 - min(1.0, (full_range / price) / 0.03)

        # Weighted score
        score = (
            impulse_bonus * 1.5 +      # displacement most important
            body_ratio * 2.0 +         # strong body = clear OB
            freshness * 1.5 +          # recent zones matter more
            compactness * 1.0          # tight zones are cleaner
        )

        return score

    def _freshness_score(self, candles: List[Dict[str, Any]], idx: int) -> float:
        """Score based on how recent the zone is."""
        age = (len(candles) - 1) - idx
        if age <= 10:
            return 1.0
        if age <= 25:
            return 0.8
        if age <= 50:
            return 0.5
        if age <= 100:
            return 0.3
        return 0.15

    # ---------------------------------------------------------
    # DEDUPLICATION
    # ---------------------------------------------------------
    def _dedupe_zones(self, zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove overlapping zones, keeping strongest."""
        if not zones:
            return []

        zones = sorted(zones, key=lambda z: z["strength"], reverse=True)
        result: List[Dict[str, Any]] = []

        for z in zones:
            overlapped = False
            for existing in result:
                if self._zones_overlap(z, existing):
                    overlapped = True
                    break
            if not overlapped:
                result.append(z)

        return result

    def _zones_overlap(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """Check if two zones overlap."""
        # Different types don't overlap (demand vs supply)
        if a["type"] != b["type"]:
            return False

        a_low, a_high = a["price_low"], a["price_high"]
        b_low, b_high = b["price_low"], b["price_high"]

        # Check price overlap
        return not (a_high < b_low or b_high < a_low)

    # ---------------------------------------------------------
    # MITIGATION
    # ---------------------------------------------------------
    def _mark_mitigation(
        self,
        candles: List[Dict[str, Any]],
        zones: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Mark zones as mitigated if price returned to them."""
        for zone in zones:
            zone["mitigated"] = self._is_mitigated(candles, zone)
        return zones

    def _is_mitigated(self, candles: List[Dict[str, Any]], zone: Dict[str, Any]) -> bool:
        """
        Check if zone has been mitigated (price returned to zone after creation).
        
        Demand zone: mitigated if price came back down into zone
        Supply zone: mitigated if price came back up into zone
        """
        # Start checking after the displacement ended
        start = int(zone.get("displacement_end_index", zone["origin_index"])) + 1
        low = float(zone["price_low"])
        high = float(zone["price_high"])

        for i in range(start, len(candles)):
            c = candles[i]
            candle_low = float(c["low"])
            candle_high = float(c["high"])

            # Demand zone: mitigated when price wicks into or through zone
            if zone["type"] == "demand":
                tolerance = high * self.mitigation_tolerance
                if candle_low <= high + tolerance:
                    return True

            # Supply zone: mitigated when price wicks into or through zone
            if zone["type"] == "supply":
                tolerance = low * self.mitigation_tolerance
                if candle_high >= low - tolerance:
                    return True

        return False


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_poi_engine_instance: Optional[POIEngine] = None


def get_poi_engine() -> POIEngine:
    """Get singleton instance of POIEngine."""
    global _poi_engine_instance
    if _poi_engine_instance is None:
        _poi_engine_instance = POIEngine()
    return _poi_engine_instance


# Direct import singleton
poi_engine = POIEngine()
