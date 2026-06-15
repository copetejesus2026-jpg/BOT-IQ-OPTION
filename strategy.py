import numpy as np
import pandas as pd

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def body(c):
    return abs(c["close"] - c["open"])

def range_c(c):
    return c["high"] - c["low"]

def bullish(c):
    return c["close"] > c["open"]

def bearish(c):
    return c["close"] < c["open"]

# =========================================================
# SOPORTES
# =========================================================

def detectar_soportes(datos, ventana=5):
    soportes = []

    for i in range(ventana, len(datos) - ventana):
        minimo = datos['low'].iloc[i-ventana:i+ventana+1].min()

        if abs(datos['low'].iloc[i] - minimo) / minimo <= 0.0018:
            soportes.append(round(minimo, 5))

    return sorted(list(set(soportes)))

# =========================================================
# RESISTENCIAS
# =========================================================

def detectar_resistencias(datos, ventana=5):
    resistencias = []

    for i in range(ventana, len(datos) - ventana):
        maximo = datos['high'].iloc[i-ventana:i+ventana+1].max()

        if abs(datos['high'].iloc[i] - maximo) / maximo <= 0.0018:
            resistencias.append(round(maximo, 5))

    return sorted(list(set(resistencias)))

# =========================================================
# COMPRESIÓN
# =========================================================

def detectar_compresion(df):
    ultimas = df.iloc[-5:]

    promedio_rango = ultimas.apply(lambda x: range_c(x), axis=1).mean()
    rango_actual = range_c(df.iloc[-1])

    return rango_actual < promedio_rango * 0.8

# =========================================================
# ESTRATEGIA PRINCIPAL
# =========================================================

def get_reversal_signal(df):

    if len(df) < 40:
        return None

    df = df.copy()

    # EMAS
    df['ema5'] = df['close'].ewm(span=5).mean()
    df['ema8'] = df['close'].ewm(span=8).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(5).mean()
    avg_loss = loss.rolling(5).mean().replace(0, 0.001)

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    df['macd'] = df['ema8'] - df['ema21']
    df['signal'] = df['macd'].ewm(span=4).mean()

    # VOLUMEN
    df['vol_media'] = df['volume'].rolling(5).mean()

    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    cierre = c1["close"]

    # CONDICIONES
    alcista = bullish(c1)
    bajista = bearish(c1)

    momentum_alcista = alcista and c1["close"] > c2["close"]
    momentum_bajista = bajista and c1["close"] < c2["close"]

    fuerza_alcista = alcista and body(c1) > range_c(c1) * 0.5
    fuerza_bajista = bajista and body(c1) > range_c(c1) * 0.5

    # SCORES
    call_score = 0
    put_score = 0

    if c1["macd"] >= c1["signal"] and momentum_alcista and fuerza_alcista:
        call_score += 60

    if c1["macd"] <= c1["signal"] and momentum_bajista and fuerza_bajista:
        put_score += 60

    # 🔥 INVERSIÓN FINAL
    if call_score >= 60:
        return ("put", call_score, "Invertido")

    if put_score >= 60:
        return ("call", put_score, "Invertido")

    return None
