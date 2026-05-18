import numpy as np
import pandas as pd

# ================= INDICADORES =================
def indicators(df):
    df = df.copy()

    # ATR
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()

    df["tr"] = np.maximum(high_low, np.maximum(high_close, low_close))
    df["atr"] = df["tr"].rolling(14).mean()

    return df


# ================= DETECCIÓN LIQUIDEZ =================
def liquidity_levels(df):
    highs = df["high"].rolling(10).max()
    lows = df["low"].rolling(10).min()
    return highs, lows


# ================= DETECCIÓN SMC =================
def get_signal(df1, df5):
    try:
        df1 = indicators(df1)
        df5 = indicators(df5)

        last = df1.iloc[-1]
        prev = df1.iloc[-2]

        highs, lows = liquidity_levels(df1)

        last_high_liq = highs.iloc[-2]
        last_low_liq = lows.iloc[-2]

        # 🔥 filtro volatilidad
        if last["atr"] < df1["atr"].mean():
            return None

        # 🔥 fuerza vela
        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]

        if range_ == 0:
            return None

        strength = body / range_

        if strength < 0.6:
            return None

        # ================= LIQUIDITY SWEEP =================

        # 🔴 FAKE BREAK ARRIBA → PUT
        if (
            last["high"] > last_high_liq and
            last["close"] < last_high_liq and
            prev["close"] > prev["open"]
        ):
            return "put"

        # 🟢 FAKE BREAK ABAJO → CALL
        if (
            last["low"] < last_low_liq and
            last["close"] > last_low_liq and
            prev["close"] < prev["open"]
        ):
            return "call"

        return None

    except:
        return None


# ================= SCORE =================
def score_market(df1, df5):
    try:
        df1 = indicators(df1)
        atr = df1["atr"].iloc[-1]
        atr_avg = df1["atr"].mean()

        if atr_avg == 0:
            return 0

        return atr / atr_avg

    except:
        return 0
