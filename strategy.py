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

# ================= ESTRUCTURA =================

def bos(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["close"] > prev["high"]:
        return "bullish"

    if last["close"] < prev["low"]:
        return "bearish"

    return None

# ================= LIQUIDEZ =================

def liquidity_grab_up(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    return last["high"] > prev["high"] and last["close"] < prev["high"]

def liquidity_grab_down(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    return last["low"] < prev["low"] and last["close"] > prev["low"]

# ================= RETROCESO =================

def pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    if bullish(c1) and bearish(c2):
        return "call"

    if bearish(c1) and bullish(c2):
        return "put"

    return None

# ================= FILTRO =================

def not_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])

    return range_c(last) < avg * 1.8

# ================= SCORE =================

def score_market(df1, df5):
    try:
        if bos(df5):
            return 2
        return 1
    except:
        return 0

# ================= SEÑAL =================

def get_signal(df1, df5):
    try:
        last = df5.iloc[-1]

        if range_c(last) == 0:
            return None

        if not not_overextended(df5):
            return None

        structure = bos(df5)

        # 🔥 REVERSIÓN
        if liquidity_grab_up(df5):
            return "put"

        if liquidity_grab_down(df5):
            return "call"

        # 🔥 CONTINUIDAD CON RETROCESO
        pb = pullback(df5)

        if structure == "bullish" and pb == "call":
            return "call"

        if structure == "bearish" and pb == "put":
            return "put"

        return None

    except:
        return None
