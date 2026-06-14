import numpy as np
import pandas as pd

def get_reversal_signal(df, tolerancia_nivel=0.0022, ventana_niveles=5):
    if len(df) < ventana_niveles + 6:
        return None

    df = df.copy()

    # Medias móviles
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

    # MACD
    df['macd'] = df['ema13'] - df['ema21']
    df['senal_macd'] = df['macd'].ewm(span=4, adjust=False).mean()

    # Detección de soportes
    def detectar_soportes(datos, ventana):
        soportes = []
        total = len(datos)
        for i in range(ventana, total - ventana):
            minimo = datos['low'].iloc[i-ventana:i+ventana+1].min()
            if abs(datos['low'].iloc[i] - minimo) / minimo <= 0.0018:
                soportes.append(round(minimo, 5))
        return sorted(list(set(soportes)))

    soportes = detectar_soportes(df, ventana_niveles)

    try:
        cierre = float(df['close'].iloc[-1])
        apertura = float(df['open'].iloc[-1])
        macd_val = float(df['macd'].iloc[-1])
        senal_macd_val = float(df['senal_macd'].iloc[-1])
        rsi_val = float(df['rsi'].iloc[-1])
        volumen = float(df['volume'].iloc[-1])
        vol_prom = float(df['volume'].iloc[-5:-1].mean()) if len(df) >= 6 else max(volumen, 1.0)
    except Exception:
        return None

    en_soporte = any(abs(cierre - s) / s <= tolerancia_nivel for s in soportes)

    # Solo compra por sobreventa + reversión
    senal = None
    fuerza = 0
    tipo_nivel = ""

    if rsi_val < 25:
        if en_soporte and macd_val >= senal_macd_val and cierre > apertura:
            senal = "call"
            tipo_nivel = "REVERSIÓN SOBREVENTA"
            fuerza = 50
            if rsi_val < 20:
                fuerza += 15
            if volumen >= vol_prom * 0.4:
                fuerza += 10
            if df['ema8'].iloc[-1] > df['ema21'].iloc[-1]:
                fuerza += 10
            if df['close'].iloc[-2] < df['open'].iloc[-2]:
                fuerza += 10

    # Solo devuelve si cumple la fuerza mínima
    if senal is not None and fuerza >= 75:
        return (senal, fuerza, tipo_nivel)

    return None
