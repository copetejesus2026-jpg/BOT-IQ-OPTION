import numpy as np

# ================= UTILIDADES =================

def body(c):
    return abs(c["close"] - c["open"])

def range_c(c):
    return c["high"] - c["low"]

def bullish(c):
    return c["close"] > c["open"]

def bearish(c):
    return c["close"] < c["open"]

def upper_wick(c):
    return c["high"] - max(c["open"], c["close"])

def lower_wick(c):
    return min(c["open"], c["close"]) - c["low"]


# ================= FILTRO MERCADO =================

def is_compression(df):
    ranges = (df["high"] - df["low"]).values[-10:]
    avg = np.mean(ranges)
    return avg < np.max(ranges) * 0.3


# ================= LIQUIDEZ =================

def equal_highs(df, tol=0.00015):
    highs = df["high"].values[-6:]
    return max(highs) - min(highs) < tol

def equal_lows(df, tol=0.00015):
    lows = df["low"].values[-6:]
    return max(lows) - min(lows) < tol


# ================= BOS =================

def bos(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["close"] > prev["high"]:
        return "bullish"

    if last["close"] < prev["low"]:
        return "bearish"

    return None


# ================= LIQUIDITY GRAB =================

def grab_up(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    return (
        last["high"] > prev["high"] and
        last["close"] < prev["high"] and
        upper_wick(last) > body(last) * 1.2
    )

def grab_down(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    return (
        last["low"] < prev["low"] and
        last["close"] > prev["low"] and
        lower_wick(last) > body(last) * 1.2
    )


# ================= ORDER BLOCK =================

def bull_ob(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    return (
        bearish(prev) and
        bullish(last) and
        last["close"] > prev["high"]
    )

def bear_ob(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    return (
        bullish(prev) and
        bearish(last) and
        last["close"] < prev["low"]
    )


# ================= CONFIRMACIÓN =================

def confirmation(df, direction):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    if direction == "call":
        return bullish(c1) and bullish(c2)

    if direction == "put":
        return bearish(c1) and bearish(c2)

    return False


# ================= SCORE =================

def score_market(df1, df5):
    try:
        score = 1

        if equal_highs(df5) or equal_lows(df5):
            score += 1

        if bos(df5):
            score += 1

        if not is_compression(df1):
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

        if is_compression(df1):
            return None

        strength = body(last) / range_c(last)
        if strength < 0.55:
            return None

        # ================= SETUPS =================

        # LIQUIDITY GRAB + CONFIRMACIÓN
        if grab_up(df1) and confirmation(df1, "put"):
            return "put"

        if grab_down(df1) and confirmation(df1, "call"):
            return "call"

        # ORDER BLOCK + CONFIRMACIÓN
        if bull_ob(df1) and confirmation(df1, "call"):
            return "call"

        if bear_ob(df1) and confirmation(df1, "put"):
            return "put"

        # BOS + FUERZA
        structure = bos(df1)

        if structure == "bullish" and confirmation(df1, "call"):
            return "call"

        if structure == "bearish" and confirmation(df1, "put"):
            return "put"

        return None

    except:
        return None
