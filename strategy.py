import numpy as np
import pandas as pd

# ==================================================
# 🚀 ESTRATEGIA CORREGIDA - ALTA PRECISIÓN
# ✅ Error de Series solucionado
# ✅ Solo entradas de alta calidad
# ✅ Evita consolidación y fin de tendencia
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
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean().replace(0, 0.001)
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    df['macd'] = df['ema13'] - df['ema34']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['hist'] = df['macd'] - df['signal']

    # ADX
    df['tr'] = np.maximum(df['high'] - df['low'],
                          np.maximum(abs(df['high'] - df['close'].shift(1)),
                                     abs(df['low'] - df['close'].shift(1))))
    df['dm_plus'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                             np.maximum(df['high'] - df['high'].shift(1), 0), 0)
    df['dm_minus'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                              np.maximum(df['low'].shift(1) - df['low'], 0), 0)

    tr14 = df['tr'].rolling(14).sum()
    dmp14 = df['dm_plus'].rolling(14).sum()
    dmm14 = df['dm_minus'].rolling(14).sum()

    di_plus = 100 * dmp14 / tr14.replace(0, 0.001)
    di_minus = 100 * dmm14 / tr14.replace(0, 0.001)
    dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus).replace(0, 0.001)
    df['adx'] = dx.rolling(14).mean()

    # Extraer ÚLTIMOS VALORES COMO NÚMEROS (CORRIGE EL ERROR)
    v1 = df.iloc[-1]
    v2 = df.iloc[-2]
    v3 = df.iloc[-3]
    v4 = df.iloc[-4]
    v5 = df.iloc[-5]

    adx_v1 = float(v1['adx'])
    adx_v2 = float(v2['adx'])
    adx_v3 = float(v3['adx'])

    if adx_v1 < 27:
        return None

    tendencia = "lateral"
    fuerza_base = 0

    # ==============================================
    # ✅ TENDENCIA ALCISTA
    # ==============================================
    if (
        float(v1['ema8']) > float(v1['ema13']) > float(v1['ema21']) > float(v1['ema34']) > float(v1['ema50']) and
        float(v2['ema8']) > float(v2['ema13']) > float(v2['ema21']) and
        float(v1['low']) > float(v2['low']) and float(v2['low']) > float(v3['low']) and float(v3['low']) > float(v4['low']) and
        float(v1['high']) > float(v2['high']) and float(v2['high']) > float(v3['high']) and
        float(v1['close']) > float(v1['ema8']) and float(v1['close']) < float(v1['ema21']) * 1.012 and
        float(v1['macd']) > float(v1['signal']) and float(v1['hist']) > float(v2['hist']) and float(v2['hist']) > float(v3['hist']) and
        51 < float(v1['rsi']) < 63 and
        adx_v1 > adx_v2 and adx_v2 > adx_v3
    ):
        distancia = (float(v1['close']) - float(v1['ema21'])) / float(v1['ema21']) * 100
        if distancia > 1.2:
            return None

        tendencia = "alcista"
        fuerza_base += 58

    # ==============================================
    # ✅ TENDENCIA BAJISTA
    # ==============================================
    elif (
        float(v1['ema8']) < float(v1['ema13']) < float(v1['ema21']) < float(v1['ema34']) < float(v1['ema50']) and
        float(v2['ema8']) < float(v2['ema13']) < float(v2['ema21']) and
        float(v1['high']) < float(v2['high']) and float(v2['high']) < float(v3['high']) and float(v3['high']) < float(v4['high']) and
        float(v1['low']) < float(v2['low']) and float(v2['low']) < float(v3['low']) and
        float(v1['close']) < float(v1['ema8']) and float(v1['close']) > float(v1['ema21']) * 0.988 and
        float(v1['macd']) < float(v1['signal']) and float(v1['hist']) < float(v2['hist']) and float(v2['hist']) < float(v3['hist']) and
        37 < float(v1['rsi']) < 49 and
        adx_v1 > adx_v2 and adx_v2 > adx_v3
    ):
        distancia = (float(v1['ema21']) - float(v1['close'])) / float(v1['ema21']) * 100
        if distancia > 1.2:
            return None

        tendencia = "bajista"
        fuerza_base += 58

    if tendencia == "lateral":
        return None

    # ==============================================
    # ✅ FILTROS DE CALIDAD
    # ==============================================
    ultimas = df.tail(18)
    rango_prom = (ultimas['high'] - ultimas['low']).mean()
    vol_prom = ultimas['volume'].mean()
    tamaño_vela = float(v1['high']) - float(v1['low'])

    if tamaño_vela < rango_prom * 0.68:
        return None
    fuerza_base += 10

    if float(v1['volume']) < vol_prom * 0.8:
        return None
    fuerza_base += 10

    cuerpo = abs(float(v1['close']) - float(v1['open']))
    if cuerpo < tamaño_vela * 0.52:
        return None
    fuerza_base += 10

    # Secuencia de confirmación
    ultimas_5 = df.tail(5).copy()
    ultimas_5['dir'] = np.where(ultimas_5['close'] > ultimas_5['open'], 1, -1)
    secuencia = ultimas_5['dir'].tolist()

    if tendencia == "alcista" and secuencia[-4:] == [1, 1, 1, 1]:
        fuerza_base += 12
        return ("call", min(fuerza_base, 100), "alcista")

    if tendencia == "bajista" and secuencia[-4:] == [-1, -1, -1, -1]:
        fuerza_base += 12
        return ("put", min(fuerza_base, 100), "bajista")

    return None

def pro_signal(df):
    return None
