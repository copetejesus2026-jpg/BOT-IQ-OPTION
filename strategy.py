import numpy as np

def indicators(df):
    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # ATR
    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift()),
            abs(df["low"] - df["close"].shift())
        )
    )
    df["atr"] = df["tr"].rolling(14).mean()

    return df

def score_market(df1, df5):
    try:
        df1 = indicators(df1)
        atr = df1["atr"].iloc[-1]
        atr_avg = df1["atr"].mean()
        return atr / atr_avg
    except:
        return 0

def get_signal(df1, df5):
    try:
        df1 = indicators(df1)
        df5 = indicators(df5)

        last = df1.iloc[-1]
        prev = df1.iloc[-2]

        if last["atr"] < df1["atr"].mean():
            return None

        # Dirección M5
        trend_up = df5["close"].iloc[-1] > df5["close"].iloc[-3]
        trend_down = df5["close"].iloc[-1] < df5["close"].iloc[-3]

        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]

        if range_ == 0:
            return None

        strength = body / range_

        if strength < 0.55:
            return None

        # CALL
        if last["close"] > prev["high"] and trend_up and last["rsi"] < 65:
            return "call"

        # PUT
        if last["close"] < prev["low"] and trend_down and last["rsi"] > 35:
            return "put"

        return None

    except:
        return None
