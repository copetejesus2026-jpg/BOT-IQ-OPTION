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

def macro_trend(df15):
    return trend(df15)

# ================= FILTROS =================

# 🔴 CONSOLIDACIÓN
def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 2

# 🔴 AGOTAMIENTO
def is_exhausted(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] < np.mean(moves) * 0.5

# 🔴 ENTRADA TARDE
def late_entry(df):
    last3 = df.iloc[-3:]
    bullish_count = sum(1 for _, c in last3.iterrows() if bullish(c))
    bearish_count = sum(1 for _, c in last3.iterrows() if bearish(c))
    return bullish_count >= 3 or bearish_count >= 3

# 🔴 ZONA YA RESPETADA (RECHAZO PREVIO)
def already_reacted(df):
    last5 = df.iloc[-5:]
    rejections = 0

    for _, c in last5.iterrows():
        upper = c["high"] - max(c["open"], c["close"])
        lower = min(c["open"], c["close"]) - c["low"]

        if upper > body(c) or lower > body(c):
            rejections += 1

    return rejections >= 3

# 🔴 MOVIMIENTO EXTENDIDO
def overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.8

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

# ================= MOMENTUM =================

def strong_move(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] > np.mean(moves)

# ================= ENTRADA =================

def get_signal(df1, df5, df15):
    try:
        macro = macro_trend(df15)
        micro = trend(df5)

        # ❌ FILTROS CRÍTICOS
        if is_ranging(df5):
            return None

        if is_exhausted(df1):
            return None

        if late_entry(df1):
            return None

        if already_reacted(df1):
            return None

        if overextended(df1):
            return None

        if is_pullback(df5, df15):
            return None

        bos = break_of_structure(df5)

        if macro != micro or bos != micro:
            return None

        # ✅ ENTRADA LIMPIA
        if macro == "bullish" and strong_move(df1):
            return "call"

        if macro == "bearish" and strong_move(df1):
            return "put"

        return None

    except:
        return None


# ================= SCORE =================

def score_market(df1, df5, df15):
    score = 0

    if macro_trend(df15):
        score += 3

    if trend(df5):
        score += 2

    if not is_ranging(df5):
        score += 2

    if strong_move(df1):
        score += 2

    return score
