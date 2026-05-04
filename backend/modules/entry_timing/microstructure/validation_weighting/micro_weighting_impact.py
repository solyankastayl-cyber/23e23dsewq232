"""
PHASE 4.8.4 — Micro Weighting Impact

Analyzes what weighting did vs filter:
- upgraded_size_wins: weighting gave bigger size on winners
- oversized_losses: weighting gave bigger size on losers (DANGER)
"""


class MicroWeightingImpact:
    """Impact analysis for weighting vs filter vs base."""

    def analyze(self, base_results: list, filter_results: list, weighting_results: list) -> dict:
        avoided_bad_filter = 0
        avoided_bad_weighting = 0
        missed_good_filter = 0
        missed_good_weighting = 0
        upgraded_size_wins = 0
        oversized_losses = 0

        for b, f, w in zip(base_results, filter_results, weighting_results):
            b_result = b.get("result", "loss")

            if b_result == "loss" and f.get("skipped", False):
                avoided_bad_filter += 1
            if b_result == "loss" and w.get("skipped", False):
                avoided_bad_weighting += 1

            if b_result == "win" and f.get("skipped", False):
                missed_good_filter += 1
            if b_result == "win" and w.get("skipped", False):
                missed_good_weighting += 1

            # Weighting gave bigger size on winner
            if (
                w.get("result") == "win"
                and not w.get("skipped", False)
                and w.get("position_size", 1.0) > f.get("position_size", 1.0)
            ):
                upgraded_size_wins += 1

            # Weighting gave bigger size on loser (DANGER)
            if (
                w.get("result") == "loss"
                and not w.get("skipped", False)
                and w.get("position_size", 1.0) > f.get("position_size", 1.0)
            ):
                oversized_losses += 1

        return {
            "filter": {
                "avoided_bad_trades": avoided_bad_filter,
                "missed_good_trades": missed_good_filter,
                "net_edge": avoided_bad_filter - missed_good_filter,
            },
            "weighting": {
                "avoided_bad_trades": avoided_bad_weighting,
                "missed_good_trades": missed_good_weighting,
                "net_edge": avoided_bad_weighting - missed_good_weighting,
                "upgraded_size_wins": upgraded_size_wins,
                "oversized_losses": oversized_losses,
                "size_edge": upgraded_size_wins - oversized_losses,
            },
        }
