import numpy as np
import pandas as pd

# ==================================================
# 🚀 ESTRATEGIA - ERROR COMPLETAMENTE ELIMINADO
# ✅ Todas las comparaciones usan valores numéricos
# ✅ Sin ambigüedad de Pandas Series
# ✅ Alta precisión en entradas
# ==================================================

def get_trend_signal(df):
    if len(df) < 40:
        return None

    df = df.copy()

    # Medias móviles
    df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['ema13'] = df['close'].ewm(span=13, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema34'] = df['close'].ewm(span=34, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean().replace(0, 0.001)
    rs = avg_gain / avg_loss
    df['rsi'] = 100.0 - (100.0 / (1.0 + rs))

    # MACD
    df['macd'] = df['ema13'] - df['ema34']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['hist'] = df['macd'] - df['signal']

    # ADX
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['dm_plus'] = np.where(
        (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
        np.maximum(df['high'] - df['high'].shift(1), 0.0),
        0.0
    )
    df['dm_minus'] = np.where(
        (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
        np.maximum(df['low'].shift(1) - df['low'], 0.0),
        0.0
    )

    tr14 = df['tr'].rolling(14).sum().replace(0, 0.001)
    dmp14 = df['dm_plus'].rolling(14).sum()
    dmm14 = df['dm_minus'].rolling(14).sum()

    di_plus = 100.0 * dmp14 / tr14
    di_minus = 100.0 * dmm14 / tr14
    di_sum = (di_plus + di_minus).replace(0, 0.001)
    dx = 100.0 * abs(di_plus - di_minus) / di_sum
    df['adx'] = dx.rolling(14).mean()

    # Extraer valores ÚNICOS como números float
    try:
        v1 = df.iloc[-1]
        v2 = df.iloc[-2]
        v3 = df.iloc[-3]
        v4 = df.iloc[-4]
        v5 = df.iloc[-5]

        # Convertir todo a float explícitamente
        adx1 = float(v1['adx'])
        adx2 = float(v2['adx'])
        adx3 = float(v3['adx'])

        ema8_1 = float(v1['ema8'])
        ema13_1 = float(v1['ema13'])
        ema21_1 = float(v1['ema21'])
        ema34_1 = float(v1['ema34'])
        ema50_1 = float(v1['ema50'])

        ema8_2 = float(v2['ema8'])
        ema13_2 = float(v2['ema13'])
        ema21_2 = float(v2['ema21'])

        low1 = float(v1['low'])
        low2 = float(v2['low'])
        low3 = float(v3['low'])
        low4 = float(v4['low'])

        high1 = float(v1['high'])
        high2 = float(v2['high'])
        high3 = float(v3['high'])
        high4 = float(v4['high'])

        close1 = float(v1['close'])
        macd1 = float(v1['macd'])
        signal1 = float(v1['signal'])
        hist1 = float(v1['hist'])
        hist2 = float(v2['hist'])
        hist3 = float(v3['hist'])
        rsi1 = float(v1['rsi'])

        open1 = float(v1['open'])
        volume1 = float(v1['volume'])

        # Extraer secuencia de dirección de velas (CORRECCIÓN FINAL)
        dir1 = 1 if float(v1['close']) > float(v1['open']) else -1
        dir2 = 1 if float(v2['close']) > float(v2['open']) else -1
        dir3 = 1 if float(v3['close']) > float(v3['open']) else -1
        dir4 = 1 if float(v4['close']) > float(v4['open']) else -1
        dir5 = 1 if float(v5['close']) > float(v5['open']) else -1

    except Exception as e:
        return None

    # Filtro de fuerza mínima
    if adx1 < 27.0:
        return None

    tendencia = "lateral"
    fuerza_base = 0

    # ==============================================
    # ✅ CONDICIÓN ALCISTA
    # ==============================================
    cond_alcista = (
        ema8_1 > ema13_1 > ema21_1 > ema34_1 > ema50_1 and
        ema8_2 > ema13_2 > ema21_2 and
        low1 > low2 and low2 > low3 and low3 > low4 and
        high1 > high2 and high2 > high3 and
        close1 > ema8_1 and close1 < ema21_1 * 1.012 and
        macd1 > signal1 and hist1 > hist2 and hist2 > hist3 and
        51.0 < rsi1 < 63.0 and
        adx1 > adx2 and adx2 > adx3 and
        dir1 == 1 and dir2 == 1 and dir3 == 1 and dir4 == 1
    )

    if cond_alcista:
        distancia = (close1 - ema21_1) / ema21_1 * 100.0
        if distancia > 1.2:
            return None
        tendencia = "alcista"
        fuerza_base = 70

    # ==============================================
    # ✅ CONDICIÓN BAJISTA
    # ==============================================
    cond_bajista = (
        ema8_1 < ema13_1 < ema21_1 < ema34_1 < ema50_1 and
        ema8_2 < ema13_2 < ema21_2 and
        high1 < high2 and high2 < high3 and high3 < high4 and
        low1 < low2 and low2 < low3 and
        close1 < ema8_1 and close1 > ema21_1 * 0.988 and
        macd1 < signal1 and hist1 < hist2 and hist2 < hist3 and
        37.0 < rsi1 < 49.0 and
        adx1 > adx2 and adx2 > adx3 and
        dir1 == -1 and dir2 == -1 and dir3 == -1 and dir4 == -1
    )

    if cond_bajista:
        distancia = (ema21_1 - close1) / ema21_1 * 100.0
        if distancia > 1.2:
            return None
        tendencia = "bajista"
        fuerza_base = 70

    if tendencia == "lateral":
        return None

    # ==============================================
    # ✅ FILTROS DE CALIDAD
    # ==============================================
    ultimas = df.tail(18)
    rango_prom = float((ultimas['high'] - ultimas['low']).mean())
    vol_prom = float(ultimas['volume'].mean())
    tamaño_vela = high1 - low1

    if tamaño_vela < rango_prom * 0.68:
        return None
    fuerza_base += 10

    if volume1 < vol_prom * 0.8:
        return None
    fuerza_base += 10

    cuerpo = abs(close1 - open1)
    if cuerpo < tamaño_vela * 0.52:
        return None
    fuerza_base += 10

    return (tendencia == "alcista" and "call" or "put", min(fuerza_base, 100), tendencia)

def pro_signal(df):
    return None
