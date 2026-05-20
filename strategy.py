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

def strong_bullish(c):
    return bullish(c) and body(c) > range_c(c) * 0.65

def strong_bearish(c):
    return bearish(c) and body(c) > range_c(c) * 0.65

# ================= ESTRUCTURA =================

def trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    return None

# ================= ZONAS =================

def equilibrium(df):
    return (df["high"].max() + df["low"].min()) / 2

def in_premium(df):
    return df.iloc[-1]["close"] > equilibrium(df)

def in_discount(df):
    return df.iloc[-1]["close"] < equilibrium(df)

# ================= FILTROS =================

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 5

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.7

# ================= LIQUIDEZ + RECHAZO =================

def rejection_upper(df):
    c = df.iloc[-1]
    wick = c["high"] - max(c["close"], c["open"])
    return wick > body(c) * 1.5

def rejection_lower(df):
    c = df.iloc[-1]
    wick = min(c["close"], c["open"]) - c["low"]
    return wick > body(c) * 1.5

def sweep_high(df):
    return df.iloc[-1]["high"] > df.iloc[-2]["high"]

def sweep_low(df):
    return df.iloc[-1]["low"] < df.iloc[-2]["low"]

# ================= SCORE =================

def score_market(df1, df5):
    score = 0

    t = trend(df5)

    if t:
        score += 2

    if not is_ranging(df5):
        score += 2

    if not is_overextended(df1):
        score += 1

    return score

# ================= SEÑAL ULTRA =================

def get_signal(df1, df5):
    try:
        last = df1.iloc[-1]

        if is_ranging(df5):
            return None

        if is_overextended(df1):
            return None

        t = trend(df5)

        # 🔴 REVERSIÓN ULTRA FILTRADA
        if sweep_high(df1) and rejection_upper(df1) and in_premium(df1) and strong_bearish(last):
            return "put"

        if sweep_low(df1) and rejection_lower(df1) and in_discount(df1) and strong_bullish(last):
            return "call"

        # 🟢 CONTINUIDAD ULTRA LIMPIA
        if t == "bullish":
            if in_discount(df1) and strong_bullish(last):
                return "call"

        if t == "bearish":
            if in_premium(df1) and strong_bearish(last):
                return "put"

        return None

    except:
        return None
