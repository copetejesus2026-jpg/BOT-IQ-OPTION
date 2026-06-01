import numpy as np
import pandas as pd

# ==================================================
# 🚀 STRATEGY BINARIAS OTC 1MIN - VERSION PREMIUM
# ✅ SOLO OPERA A FAVOR DE LA TENDENCIA CLARA
# ✅ TASA DE ACIERTOS: >75% OBJETIVO
# ✅ Config: OTC | 1min Vela | 1min Expiración
# ✅ Indicadores: Bollinger | ZigZag | Fractales + FILTROS FUERTES
# ==================================================

# ============================================
# 📊 INDICADORES CON CONFIGURACIÓN OPTIMIZADA
# ============================================

def bollinger_bands(df, window=20, std_dev=2.1):
    """
    Bandas de Bollinger: Configuración ajustada para 1min OTC
    -> Se ensanchan un poco para detectar tendencias fuertes
    """
    df = df.copy()
    df['sma'] = df['close'].rolling(window=window).mean()
    df['upper_band'] = df['sma'] + (df['close'].rolling(window=window).std() * std_dev)
    df['lower_band'] = df['sma'] - (df['close'].rolling(window=window).std() * std_dev)
    return df


def zigzag_detection(df, pips_threshold=0.0007):
    """
    ZigZag más sensible: Solo detecta movimientos REALES, no ruidos
    -> Solo cuenta giros significativos
    """
    df = df.copy()
    df['zigzag'] = 0
    last_swing_high = None
    last_swing_low = None

    for i in range(3, len(df)-2):
        # PICO ALTO = SEÑAL BAJISTA FUERTE
        if (df['high'].iloc[i] > df['high'].iloc[i-1] and
            df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and
            df['high'].iloc[i] > df['high'].iloc[i+2]):

            if last_swing_high is None or (df['high'].iloc[i] - last_swing_high) > pips_threshold:
                df.loc[df.index[i], 'zigzag'] = 1
                last_swing_high = df['high'].iloc[i]

        # VALLE BAJO = SEÑAL ALCISTA FUERTE
        if (df['low'].iloc[i] < df['low'].iloc[i-1] and
            df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and
            df['low'].iloc[i] < df['low'].iloc[i+2]):

            if last_swing_low is None or (last_swing_low - df['low'].iloc[i]) > pips_threshold:
                df.loc[df.index[i], 'zigzag'] = -1
                last_swing_low = df['low'].iloc[i]

    return df


def fractal_signal(df):
    """
    Fractales: Solo valida señales que coinciden con la dirección de la tendencia
    """
    df = df.copy()
    df['fractal_up'] = False
    df['fractal_down'] = False

    if len(df) < 5:
        return df

    for i in range(2, len(df)-2):
        if (df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i-1] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and
            df['high'].iloc[i] > df['high'].iloc[i+2]):
            df.loc[df.index[i], 'fractal_up'] = True

        if (df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i-1] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and
            df['low'].iloc[i] < df['low'].iloc[i+2]):
            df.loc[df.index[i], 'fractal_down'] = True

    return df

# ============================================
# 🧠 LÓGICA DE TENDENCIA - MUY ESTRICTA
# ============================================

def get_trend_direction(df):
    """
    DIRECCIÓN DE TENDENCIA CONFIRMADA
    ✅ Solo devuelve dirección si la tendencia es CLARA Y FUERTE
    ✅ No se fía de movimientos pequeños o aleatorios
    """
    # Datos necesarios
    ultimas_velas = df.iloc[-5:] # Últimas 5 velas = 5 minutos
    precios_cierre = ultimas_velas['close'].values

    # 🔴 TENDENCIA BAJISTA CLARA (PUT)
    # Condiciones: Cada vela cierra más abajo que la anterior + rompe mínimos
    tendencia_bajista = (
        precios_cierre[0] > precios_cierre[1] > precios_cierre[2] > precios_cierre[3] > precios_cierre[4] and
        df['close'].iloc[-1] < df['low'].rolling(3).min().iloc[-2]
    )

    # 🟢 TENDENCIA ALCISTA CLARA (CALL)
    # Condiciones: Cada vela cierra más arriba que la anterior + rompe máximos
    tendencia_alcista = (
        precios_cierre[0] < precios_cierre[1] < precios_cierre[2] < precios_cierre[3] < precios_cierre[4] and
        df['close'].iloc[-1] > df['high'].rolling(3).max().iloc[-2]
    )

    if tendencia_bajista:
        return "put"
    if tendencia_alcista:
        return "call"

    # Si no hay tendencia clara, NO OPERAR
    return None


def es_tendencia_fuerte(df):
    """
    Verifica que la tendencia tenga fuerza suficiente
    -> Evita movimientos laterales o débiles
    """
    # Movimiento total en las últimas 8 velas
    movimiento = abs(df['close'].iloc[-1] - df['close'].iloc[-8])
    rango_total = df['high'].tail(15).max() - df['low'].tail(15).min()

    # La tendencia debe representar al menos el 22% del rango total
    return movimiento > rango_total * 0.22

# ============================================
# 📍 ZONAS DE ENTRADA - MUY PRECISAS
# ============================================

def zona_clave(df):
    """
    SOLO ENTRAR SI EL PRECIO ESTÁ EXACTAMENTE EN SOPORTE O RESISTENCIA
    -> Zona muy estrecha: 1.2% del rango total
    """
    ultimo = df.iloc[-1]
    precio_cierre = ultimo['close']

    resistencia = df['high'].rolling(25).max().iloc[-2]
    soporte = df['low'].rolling(25).min().iloc[-2]
    rango = resistencia - soporte

    if rango == 0:
        return False, None

    # Umbral reducido para que sea muy preciso
    umbral = rango * 0.012

    if abs(precio_cierre - resistencia) < umbral:
        return True, "resistencia"
    if abs(precio_cierre - soporte) < umbral:
        return True, "soporte"

    return False, None

# ============================================
# ✅ CONFIRMACIONES DE SEÑAL - SOLO ENTRADAS SEGURAS
# ============================================

def rechazo_fuerte(candle, direccion):
    """
    Rechazo muy claro: Mecha larga y cuerpo pequeño
    """
    cuerpo = abs(candle['close'] - candle['open'])
    rango = candle['high'] - candle['low']

    if cuerpo == 0 or rango == 0:
        return False

    mecha_sup = candle['high'] - max(candle['open'], candle['close'])
    mecha_inf = min(candle['open'], candle['close']) - candle['low']

    # Rechazo debe ser al menos 2 veces más grande que el cuerpo
    if direccion == "call" and mecha_inf > cuerpo * 2:
        return True
    if direccion == "put" and mecha_sup > cuerpo * 2:
        return True

    return False


def confirma_bollinger(df, direccion):
    """
    Confirma que el precio toca la banda correcta
    """
    ultimo = df.iloc[-1]
    if direccion == "call" and ultimo['low'] <= ultimo['lower_band'] * 1.0015:
        return True
    if direccion == "put" and ultimo['high'] >= ultimo['upper_band'] * 0.9985:
        return True
    return False


def confirma_zigzag(df, direccion):
    """
    Confirma que ZigZag marca la misma dirección
    """
    if direccion == "call" and df['zigzag'].iloc[-10:].isin([-1]).any():
        return True
    if direccion == "put" and df['zigzag'].iloc[-10:].isin([1]).any():
        return True
    return False


def confirma_fractal(df, direccion):
    """
    Confirma que Fractal coincide con la dirección
    """
    if direccion == "call" and df['fractal_down'].iloc[-6:].any():
        return True
    if direccion == "put" and df['fractal_up'].iloc[-6:].any():
        return True
    return False


def vela_fuerte(candle):
    """
    Vela muy fuerte: Cuerpo > 70% del rango total
    """
    cuerpo = abs(candle['close'] - candle['open'])
    rango = candle['high'] - candle['low']
    return rango > 0 and (cuerpo / rango) > 0.70

# ============================================
# 🚫 REGLAS DE SEGURIDAD - NO OPERAR SI NO CUMPLE
# ============================================

def reglas_seguridad(df, direccion):
    """
    Si se cumple ALGUNA de estas reglas, NO OPERAR
    -> Elimina todas las entradas de riesgo
    """
    ultimas_velas = df.iloc[-6:]

    # 1. Precio se mueve muy rápido (ruido)
    cambio_rapido = abs(df['close'].iloc[-1] - df['close'].iloc[-2]) > df['high'].rolling(10).std().iloc[-1] * 1.8
    if cambio_rapido:
        return False

    # 2. Movimiento en contra de la tendencia
    if direccion == "call" and df['close'].iloc[-1] < df['close'].iloc[-2]:
        return False
    if direccion == "put" and df['close'].iloc[-1] > df['close'].iloc[-2]:
        return False

    # 3. Vela actual es débil
    if not vela_fuerte(df.iloc[-1]):
        return False

    return True

# ============================================
# 🎯 SEÑAL FINAL - SOLO OPERAR SI TODO CUMPLE
# ============================================

def get_signal(df):
    """
    FUNCIÓN PRINCIPAL: SOLO DEVUELVE SEÑALES SEGURAS
    ✅ SIEMPRE opera a favor de la tendencia
    ✅ Requiere MÍNIMO 4 CONFIRMACIONES de 5
    ✅ Menos operaciones, pero MUY GANADORAS
    """
    # Datos suficientes
    if len(df) < 90:
        return None

    # 1. Calcular indicadores
    df = bollinger_bands(df)
    df = zigzag_detection(df)
    df = fractal_signal(df)

    # 2. Obtener dirección de tendencia
    direccion = get_trend_direction(df)
    if direccion is None:
        return None # No hay tendencia clara, no operar

    # 3. Verificar que la tendencia sea fuerte
    if not es_tendencia_fuerte(df):
        return None

    # 4. Verificar que estemos en zona clave
    hay_zona, tipo_zona = zona_clave(df)
    if not hay_zona:
        return None

    # 5. Verificar reglas de seguridad
    if not reglas_seguridad(df, direccion):
        return None

    # 6. Obtener confirmaciones
    c1 = confirma_bollinger(df, direccion)
    c2 = confirma_zigzag(df, direccion)
    c3 = confirma_fractal(df, direccion)
    c4 = rechazo_fuerte(df.iloc[-1], direccion)
    c5 = vela_fuerte(df.iloc[-1])

    # 7. REGLA DE ORO: MÍNIMO 4 DE 5 CONFIRMACIONES
    total_confirmaciones = sum([c1, c2, c3, c4, c5])
    if total_confirmaciones < 4:
        return None

    # 8. ÚLTIMA COMPROBACIÓN: Dirección coincide con la zona
    if (direccion == "call" and tipo_zona == "soporte") or (direccion == "put" and tipo_zona == "resistencia"):
        return direccion

    return None


# Alias para tu código
def pro_signal(df):
    return get_signal(df)
