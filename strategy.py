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

# ================= ESTRUCTURA =================

def trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    return None

# ================= RETROCESO (CLAVE) =================

def pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    # retroceso contra tendencia
    if bullish(c2) and bearish(c1):
        return "bearish_pullback"

    if bearish(c2) and bullish(c1):
        return "bullish_pullback"

    return None

# ================= AGOTAMIENTO =================

def is_exhausted(df):
    moves = df["close"].diff().dropna()
    consecutive = (moves > 0).astype(int).groupby((moves <= 0).cumsum()).sum().max()

    return consecutive >= 4  # muchas velas seguidas

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

# ================= ENTRADA FINAL =================

def get_signal(df1, df5):
    try:
        last = df1.iloc[-1]

        if is_ranging(df5):
            return None

        if is_overextended(df1):
            return None

        t = trend(df5)
        pb = pullback(df1)

        # ❌ evitar vender en suelo / comprar en techo
        if is_exhausted(df1):
            return None

        # ================= CONTINUIDAD CON RETROCESO =================
        if t == "bearish":
            if pb == "bullish_pullback" and strong_bearish(last) and in_premium(df1):
                return "put"

        if t == "bullish":
            if pb == "bearish_pullback" and strong_bullish(last) and in_discount(df1):
                return "call"

        return None

    except:
        return None
