import numpy as np

def body(c):
    return abs(c["close"] - c["open"])

def bullish(c):
    return c["close"] > c["open"]

def bearish(c):
    return c["close"] < c["open"]

# ================= TENDENCIA =================

def trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    return None

# ================= FILTROS =================

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 2

def is_exhausted(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] < np.mean(moves) * 0.5

def strong_support_resistance(df):
    highs = df["high"].values
    lows = df["low"].values
    tol = np.mean(df["high"] - df["low"]) * 0.3

    touches_high = sum(abs(h - max(highs[-10:])) < tol for h in highs[-10:])
    touches_low = sum(abs(l - min(lows[-10:])) < tol for l in lows[-10:])

    return touches_high >= 3 or touches_low >= 3

# ================= NUEVOS FILTROS PRO =================

def strong_momentum(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return (last["high"] - last["low"]) > avg * 1.2

def late_entry(df):
    closes = df["close"].values
    count = 0

    for i in range(-1, -6, -1):
        if closes[i] > closes[i-1]:
            count += 1

    return count >= 3

def optimal_zone(df):
    high = df["high"].max()
    low = df["low"].min()
    price = df.iloc[-1]["close"]

    mid = (high + low) / 2

    if price < mid:
        return "discount"

    if price > mid:
        return "premium"

    return None

# ================= CONFIRMACIONES =================

def liquidity_sweep(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["high"] > prev["high"] and last["close"] < prev["high"]:
        return "bearish"

    if last["low"] < prev["low"] and last["close"] > prev["low"]:
        return "bullish"

    return None

def rejection(df):
    c = df.iloc[-1]
    upper = c["high"] - max(c["open"], c["close"])
    lower = min(c["open"], c["close"]) - c["low"]
    b = body(c)

    if upper > b * 1.5:
        return "bearish"

    if lower > b * 1.5:
        return "bullish"

    return None

def engulfing(df):
    c1 = df.iloc[-2]
    c2 = df.iloc[-1]

    if bearish(c1) and bullish(c2):
        if c2["close"] > c1["open"] and c2["open"] < c1["close"]:
            return "bullish"

    if bullish(c1) and bearish(c2):
        if c2["close"] < c1["open"] and c2["open"] > c1["close"]:
            return "bearish"

    return None

def pullback(df):
    return body(df.iloc[-1]) < body(df.iloc[-2])

# ================= ENTRADA FINAL =================

def get_signal(df1, df5, df30):
    try:
        macro = trend(df30)
        micro = trend(df5)

        if not macro or not micro:
            return None

        if macro != micro:
            return None

        if is_ranging(df5):
            return None

        if is_exhausted(df1):
            return None

        if strong_support_resistance(df5):
            return None

        if not pullback(df5):
            return None

        if late_entry(df5):
            return None

        if not strong_momentum(df1):
            return None

        zone = optimal_zone(df5)

        sweep = liquidity_sweep(df1)
        rej = rejection(df1)
        eng = engulfing(df1)

        if not sweep:
            return None

        # ===== CALL =====
        if macro == "bullish":
            if zone != "discount":
                return None
            if sweep == "bullish" and (rej == "bullish" or eng == "bullish"):
                return "call"

        # ===== PUT =====
        if macro == "bearish":
            if zone != "premium":
                return None
            if sweep == "bearish" and (rej == "bearish" or eng == "bearish"):
                return "put"

        return None

    except:
        return None

# ================= SCORE =================

def score_market(df1, df5, df30):
    score = 0

    if trend(df30):
        score += 3

    if trend(df5):
        score += 2

    if not is_ranging(df5):
        score += 2

    if not is_exhausted(df1):
        score += 2

    return score
