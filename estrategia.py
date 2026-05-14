import numpy as np

# ================= INDICADORES =================

def add_indicators(df):

    # EMA tendencia
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    # ATR volatilidad
    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift()),
            abs(df["low"] - df["close"].shift())
        )
    )

    df["atr"] = df["tr"].rolling(14).mean()

    return df

# ================= SOPORTE / RESISTENCIA =================

def near_sr(df):

    last = df.iloc[-1]

    atr = last["atr"]

    # máximos / mínimos históricos
    high_zone = df["high"].rolling(50).max().iloc[-2]
    low_zone = df["low"].rolling(50).min().iloc[-2]

    # cerca resistencia
    if abs(last["close"] - high_zone) < atr * 0.8:
        return True

    # cerca soporte
    if abs(last["close"] - low_zone) < atr * 0.8:
        return True

    return False

# ================= AGOTAMIENTO =================

def exhaustion(df):

    last = df.iloc[-1]

    move = abs(
        df["close"].iloc[-1] -
        df["close"].iloc[-6]
    )

    # movimiento demasiado extendido
    if move > last["atr"] * 2.5:
        return True

    return False

# ================= RECHAZO =================

def rejection(df, direction):

    last = df.iloc[-1]

    body = abs(last["close"] - last["open"])

    upper_wick = (
        last["high"] -
        max(last["close"], last["open"])
    )

    lower_wick = (
        min(last["close"], last["open"]) -
        last["low"]
    )

    # rechazo arriba
    if direction == "call":

        if upper_wick > body * 1.5:
            return True

    # rechazo abajo
    if direction == "put":

        if lower_wick > body * 1.5:
            return True

    return False

# ================= LATERAL =================

def lateral_market(df):

    ema20 = df["ema20"].iloc[-1]
    ema50 = df["ema50"].iloc[-1]

    distance = abs(ema20 - ema50)

    # mercado lateral
    if distance < 0.00003:
        return True

    return False

# ================= FUERZA =================

def strong_candle(candle):

    body = abs(candle["close"] - candle["open"])

    range_ = candle["high"] - candle["low"]

    if range_ == 0:
        return False

    return (body / range_) > 0.7

# ================= CONTINUIDAD =================

def continuation(df, direction):

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # CALL
    if direction == "call":

        if (

            prev["close"] < prev["open"] and
            last["close"] > last["open"] and

            last["close"] > prev["high"] and

            strong_candle(last)

        ):

            return True

    # PUT
    if direction == "put":

        if (

            prev["close"] > prev["open"] and
            last["close"] < last["open"] and

            last["close"] < prev["low"] and

            strong_candle(last)

        ):

            return True

    return False

# ================= TENDENCIA =================

def trend(df):

    ema20 = df["ema20"].iloc[-1]
    ema50 = df["ema50"].iloc[-1]

    # CALL
    if ema20 > ema50:
        return "call"

    # PUT
    if ema20 < ema50:
        return "put"

    return None

# ================= SEÑAL PRINCIPAL =================

def pro_signal(df_m1, df_m5):

    # datos insuficientes
    if len(df_m1) < 60 or len(df_m5) < 60:
        return None

    # lateral
    if lateral_market(df_m5):
        return None

    direction = trend(df_m5)

    if direction is None:
        return None

    # evitar soporte / resistencia
    if near_sr(df_m1):
        return None

    # evitar agotamiento
    if exhaustion(df_m1):
        return None

    # continuidad
    if not continuation(df_m1, direction):
        return None

    # rechazo
    if rejection(df_m1, direction):
        return None

    return direction
