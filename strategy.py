import numpy as np
import pandas as pd

def get_reversal_signal(df, tolerancia_nivel=0.0022, ventana_niveles=5):
    if len(df) < ventana_niveles + 3:
        return None

    df = df.copy()

    # Cálculo de medias móviles
    df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['ema13'] = df['close'].ewm(span=13, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    # Cálculo RSI
    delta = df['close'].diff()
    ganancia = delta.where(delta > 0, 0.0)
    perdida = -delta.where(delta < 0, 0.0)
    ganancia_media = ganancia.rolling(window=5, min_periods=1).mean()
    perdida_media = perdida.rolling(window=5, min_periods=1).mean().replace(0, 0.001)
    rs = ganancia_media / perdida_media
    df['rsi'] = 100.0 - (100.0 / (1.0 + rs))

    # Cálculo MACD
    df['macd'] = df['ema13'] - df['ema21']
    df['senal_macd'] = df['macd'].ewm(span=4, adjust=False).mean()

    # Detección de soportes y resistencias
    def detectar_niveles(datos, ventana):
        soportes = []
        resistencias = []
        total = len(datos)
        for i in range(ventana, total - ventana):
            minimo = datos['low'].iloc[i-ventana:i+ventana+1].min()
            maximo = datos['high'].iloc[i-ventana:i+ventana+1].max()
            if abs(datos['low'].iloc[i] - minimo) / minimo <= 0.0015:
                soportes.append(round(minimo, 5))
            if abs(datos['high'].iloc[i] - maximo) / maximo <= 0.0015:
                resistencias.append(round(maximo, 5))
        return sorted(list(set(soportes))), sorted(list(set(resistencias)))

    soportes, resistencias = detectar_niveles(df, ventana_niveles)

    # Extraer datos actuales
    try:
        cierre = float(df['close'].iloc[-1])
        apertura = float(df['open'].iloc[-1])
        ema8 = float(df['ema8'].iloc[-1])
        ema13 = float(df['ema13'].iloc[-1])
        ema21 = float(df['ema21'].iloc[-1])
        macd_val = float(df['macd'].iloc[-1])
        senal_macd_val = float(df['senal_macd'].iloc[-1])
        rsi_val = float(df['rsi'].iloc[-1])
        volumen = float(df['volume'].iloc[-1])
        vol_promedio = float(df['volume'].iloc[-4:-1].mean()) if len(df) >= 5 else max(volumen, 1.0)
    except Exception:
        return None

    # Verificar si está en zona
    en_soporte = any(abs(cierre - s) / s <= tolerancia_nivel for s in soportes)
    en_resistencia = any(abs(cierre - r) / r <= tolerancia_nivel for r in resistencias)

    if not en_soporte and not en_resistencia:
        return None

    senal = None
    fuerza = 0
    tipo_nivel = ""

    # Condición de compra
    if en_soporte:
        if macd_val >= senal_macd_val and 28 < rsi_val < 72 and cierre >= apertura * 0.998:
            senal = "call"
            tipo_nivel = "soporte"
            fuerza = 40
            if ema8 > ema13: fuerza += 5
            if ema13 > ema21: fuerza += 5
            if volumen >= vol_promedio * 0.3: fuerza += 5

    # Condición de venta
    if en_resistencia:
        if macd_val <= senal_macd_val and 28 < rsi_val < 72 and cierre <= apertura * 1.002:
            senal = "put"
            tipo_nivel = "resistencia"
            fuerza = 40
            if ema8 < ema13: fuerza += 5
            if ema13 < ema21: fuerza += 5
            if volumen >= vol_promedio * 0.3: fuerza += 5

    if senal is not None:
        fuerza = max(30, min(fuerza, 100))
        return (senal, fuerza, tipo_nivel)

    return None
