import numpy as np

# ================= BASICOS =================

def bullish(c):
    return c["close"] > c["open"]

def bearish(c):
    return c["close"] < c["open"]

def body(c):
    return abs(c["close"] - c["open"])

def range_c(c):
    return c["high"] - c["low"]

# ================= ESTRUCTURA =================

def bos(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["close"] > prev["high"]:
        return "bullish"

    if last["close"] < prev["low"]:
        return "bearish"

    return None

# ================= FILTROS =================

def not_overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) < avg * 1.5

def valid_pullback(df, direction):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    # pullback en tendencia alcista
    if direction == "bullish":
        return bearish(c2) and bullish(c1)

    # pullback en tendencia bajista
    if direction == "bearish":
        return bullish(c2) and bearish(c1)

    return False

def strong_close(df, direction):
    last = df.iloc[-1]

    strength = body(last) / range_c(last) if range_c(last) != 0 else 0

    if direction == "bullish":
        return bullish(last) and strength > 0.5

    if direction == "bearish":
        return bearish(last) and strength > 0.5

    return False

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
        df = df5  # trabajamos solo M5

        last = df.iloc[-1]

        if range_c(last) == 0:
            return None

        if not not_overextended(df):
            return None

        structure = bos(df)

        # ================= CONTINUACIÓN =================

        # 📈 CALL
        if structure == "bullish":
            if valid_pullback(df, "bullish") and strong_close(df, "bullish"):
                return "call"

        # 📉 PUT
        if structure == "bearish":
            if valid_pullback(df, "bearish") and strong_close(df, "bearish"):
                return "put"

        return None

    except:
        return None
