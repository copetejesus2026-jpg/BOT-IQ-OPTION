import numpy as np

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

# ================= FILTROS =================

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 2

def is_exhausted(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] < np.mean(moves) * 0.6

def late_trend(df):
    closes = df["close"].values
    count = 0

    for i in range(-1, -6, -1):
        if closes[i] > closes[i-1]:
            count += 1

    return count >= 4

def overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.6

# ================= BOS (CLAVE) =================

def break_of_structure(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-3] and highs[-2] <= highs[-3]:
        return "bullish"

    if lows[-1] < lows[-3] and lows[-2] >= lows[-3]:
        return "bearish"

    return None

# ================= RETEST =================

def small_pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    return body(c1) < body(c2)

# ================= IMPULSO =================

def strong_impulse(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] > np.mean(moves) * 1.2

# ================= ENTRADA =================

def get_signal(df1, df5, df15):
    try:
        macro = trend(df15)
        micro = trend(df5)

        if not macro or not micro:
            return None

        if macro != micro:
            return None

        # ❌ FILTROS
        if is_ranging(df5):
            return None

        if is_exhausted(df1):
            return None

        if late_trend(df5):
            return None

        if overextended(df1):
            return None

        # 🔥 BOS (inicio real)
        bos = break_of_structure(df5)

        if bos != macro:
            return None

        # 🔥 RETEST (no entrar en pico)
        if not small_pullback(df1):
            return None

        # 🔥 IMPULSO REAL
        if not strong_impulse(df1):
            return None

        # 🎯 ENTRADA
        if macro == "bullish":
            return "call"

        if macro == "bearish":
            return "put"

        return None

    except:
        return None


# ================= SCORE =================

def score_market(df1, df5, df15):
    score = 0

    if trend(df15):
        score += 3

    if trend(df5):
        score += 2

    if not is_ranging(df5):
        score += 2

    if strong_impulse(df1):
        score += 3

    return score
