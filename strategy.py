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

# ================= TENDENCIA =================

def trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    return None

# ================= ZONAS =================

def mid_price(df):
    return (df["high"].max() + df["low"].min()) / 2

def in_discount(df):
    return df.iloc[-1]["close"] < mid_price(df)

def in_premium(df):
    return df.iloc[-1]["close"] > mid_price(df)

# ================= FILTROS =================

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 3

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.8

# ================= PULLBACK REAL =================

def valid_pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]

    return body(c2) < body(c3) and body(c1) > body(c2)

# ================= RECHAZO =================

def rejection_up(df):
    c = df.iloc[-1]
    return bearish(c) and (c["high"] - max(c["open"], c["close"])) > body(c)

def rejection_down(df):
    c = df.iloc[-1]
    return bullish(c) and (min(c["open"], c["close"]) - c["low"]) > body(c)

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

# ================= ENTRADA PRO =================

def get_signal(df1, df5):
    try:
        if is_ranging(df5):
            return None

        if is_overextended(df1):
            return None

        t = trend(df5)

        # ================= VENTAS (ZONA PREMIUM) =================

        if t == "bullish" and in_premium(df5):
            if rejection_up(df1):
                return "put"

        # ================= COMPRAS (ZONA DISCOUNT) =================

        if t == "bearish" and in_discount(df5):
            if rejection_down(df1):
                return "call"

        # ================= CONTINUACION =================

        if t == "bullish" and in_discount(df5):
            if valid_pullback(df1) and strong_bull(df1.iloc[-1]):
                return "call"

        if t == "bearish" and in_premium(df5):
            if valid_pullback(df1) and strong_bear(df1.iloc[-1]):
                return "put"

        return None

    except:
        return None
