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
# DETECCIÓN DE SOPORTES
# =========================================================

def detectar_soportes(datos, ventana=5):

    soportes = []

    for i in range(ventana, len(datos) - ventana):

        minimo = datos['low'].iloc[i-ventana:i+ventana+1].min()

        if abs(datos['low'].iloc[i] - minimo) / minimo <= 0.0018:

            soportes.append(round(minimo, 5))

    return sorted(list(set(soportes)))

# =========================================================
# DETECCIÓN DE RESISTENCIAS
# =========================================================

def detectar_resistencias(datos, ventana=5):

    resistencias = []

    for i in range(ventana, len(datos) - ventana):

        maximo = datos['high'].iloc[i-ventana:i+ventana+1].max()

        if abs(datos['high'].iloc[i] - maximo) / maximo <= 0.0018:

            resistencias.append(round(maximo, 5))

    return sorted(list(set(resistencias)))

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

    if len(df) < 35:
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

    avg_gain = gain.rolling(window=5, min_periods=1).mean()
    avg_loss = loss.rolling(window=5, min_periods=1).mean()

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
    # VELAS ACTUALES
    # =====================================================

    try:

        c1 = df.iloc[-1]
        c2 = df.iloc[-2]
        c3 = df.iloc[-3]

        cierre = float(c1["close"])
        apertura = float(c1["open"])

        high = float(c1["high"])
        low = float(c1["low"])

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
    # FUERZA VELA
    # =====================================================

    fuerza_vela_alcista = (
        bullish(c1)
        and body(c1) >= range_c(c1) * 0.55
    )

    fuerza_vela_bajista = (
        bearish(c1)
        and body(c1) >= range_c(c1) * 0.55
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
    # ESTRUCTURA
    # =====================================================

    estructura_alcista = (
        c1["low"] > c2["low"]
        and c1["high"] > c2["high"]
    )

    estructura_bajista = (
        c1["high"] < c2["high"]
        and c1["low"] < c2["low"]
    )

    # =====================================================
    # ACELERACIÓN
    # =====================================================

    aceleracion_alcista = (
        body(c1) > body(c2) * 1.10
    )

    aceleracion_bajista = (
        body(c1) > body(c2) * 1.10
    )

    # =====================================================
    # FILTRO ANTI-RANGO (MÁS FLEXIBLE)
    # =====================================================

    rango = abs(df["close"].iloc[-5] - cierre) / cierre

    if rango < 0.0007:
        return None

    # =====================================================
    # FILTRO DE TENDENCIA
    # =====================================================

    tendencia_alcista = (
        ema5 > ema8 > ema13
    )

    tendencia_bajista = (
        ema5 < ema8 < ema13
    )

    # =====================================================
    # DETECCIÓN CALL
    # =====================================================

    call_fuerza = 0

    if (
        macd >= signal_macd
        and fuerza_vela_alcista
        and momentum_alcista
    ):

        call_fuerza += 35

        if estructura_alcista:
            call_fuerza += 10

        if aceleracion_alcista:
            call_fuerza += 10

        if tendencia_alcista:
            call_fuerza += 15

        if cierre > ema21:
            call_fuerza += 10

        if volumen >= vol_media * 0.8:
            call_fuerza += 10

        if rsi < 35:
            call_fuerza += 10

        if en_soporte:
            call_fuerza += 8

        if cierre > c2["high"]:
            call_fuerza += 12

    # =====================================================
    # DETECCIÓN PUT
    # =====================================================

    put_fuerza = 0

    if (
        macd <= signal_macd
        and fuerza_vela_bajista
        and momentum_bajista
    ):

        put_fuerza += 35

        if estructura_bajista:
            put_fuerza += 10

        if aceleracion_bajista:
            put_fuerza += 10

        if tendencia_bajista:
            put_fuerza += 15

        if cierre < ema21:
            put_fuerza += 10

        if volumen >= vol_media * 0.8:
            put_fuerza += 10

        if rsi > 65:
            put_fuerza += 10

        if en_resistencia:
            put_fuerza += 8

        if cierre < c2["low"]:
            put_fuerza += 12

    # =====================================================
    # ENTRADA CALL
    # =====================================================

    if call_fuerza >= 70:

        return (
            "call",
            min(call_fuerza, 100),
            "CALL MOMENTUM + ESTRUCTURA"
        )

    # =====================================================
    # ENTRADA PUT
    # =====================================================

    if put_fuerza >= 70:

        return (
            "put",
            min(put_fuerza, 100),
            "PUT MOMENTUM + ESTRUCTURA"
        )

    # =====================================================
    # SIN ENTRADA
    # =====================================================

    return None
