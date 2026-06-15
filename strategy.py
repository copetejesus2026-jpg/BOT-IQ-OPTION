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

    promedio_rango = ultimas.apply(
        lambda x: range_c(x),
        axis=1
    ).mean()

    rango_actual = range_c(df.iloc[-1])

    return rango_actual < promedio_rango * 0.8

# =========================================================
# ESTRATEGIA PRINCIPAL
# =========================================================

def get_reversal_signal(
    df,
    tolerancia_nivel=0.0025,
    ventana_niveles=5,
    confirmar_tendencia=True
):

    # VALIDACIÓN
    if len(df) < 40:
        return None

    df = df.copy()

    # ================= EMAS =================
    df['ema5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['ema13'] = df['close'].ewm(span=13, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    # ================= RSI =================
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=5).mean()
    avg_loss = loss.rolling(window=5).mean()
    avg_loss = avg_loss.replace(0, 0.001)

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ================= MACD =================
    df['macd'] = df['ema8'] - df['ema21']
    df['signal_macd'] = df['macd'].ewm(span=4, adjust=False).mean()

    # ================= VOLUMEN =================
    df['vol_media'] = df['volume'].rolling(5).mean()

    # ================= NIVELES =================
    soportes = detectar_soportes(df, ventana_niveles)
    resistencias = detectar_resistencias(df, ventana_niveles)

    # ================= DATOS RECIENTES =================
    try:
        c1 = df.iloc[-1]
        c2 = df.iloc[-2]
        c3 = df.iloc[-3]

        cierre = float(c1["close"])
        ema21 = float(c1["ema21"])
        rsi = float(c1["rsi"])
        macd = float(c1["macd"])
        signal_macd = float(c1["signal_macd"])
        volumen = float(c1["volume"])
        vol_media = float(c1["vol_media"])
    except:
        return None

    # ================= CONDICIONES =================

    fuerza_alcista = bullish(c1) and body(c1) >= range_c(c1) * 0.55
    fuerza_bajista = bearish(c1) and body(c1) >= range_c(c1) * 0.55

    momentum_alcista = bullish(c1) and c1["close"] > c2["close"]
    momentum_bajista = bearish(c1) and c1["close"] < c2["close"]

    tendencia_alcista = df['ema5'].iloc[-1] > df['ema8'].iloc[-1]
    tendencia_bajista = df['ema5'].iloc[-1] < df['ema8'].iloc[-1]

    compresion = detectar_compresion(df)

    # FILTRO RANGO
    rango = abs(df["close"].iloc[-6] - cierre) / cierre
    if rango < 0.0006:
        return None

    # ================= SCORES =================

    call_score = 0
    put_score = 0

    # CALL ORIGINAL
    if macd >= signal_macd and momentum_alcista and fuerza_alcista:
        call_score += 30
        if tendencia_alcista:
            call_score += 15
        if cierre > ema21:
            call_score += 10
        if volumen >= vol_media * 0.8:
            call_score += 10
        if compresion:
            call_score += 10
        if rsi < 40:
            call_score += 5

    # PUT ORIGINAL
    if macd <= signal_macd and momentum_bajista and fuerza_bajista:
        put_score += 30
        if tendencia_bajista:
            put_score += 15
        if cierre < ema21:
            put_score += 10
        if volumen >= vol_media * 0.8:
            put_score += 10
        if compresion:
            put_score += 10
        if rsi > 60:
            put_score += 5

    # ================= INVERSIÓN FINAL =================

    if call_score >= 65:
        return (
            "put",
            min(call_score, 100),
            "PUT (invertido)"
        )

    if put_score >= 65:
        return (
            "call",
            min(put_score, 100),
            "CALL (invertido)"
        )

    return None
