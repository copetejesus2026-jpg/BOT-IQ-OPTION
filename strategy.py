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
# DETECCIÓN DE COMPRESIÓN
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

    # =====================================================
    # VALIDACIÓN
    # =====================================================

    if len(df) < 40:
        return None

    df = df.copy()

    # =====================================================
    # EMAS
    # =====================================================

    df['ema5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['ema13'] = df['close'].ewm(span=13, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    # =====================================================
    # RSI
    # =====================================================

    delta = df['close'].diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=5).mean()
    avg_loss = loss.rolling(window=5).mean()

    avg_loss = avg_loss.replace(0, 0.001)

    rs = avg_gain / avg_loss

    df['rsi'] = 100 - (100 / (1 + rs))

    # =====================================================
    # MACD
    # =====================================================

    df['macd'] = df['ema8'] - df['ema21']
    df['signal_macd'] = df['macd'].ewm(span=4, adjust=False).mean()

    # =====================================================
    # VOLUMEN
    # =====================================================

    df['vol_media'] = df['volume'].rolling(5).mean()

    # =====================================================
    # SOPORTES Y RESISTENCIAS
    # =====================================================

    soportes = detectar_soportes(df, ventana_niveles)
    resistencias = detectar_resistencias(df, ventana_niveles)

    # =====================================================
    # VELAS
    # =====================================================

    try:

        c1 = df.iloc[-1]
        c2 = df.iloc[-2]
        c3 = df.iloc[-3]
        c4 = df.iloc[-4]

        cierre = float(c1["close"])

        ema5 = float(c1["ema5"])
        ema8 = float(c1["ema8"])
        ema13 = float(c1["ema13"])
        ema21 = float(c1["ema21"])

        rsi = float(c1["rsi"])

        macd = float(c1["macd"])
        signal_macd = float(c1["signal_macd"])

        volumen = float(c1["volume"])
        vol_media = float(c1["vol_media"])

    except:
        return None

    # =====================================================
    # SOPORTE / RESISTENCIA
    # =====================================================

    en_soporte = any(
        abs(cierre - s) / s <= tolerancia_nivel
        for s in soportes
    )

    en_resistencia = any(
        abs(cierre - r) / r <= tolerancia_nivel
        for r in resistencias
    )

    # =====================================================
    # FUERZA DE VELA
    # =====================================================

    fuerza_alcista = (
        bullish(c1)
        and body(c1) >= range_c(c1) * 0.55
    )

    fuerza_bajista = (
        bearish(c1)
        and body(c1) >= range_c(c1) * 0.55
    )

    # =====================================================
    # VELA EXPLOSIVA
    # =====================================================

    vela_explosiva_alcista = (
        bullish(c1)
        and body(c1) > body(c2) * 1.5
    )

    vela_explosiva_bajista = (
        bearish(c1)
        and body(c1) > body(c2) * 1.5
    )

    # =====================================================
    # MOMENTUM
    # =====================================================

    momentum_alcista = (
        bullish(c1)
        and c1["close"] > c2["close"]
        and body(c1) >= body(c2) * 0.9
    )

    momentum_bajista = (
        bearish(c1)
        and c1["close"] < c2["close"]
        and body(c1) >= body(c2) * 0.9
    )

    # =====================================================
    # RETROCESO DÉBIL
    # =====================================================

    retroceso_debil_alcista = (
        bearish(c2)
        and body(c2) < body(c3) * 0.7
    )

    retroceso_debil_bajista = (
        bullish(c2)
        and body(c2) < body(c3) * 0.7
    )

    # =====================================================
    # ABSORCIÓN
    # =====================================================

    absorcion_alcista = (
        c2["low"] < c3["low"]
        and c2["close"] > c2["open"]
    )

    absorcion_bajista = (
        c2["high"] > c3["high"]
        and c2["close"] < c2["open"]
    )

    # =====================================================
    # ESTRUCTURA
    # =====================================================

    estructura_alcista = (
        c1["high"] > c2["high"]
        and c1["low"] > c2["low"]
    )

    estructura_bajista = (
        c1["high"] < c2["high"]
        and c1["low"] < c2["low"]
    )

    # =====================================================
    # TENDENCIA
    # =====================================================

    tendencia_alcista = (
        ema5 > ema8 > ema13
    )

    tendencia_bajista = (
        ema5 < ema8 < ema13
    )

    # =====================================================
    # COMPRESIÓN
    # =====================================================

    compresion = detectar_compresion(df)

    # =====================================================
    # FILTRO ANTI RANGO
    # =====================================================

    rango = abs(df["close"].iloc[-6] - cierre) / cierre

    if rango < 0.0006:
        return None

    # =====================================================
    # DETECCIÓN CALL
    # =====================================================

    call_score = 0

    if (
        macd >= signal_macd - 0.00002
        and momentum_alcista
        and fuerza_alcista
    ):

        call_score += 30

        if estructura_alcista:
            call_score += 10

        if tendencia_alcista:
            call_score += 15

        if cierre > ema21:
            call_score += 10

        if volumen >= vol_media * 0.8:
            call_score += 10

        if vela_explosiva_alcista:
            call_score += 15

        if retroceso_debil_alcista:
            call_score += 10

        if absorcion_alcista:
            call_score += 10

        if compresion:
            call_score += 10

        if en_soporte:
            call_score += 5

        if rsi < 40:
            call_score += 5

        if cierre > c2["high"]:
            call_score += 10

    # =====================================================
    # DETECCIÓN PUT
    # =====================================================

    put_score = 0

    if (
        macd <= signal_macd + 0.00002
        and momentum_bajista
        and fuerza_bajista
    ):

        put_score += 30

        if estructura_bajista:
            put_score += 10

        if tendencia_bajista:
            put_score += 15

        if cierre < ema21:
            put_score += 10

        if volumen >= vol_media * 0.8:
            put_score += 10

        if vela_explosiva_bajista:
            put_score += 15

        if retroceso_debil_bajista:
            put_score += 10

        if absorcion_bajista:
            put_score += 10

        if compresion:
            put_score += 10

        if en_resistencia:
            put_score += 5

        if rsi > 60:
            put_score += 5

        if cierre < c2["low"]:
            put_score += 10

    # =====================================================
    # ENTRADA CALL
    # =====================================================

    if call_score >= 65:

        return (
            "call",
            min(call_score, 100),
            "CALL IMPULSO + CONTINUIDAD"
        )

    # =====================================================
    # ENTRADA PUT
    # =====================================================

    if put_score >= 65:

        return (
            "put",
            min(put_score, 100),
            "PUT IMPULSO + CONTINUIDAD"
        )

    # =====================================================
    # SIN ENTRADA
    # =====================================================

    return None
