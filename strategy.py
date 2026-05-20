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

# ================= ESTRUCTURA REAL =================

def structure_trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    return None

# ================= FILTROS =================

def is_strong_candle(c):
    return body(c) > (range_c(c) * 0.6)

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.5

def market_range(df):
    return (df["high"].max() - df["low"].min())

def is_ranging(df):
    return market_range(df) < np.mean(df["high"] - df["low"]) * 6

# ================= ZONAS =================

def equilibrium(df):
    return (df["high"].max() + df["low"].min()) / 2

def in_discount(df):
    return df.iloc[-1]["close"] < equilibrium(df)

def in_premium(df):
    return df.iloc[-1]["close"] > equilibrium(df)

# ================= LIQUIDITY =================

def liquidity_sweep_high(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last["high"] > prev["high"] and last["close"] < prev["high"]

def liquidity_sweep_low(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last["low"] < prev["low"] and last["close"] > prev["low"]

# ================= SCORE =================

def score_market(df1, df5):
    score = 0

    trend = structure_trend(df5)

    if trend:
        score += 2

    if not is_ranging(df5):
        score += 2

    if not is_overextended(df1):
        score += 1

    return score

# ================= SEÑAL =================

def get_signal(df1, df5):
    try:
        last = df1.iloc[-1]
        prev = df1.iloc[-2]

        if range_c(last) == 0:
            return None

        # ❌ evitar mercado feo
        if is_ranging(df5):
            return None

        if is_overextended(df1):
            return None

        trend = structure_trend(df5)

        # ================= REVERSIÓN PRO =================
        if liquidity_sweep_high(df1) and in_premium(df1) and bearish(last):
            return "put"

        if liquidity_sweep_low(df1) and in_discount(df1) and bullish(last):
            return "call"

        # ================= CONTINUIDAD PRO =================
        if trend == "bullish":
            if in_discount(df1) and bullish(last) and is_strong_candle(last):
                return "call"

        if trend == "bearish":
            if in_premium(df1) and bearish(last) and is_strong_candle(last):
                return "put"

        return None

    except:
        return None
