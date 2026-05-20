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

# ================= FUERZA REAL =================

def strong_bull(c):
    return bullish(c) and body(c) > range_c(c) * 0.65

def strong_bear(c):
    return bearish(c) and body(c) > range_c(c) * 0.65

# ================= TENDENCIA =================

def trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    return None

# ================= RANGO =================

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 3.5

# ================= EXTENSION =================

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.9

# ================= RETROCESO CONTROLADO =================

def valid_pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]

    # pequeño retroceso (no cambio de tendencia)
    return body(c2) < body(c3) and body(c1) > body(c2)

# ================= LIQUIDEZ REAL =================

def liquidity_grab_up(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    return last["high"] > prev["high"] and bearish(last)

def liquidity_grab_down(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    return last["low"] < prev["low"] and bullish(last)

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

# ================= ENTRADAS PRECISAS =================

def get_signal(df1, df5):
    try:
        if is_ranging(df5):
            return None

        if is_overextended(df1):
            return None

        t = trend(df5)

        # ================= CONTINUACION PERFECTA =================

        if t == "bearish":
            if valid_pullback(df1) and strong_bear(df1.iloc[-1]):
                return "put"

        if t == "bullish":
            if valid_pullback(df1) and strong_bull(df1.iloc[-1]):
                return "call"

        # ================= TRAMPAS (ALTA EFECTIVIDAD) =================

        if liquidity_grab_up(df1) and strong_bear(df1.iloc[-1]):
            return "put"

        if liquidity_grab_down(df1) and strong_bull(df1.iloc[-1]):
            return "call"

        return None

    except:
        return None
