import numpy as np
import pandas as pd

# =========================
# FUNCIONES BÁSICAS
# =========================

def body(c):
    return abs(c["close"] - c["open"])

def range_c(c):
    return c["high"] - c["low"]

def bullish(c):
    return c["close"] > c["open"]

def bearish(c):
    return c["close"] < c["open"]

# =========================
# SOPORTE / RESISTENCIA
# =========================

def detectar_soportes(df, ventana=5):
    niveles = []
    for i in range(ventana, len(df)-ventana):
        minimo = df['low'].iloc[i-ventana:i+ventana+1].min()
        if abs(df['low'].iloc[i] - minimo) / minimo <= 0.002:
            niveles.append(minimo)
    return niveles

def detectar_resistencias(df, ventana=5):
    niveles = []
    for i in range(ventana, len(df)-ventana):
        maximo = df['high'].iloc[i-ventana:i+ventana+1].max()
        if abs(df['high'].iloc[i] - maximo) / maximo <= 0.002:
            niveles.append(maximo)
    return niveles

# =========================
# ESTRATEGIA INTELIGENTE
# =========================

def get_reversal_signal(df):

    if len(df) < 40:
        return None

    df = df.copy()

    # EMAs
    df['ema5'] = df['close'].ewm(span=5).mean()
    df['ema13'] = df['close'].ewm(span=13).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    rs = gain.rolling(5).mean() / (loss.rolling(5).mean() + 0.0001)
    df['rsi'] = 100 - (100 / (1 + rs))

    # Última vela
    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    cierre = c1["close"]
    rsi = c1["rsi"]

    # Tendencia
    tendencia_alcista = c1["ema5"] > c1["ema13"] > c1["ema21"]
    tendencia_bajista = c1["ema5"] < c1["ema13"] < c1["ema21"]

    # Fuerza vela (modo sniper)
    fuerza = body(c1) / range_c(c1)

    if fuerza < 0.98:
        return None

    # Soportes / Resistencias
    soportes = detectar_soportes(df)
    resistencias = detectar_resistencias(df)

    en_soporte = any(abs(cierre - s)/s < 0.002 for s in soportes)
    en_resistencia = any(abs(cierre - r)/r < 0.002 for r in resistencias)

    # =========================
    # DECISIÓN AUTOMÁTICA
    # =========================

    # 🔄 MODO INVERTIDO (REVERSIÓN)
    if en_resistencia and rsi > 65 and bullish(c1):
        return ("put", 100, "REVERSIÓN AUTOMÁTICA")

    if en_soporte and rsi < 35 and bearish(c1):
        return ("call", 100, "REVERSIÓN AUTOMÁTICA")

    # ✅ MODO NORMAL (TENDENCIA)
    if tendencia_alcista and bullish(c1) and not en_resistencia:
        return ("call", 98, "TENDENCIA LIMPIA")

    if tendencia_bajista and bearish(c1) and not en_soporte:
        return ("put", 98, "TENDENCIA LIMPIA")

    return None
