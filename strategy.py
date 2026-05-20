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
    return bullish(c) and body(c) > range_c(c) * 0.6

def strong_bearish(c):
    return bearish(c) and body(c) > range_c(c) * 0.6

# ================= TENDENCIA =================

def trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    return None

# ================= MOMENTUM =================

def bullish_momentum(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]

    return strong_bullish(c1) and bullish(c2) and bullish(c3)

def bearish_momentum(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]

    return strong_bearish(c1) and bearish(c2) and bearish(c3)

# ================= EXTENSION =================

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.8

# ================= RANGO =================

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 4

# ================= SCORE =================

def score_market(df1, df5):
    score = 0

    if trend(df5):
        score += 2

    if not is_ranging(df5):
        score += 2

    if not is_overextended(df1):
        score += 1

    return score

# ================= ENTRADA =================

def get_signal(df1, df5):
    try:
        if is_ranging(df5):
            return None

        if is_overextended(df1):
            return None

        t = trend(df5)

        # 🟢 CONTINUIDAD CORTA (como tu imagen)
        if t == "bearish":
            if bullish_momentum(df1):
                return "call"

        # 🔴 CONTINUIDAD CORTA
        if t == "bullish":
            if bearish_momentum(df1):
                return "put"

        return None

    except:
        return None
