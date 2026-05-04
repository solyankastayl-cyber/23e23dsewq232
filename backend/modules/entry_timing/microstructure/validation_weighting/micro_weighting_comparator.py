"""
PHASE 4.8.4 — Micro Weighting Comparator

Three-way comparison: Base vs Filter vs Weighting.
"""


class MicroWeightingComparator:
    """Compares three pipeline variants."""

    def compare(self, base_metrics: dict, filter_metrics: dict, weighting_metrics: dict) -> dict:
        return {
            "filter_vs_base": self._delta(filter_metrics, base_metrics),
            "weighting_vs_filter": self._delta(weighting_metrics, filter_metrics),
            "weighting_vs_base": self._delta(weighting_metrics, base_metrics),
        }

    def _delta(self, a: dict, b: dict) -> dict:
        keys = [
            "win_rate", "pnl", "avg_rr", "wrong_early_rate",
            "stop_out_rate", "skip_rate", "expectancy",
            "avg_position_size", "avg_execution_confidence",
        ]
        result = {}
        for k in keys:
            av = a.get(k)
            bv = b.get(k)
            if av is not None and bv is not None:
                result[f"{k}_delta"] = round(av - bv, 6)

        result["profit_factor_delta"] = self._safe_delta(
            a.get("profit_factor"), b.get("profit_factor")
        )
        result["size_adjusted_pnl_delta"] = self._safe_delta(
            a.get("size_adjusted_pnl"), b.get("size_adjusted_pnl")
        )
        result["size_adjusted_pf_delta"] = self._safe_delta(
            a.get("size_adjusted_profit_factor"), b.get("size_adjusted_profit_factor")
        )

        return result

    @staticmethod
    def _safe_delta(a, b):
        if a is None or b is None:
            return None
        return round(a - b, 4)
