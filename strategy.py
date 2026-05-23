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

# ================= TENDENCIAS =================

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
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 3

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.8

# ❗ Movimiento demasiado extendido (evita entrar tarde)
def is_extended_move(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] > np.mean(moves) * 1.5

# ❗ Detecta si ya hubo demasiadas velas en la misma dirección
def late_entry(df):
    last3 = df.iloc[-3:]

    bullish_count = sum(1 for _, c in last3.iterrows() if c["close"] > c["open"])
    bearish_count = sum(1 for _, c in last3.iterrows() if c["close"] < c["open"])

    return bullish_count >= 3 or bearish_count >= 3

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

    if not is_overextended(df1):
        score += 1

    return score

# ================= ENTRADA PRO =================

def get_signal(df1, df5, df15):
    try:
        # ❌ mercado lateral
        if is_ranging(df5):
            return None

        # ❌ vela exagerada
        if is_overextended(df1):
            return None

        # ❌ entrada tarde
        if late_entry(df1):
            return None

        # ❌ movimiento ya extendido
        if is_extended_move(df1):
            return None

        macro = macro_trend(df15)
        micro = trend(df5)

        # ❌ si no están alineadas → NO OPERAR
        if macro != micro:
            return None

        # ================= COMPRAS =================
        if macro == "bullish":

            if valid_pullback(df1):
                last = df1.iloc[-1]

                if strong_bull(last):
                    return "call"

        # ================= VENTAS =================
        if macro == "bearish":

            if valid_pullback(df1):
                last = df1.iloc[-1]

                if strong_bear(last):
                    return "put"

        return None

    except:
        return None
