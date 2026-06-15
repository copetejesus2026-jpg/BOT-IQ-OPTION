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
# ESTRATEGIA PRINCIPAL
# =========================================================

def get_reversal_signal(
    df,
    tolerancia_nivel=0.0020,
    ventana_niveles=6,
    confirmar_tendencia=True
):

    if len(df) < 35:
        return None

    df = df.copy()

    # =====================================================
    # EMAS
    # =====================================================

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

    df['macd'] = df['ema13'] - df['ema21']
    df['signal_macd'] = df['macd'].ewm(span=4, adjust=False).mean()

    # =====================================================
    # SOPORTES
    # =====================================================

    def detectar_soportes(datos, ventana):

        soportes = []

        for i in range(ventana, len(datos) - ventana):

            minimo = datos['low'].iloc[i-ventana:i+ventana+1].min()

            if abs(datos['low'].iloc[i] - minimo) / minimo <= 0.0015:

                if all(datos['low'].iloc[-3:] >= minimo * 0.999):

                    soportes.append(round(minimo, 5))

        return sorted(list(set(soportes)))

    soportes = detectar_soportes(df, ventana_niveles)

    # =====================================================
    # DATOS ACTUALES
    # =====================================================

    try:

        c1 = df.iloc[-1]
        c2 = df.iloc[-2]
        c3 = df.iloc[-3]

        cierre = float(c1["close"])
        apertura = float(c1["open"])

        high = float(c1["high"])
        low = float(c1["low"])

        rsi = float(c1["rsi"])

        macd = float(c1["macd"])
        signal_macd = float(c1["signal_macd"])

        ema8 = float(c1["ema8"])
        ema13 = float(c1["ema13"])
        ema21 = float(c1["ema21"])

        volumen = float(c1["volume"])

        vol_prom = float(df["volume"].iloc[-6:-1].mean())

    except:
        return None

    # =====================================================
    # DETECCIÓN DE ESTRUCTURA
    # =====================================================

    higher_low = c1["low"] > c2["low"]
    higher_high = c1["high"] > c2["high"]

    estructura_alcista = higher_low and higher_high

    # =====================================================
    # SOPORTE
    # =====================================================

    en_soporte = any(
        abs(cierre - s) / s <= tolerancia_nivel
        for s in soportes
    )

    # =====================================================
    # MOMENTUM
    # =====================================================

    momentum_fuerte = (
        body(c1) > body(c2)
        and bullish(c1)
        and cierre > c2["close"]
    )

    # =====================================================
    # FUERZA DE VELA
    # =====================================================

    fuerza_vela = (
        body(c1) >= range_c(c1) * 0.60
    )

    # =====================================================
    # ACELERACIÓN
    # =====================================================

    aceleracion = (
        body(c1) > body(c2) * 1.2
    )

    # =====================================================
    # FILTRO ANTI RANGO
    # =====================================================

    rango_pequeno = (
        abs(df["close"].iloc[-5] - cierre) / cierre < 0.0015
    )

    if rango_pequeno:
        return None

    # =====================================================
    # FILTRO CONTRA TENDENCIA
    # =====================================================

    if confirmar_tendencia:

        if cierre < ema21:
            return None

        if ema8 < ema21:
            return None

    # =====================================================
    # DETECCIÓN REVERSIÓN + CONTINUACIÓN
    # =====================================================

    fuerza = 0
    tipo = ""
    senal = None

    if (
        rsi < 38
        and macd >= signal_macd
        and bullish(c1)
        and momentum_fuerte
        and fuerza_vela
        and aceleracion
        and estructura_alcista
    ):

        senal = "call"

        tipo = "MOMENTUM + ESTRUCTURA + ACELERACIÓN"

        fuerza = 50

        if en_soporte:
            fuerza += 10

        if rsi < 30:
            fuerza += 10

        if volumen >= vol_prom:
            fuerza += 10

        if ema8 > ema13 > ema21:
            fuerza += 15

        if cierre > c2["high"]:
            fuerza += 15

        if body(c1) > range_c(c1) * 0.75:
            fuerza += 10

    # =====================================================
    # VALIDACIÓN FINAL
    # =====================================================

    if senal and fuerza >= 80:

        return (
            senal,
            min(fuerza, 100),
            tipo
        )

    return None
