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

# ================= FUERZA =================

def strong_bull(c):
    return bullish(c) and body(c) > range_c(c) * 0.6

def strong_bear(c):
    return bearish(c) and body(c) > range_c(c) * 0.6

def strong_momentum(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] > np.mean(moves) * 1.3

# ================= TENDENCIA =================

def trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    return None

def macro_trend(df15):
    return trend(df15)

# ================= FILTROS =================

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 2.5

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.8

def late_entry(df):
    last3 = df.iloc[-3:]
    bullish_count = sum(1 for _, c in last3.iterrows() if bullish(c))
    bearish_count = sum(1 for _, c in last3.iterrows() if bearish(c))
    return bullish_count >= 3 or bearish_count >= 3

def weak_structure(df):
    bodies = np.abs(df["close"] - df["open"])
    return np.mean(bodies) < np.mean(df["high"] - df["low"]) * 0.4

# ================= ESTRUCTURA =================

def break_of_structure(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] > highs[-3]:
        return "bullish"

    if lows[-1] < lows[-2] < lows[-3]:
        return "bearish"

    return None

def is_pullback(df5, df15):
    macro = trend(df15)
    micro = trend(df5)
    return macro and micro and macro != micro

# ================= SNIPER =================

def liquidity_sweep(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["high"] > prev["high"] and last["close"] < prev["high"]:
        return "bearish"

    if last["low"] < prev["low"] and last["close"] > prev["low"]:
        return "bullish"

    return None

def sniper_candle(df):
    c = df.iloc[-1]

    upper_wick = c["high"] - max(c["open"], c["close"])
    lower_wick = min(c["open"], c["close"]) - c["low"]
    body_size = body(c)

    if upper_wick > body_size * 1.5:
        return "bearish"

    if lower_wick > body_size * 1.5:
        return "bullish"

    return None

# ================= PULLBACK =================

def valid_pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]
    return body(c2) < body(c3) and body(c1) > body(c2)

# ================= SCORE =================

def score_market(df1, df5, df15):
    score = 0

    if macro_trend(df15):
        score += 3

    if trend(df5):
        score += 2

    if not is_ranging(df5):
        score += 2

    if strong_momentum(df1):
        score += 2

    return score

# ================= ENTRADA FINAL =================

def get_signal(df1, df5, df15):
    try:
        if is_ranging(df5):
            return None

        if is_overextended(df1):
            return None

        if late_entry(df1):
            return None

        if weak_structure(df1):
            return None

        if is_pullback(df5, df15):
            return None

        macro = macro_trend(df15)
        micro = trend(df5)
        bos = break_of_structure(df5)

        if macro != micro or bos != micro:
            return None

        # 🔥 SNIPER ENTRY
        sweep = liquidity_sweep(df1)
        sniper = sniper_candle(df1)

        if sweep and sniper and sweep == sniper and sweep == macro:
            return "call" if sweep == "bullish" else "put"

        # fallback (continuación)
        if macro == "bullish":
            if valid_pullback(df1) and strong_bull(df1.iloc[-1]) and strong_momentum(df1):
                return "call"

        if macro == "bearish":
            if valid_pullback(df1) and strong_bear(df1.iloc[-1]) and strong_momentum(df1):
                return "put"

        return None

    except:
        return None
