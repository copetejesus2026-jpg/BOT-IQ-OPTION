import numpy as np

def body(c):
    return abs(c["close"] - c["open"])

def range_c(c):
    return c["high"] - c["low"]

def bullish(c):
    return c["close"] > c["open"]

def bearish(c):
    return c["close"] < c["open"]

def trend(df):
    highs = df["high"].values
    lows = df["low"].values

    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"

    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"

    return None

def is_ranging(df):
    return (df["high"].max() - df["low"].min()) < np.mean(df["high"] - df["low"]) * 2

def is_exhausted(df):
    moves = np.abs(df["close"] - df["open"])
    return moves.iloc[-1] < np.mean(moves) * 0.5

def strong_support_resistance(df):
    highs = df["high"].values
    lows = df["low"].values

    tol = np.mean(df["high"] - df["low"]) * 0.3

    touches_high = sum(abs(h - max(highs[-10:])) < tol for h in highs[-10:])
    touches_low = sum(abs(l - min(lows[-10:])) < tol for l in lows[-10:])

    return touches_high >= 3 or touches_low >= 3

def liquidity_sweep(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["high"] > prev["high"] and last["close"] < prev["high"]:
        return "bearish"

    if last["low"] < prev["low"] and last["close"] > prev["low"]:
        return "bullish"

    return None

def rejection(df):
    c = df.iloc[-1]
    upper = c["high"] - max(c["open"], c["close"])
    lower = min(c["open"], c["close"]) - c["low"]
    b = body(c)

    if upper > b * 1.5:
        return "bearish"

    if lower > b * 1.5:
        return "bullish"

    return None

def engulfing(df):
    c1 = df.iloc[-2]
    c2 = df.iloc[-1]

    if bearish(c1) and bullish(c2):
        if c2["close"] > c1["open"] and c2["open"] < c1["close"]:
            return "bullish"

    if bullish(c1) and bearish(c2):
        if c2["close"] < c1["open"] and c2["open"] > c1["close"]:
            return "bearish"

    return None

def pullback(df5):
    c1 = df5.iloc[-1]
    c2 = df5.iloc[-2]
    return body(c1) < body(c2)

def get_signal(df1, df5, df30):
    try:
        macro = trend(df30)
        micro = trend(df5)

        if not macro or not micro:
            return None

        if macro != micro:
            return None

        if is_ranging(df5):
            return None

        if is_exhausted(df1):
            return None

        if strong_support_resistance(df5):
            return None

        if not pullback(df5):
            return None

        sweep = liquidity_sweep(df1)
        rej = rejection(df1)
        eng = engulfing(df1)

        if not sweep:
            return None

        if macro == "bullish":
            if sweep == "bullish" and (rej == "bullish" or eng == "bullish"):
                return "call"

        if macro == "bearish":
            if sweep == "bearish" and (rej == "bearish" or eng == "bearish"):
                return "put"

        return None

    except:
        return None

def score_market(df1, df5, df30):
    score = 0

    if trend(df30):
        score += 3

    if trend(df5):
        score += 2

    if not is_ranging(df5):
        score += 2

    if not is_exhausted(df1):
        score += 2

    return score
