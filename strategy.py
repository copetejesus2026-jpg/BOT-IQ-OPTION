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

# ================= FILTROS =================

# 🔴 CONSOLIDACIÓN
def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 2

# 🔴 AGOTAMIENTO
def is_exhausted(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] < np.mean(moves) * 0.6

# 🔴 DEMASIADO TARDE (muchas velas seguidas)
def too_strong_move(df):
    closes = df["close"].values
    up = 0
    down = 0

    for i in range(-1, -6, -1):
        if closes[i] > closes[i-1]:
            up += 1
        if closes[i] < closes[i-1]:
            down += 1

    return up >= 4 or down >= 4

# 🔴 MOVIMIENTO EXTENDIDO
def overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.6

# 🔴 CERCA DE SOPORTE / RESISTENCIA
def near_key_level(df):
    last = df.iloc[-1]

    high_zone = df["high"].rolling(20).max().iloc[-1]
    low_zone = df["low"].rolling(20).min().iloc[-1]

    avg = np.mean(df["high"] - df["low"])

    near_resistance = abs(last["high"] - high_zone) < avg * 0.5
    near_support = abs(last["low"] - low_zone) < avg * 0.5

    return near_resistance or near_support

# 🔴 RECHAZO (vela peligrosa)
def rejection_candle(c):
    upper = c["high"] - max(c["open"], c["close"])
    lower = min(c["open"], c["close"]) - c["low"]

    return upper > body(c) or lower > body(c)

# ================= ESTRUCTURA =================

# 🔥 BREAK OF STRUCTURE (inicio real)
def break_of_structure(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-3] and highs[-2] <= highs[-3]:
        return "bullish"

    if lows[-1] < lows[-3] and lows[-2] >= lows[-3]:
        return "bearish"

    return None

# 🔥 RETROCESO (entrada inteligente)
def pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    return body(c1) < body(c2)

# 🔥 IMPULSO REAL
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

        # ❌ NO ir contra tendencia
        if macro != micro:
            return None

        # ❌ FILTROS CRÍTICOS
        if is_ranging(df5):
            return None

        if is_exhausted(df1):
            return None

        if too_strong_move(df5):
            return None

        if overextended(df1):
            return None

        if near_key_level(df5):
            return None

        if rejection_candle(df1.iloc[-1]):
            return None

        # 🔥 CONFIRMACIÓN DE INICIO REAL
        bos = break_of_structure(df5)

        if bos != macro:
            return None

        # 🔥 ESPERAR RETROCESO
        if not pullback(df1):
            return None

        # 🔥 IMPULSO REAL
        if not strong_impulse(df1):
            return None

        # 🎯 ENTRADA FINAL
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
