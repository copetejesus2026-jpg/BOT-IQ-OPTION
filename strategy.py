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

# ================= FILTROS =================

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.7

def mid_price(df):
    high = df["high"].max()
    low = df["low"].min()
    return (high + low) / 2

def in_discount(df):
    last = df.iloc[-1]
    return last["close"] < mid_price(df)

def in_premium(df):
    last = df.iloc[-1]
    return last["close"] > mid_price(df)

# ================= ESTRUCTURA =================

def bos(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["close"] > prev["high"]:
        return "bullish"
    if last["close"] < prev["low"]:
        return "bearish"
    return None

# ================= PULLBACK =================

def pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    if bullish(c1) and bearish(c2):
        return "call"

    if bearish(c1) and bullish(c2):
        return "put"

    return None

# ================= LIQUIDITY =================

def liquidity_grab_up(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last["high"] > prev["high"] and last["close"] < prev["high"]

def liquidity_grab_down(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last["low"] < prev["low"] and last["close"] > prev["low"]

# ================= SCORE =================

def score_market(df1, df5):
    try:
        score = 1

        if bos(df5):
            score += 1

        if not is_overextended(df1):
            score += 1

        return score
    except:
        return 0

# ================= SEÑAL =================

def get_signal(df1, df5):
    try:
        last = df1.iloc[-1]

        if range_c(last) == 0:
            return None

        # ❌ evitar entrar tarde
        if is_overextended(df1):
            return None

        structure = bos(df5)

        # 🔥 REVERSIÓN (MEJORADA)
        if liquidity_grab_up(df1) and in_premium(df1):
            return "put"

        if liquidity_grab_down(df1) and in_discount(df1):
            return "call"

        # 🔥 CONTINUIDAD CON RETROCESO
        pb = pullback(df1)

        if structure == "bullish" and pb == "call" and in_discount(df1):
            return "call"

        if structure == "bearish" and pb == "put" and in_premium(df1):
            return "put"

        return None

    except:
        return None
