"""
PHASE 4.8.2 — Micro Impact Analyzer

Determines what microstructure actually did:
- How many bad trades it avoided
- How many good trades it missed
- Net edge calculation
"""


class MicroImpactAnalyzer:
    """Analyzes real impact of microstructure filter."""

    def analyze(self, base_results: list, micro_results: list) -> dict:
        avoided_bad = 0
        missed_good = 0
        upgraded_entries = 0
        downgraded_entries = 0

        for b, m in zip(base_results, micro_results):
            b_result = b.get("result", "loss")
            m_skipped = m.get("skipped", False)

            if b_result == "loss" and m_skipped:
                avoided_bad += 1

            if b_result == "win" and m_skipped:
                missed_good += 1

            if not m_skipped and not b.get("skipped", False):
                m_eff = m.get("entry_efficiency", 0)
                b_eff = b.get("entry_efficiency", 0)
                if m_eff > b_eff:
                    upgraded_entries += 1
                elif m_eff < b_eff:
                    downgraded_entries += 1

        net_edge = avoided_bad - missed_good
        total = len(base_results) or 1

        avoided_pnl = sum(
            abs(b.get("pnl", 0))
            for b, m in zip(base_results, micro_results)
            if b.get("result") == "loss" and m.get("skipped", False)
        )

        missed_pnl = sum(
            b.get("pnl", 0)
            for b, m in zip(base_results, micro_results)
            if b.get("result") == "win" and m.get("skipped", False)
        )

        return {
            "avoided_bad_trades": avoided_bad,
            "missed_good_trades": missed_good,
            "upgraded_entries": upgraded_entries,
            "downgraded_entries": downgraded_entries,
            "net_edge": net_edge,
            "net_edge_rate": round(net_edge / total, 4),
            "avoided_loss_pnl": round(avoided_pnl, 4),
            "missed_profit_pnl": round(missed_pnl, 4),
            "net_pnl_impact": round(avoided_pnl - missed_pnl, 4),
            "filter_efficiency": round(avoided_bad / (avoided_bad + missed_good), 4) if (avoided_bad + missed_good) > 0 else 0,
        }
