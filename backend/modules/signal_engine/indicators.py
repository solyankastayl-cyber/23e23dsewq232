"""Technical Indicators — Core TA Math"""

from statistics import mean


def sma(values, period):
    """Simple Moving Average."""
    if len(values) < period:
        return None
    return mean(values[-period:])


def ema(values, period):
    """Exponential Moving Average."""
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    ema_val = mean(values[:period])
    for price in values[period:]:
        ema_val = (price - ema_val) * multiplier + ema_val
    return ema_val


def rsi(closes, period=14):
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))

    avg_gain = mean(gains)
    avg_loss = mean(losses)

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(highs, lows, closes, period=14):
    """Average True Range."""
    if len(closes) < period + 1:
        return None

    trs = []
    for i in range(-period, 0):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i - 1]

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        trs.append(tr)

    return mean(trs)


def momentum(closes, period=10):
    """Price momentum (% change)."""
    if len(closes) < period + 1:
        return None
    old = closes[-period - 1]
    new = closes[-1]
    if old == 0:
        return 0.0
    return (new - old) / old


def realized_volatility(closes, period=20):
    """Realized volatility (std dev of returns)."""
    if len(closes) < period + 1:
        return 0.02

    rets = []
    for i in range(-period, 0):
        prev = closes[i - 1]
        cur = closes[i]
        if prev != 0:
            rets.append((cur - prev) / prev)

    if not rets:
        return 0.02

    mu = mean(rets)
    var = mean([(r - mu) ** 2 for r in rets])
    return var ** 0.5
