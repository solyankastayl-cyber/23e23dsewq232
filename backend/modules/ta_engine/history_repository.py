"""
History Repository
==================

MongoDB operations for pattern outcome history.

Collection: pattern_outcomes

Document schema:
{
    "symbol": "BTC",
    "pattern_type": "triangle",
    "context_key": "triangle|compression|bearish|down|mid",
    "outcome": "win" | "loss",
    "move_pct": 4.2,
    "duration_h": 26,
    "entry_price": 84000,
    "exit_price": 87528,
    "timeframe": "1D",
    "created_at": datetime,
    "resolved_at": datetime
}
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pymongo.database import Database
from pymongo import DESCENDING


COLLECTION_NAME = "pattern_outcomes"


def get_records_by_key(db: Database, context_key: str, limit: int = 100) -> List[Dict]:
    """
    Get historical outcome records by context key.
    
    Args:
        db: MongoDB database instance
        context_key: Pattern × Context key from build_history_key()
        limit: Maximum records to return
    
    Returns:
        List of outcome records
    """
    try:
        cursor = db[COLLECTION_NAME].find(
            {"context_key": context_key},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    except Exception as e:
        print(f"[HistoryRepo] Error getting records: {e}")
        return []


def get_records_by_pattern(db: Database, pattern_type: str, limit: int = 100) -> List[Dict]:
    """
    Get all records for a pattern type (regardless of context).
    """
    try:
        cursor = db[COLLECTION_NAME].find(
            {"pattern_type": pattern_type.lower()},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    except Exception as e:
        print(f"[HistoryRepo] Error getting pattern records: {e}")
        return []


def get_records_by_symbol(db: Database, symbol: str, limit: int = 100) -> List[Dict]:
    """
    Get all records for a symbol.
    """
    try:
        cursor = db[COLLECTION_NAME].find(
            {"symbol": symbol.upper()},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    except Exception as e:
        print(f"[HistoryRepo] Error getting symbol records: {e}")
        return []


def store_outcome(db: Database, payload: Dict) -> bool:
    """
    Store a new pattern outcome record.
    
    Args:
        db: MongoDB database instance
        payload: Outcome data
    
    Returns:
        True if successful
    """
    try:
        # Ensure required fields
        required = ["symbol", "pattern_type", "context_key", "outcome"]
        for field in required:
            if field not in payload:
                print(f"[HistoryRepo] Missing required field: {field}")
                return False
        
        # Add timestamp if not present
        if "created_at" not in payload:
            payload["created_at"] = datetime.now(timezone.utc)
        
        # Normalize
        payload["symbol"] = payload["symbol"].upper()
        payload["pattern_type"] = payload["pattern_type"].lower()
        payload["outcome"] = payload["outcome"].lower()
        
        db[COLLECTION_NAME].insert_one(payload)
        print(f"[HistoryRepo] Stored outcome: {payload['context_key']} → {payload['outcome']}")
        return True
        
    except Exception as e:
        print(f"[HistoryRepo] Error storing outcome: {e}")
        return False


def get_stats_summary(db: Database) -> Dict:
    """
    Get summary statistics for all historical data.
    """
    try:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_records": {"$sum": 1},
                    "total_wins": {"$sum": {"$cond": [{"$eq": ["$outcome", "win"]}, 1, 0]}},
                    "total_losses": {"$sum": {"$cond": [{"$eq": ["$outcome", "loss"]}, 1, 0]}},
                    "unique_keys": {"$addToSet": "$context_key"},
                    "unique_patterns": {"$addToSet": "$pattern_type"},
                }
            }
        ]
        
        result = list(db[COLLECTION_NAME].aggregate(pipeline))
        
        if result:
            r = result[0]
            total = r["total_wins"] + r["total_losses"]
            return {
                "total_records": r["total_records"],
                "total_wins": r["total_wins"],
                "total_losses": r["total_losses"],
                "overall_winrate": round(r["total_wins"] / total, 3) if total > 0 else 0,
                "unique_context_keys": len(r["unique_keys"]),
                "unique_patterns": len(r["unique_patterns"]),
            }
        
        return {
            "total_records": 0,
            "total_wins": 0,
            "total_losses": 0,
            "overall_winrate": 0,
            "unique_context_keys": 0,
            "unique_patterns": 0,
        }
        
    except Exception as e:
        print(f"[HistoryRepo] Error getting stats: {e}")
        return {}


def seed_historical_data(db: Database) -> int:
    """
    Seed initial historical data for testing.
    Returns number of records created.
    """
    # Check if already seeded
    existing = db[COLLECTION_NAME].count_documents({})
    if existing > 0:
        print(f"[HistoryRepo] Already has {existing} records, skipping seed")
        return 0
    
    # Sample historical data for various pattern × context combinations
    seed_records = [
        # Triangle in compression - historically strong
        {"symbol": "BTC", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 5.2, "duration_h": 24},
        {"symbol": "BTC", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 4.8, "duration_h": 18},
        {"symbol": "BTC", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 6.1, "duration_h": 32},
        {"symbol": "BTC", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "loss", "move_pct": -2.3, "duration_h": 12},
        {"symbol": "BTC", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 3.9, "duration_h": 20},
        {"symbol": "ETH", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 7.2, "duration_h": 28},
        {"symbol": "ETH", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 4.5, "duration_h": 22},
        {"symbol": "BTC", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "loss", "move_pct": -1.8, "duration_h": 8},
        {"symbol": "BTC", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 5.5, "duration_h": 26},
        {"symbol": "SOL", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 8.1, "duration_h": 30},
        {"symbol": "BTC", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "win", "move_pct": 4.2, "duration_h": 16},
        {"symbol": "ETH", "pattern_type": "triangle", "context_key": "triangle|compression|bearish|down|mid", "outcome": "loss", "move_pct": -3.1, "duration_h": 14},
        
        # Descending channel in trend - good performance
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 6.8, "duration_h": 48},
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 5.2, "duration_h": 36},
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "loss", "move_pct": -4.1, "duration_h": 24},
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 7.5, "duration_h": 52},
        {"symbol": "ETH", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 8.3, "duration_h": 44},
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 4.9, "duration_h": 32},
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "loss", "move_pct": -2.8, "duration_h": 20},
        {"symbol": "SOL", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 9.1, "duration_h": 56},
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 5.6, "duration_h": 40},
        {"symbol": "ETH", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 6.2, "duration_h": 38},
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "loss", "move_pct": -3.5, "duration_h": 28},
        {"symbol": "BTC", "pattern_type": "descending_channel", "context_key": "descending_channel|trend|bearish|down|high", "outcome": "win", "move_pct": 7.8, "duration_h": 46},
        
        # Flag in trend - very strong
        {"symbol": "BTC", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 8.5, "duration_h": 12},
        {"symbol": "BTC", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 7.2, "duration_h": 8},
        {"symbol": "BTC", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 9.1, "duration_h": 16},
        {"symbol": "ETH", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 6.8, "duration_h": 10},
        {"symbol": "BTC", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "loss", "move_pct": -2.1, "duration_h": 6},
        {"symbol": "BTC", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 10.2, "duration_h": 14},
        {"symbol": "SOL", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 12.5, "duration_h": 18},
        {"symbol": "BTC", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 7.8, "duration_h": 11},
        {"symbol": "ETH", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 8.9, "duration_h": 13},
        {"symbol": "BTC", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "loss", "move_pct": -1.5, "duration_h": 4},
        {"symbol": "BTC", "pattern_type": "flag", "context_key": "flag|trend|bullish|up|mid", "outcome": "win", "move_pct": 6.5, "duration_h": 9},
        
        # Rectangle in range - neutral
        {"symbol": "BTC", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "win", "move_pct": 3.2, "duration_h": 72},
        {"symbol": "BTC", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "loss", "move_pct": -2.8, "duration_h": 48},
        {"symbol": "BTC", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "win", "move_pct": 2.9, "duration_h": 64},
        {"symbol": "ETH", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "loss", "move_pct": -3.1, "duration_h": 56},
        {"symbol": "BTC", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "win", "move_pct": 3.5, "duration_h": 80},
        {"symbol": "BTC", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "loss", "move_pct": -2.4, "duration_h": 40},
        {"symbol": "SOL", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "win", "move_pct": 4.1, "duration_h": 68},
        {"symbol": "BTC", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "loss", "move_pct": -3.5, "duration_h": 52},
        {"symbol": "ETH", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "win", "move_pct": 2.7, "duration_h": 76},
        {"symbol": "BTC", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "loss", "move_pct": -2.9, "duration_h": 44},
        {"symbol": "BTC", "pattern_type": "rectangle", "context_key": "rectangle|range|neutral|none|low", "outcome": "win", "move_pct": 3.8, "duration_h": 84},
        
        # Wedge in volatile - weak performance
        {"symbol": "BTC", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "loss", "move_pct": -5.2, "duration_h": 8},
        {"symbol": "BTC", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "loss", "move_pct": -4.8, "duration_h": 12},
        {"symbol": "BTC", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "win", "move_pct": 3.1, "duration_h": 6},
        {"symbol": "ETH", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "loss", "move_pct": -6.2, "duration_h": 10},
        {"symbol": "BTC", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "loss", "move_pct": -4.1, "duration_h": 14},
        {"symbol": "BTC", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "win", "move_pct": 2.8, "duration_h": 8},
        {"symbol": "SOL", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "loss", "move_pct": -7.5, "duration_h": 16},
        {"symbol": "BTC", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "loss", "move_pct": -5.8, "duration_h": 11},
        {"symbol": "ETH", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "win", "move_pct": 4.2, "duration_h": 9},
        {"symbol": "BTC", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "loss", "move_pct": -3.9, "duration_h": 7},
        {"symbol": "BTC", "pattern_type": "wedge", "context_key": "wedge|volatile|neutral|none|high", "outcome": "loss", "move_pct": -6.1, "duration_h": 13},
        
        # Head & Shoulders in trend - good performance (NEW!)
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 7.5, "duration_h": 36},
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 6.2, "duration_h": 28},
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 8.1, "duration_h": 42},
        {"symbol": "ETH", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "loss", "move_pct": -3.2, "duration_h": 18},
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 5.8, "duration_h": 32},
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 9.2, "duration_h": 48},
        {"symbol": "SOL", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 11.5, "duration_h": 56},
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "loss", "move_pct": -4.1, "duration_h": 22},
        {"symbol": "ETH", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 6.8, "duration_h": 38},
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 7.9, "duration_h": 44},
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "win", "move_pct": 5.4, "duration_h": 30},
        {"symbol": "BTC", "pattern_type": "head_shoulders", "context_key": "head_shoulders|trend|bearish|down|high", "outcome": "loss", "move_pct": -2.9, "duration_h": 16},
    ]
    
    # Add timestamps
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i, record in enumerate(seed_records):
        record["created_at"] = base_time.replace(day=1 + (i % 28), month=1 + (i // 28) % 12)
        record["timeframe"] = "1D"
    
    # Insert all records
    try:
        db[COLLECTION_NAME].insert_many(seed_records)
        print(f"[HistoryRepo] Seeded {len(seed_records)} historical records")
        return len(seed_records)
    except Exception as e:
        print(f"[HistoryRepo] Error seeding data: {e}")
        return 0


def ensure_indexes(db: Database):
    """Create indexes for efficient queries."""
    try:
        db[COLLECTION_NAME].create_index("context_key")
        db[COLLECTION_NAME].create_index("pattern_type")
        db[COLLECTION_NAME].create_index("symbol")
        db[COLLECTION_NAME].create_index([("created_at", DESCENDING)])
        print("[HistoryRepo] Indexes created")
    except Exception as e:
        print(f"[HistoryRepo] Error creating indexes: {e}")
