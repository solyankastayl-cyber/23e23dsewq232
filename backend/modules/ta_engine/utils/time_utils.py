"""
TA Engine — Time / Timeframe normalization utilities
=====================================================

Single source of truth for converting heterogeneous timestamp/timeframe
inputs (BSON Int64 ms, int seconds, ISO strings, datetimes) into a
predictable canonical form.

Why this exists:
    The TA Engine receives candle data from multiple sources:
      - BinanceProvider → candle.openTime as BSON Int64 (ms since epoch)
      - Mongo aggregations → can be int or str
      - Coinbase / CSV / fixtures → ISO strings or seconds-since-epoch
      - Frontend queries → '1h', '4H', '1d' (mixed case)

    Without normalization we get ValueError: year is out of range
    (datetime.fromtimestamp expects seconds, gets ms),
    Pydantic Int64 validation errors, and silent timeframe mismatches.
"""
from datetime import datetime, timezone
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════
# TIMESTAMP NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def normalize_timestamp(ts: Any) -> Optional[datetime]:
    """
    Convert any incoming timestamp value into an aware UTC datetime.

    Handles:
      - None             → None
      - datetime         → ensure tz=UTC
      - int / float / Int64 (BSON):
            * value > 1e12  → milliseconds since epoch
            * value > 1e10  → ambiguous (treat as ms — modern era)
            * else          → seconds since epoch
      - ISO-8601 string  → parsed; supports trailing 'Z'

    Returns:
      datetime (tz-aware UTC) or None.

    Raises:
      ValueError on truly unknown inputs.
    """
    if ts is None:
        return None

    # Already a datetime — make sure it's tz-aware
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts

    # Numeric (handles BSON Int64 because isinstance(Int64, int) is True)
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        v = float(ts)
        # Heuristic: anything >= 1e12 is definitely ms (year ~33658 if treated
        # as seconds). Anything >= 1e10 is most likely ms too (seconds → 2286+).
        if v >= 1e12:
            return datetime.fromtimestamp(v / 1000.0, tz=timezone.utc)
        if v >= 1e10:
            return datetime.fromtimestamp(v / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(v, tz=timezone.utc)

    # String — try ISO first, then numeric string
    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            return None
        # ISO with trailing Z
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00'))
        except ValueError:
            pass
        # Numeric string fallback
        try:
            return normalize_timestamp(float(s))
        except (TypeError, ValueError):
            pass
        # Last resort: return None instead of raising — keeps pipelines alive
        return None

    raise ValueError(f"Unknown timestamp format: {type(ts).__name__} ({ts!r})")


def normalize_timestamp_iso(ts: Any) -> Optional[str]:
    """Normalize and serialize as ISO-8601 string (or None)."""
    dt = normalize_timestamp(ts)
    return dt.isoformat() if dt is not None else None


def normalize_timestamp_ms(ts: Any) -> Optional[int]:
    """Normalize and serialize as epoch milliseconds (or None)."""
    dt = normalize_timestamp(ts)
    return int(dt.timestamp() * 1000) if dt is not None else None


# ═══════════════════════════════════════════════════════════════
# TIMEFRAME NORMALIZATION
# ═══════════════════════════════════════════════════════════════

# Canonical timeframe codes used everywhere downstream.
# Markets live in: 1m, 5m, 15m, 30m, 1H, 4H, 1D, 1W, 1M, etc.
_TF_ALIASES = {
    # minutes — keep lowercase
    "1m": "1m", "1M_min": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    # hours — uppercase H
    "1h": "1H", "1H": "1H", "60m": "1H",
    "2h": "2H", "2H": "2H",
    "4h": "4H", "4H": "4H", "240m": "4H",
    "6h": "6H", "6H": "6H",
    "8h": "8H", "8H": "8H",
    "12h": "12H", "12H": "12H",
    # days
    "1d": "1D", "1D": "1D", "24h": "1D",
    "3d": "3D", "3D": "3D",
    # weeks
    "1w": "1W", "1W": "1W", "7d": "1W", "7D": "1W",
    # months
    "1mo": "1M", "1M": "1M", "30d": "1M", "30D": "1M",
    # extended (used by /api/ta/research)
    "180d": "180D", "180D": "180D",
    "1y": "1Y", "1Y": "1Y", "365d": "1Y",
}


def normalize_tf(tf: Any) -> str:
    """
    Normalize timeframe input to canonical code.

    Examples:
      '1h' / '1H' / '60m' → '1H'
      '4h' / '4H'         → '4H'
      '1d' / '1D' / '24h' → '1D'
      '7d' / '1w' / '1W'  → '1W'
      '1m' (minute)       → '1m'  (lowercase preserved for minute TFs)

    Falls back to upper() if nothing matches — that keeps custom TFs working.
    """
    if tf is None:
        return "1H"
    s = str(tf).strip()
    if not s:
        return "1H"
    if s in _TF_ALIASES:
        return _TF_ALIASES[s]
    # Try lowercase lookup
    if s.lower() in _TF_ALIASES:
        return _TF_ALIASES[s.lower()]
    # Try uppercase lookup
    if s.upper() in _TF_ALIASES:
        return _TF_ALIASES[s.upper()]
    # Unknown — return as-is uppercased (markets convention)
    return s.upper()
