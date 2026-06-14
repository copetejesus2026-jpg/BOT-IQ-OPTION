import numpy as np
import pandas as pd

def get_reversal_signal(df, tolerancia_nivel=0.0020, ventana_niveles=6, confirmar_tendencia=True):
    if len(df) < ventana_niveles + 8:
        return None

    df = df.copy()

    # Medias móviles
    df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['ema13'] = df['close'].ewm(span=13, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    # RSI
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

    # Detección de soportes + verificación de rotura
    def detectar_soportes_activos(datos, ventana):
        soportes = []
        total = len(datos)
        for i in range(ventana, total - ventana):
            minimo = datos['low'].iloc[i-ventana:i+ventana+1].min()
            if abs(datos['low'].iloc[i] - minimo) / minimo <= 0.0018:
                # Verificar que no se haya roto en últimas 3 velas
                if all(datos['low'].iloc[-3:] >= minimo * 0.9995):
                    soportes.append(round(minimo, 5))
        return sorted(list(set(soportes)))

    soportes = detectar_soportes_activos(df, ventana_niveles)

    try:
        cierre = float(df['close'].iloc[-1])
        apertura = float(df['open'].iloc[-1])
        macd_val = float(df['macd'].iloc[-1])
        senal_macd_val = float(df['senal_macd'].iloc[-1])
        rsi_val = float(df['rsi'].iloc[-1])
        volumen = float(df['volume'].iloc[-1])
        vol_prom = float(df['volume'].iloc[-6:-1].mean()) if len(df) >= 7 else max(volumen, 1.0)
        ema21_actual = float(df['ema21'].iloc[-1])
        # Verificar tendencia últimas 2 velas
        tendencia_bajista = (df['close'].iloc[-2] < df['open'].iloc[-2]) and (df['close'].iloc[-3] < df['open'].iloc[-3])
    except Exception:
        return None

    en_soporte = any(abs(cierre - s) / s <= tolerancia_nivel for s in soportes)

    # Condiciones estrictas para compra
    senal = None
    fuerza = 0
    tipo = ""

    if rsi_val < 25:
        if en_soporte and macd_val >= senal_macd_val and cierre > apertura:
            # Evitar contra tendencia bajista fuerte
            if confirmar_tendencia and tendencia_bajista:
                return None
            if confirmar_tendencia and cierre < ema21_actual:
                return None

            senal = "call"
            tipo = "REVERSIÓN SOBREVENTA + SOPORTE ACTIVO"
            fuerza = 50
            if rsi_val < 20:
                fuerza += 15
            if volumen >= vol_prom * 0.5:
                fuerza += 10
            if df['ema8'].iloc[-1] > df['ema21'].iloc[-1]:
                fuerza += 10
            if cierre > df['close'].iloc[-2]:
                fuerza += 10
            if en_soporte:
                fuerza += 8

    if senal is not None and fuerza >= 78:
        return (senal, fuerza, tipo)

    return None
