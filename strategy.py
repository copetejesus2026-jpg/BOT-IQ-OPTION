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

def is_strong_candle(c):
    return body(c) > (range_c(c) * 0.6)

def is_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.5

def mid_price(df):
    return (df["high"].max() + df["low"].min()) / 2

def in_discount(df):
    return df.iloc[-1]["close"] < mid_price(df)

def in_premium(df):
    return df.iloc[-1]["close"] > mid_price(df)

def is_ranging(df):
    highs = df["high"].rolling(10).max()
    lows = df["low"].rolling(10).min()
    return (highs.iloc[-1] - lows.iloc[-1]) < np.mean(df["high"] - df["low"]) * 5

# ================= ESTRUCTURA =================

def trend(df):
    highs = df["high"].rolling(5).max()
    lows = df["low"].rolling(5).min()

    if df["close"].iloc[-1] > highs.iloc[-2]:
        return "bullish"
    elif df["close"].iloc[-1] < lows.iloc[-2]:
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

# ================= CONFIRMACION =================

def confirmation(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    if bullish(c1) and is_strong_candle(c1) and bearish(c2):
        return "call"

    if bearish(c1) and is_strong_candle(c1) and bullish(c2):
        return "put"

    return None

# ================= SCORE =================

def score_market(df1, df5):
    try:
        score = 0

        if trend(df5):
            score += 2

        if not is_ranging(df5):
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

        if is_overextended(df1):
            return None

        if is_ranging(df5):
            return None

        t = trend(df5)
        conf = confirmation(df1)

        # 🔥 REVERSIÓN LIMPIA
        if liquidity_grab_up(df1) and in_premium(df1) and conf == "put":
            return "put"

        if liquidity_grab_down(df1) and in_discount(df1) and conf == "call":
            return "call"

        # 🔥 CONTINUIDAD REAL
        if t == "bullish" and in_discount(df1) and conf == "call":
            return "call"

        if t == "bearish" and in_premium(df1) and conf == "put":
            return "put"

        return None

    except:
        return None
