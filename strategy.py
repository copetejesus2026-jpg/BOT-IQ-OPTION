import numpy as np

# ================= BASICOS =================

def range_c(c):
    return c["high"] - c["low"]

# ================= TENDENCIA M5 =================

def trend_m5(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] > highs[-3] and lows[-1] > lows[-2] > lows[-3]:
        return "bullish"

    if highs[-1] < highs[-2] < highs[-3] and lows[-1] < lows[-2] < lows[-3]:
        return "bearish"

    return None

# ================= IMPULSO =================

def strong_impulse(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 1.5

# ================= SOBREEXTENSION =================

def overextended(df):
    last = df.iloc[-1]
    avg = np.mean(df["high"] - df["low"])
    return range_c(last) > avg * 2

# ================= LIQUIDITY (STOP HUNT) =================

def liquidity_sweep_high(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last["high"] > prev["high"] and last["close"] < prev["high"]

def liquidity_sweep_low(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last["low"] < prev["low"] and last["close"] > prev["low"]

# ================= PULLBACK =================

def valid_pullback(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]

    return (
        (c2["close"] < c3["close"] and c1["close"] > c2["close"]) or
        (c2["close"] > c3["close"] and c1["close"] < c2["close"])
    )

# ================= CONFIRMACION =================

def confirmation_candle(df):
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    # vela confirma dirección
    return (
        (c1["close"] > c1["open"] and c2["close"] < c2["open"]) or
        (c1["close"] < c1["open"] and c2["close"] > c2["open"])
    )

# ================= LATERAL =================

def is_lateral(df):
    highs = df["high"].values
    lows = df["low"].values
    return abs(highs[-1] - highs[-5]) < 0.0003

# ================= SEÑAL FINAL =================

def get_signal(df1, df5):
    try:
        trend = trend_m5(df5)

        if trend is None:
            return None

        if is_lateral(df1):
            return None

        if overextended(df1):
            return None

        if not strong_impulse(df1):
            return None

        if not valid_pullback(df1):
            return None

        if not confirmation_candle(df1):
            return None

        # 🔥 LIQUIDEZ + CONTINUIDAD

        if trend == "bullish" and liquidity_sweep_low(df1):
            return "call"

        if trend == "bearish" and liquidity_sweep_high(df1):
            return "put"

        return None

    except:
        return None
