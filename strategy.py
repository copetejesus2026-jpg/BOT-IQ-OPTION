import numpy as np

# ================= BASICOS =================

def body(c):
    return abs(c["close"] - c["open"])

def range_c(c):
    return c["high"] - c["low"]

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

# ================= CONSOLIDACIÓN =================

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 2

# ================= AGOTAMIENTO =================

def is_exhausted(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] < np.mean(moves) * 0.5

# ================= SOPORTE / RESISTENCIA =================

def near_support_resistance(df):
    high_zone = df["high"].max()
    low_zone = df["low"].min()
    price = df.iloc[-1]["close"]

    if abs(price - high_zone) < (high_zone - low_zone) * 0.1:
        return True

    if abs(price - low_zone) < (high_zone - low_zone) * 0.1:
        return True

    return False

# 🔥 ZONAS FUERTES (3+ TOQUES)

def strong_support_resistance(df):
    highs = df["high"].values
    lows = df["low"].values

    tolerance = np.mean(df["high"] - df["low"]) * 0.3

    touches_high = 0
    touches_low = 0

    for i in range(-10, 0):
        if abs(highs[i] - max(highs[-10:])) < tolerance:
            touches_high += 1

        if abs(lows[i] - min(lows[-10:])) < tolerance:
            touches_low += 1

    if touches_high >= 3 or touches_low >= 3:
        return True

    return False

# ================= MANIPULACIÓN =================

def liquidity_sweep(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["high"] > prev["high"] and last["close"] < prev["high"]:
        return "bearish"

    if last["low"] < prev["low"] and last["close"] > prev["low"]:
        return "bullish"

    return None

# ================= FALSA RUPTURA =================

def fake_breakout(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["high"] > prev["high"] and last["close"] < prev["high"]:
        return True

    if last["low"] < prev["low"] and last["close"] > prev["low"]:
        return True

    return False

# ================= RECHAZO =================

def rejection_candle(df):
    c = df.iloc[-1]

    upper = c["high"] - max(c["open"], c["close"])
    lower = min(c["open"], c["close"]) - c["low"]
    b = body(c)

    if upper > b * 1.5:
        return "bearish"

    if lower > b * 1.5:
        return "bullish"

    return None

# ================= ENTRADA =================

def get_signal(df1, df5):
    try:
        t = trend(df5)

        if not t:
            return None

        # ❌ FILTROS CLAVE
        if is_ranging(df5):
            return None

        if is_exhausted(df1):
            return None

        if near_support_resistance(df5):
            return None

        if strong_support_resistance(df5):
            return None

        # 🔥 MANIPULACIÓN + RECHAZO
        sweep = liquidity_sweep(df1)
        reject = rejection_candle(df1)

        if not sweep or not reject:
            return None

        # ================= CALL =================
        if t == "bullish":
            if sweep == "bullish" and reject == "bullish":
                return "call"

        # ================= PUT =================
        if t == "bearish":
            if sweep == "bearish" and reject == "bearish":
                return "put"

        return None

    except:
        return None

# ================= SCORE =================

def score_market(df1, df5):
    score = 0

    if trend(df5):
        score += 3

    if not is_ranging(df5):
        score += 2

    if not is_exhausted(df1):
        score += 2

    return score
