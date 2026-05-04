"""
Structure Rendering Engine
===========================

Converts raw candles into full price action structure visualization.

Pipeline:
  candles → Swing Detection → Structure Builder → Labeling → BOS/CHOCH → Render Plan

Output (chart_structure):
  - swings: [{type, index, price, time}]
  - labels: [{type, index, price, time, label}]  (HH/HL/LH/LL)
  - legs:   [{type, from, to}]  (bullish_leg / bearish_leg)
  - breaks: [{type, direction, level, index, time, from_label}]  (BOS / CHOCH)
  - trend:  "uptrend" | "downtrend" | "range"

RULE: This is the FOUNDATION layer. Always visible, highest priority.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class StructureRenderingEngine:

    def __init__(self, lookback: int = 5, min_move_pct: float = 0.008):
        self.lookback = lookback
        self.min_move_pct = min_move_pct  # 0.8% minimum swing size

    def build(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Full pipeline: candles → structure render plan.
        """
        if len(candles) < self.lookback * 2 + 1:
            return {"swings": [], "labels": [], "legs": [], "breaks": [], "trend": "unknown"}

        # 1. Detect swings
        swings = self._detect_swings(candles)

        # 2. Filter noise (min move)
        swings = self._filter_noise(swings, candles)

        # 3. Label (HH/HL/LH/LL)
        labels = self._label_structure(swings)

        # 4. Build legs
        legs = self._build_legs(labels)

        # 5. Detect BOS / CHOCH
        breaks = self._detect_breaks(labels)

        # 6. Determine trend
        trend = self._determine_trend(labels, breaks)

        return {
            "swings": swings,
            "labels": labels,
            "legs": legs,
            "breaks": breaks,
            "trend": trend,
        }

    # ═══════════════════════════════════════════════════════════════
    # 1. SWING DETECTION (pivot-based)
    # ═══════════════════════════════════════════════════════════════

    def _detect_swings(self, candles: List[Dict]) -> List[Dict]:
        """Find real pivot points using lookback window."""
        swings = []
        lb = self.lookback

        for i in range(lb, len(candles) - lb):
            high = candles[i]["high"]
            low = candles[i]["low"]
            time = candles[i].get("time", candles[i].get("timestamp", i))

            # Swing high: higher than all neighbors
            is_swing_high = all(
                high >= candles[j]["high"]
                for j in range(i - lb, i + lb + 1)
                if j != i
            )

            # Swing low: lower than all neighbors
            is_swing_low = all(
                low <= candles[j]["low"]
                for j in range(i - lb, i + lb + 1)
                if j != i
            )

            if is_swing_high:
                swings.append({
                    "type": "high",
                    "index": i,
                    "price": high,
                    "time": time,
                })

            if is_swing_low:
                swings.append({
                    "type": "low",
                    "index": i,
                    "price": low,
                    "time": time,
                })

        # Sort by index
        swings.sort(key=lambda s: s["index"])
        return swings

    # ═══════════════════════════════════════════════════════════════
    # 2. NOISE FILTER
    # ═══════════════════════════════════════════════════════════════

    def _filter_noise(self, swings: List[Dict], candles: List[Dict]) -> List[Dict]:
        """Remove micro swings that don't represent real moves."""
        if len(swings) < 2:
            return swings

        filtered = [swings[0]]

        for i in range(1, len(swings)):
            prev = filtered[-1]
            curr = swings[i]

            # Same type consecutive: keep the more extreme one
            if prev["type"] == curr["type"]:
                if curr["type"] == "high" and curr["price"] > prev["price"]:
                    filtered[-1] = curr
                elif curr["type"] == "low" and curr["price"] < prev["price"]:
                    filtered[-1] = curr
                continue

            # Different type: check minimum move
            move_pct = abs(curr["price"] - prev["price"]) / prev["price"]
            if move_pct >= self.min_move_pct:
                filtered.append(curr)
            else:
                # Too small, skip
                pass

        return filtered

    # ═══════════════════════════════════════════════════════════════
    # 3. HH / HL / LH / LL LABELING
    # ═══════════════════════════════════════════════════════════════

    def _label_structure(self, swings: List[Dict]) -> List[Dict]:
        """Label each swing as HH/HL/LH/LL."""
        if not swings:
            return []

        labels = []
        last_high = None
        last_low = None

        for s in swings:
            entry = {**s}

            if s["type"] == "high":
                if last_high is None:
                    entry["label"] = "HH"  # First high defaults to HH
                else:
                    entry["label"] = "HH" if s["price"] > last_high else "LH"
                last_high = s["price"]

            else:  # low
                if last_low is None:
                    entry["label"] = "HL"  # First low defaults to HL
                else:
                    entry["label"] = "HL" if s["price"] > last_low else "LL"
                last_low = s["price"]

            labels.append(entry)

        return labels

    # ═══════════════════════════════════════════════════════════════
    # 4. STRUCTURE LEGS
    # ═══════════════════════════════════════════════════════════════

    def _build_legs(self, labels: List[Dict]) -> List[Dict]:
        """Build structure legs connecting consecutive swings."""
        legs = []

        for i in range(1, len(labels)):
            prev = labels[i - 1]
            curr = labels[i]

            if prev["type"] == "low" and curr["type"] == "high":
                leg_type = "bullish_leg"
            elif prev["type"] == "high" and curr["type"] == "low":
                leg_type = "bearish_leg"
            else:
                leg_type = "continuation"

            legs.append({
                "type": leg_type,
                "from": {
                    "time": prev["time"],
                    "price": prev["price"],
                    "index": prev["index"],
                    "label": prev.get("label", ""),
                },
                "to": {
                    "time": curr["time"],
                    "price": curr["price"],
                    "index": curr["index"],
                    "label": curr.get("label", ""),
                },
            })

        return legs

    # ═══════════════════════════════════════════════════════════════
    # 5. BOS / CHOCH DETECTION
    # ═══════════════════════════════════════════════════════════════

    def _detect_breaks(self, labels: List[Dict]) -> List[Dict]:
        """
        Detect Break of Structure (BOS) and Change of Character (CHOCH).

        BOS = continuation break (HH breaks previous HH in uptrend)
        CHOCH = reversal break (LL breaks previous HL in uptrend → shift to downtrend)
        """
        breaks = []
        if len(labels) < 3:
            return breaks

        # Track last significant highs/lows for break detection
        for i in range(2, len(labels)):
            curr = labels[i]
            prev1 = labels[i - 1]
            prev2 = labels[i - 2]

            # ── BULLISH BOS ──
            # HH after HH → trend continuation upward
            if curr["label"] == "HH" and prev2["label"] == "HH" and curr["type"] == "high":
                breaks.append({
                    "type": "BOS",
                    "direction": "bullish",
                    "level": prev2["price"],
                    "index": curr["index"],
                    "time": curr["time"],
                    "from_label": prev2["label"],
                })

            # ── BEARISH BOS ──
            # LL after LL → trend continuation downward
            elif curr["label"] == "LL" and prev2["label"] == "LL" and curr["type"] == "low":
                breaks.append({
                    "type": "BOS",
                    "direction": "bearish",
                    "level": prev2["price"],
                    "index": curr["index"],
                    "time": curr["time"],
                    "from_label": prev2["label"],
                })

            # ── BULLISH CHOCH ──
            # After a downtrend (LL/LH sequence), a HH breaks the last LH
            elif curr["label"] == "HH" and prev2.get("label") in ("LH", "LL"):
                breaks.append({
                    "type": "CHOCH",
                    "direction": "bullish",
                    "level": prev2["price"] if prev2["type"] == "high" else prev1["price"],
                    "index": curr["index"],
                    "time": curr["time"],
                    "from_label": prev2["label"],
                })

            # ── BEARISH CHOCH ──
            # After an uptrend (HH/HL sequence), a LL breaks the last HL
            elif curr["label"] == "LL" and prev2.get("label") in ("HL", "HH"):
                breaks.append({
                    "type": "CHOCH",
                    "direction": "bearish",
                    "level": prev2["price"] if prev2["type"] == "low" else prev1["price"],
                    "index": curr["index"],
                    "time": curr["time"],
                    "from_label": prev2["label"],
                })

        return breaks

    # ═══════════════════════════════════════════════════════════════
    # 6. TREND DETERMINATION
    # ═══════════════════════════════════════════════════════════════

    def _determine_trend(self, labels: List[Dict], breaks: List[Dict]) -> str:
        """Determine current trend from last 4-6 labels."""
        if len(labels) < 4:
            return "unknown"

        recent = labels[-6:]

        hh_count = sum(1 for l in recent if l["label"] == "HH")
        hl_count = sum(1 for l in recent if l["label"] == "HL")
        lh_count = sum(1 for l in recent if l["label"] == "LH")
        ll_count = sum(1 for l in recent if l["label"] == "LL")

        bullish = hh_count + hl_count
        bearish = lh_count + ll_count

        if bullish >= bearish + 2:
            return "uptrend"
        elif bearish >= bullish + 2:
            return "downtrend"
        else:
            return "range"


# Singleton
_engine: Optional[StructureRenderingEngine] = None

def get_structure_rendering_engine() -> StructureRenderingEngine:
    global _engine
    if _engine is None:
        _engine = StructureRenderingEngine()
    return _engine
