import numpy as np
import pandas as pd

# ==================================================
# 🚀 ESTRATEGIA 100% COMPATIBLE - ERROR ELIMINADO
# ✅ Extracción explícita de valores individuales
# ✅ Sin ambigüedad en Pandas
# ✅ Compatible con Railway / cualquier entorno
# ==================================================

def get_trend_signal(df):
    if len(df) < 40:
        return None

    df = df.copy()

    # --------------------------
    # CÁLCULO DE INDICADORES
    # --------------------------
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

    # --------------------------
    # EXTRACCIÓN SEGURA DE VALORES
    # --------------------------
    try:
        # Convertimos CADA valor a float explícitamente con .item()
        adx1 = float(df['adx'].iloc[-1].item())
        adx2 = float(df['adx'].iloc[-2].item())
        adx3 = float(df['adx'].iloc[-3].item())

        e8_1 = float(df['ema8'].iloc[-1].item())
        e13_1 = float(df['ema13'].iloc[-1].item())
        e21_1 = float(df['ema21'].iloc[-1].item())
        e34_1 = float(df['ema34'].iloc[-1].item())
        e50_1 = float(df['ema50'].iloc[-1].item())

        e8_2 = float(df['ema8'].iloc[-2].item())
        e13_2 = float(df['ema13'].iloc[-2].item())
        e21_2 = float(df['ema21'].iloc[-2].item())

        l1 = float(df['low'].iloc[-1].item())
        l2 = float(df['low'].iloc[-2].item())
        l3 = float(df['low'].iloc[-3].item())
        l4 = float(df['low'].iloc[-4].item())

        h1 = float(df['high'].iloc[-1].item())
        h2 = float(df['high'].iloc[-2].item())
        h3 = float(df['high'].iloc[-3].item())
        h4 = float(df['high'].iloc[-4].item())

        c1 = float(df['close'].iloc[-1].item())
        c2 = float(df['close'].iloc[-2].item())
        c3 = float(df['close'].iloc[-3].item())
        c4 = float(df['close'].iloc[-4].item())

        o1 = float(df['open'].iloc[-1].item())
        o2 = float(df['open'].iloc[-2].item())
        o3 = float(df['open'].iloc[-3].item())
        o4 = float(df['open'].iloc[-4].item())

        macd1 = float(df['macd'].iloc[-1].item())
        sig1 = float(df['signal'].iloc[-1].item())
        hist1 = float(df['hist'].iloc[-1].item())
        hist2 = float(df['hist'].iloc[-2].item())
        hist3 = float(df['hist'].iloc[-3].item())

        rsi1 = float(df['rsi'].iloc[-1].item())
        vol1 = float(df['volume'].iloc[-1].item())
        vol_prom = float(df['volume'].iloc[-18:-1].mean().item())
        rango_prom = float((df['high'].iloc[-18:-1] - df['low'].iloc[-18:-1]).mean().item())

    except Exception:
        return None

    # --------------------------
    # FILTROS Y CONDICIONES
    # --------------------------
    if adx1 < 27.0:
        return None

    fuerza = 0
    senal = None
    tipo = ""

    # Condición COMPRA
    cond_compra = (
        e8_1 > e13_1 > e21_1 > e34_1 > e50_1 and
        e8_2 > e13_2 > e21_2 and
        l1 > l2 and l2 > l3 and l3 > l4 and
        h1 > h2 and h2 > h3 and
        c1 > e8_1 and c1 < e21_1 * 1.012 and
        macd1 > sig1 and hist1 > hist2 and hist2 > hist3 and
        51.0 < rsi1 < 63.0 and
        adx1 > adx2 and adx2 > adx3 and
        c1 > o1 and c2 > o2 and c3 > o3 and c4 > o4
    )

    if cond_compra:
        distancia = (c1 - e21_1) / e21_1 * 100.0
        if distancia <= 1.2:
            senal = "call"
            tipo = "alcista"
            fuerza = 70

    # Condición VENTA
    cond_venta = (
        e8_1 < e13_1 < e21_1 < e34_1 < e50_1 and
        e8_2 < e13_2 < e21_2 and
        h1 < h2 and h2 < h3 and h3 < h4 and
        l1 < l2 and l2 < l3 and
        c1 < e8_1 and c1 > e21_1 * 0.988 and
        macd1 < sig1 and hist1 < hist2 and hist2 < hist3 and
        37.0 < rsi1 < 49.0 and
        adx1 > adx2 and adx2 > adx3 and
        c1 < o1 and c2 < o2 and c3 < o3 and c4 < o4
    )

    if cond_venta:
        distancia = (e21_1 - c1) / e21_1 * 100.0
        if distancia <= 1.2:
            senal = "put"
            tipo = "bajista"
            fuerza = 70

    if senal is None:
        return None

    # Filtros de calidad adicionales
    vela_tam = h1 - l1
    if vela_tam < rango_prom * 0.68:
        return None
    fuerza += 10

    if vol1 < vol_prom * 0.8:
        return None
    fuerza += 10

    cuerpo = abs(c1 - o1)
    if cuerpo < vela_tam * 0.52:
        return None
    fuerza += 10

    return (senal, min(fuerza, 100), tipo)

def pro_signal(df):
    return None
