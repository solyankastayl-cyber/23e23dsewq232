"""
Decision Quality Analytics Module
==================================
P2: Analytics-only. Queries MongoDB for trade quality metrics.
NO strategy/signal/adaptation changes.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DecisionQualityService:
    def __init__(self, db):
        self.db = db

    async def get_quality_report(self) -> Dict[str, Any]:
        outcomes = await self.db.decision_outcomes.find(
            {}, {"_id": 0}
        ).to_list(length=5000)

        if not outcomes:
            return self._empty_report()

        # Join with pending_decisions for confidence + signal_price
        decision_ids = [o["decision_id"] for o in outcomes if o.get("decision_id")]
        decisions_map = {}
        if decision_ids:
            decisions = await self.db.pending_decisions.find(
                {"decision_id": {"$in": decision_ids}},
                {"_id": 0, "decision_id": 1, "confidence": 1, "entry_price": 1}
            ).to_list(length=5000)
            decisions_map = {d["decision_id"]: d for d in decisions}

        # Enrich outcomes with confidence and signal_price
        enriched = []
        for o in outcomes:
            dec = decisions_map.get(o.get("decision_id"), {})
            o["confidence"] = dec.get("confidence", 0.5)
            # signal_price: prefer outcome doc's own field, fallback to decision entry_price
            if not o.get("signal_price"):
                o["signal_price"] = dec.get("entry_price", 0)
            enriched.append(o)

        total = len(enriched)
        wins = [o for o in enriched if o.get("pnl_usd", 0) > 0]
        losses = [o for o in enriched if o.get("pnl_usd", 0) <= 0]

        win_rate = round((len(wins) / total) * 100, 1) if total else 0.0
        avg_win = round(sum(o["pnl_usd"] for o in wins) / len(wins), 4) if wins else 0.0
        avg_loss = round(sum(o["pnl_usd"] for o in losses) / len(losses), 4) if losses else 0.0
        sum_wins = sum(o["pnl_usd"] for o in wins)
        sum_losses = abs(sum(o["pnl_usd"] for o in losses))
        profit_factor = round(sum_wins / sum_losses, 2) if sum_losses > 0 else 0.0

        by_confidence = self._confidence_buckets(enriched)
        by_strategy = self._strategy_breakdown(enriched)
        by_direction = self._direction_analysis(enriched)
        by_hour = self._hour_analysis(enriched)
        slippage = self._slippage_analysis(enriched)
        recent_losses = self._recent_losses(enriched)

        return {
            "total_trades": total,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "by_confidence": by_confidence,
            "by_strategy": by_strategy,
            "by_direction": by_direction,
            "by_hour": by_hour,
            "avg_slippage": slippage["avg_slippage"],
            "max_slippage": slippage["max_slippage"],
            "slippage_distribution": slippage["distribution"],
            "recent_losses": recent_losses,
        }

    def _confidence_buckets(self, outcomes: List[Dict]) -> Dict:
        buckets = {
            "0.0-0.5": [], "0.5-0.6": [], "0.6-0.7": [],
            "0.7-0.8": [], "0.8-1.0": [],
        }
        for o in outcomes:
            c = o.get("confidence", 0.5)
            if c < 0.5:
                buckets["0.0-0.5"].append(o)
            elif c < 0.6:
                buckets["0.5-0.6"].append(o)
            elif c < 0.7:
                buckets["0.6-0.7"].append(o)
            elif c < 0.8:
                buckets["0.7-0.8"].append(o)
            else:
                buckets["0.8-1.0"].append(o)

        result = {}
        for key, items in buckets.items():
            n = len(items)
            if n == 0:
                result[key] = {"trades": 0, "win_rate": 0.0, "avg_pnl": 0.0}
            else:
                w = sum(1 for o in items if o.get("pnl_usd", 0) > 0)
                avg = sum(o.get("pnl_usd", 0) for o in items) / n
                result[key] = {
                    "trades": n,
                    "win_rate": round((w / n) * 100, 1),
                    "avg_pnl": round(avg, 4),
                }
        return result

    def _strategy_breakdown(self, outcomes: List[Dict]) -> Dict:
        groups = {}
        for o in outcomes:
            s = o.get("strategy", "UNKNOWN")
            groups.setdefault(s, []).append(o)

        result = {}
        for name, items in groups.items():
            n = len(items)
            w = sum(1 for o in items if o.get("pnl_usd", 0) > 0)
            total_pnl = sum(o.get("pnl_usd", 0) for o in items)
            result[name] = {
                "trades": n,
                "win_rate": round((w / n) * 100, 1) if n else 0.0,
                "total_pnl": round(total_pnl, 4),
                "avg_pnl": round(total_pnl / n, 4) if n else 0.0,
            }
        return result

    def _direction_analysis(self, outcomes: List[Dict]) -> Dict:
        result = {}
        for direction in ["LONG", "SHORT"]:
            items = [o for o in outcomes if o.get("side") == direction]
            n = len(items)
            if n == 0:
                result[direction] = {"trades": 0, "win_rate": 0.0, "avg_pnl": 0.0, "total_pnl": 0.0}
            else:
                w = sum(1 for o in items if o.get("pnl_usd", 0) > 0)
                total_pnl = sum(o.get("pnl_usd", 0) for o in items)
                result[direction] = {
                    "trades": n,
                    "win_rate": round((w / n) * 100, 1),
                    "avg_pnl": round(total_pnl / n, 4),
                    "total_pnl": round(total_pnl, 4),
                }
        return result

    def _hour_analysis(self, outcomes: List[Dict]) -> Dict:
        hours = {str(h): [] for h in range(24)}
        for o in outcomes:
            ts = o.get("closed_at") or o.get("created_at")
            if not ts:
                continue
            try:
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    dt = ts
                hours[str(dt.hour)].append(o)
            except Exception:
                pass

        result = {}
        for h, items in hours.items():
            n = len(items)
            if n == 0:
                result[h] = {"trades": 0, "win_rate": 0.0, "avg_pnl": 0.0}
            else:
                w = sum(1 for o in items if o.get("pnl_usd", 0) > 0)
                avg = sum(o.get("pnl_usd", 0) for o in items) / n
                result[h] = {
                    "trades": n,
                    "win_rate": round((w / n) * 100, 1),
                    "avg_pnl": round(avg, 4),
                }
        return result

    def _slippage_analysis(self, outcomes: List[Dict]) -> Dict:
        slippages = []
        for o in outcomes:
            # signal_price: price from the decision at generation time
            # entry_price: actual execution price (from Coinbase)
            signal_p = o.get("signal_price", 0)
            exec_p = o.get("entry_price", 0)
            # Only count slippage when we have a real signal price
            if signal_p > 0 and exec_p > 0:
                slip = abs(exec_p - signal_p)
                slippages.append(slip)

        if not slippages:
            return {"avg_slippage": 0.0, "max_slippage": 0.0, "distribution": {}}

        avg_s = round(sum(slippages) / len(slippages), 4)
        max_s = round(max(slippages), 4)

        dist = {"<1": 0, "1-10": 0, "10-50": 0, "50-100": 0, ">100": 0}
        for s in slippages:
            if s < 1:
                dist["<1"] += 1
            elif s < 10:
                dist["1-10"] += 1
            elif s < 50:
                dist["10-50"] += 1
            elif s < 100:
                dist["50-100"] += 1
            else:
                dist[">100"] += 1

        return {"avg_slippage": avg_s, "max_slippage": max_s, "distribution": dist}

    def _recent_losses(self, outcomes: List[Dict]) -> List[Dict]:
        losses = [o for o in outcomes if o.get("pnl_usd", 0) <= 0]
        losses.sort(key=lambda x: x.get("closed_at") or x.get("created_at") or "", reverse=True)
        return [
            {
                "decision_id": o.get("decision_id", ""),
                "symbol": o.get("symbol", ""),
                "side": o.get("side", ""),
                "confidence": o.get("confidence", 0),
                "entry_price": o.get("entry_price", 0),
                "exit_price": o.get("exit_price", 0),
                "pnl": round(o.get("pnl_usd", 0), 4),
                "timestamp": o.get("closed_at") or o.get("created_at") or "",
            }
            for o in losses[:10]
        ]

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "total_trades": 0, "win_rate": 0.0, "avg_win": 0.0,
            "avg_loss": 0.0, "profit_factor": 0.0,
            "by_confidence": {}, "by_strategy": {}, "by_direction": {},
            "by_hour": {}, "avg_slippage": 0.0, "max_slippage": 0.0,
            "slippage_distribution": {}, "recent_losses": [],
        }


# Singleton
_service = None

def init_decision_quality_service(db):
    global _service
    _service = DecisionQualityService(db=db)
    return _service

def get_decision_quality_service():
    return _service
