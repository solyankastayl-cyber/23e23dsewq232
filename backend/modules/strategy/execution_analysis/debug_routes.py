"""
Debug Routes for Phase 3.2 - Discovery Debugging
=================================================

Provides feature breakdown from shadow_trades for data-driven filtering decisions.
"""

from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from pymongo import MongoClient
import os

router = APIRouter(prefix="/api/debug", tags=["debug"])


def get_sync_db():
    """Get sync MongoDB client for aggregations"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = MongoClient(mongo_url)
    return client["trading_os"]


@router.get("/features-from-shadow")
async def features_from_shadow(
    days: int = 7,
    experiment_id: str = "market_dynamic",
) -> Dict[str, Any]:
    """
    DEBUG: Feature breakdown directly from shadow_trades.
    Source of truth for Phase 3.2 Discovery Debugging.
    
    Returns winrate and avg_pnl grouped by:
    - cluster (majors/alts)
    - timeframe (1h/4h/1d)
    - alignment (aligned/divergent)
    - score bucket (0-1, 1-2, etc.)
    
    Args:
        days: Look back period (default: 7)
        experiment_id: Experiment to analyze (default: market_dynamic)
    
    Returns:
        Breakdown showing which features are killing winrate
    """
    
    db = get_sync_db()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # MongoDB aggregation pipeline
    pipeline = [
        {
            "$match": {
                "experiment_id": experiment_id,
                "created_at": {"$gte": since},
            }
        },
        
        # Unwind horizons to analyze resolved trades
        {
            "$unwind": "$horizons"
        },
        
        # Only resolved horizons with PnL data
        {
            "$match": {
                "horizons.resolved": True,
                "horizons.pnl": {"$ne": None}
            }
        },
        
        # Normalize fields for grouping
        {
            "$addFields": {
                "cluster": {
                    "$ifNull": ["$features.cluster", "unknown"]
                },
                "timeframe": {
                    "$ifNull": ["$timeframe", "unknown"]
                },
                "alignment": {
                    "$ifNull": ["$features.alignment", "unknown"]
                },
                "score": {
                    "$ifNull": ["$features.score", 0.5]
                },
                "pnl": "$horizons.pnl",
                "horizon": "$horizons.name",
                "is_win": {
                    "$cond": [{"$gt": ["$horizons.pnl", 0]}, 1, 0]
                }
            }
        },
        
        # Create facets for different breakdowns
        {
            "$facet": {
                # === BY CLUSTER ===
                "by_cluster": [
                    {
                        "$group": {
                            "_id": "$cluster",
                            "count": {"$sum": 1},
                            "wins": {"$sum": "$is_win"},
                            "avg_pnl": {"$avg": "$pnl"},
                            "total_pnl": {"$sum": "$pnl"}
                        }
                    },
                    {
                        "$addFields": {
                            "winrate": {
                                "$cond": [
                                    {"$gt": ["$count", 0]},
                                    {"$divide": ["$wins", "$count"]},
                                    0
                                ]
                            }
                        }
                    },
                    {"$sort": {"count": -1}}
                ],
                
                # === BY TIMEFRAME ===
                "by_timeframe": [
                    {
                        "$group": {
                            "_id": "$timeframe",
                            "count": {"$sum": 1},
                            "wins": {"$sum": "$is_win"},
                            "avg_pnl": {"$avg": "$pnl"},
                            "total_pnl": {"$sum": "$pnl"}
                        }
                    },
                    {
                        "$addFields": {
                            "winrate": {
                                "$cond": [
                                    {"$gt": ["$count", 0]},
                                    {"$divide": ["$wins", "$count"]},
                                    0
                                ]
                            }
                        }
                    },
                    {"$sort": {"count": -1}}
                ],
                
                # === BY ALIGNMENT ===
                "by_alignment": [
                    {
                        "$group": {
                            "_id": "$alignment",
                            "count": {"$sum": 1},
                            "wins": {"$sum": "$is_win"},
                            "avg_pnl": {"$avg": "$pnl"},
                            "total_pnl": {"$sum": "$pnl"}
                        }
                    },
                    {
                        "$addFields": {
                            "winrate": {
                                "$cond": [
                                    {"$gt": ["$count", 0]},
                                    {"$divide": ["$wins", "$count"]},
                                    0
                                ]
                            }
                        }
                    },
                    {"$sort": {"count": -1}}
                ],
                
                # === BY SCORE BUCKET ===
                "by_score": [
                    {
                        "$addFields": {
                            "score_bucket": {
                                "$concat": [
                                    {
                                        "$toString": {
                                            "$multiply": [
                                                {"$floor": {"$multiply": ["$score", 10]}},
                                                0.1
                                            ]
                                        }
                                    },
                                    "-",
                                    {
                                        "$toString": {
                                            "$multiply": [
                                                {
                                                    "$add": [
                                                        {"$floor": {"$multiply": ["$score", 10]}},
                                                        1
                                                    ]
                                                },
                                                0.1
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    },
                    {
                        "$group": {
                            "_id": "$score_bucket",
                            "count": {"$sum": 1},
                            "wins": {"$sum": "$is_win"},
                            "avg_pnl": {"$avg": "$pnl"},
                            "total_pnl": {"$sum": "$pnl"}
                        }
                    },
                    {
                        "$addFields": {
                            "winrate": {
                                "$cond": [
                                    {"$gt": ["$count", 0]},
                                    {"$divide": ["$wins", "$count"]},
                                    0
                                ]
                            }
                        }
                    },
                    {"$sort": {"_id": 1}}
                ],
                
                # === BY HORIZON ===
                "by_horizon": [
                    {
                        "$group": {
                            "_id": "$horizon",
                            "count": {"$sum": 1},
                            "wins": {"$sum": "$is_win"},
                            "avg_pnl": {"$avg": "$pnl"},
                            "total_pnl": {"$sum": "$pnl"}
                        }
                    },
                    {
                        "$addFields": {
                            "winrate": {
                                "$cond": [
                                    {"$gt": ["$count", 0]},
                                    {"$divide": ["$wins", "$count"]},
                                    0
                                ]
                            }
                        }
                    },
                    {"$sort": {"_id": 1}}
                ]
            }
        }
    ]
    
    # Sync MongoDB aggregation
    result = list(db.shadow_trades.aggregate(pipeline))
    
    if not result:
        return {
            "ok": False,
            "error": "no_data",
            "message": f"No shadow_trades found for experiment_id={experiment_id} in last {days} days",
            "hint": "Try enabling market_dynamic experiment or check if shadow trades are being created"
        }
    
    data = result[0]
    
    # Normalize output (filter noise, format numbers)
    def normalize(items, min_sample=5):
        """Format and filter by minimum sample size"""
        return [
            {
                "value": x["_id"],
                "count": x["count"],
                "winrate": round(x["winrate"], 4),
                "avg_pnl": round(x["avg_pnl"], 6),
                "total_pnl": round(x["total_pnl"], 4),
                # Quality indicator
                "quality": "🔴 BAD" if x["winrate"] < 0.4 else "🟡 MEDIOCRE" if x["winrate"] < 0.55 else "🟢 GOOD"
            }
            for x in items
            if x["count"] >= min_sample  # Filter noise
        ]
    
    # Get total stats
    total_trades = sum(x["count"] for x in data.get("by_cluster", []))
    
    return {
        "ok": True,
        "meta": {
            "experiment_id": experiment_id,
            "days": days,
            "total_trades": total_trades,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "interpretation": {
                "🔴 BAD": "winrate < 40% → REJECT these",
                "🟡 MEDIOCRE": "40% ≤ winrate < 55% → CAUTION",
                "🟢 GOOD": "winrate ≥ 55% → ACCEPT these"
            }
        },
        "breakdown": {
            "cluster": normalize(data.get("by_cluster", [])),
            "timeframe": normalize(data.get("by_timeframe", [])),
            "alignment": normalize(data.get("by_alignment", [])),
            "score": normalize(data.get("by_score", []), min_sample=3),
            "horizon": normalize(data.get("by_horizon", []))
        },
        "recommended_filters": _generate_filter_recommendations(data)
    }


def _generate_filter_recommendations(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate hard filter recommendations based on data.
    
    Logic:
    - Reject if winrate < 0.40
    - Warn if winrate < 0.55
    """
    recommendations = {
        "reject": [],
        "warn": [],
        "reasoning": []
    }
    
    # Check clusters
    for item in data.get("by_cluster", []):
        if item["count"] < 5:
            continue
        winrate = item["winrate"]
        cluster = item["_id"]
        
        if winrate < 0.40:
            recommendations["reject"].append(f"cluster != '{cluster}'")
            recommendations["reasoning"].append(
                f"❌ Cluster '{cluster}': {winrate:.1%} winrate (< 40% threshold)"
            )
        elif winrate < 0.55:
            recommendations["warn"].append(f"cluster == '{cluster}' has weak performance")
            recommendations["reasoning"].append(
                f"⚠️ Cluster '{cluster}': {winrate:.1%} winrate (marginal)"
            )
    
    # Check timeframes
    for item in data.get("by_timeframe", []):
        if item["count"] < 5:
            continue
        winrate = item["winrate"]
        tf = item["_id"]
        
        if winrate < 0.40:
            recommendations["reject"].append(f"timeframe != '{tf}'")
            recommendations["reasoning"].append(
                f"❌ Timeframe '{tf}': {winrate:.1%} winrate (< 40% threshold)"
            )
        elif winrate < 0.55:
            recommendations["warn"].append(f"timeframe == '{tf}' has weak performance")
            recommendations["reasoning"].append(
                f"⚠️ Timeframe '{tf}': {winrate:.1%} winrate (marginal)"
            )
    
    # Check alignment
    for item in data.get("by_alignment", []):
        if item["count"] < 5:
            continue
        winrate = item["winrate"]
        alignment = item["_id"]
        
        if winrate < 0.40:
            recommendations["reject"].append(f"alignment != '{alignment}'")
            recommendations["reasoning"].append(
                f"❌ Alignment '{alignment}': {winrate:.1%} winrate (< 40% threshold)"
            )
    
    if not recommendations["reject"]:
        recommendations["reasoning"].append("✅ No critical filters needed (all features above 40% winrate)")
    
    return recommendations
