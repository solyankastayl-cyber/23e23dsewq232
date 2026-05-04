"""
Alert Rules
===========

Phase 2.8: Alert rule definitions (5 categories).

Categories:
  A. Performance Degradation (overall winrate/pnl)
  B. Feature Breakdown (cluster/timeframe/alignment)
  C. Directional Bias Risk (LONG-only or SHORT-only)
  D. Calibration Drift (calibration making things worse)
  E. Constraint Instability (frequent mode changes)

Each rule returns:
  {
    "type": "performance_degradation",
    "severity": "critical",
    "message": "Winrate dropped below 0.5",
    "context": {...}
  }
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Thresholds
PERFORMANCE_WINRATE_CRITICAL = 0.5
PERFORMANCE_WINRATE_WARNING = 0.55
PERFORMANCE_MIN_TRADES = 20

FEATURE_WINRATE_WARNING = 0.45
FEATURE_WINRATE_CRITICAL = 0.4
FEATURE_MIN_TRADES = 15

BIAS_MIN_TRADES_ONE_SIDE = 20
BIAS_MAX_TRADES_OTHER_SIDE = 3

CALIBRATION_MIN_TRADES_POST = 10

JITTER_MAX_MODE_CHANGES_24H = 3


class AlertRules:
    """
    Alert rule evaluation logic.
    
    Each check_* method returns a list of alert dicts.
    """
    
    @staticmethod
    def check_performance_degradation(
        performance: Dict[str, Any],
        horizon: str = "24h"
    ) -> List[Dict[str, Any]]:
        """
        A. Performance Degradation
        
        Checks:
          - Winrate < 0.5 (critical)
          - Winrate < 0.55 (warning)
          - Avg PnL < 0 (warning)
        
        Args:
            performance: Performance data from /performance endpoint
            horizon: Time horizon to check
        
        Returns:
            List of alert dicts
        """
        alerts = []
        
        if not performance or "overall" not in performance:
            return alerts
        
        overall = performance["overall"]
        total_trades = overall.get("total_trades", 0)
        winrate = overall.get("winrate", 0)
        avg_pnl = overall.get("avg_pnl", 0)
        
        # Need minimum sample size
        if total_trades < PERFORMANCE_MIN_TRADES:
            return alerts
        
        # Critical: Winrate < 0.5
        if winrate < PERFORMANCE_WINRATE_CRITICAL:
            alerts.append({
                "type": "performance_degradation",
                "severity": "critical",
                "message": f"Winrate dropped below {PERFORMANCE_WINRATE_CRITICAL:.0%} ({winrate:.2%}, {total_trades} trades)",
                "context": {
                    "horizon": horizon,
                    "winrate": winrate,
                    "threshold": PERFORMANCE_WINRATE_CRITICAL,
                    "total_trades": total_trades
                }
            })
        
        # Warning: Winrate < 0.55
        elif winrate < PERFORMANCE_WINRATE_WARNING:
            alerts.append({
                "type": "performance_degradation",
                "severity": "warning",
                "message": f"Winrate below {PERFORMANCE_WINRATE_WARNING:.0%} ({winrate:.2%}, {total_trades} trades)",
                "context": {
                    "horizon": horizon,
                    "winrate": winrate,
                    "threshold": PERFORMANCE_WINRATE_WARNING,
                    "total_trades": total_trades
                }
            })
        
        # Warning: Negative avg PnL
        if avg_pnl < 0:
            alerts.append({
                "type": "performance_degradation",
                "severity": "warning",
                "message": f"Average PnL negative ({avg_pnl:.4f}, {total_trades} trades)",
                "context": {
                    "horizon": horizon,
                    "avg_pnl": avg_pnl,
                    "total_trades": total_trades
                }
            })
        
        return alerts
    
    @staticmethod
    def check_feature_breakdown(
        features: Dict[str, Any],
        horizon: str = "24h"
    ) -> List[Dict[str, Any]]:
        """
        B. Feature Breakdown
        
        Checks each dimension (cluster, alignment, timeframe):
          - Winrate < 0.4 (critical)
          - Winrate < 0.45 (warning)
        
        Args:
            features: Feature performance data from /features endpoint
            horizon: Time horizon to check
        
        Returns:
            List of alert dicts
        """
        alerts = []
        
        if not features or "horizons" not in features:
            return alerts
        
        horizon_data = features["horizons"].get(horizon, {})
        
        # Check clusters
        for cluster in horizon_data.get("by_cluster", []):
            if not cluster.get("valid"):
                continue  # Skip statistically insignificant
            
            name = cluster["cluster"]
            winrate = cluster["winrate"]
            count = cluster["count"]
            avg_pnl = cluster["avg_pnl"]
            
            if winrate < FEATURE_WINRATE_CRITICAL:
                alerts.append({
                    "type": "cluster_degradation",
                    "severity": "critical",
                    "message": f"Cluster '{name}' severely underperforming ({winrate:.2%} winrate, {count} trades)",
                    "context": {
                        "horizon": horizon,
                        "dimension": "cluster",
                        "cluster": name,
                        "winrate": winrate,
                        "avg_pnl": avg_pnl,
                        "count": count
                    }
                })
            elif winrate < FEATURE_WINRATE_WARNING:
                alerts.append({
                    "type": "cluster_degradation",
                    "severity": "warning",
                    "message": f"Cluster '{name}' underperforming ({winrate:.2%} winrate, {count} trades)",
                    "context": {
                        "horizon": horizon,
                        "dimension": "cluster",
                        "cluster": name,
                        "winrate": winrate,
                        "avg_pnl": avg_pnl,
                        "count": count
                    }
                })
        
        # Check timeframes
        for tf in horizon_data.get("by_timeframe", []):
            if not tf.get("valid"):
                continue
            
            name = tf["timeframe"]
            winrate = tf["winrate"]
            count = tf["count"]
            avg_pnl = tf["avg_pnl"]
            
            if winrate < FEATURE_WINRATE_CRITICAL:
                alerts.append({
                    "type": "timeframe_degradation",
                    "severity": "critical",
                    "message": f"Timeframe '{name}' severely underperforming ({winrate:.2%} winrate, {count} trades)",
                    "context": {
                        "horizon": horizon,
                        "dimension": "timeframe",
                        "timeframe": name,
                        "winrate": winrate,
                        "avg_pnl": avg_pnl,
                        "count": count
                    }
                })
            elif winrate < FEATURE_WINRATE_WARNING:
                alerts.append({
                    "type": "timeframe_degradation",
                    "severity": "warning",
                    "message": f"Timeframe '{name}' underperforming ({winrate:.2%} winrate, {count} trades)",
                    "context": {
                        "horizon": horizon,
                        "dimension": "timeframe",
                        "timeframe": name,
                        "winrate": winrate,
                        "avg_pnl": avg_pnl,
                        "count": count
                    }
                })
        
        # Check alignment
        for alignment in horizon_data.get("by_alignment", []):
            if not alignment.get("valid"):
                continue
            
            name = alignment["alignment"]
            winrate = alignment["winrate"]
            count = alignment["count"]
            avg_pnl = alignment["avg_pnl"]
            
            if winrate < FEATURE_WINRATE_CRITICAL:
                alerts.append({
                    "type": "alignment_degradation",
                    "severity": "critical",
                    "message": f"Alignment '{name}' severely underperforming ({winrate:.2%} winrate, {count} trades)",
                    "context": {
                        "horizon": horizon,
                        "dimension": "alignment",
                        "alignment": name,
                        "winrate": winrate,
                        "avg_pnl": avg_pnl,
                        "count": count
                    }
                })
            elif winrate < FEATURE_WINRATE_WARNING:
                alerts.append({
                    "type": "alignment_degradation",
                    "severity": "warning",
                    "message": f"Alignment '{name}' underperforming ({winrate:.2%} winrate, {count} trades)",
                    "context": {
                        "horizon": horizon,
                        "dimension": "alignment",
                        "alignment": name,
                        "winrate": winrate,
                        "avg_pnl": avg_pnl,
                        "count": count
                    }
                })
        
        return alerts
    
    @staticmethod
    def check_directional_bias(
        features: Dict[str, Any],
        horizon: str = "24h"
    ) -> List[Dict[str, Any]]:
        """
        C. Directional Bias Risk
        
        Checks:
          - LONG-only (SHORT count very low)
          - SHORT-only (LONG count very low)
        
        This is CRITICAL because it means system is blind to one side.
        
        Args:
            features: Feature performance data
            horizon: Time horizon to check
        
        Returns:
            List of alert dicts
        """
        alerts = []
        
        if not features or "horizons" not in features:
            return alerts
        
        horizon_data = features["horizons"].get(horizon, {})
        by_side = horizon_data.get("by_side", [])
        
        if len(by_side) < 2:
            # Only one side present
            if len(by_side) == 1:
                side = by_side[0]
                if side["count"] >= BIAS_MIN_TRADES_ONE_SIDE:
                    alerts.append({
                        "type": "directional_bias",
                        "severity": "critical",
                        "message": f"System is {side['side']}-only ({side['count']} trades, zero opposite side)",
                        "context": {
                            "horizon": horizon,
                            "dimension": "side",
                            "dominant_side": side["side"],
                            "dominant_count": side["count"],
                            "other_count": 0
                        }
                    })
            return alerts
        
        # Both sides present - check for severe imbalance
        long_data = next((s for s in by_side if s["side"] == "LONG"), None)
        short_data = next((s for s in by_side if s["side"] == "SHORT"), None)
        
        if long_data and short_data:
            long_count = long_data["count"]
            short_count = short_data["count"]
            
            # LONG bias
            if long_count >= BIAS_MIN_TRADES_ONE_SIDE and short_count <= BIAS_MAX_TRADES_OTHER_SIDE:
                alerts.append({
                    "type": "directional_bias",
                    "severity": "warning",
                    "message": f"Strong LONG bias ({long_count} LONG vs {short_count} SHORT)",
                    "context": {
                        "horizon": horizon,
                        "dimension": "side",
                        "long_count": long_count,
                        "short_count": short_count
                    }
                })
            
            # SHORT bias
            elif short_count >= BIAS_MIN_TRADES_ONE_SIDE and long_count <= BIAS_MAX_TRADES_OTHER_SIDE:
                alerts.append({
                    "type": "directional_bias",
                    "severity": "warning",
                    "message": f"Strong SHORT bias ({short_count} SHORT vs {long_count} LONG)",
                    "context": {
                        "horizon": horizon,
                        "dimension": "side",
                        "long_count": long_count,
                        "short_count": short_count
                    }
                })
        
        return alerts
    
    @staticmethod
    def check_calibration_drift(
        calibration_state: Optional[Dict[str, Any]],
        features: Dict[str, Any],
        horizon: str = "24h"
    ) -> List[Dict[str, Any]]:
        """
        D. Calibration Drift
        
        Checks if calibration is making things worse.
        
        Logic:
          - If bucket got positive adjustment (e.g., +0.03)
          - But post-calibration performance is worse
          - → Critical alert
        
        NOTE: This requires tracking pre/post calibration performance.
              For MVP, we check if calibrated buckets have low winrate.
        
        Args:
            calibration_state: Calibration state from ScoreCalibrator
            features: Feature performance data
            horizon: Time horizon to check
        
        Returns:
            List of alert dicts
        """
        alerts = []
        
        if not calibration_state or not features:
            return alerts
        
        # Get buckets with adjustments
        buckets = calibration_state.get("buckets", {})
        
        horizon_data = features["horizons"].get(horizon, {})
        score_buckets = horizon_data.get("by_score_bucket", [])
        
        for bucket_key, bucket_data in buckets.items():
            adjustment = bucket_data.get("adjustment", 0)
            
            # Only check buckets with positive adjustment (boosted)
            if adjustment <= 0:
                continue
            
            # Find corresponding performance
            perf = next(
                (b for b in score_buckets if bucket_key in b["score_bucket"]),
                None
            )
            
            if perf and perf.get("valid"):
                winrate = perf["winrate"]
                count = perf["count"]
                
                # If boosted bucket has low winrate → calibration may be harmful
                if winrate < FEATURE_WINRATE_WARNING:
                    alerts.append({
                        "type": "calibration_drift",
                        "severity": "warning",
                        "message": f"Calibrated bucket '{bucket_key}' underperforming despite +{adjustment:.2f} boost ({winrate:.2%} winrate)",
                        "context": {
                            "horizon": horizon,
                            "bucket": bucket_key,
                            "adjustment": adjustment,
                            "winrate": winrate,
                            "count": count
                        }
                    })
        
        return alerts
    
    @staticmethod
    def check_constraint_instability(
        constraint_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        E. Constraint Instability (Jitter)
        
        Checks if dynamic constraints are changing mode too frequently.
        
        Frequent mode changes indicate:
          - Unstable signals
          - Poor adaptation
          - Noise in inputs
        
        Args:
            constraint_history: Recent constraint state snapshots
                [{mode: "neutral", timestamp: ...}, ...]
        
        Returns:
            List of alert dicts
        """
        alerts = []
        
        if not constraint_history or len(constraint_history) < 2:
            return alerts
        
        # Count mode changes in last 24h
        mode_changes = 0
        prev_mode = constraint_history[0].get("mode")
        
        for state in constraint_history[1:]:
            current_mode = state.get("mode")
            if current_mode != prev_mode:
                mode_changes += 1
                prev_mode = current_mode
        
        if mode_changes > JITTER_MAX_MODE_CHANGES_24H:
            alerts.append({
                "type": "constraint_instability",
                "severity": "warning",
                "message": f"Dynamic constraints changed mode {mode_changes} times in 24h (threshold: {JITTER_MAX_MODE_CHANGES_24H})",
                "context": {
                    "mode_changes": mode_changes,
                    "threshold": JITTER_MAX_MODE_CHANGES_24H,
                    "recent_modes": [s.get("mode") for s in constraint_history[:5]]
                }
            })
        
        return alerts
