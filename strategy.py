import numpy as np
import pandas as pd

# ==================================================
# 🚀 STRATEGY BINARIAS OTC 1MIN - VERSION FINAL
# 🛑 BLOQUEADO PARA NO OPERAR EN CONTRA DE LA TENDENCIA
# ✅ SOLO OPERA CUANDO TODO CUMPLE AL 100%
# ✅ Config: OTC | 1min Vela | 1min Expiración
# ✅ REGLAS ESTRICTAS: Ninguna entrada sin confirmación
# ==================================================

# ============================================
# 📊 INDICADORES TÉCNICOS - CONFIGURACIÓN ESTRICTA
# ============================================

def bollinger_bands(df, window=20, std_dev=2.1):
    """Bandas de Bollinger ajustadas para detectar niveles exactos"""
    df = df.copy()
    df['sma'] = df['close'].rolling(window=window).mean()
    df['upper_band'] = df['sma'] + (df['close'].rolling(window=window).std() * std_dev)
    df['lower_band'] = df['sma'] - (df['close'].rolling(window=window).std() * std_dev)
    return df


def zigzag_detection(df, pips_threshold=0.0008):
    """Solo detecta movimientos reales, ignora el ruido"""
    df = df.copy()
    df['zigzag'] = 0
    last_swing_high = None
    last_swing_low = None

    for i in range(3, len(df)-2):
        # PICO ALTO = SOLO PARA SEÑAL PUT
        if (df['high'].iloc[i] > df['high'].iloc[i-1] and
            df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and
            df['high'].iloc[i] > df['high'].iloc[i+2]):

            if last_swing_high is None or (df['high'].iloc[i] - last_swing_high) > pips_threshold:
                df.loc[df.index[i], 'zigzag'] = 1
                last_swing_high = df['high'].iloc[i]

        # VALLE BAJO = SOLO PARA SEÑAL CALL
        if (df['low'].iloc[i] < df['low'].iloc[i-1] and
            df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and
            df['low'].iloc[i] < df['low'].iloc[i+2]):

            if last_swing_low is None or (last_swing_low - df['low'].iloc[i]) > pips_threshold:
                df.loc[df.index[i], 'zigzag'] = -1
                last_swing_low = df['low'].iloc[i]

    return df


def fractal_signal(df):
    """Solo valida señales que coincidan exactamente con la tendencia"""
    df = df.copy()
    df['fractal_up'] = False
    df['fractal_down'] = False

    if len(df) < 5:
        return df

    for i in range(2, len(df)-2):
        # FRACTAL ARRIBA = SOLO PARA PUT
        if (df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i-1] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and
            df['high'].iloc[i] > df['high'].iloc[i+2]):
            df.loc[df.index[i], 'fractal_up'] = True

        # FRACTAL ABAJO = SOLO PARA CALL
        if (df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i-1] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and
            df['low'].iloc[i] < df['low'].iloc[i+2]):
            df.loc[df.index[i], 'fractal_down'] = True

    return df

# ============================================
# 🧠 TENDENCIA - BLOQUEADO PARA NO OPERAR EN CONTRA
# ============================================

def get_trend_direction(df):
    """
    🛑 REGLAS ESTRICTAS:
    - SOLO DEVUELVE DIRECCIÓN SI LA TENDENCIA ES MUY CLARA
    - NUNCA DEVUELVE SEÑAL SI HAY DUDA
    - BLOQUEADO PARA NO OPERAR EN CONTRA
    """
    # Datos de las últimas 6 velas (6 minutos)
    cierre = df['close'].values
    maximos = df['high'].values
    minimos = df['low'].values

    # ------------------------------
    # TENDENCIA BAJISTA CLARA (PUT)
    # Condiciones OBLIGATORIAS:
    # 1. Cada vela cierra más abajo que la anterior
    # 2. Rompe los mínimos de las últimas 3 velas
    # 3. No hay ninguna vela que cierre arriba de la anterior
    tendencia_bajista = (
        cierre[-1] < cierre[-2] < cierre[-3] < cierre[-4] < cierre[-5] and
        cierre[-1] < minimos[-3] and
        all(cierre[i] < cierre[i-1] for i in range(-1, -6, -1))
    )

    # ------------------------------
    # TENDENCIA ALCISTA CLARA (CALL)
    # Condiciones OBLIGATORIAS:
    # 1. Cada vela cierra más arriba que la anterior
    # 2. Rompe los máximos de las últimas 3 velas
    # 3. No hay ninguna vela que cierre abajo de la anterior
    tendencia_alcista = (
        cierre[-1] > cierre[-2] > cierre[-3] > cierre[-4] > cierre[-5] and
        cierre[-1] > maximos[-3] and
        all(cierre[i] > cierre[i-1] for i in range(-1, -6, -1))
    )

    # 🛑 SI NO CUMPLE TODAS LAS CONDICIONES, NO DEVUELVE NADA
    if tendencia_bajista:
        return "put"
    if tendencia_alcista:
        return "call"

    # Si no hay tendencia clara o no cumple todo: NO OPERAR
    return None


def verificar_fuerza_tendencia(df, direccion):
    """
    🛑 SOLO PERMITE OPERAR SI LA TENDENCIA ES FUERZA TOTAL
    - Movimiento mayor al 25% del rango total
    - Sin movimientos laterales
    """
    movimiento = abs(df['close'].iloc[-1] - df['close'].iloc[-10])
    rango_total = df['high'].tail(20).max() - df['low'].tail(20).min()

    if rango_total == 0:
        return False

    # Mínimo 25% del rango total debe ser movimiento de tendencia
    fuerza_suficiente = movimiento > rango_total * 0.25

    # Verifica que el movimiento siga la dirección
    if direccion == "put":
        sigue_direccion = all(df['close'].iloc[i] < df['close'].iloc[i-1] for i in range(-1, -6, -1))
    else:
        sigue_direccion = all(df['close'].iloc[i] > df['close'].iloc[i-1] for i in range(-1, -6, -1))

    return fuerza_suficiente and sigue_direccion

# ============================================
# 📍 ZONAS DE ENTRADA - MUY PRECISAS Y OBLIGATORIAS
# ============================================

def en_zona_clave(df):
    """
    🛑 SOLO ENTRAR SI ESTÁ EXACTAMENTE EN EL NIVEL
    - Zona de 1% del rango total (muy estrecha)
    - Si no está aquí: NO OPERAR
    """
    ultimo = df.iloc[-1]
    precio = ultimo['close']

    resistencia = df['high'].rolling(30).max().iloc[-2]
    soporte = df['low'].rolling(30).min().iloc[-2]
    rango = resistencia - soporte

    if rango == 0:
        return False, None

    # Umbral reducido al 1% para máxima precisión
    umbral = rango * 0.01

    if abs(precio - resistencia) < umbral:
        return True, "resistencia"
    if abs(precio - soporte) < umbral:
        return True, "soporte"

    # Si no está en ninguna zona: NO OPERAR
    return False, None

# ============================================
# ✅ CONFIRMACIONES - TODAS DEBEN CUMPLIRSE
# ============================================

def rechazo_fuerte(df):
    """
    🛑 RECHAZO OBLIGATORIO
    - Mecha mayor a 2 veces el tamaño del cuerpo
    - Sin excepciones: si no hay rechazo, no hay señal
    """
    ultimo = df.iloc[-1]
    cuerpo = abs(ultimo['close'] - ultimo['open'])
    rango = ultimo['high'] - ultimo['low']

    if cuerpo == 0 or rango == 0:
        return False

    mecha_sup = ultimo['high'] - max(ultimo['open'], ultimo['close'])
    mecha_inf = min(ultimo['open'], ultimo['close']) - ultimo['low']

    return mecha_sup > cuerpo * 2 or mecha_inf > cuerpo * 2


def confirma_bollinger(df, direccion):
    """
    🛑 CONFIRMACIÓN OBLIGATORIA
    - Toca la banda correcta
    """
    ultimo = df.iloc[-1]
    if direccion == "call" and ultimo['low'] <= ultimo['lower_band'] * 1.001:
        return True
    if direccion == "put" and ultimo['high'] >= ultimo['upper_band'] * 0.999:
        return True
    return False


def confirma_zigzag(df, direccion):
    """
    🛑 CONFIRMACIÓN OBLIGATORIA
    - ZigZag marca la dirección correcta
    """
    if direccion == "call" and df['zigzag'].iloc[-15:].isin([-1]).any():
        return True
    if direccion == "put" and df['zigzag'].iloc[-15:].isin([1]).any():
        return True
    return False


def confirma_fractal(df, direccion):
    """
    🛑 CONFIRMACIÓN OBLIGATORIA
    - Fractal marca la dirección correcta
    """
    if direccion == "call" and df['fractal_down'].iloc[-8:].any():
        return True
    if direccion == "put" and df['fractal_up'].iloc[-8:].any():
        return True
    return False


def vela_fuerte(df):
    """
    🛑 VELA FUERTE OBLIGATORIA
    - Cuerpo mayor al 75% del rango total
    """
    ultimo = df.iloc[-1]
    cuerpo = abs(ultimo['close'] - ultimo['open'])
    rango = ultimo['high'] - ultimo['low']

    return rango > 0 and (cuerpo / rango) > 0.75

# ============================================
# 🚫 REGLAS DE RECHAZO - SI CUMPLE ALGUNA, NO OPERA
# ============================================

def hay_que_rechazar(df, direccion):
    """
    🛑 SI CUMPLE ALGUNA DE ESTAS REGLAS: NO OPERAR
    - Ninguna excepción
    """
    ultimo = df.iloc[-1]
    penultimo = df.iloc[-2]

    # 1. Movimiento muy rápido (ruido)
    cambio_rapido = abs(ultimo['close'] - penultimo['close']) > (df['high'].rolling(10).std().iloc[-1] * 2)
    if cambio_rapido:
        return True

    # 2. Precio se mueve en contra de la tendencia
    if direccion == "call" and ultimo['close'] < penultimo['close']:
        return True
    if direccion == "put" and ultimo['close'] > penultimo['close']:
        return True

    # 3. Vela es muy débil
    cuerpo = abs(ultimo['close'] - ultimo['open'])
    rango = ultimo['high'] - ultimo['low']
    if rango > 0 and (cuerpo / rango) < 0.5:
        return True

    # 4. Precio está muy lejos de la zona
    resistencia = df['high'].rolling(30).max().iloc[-2]
    soporte = df['low'].rolling(30).min().iloc[-2]
    rango_total = resistencia - soporte
    if rango_total == 0:
        return True
    distancia = abs(ultimo['close'] - ((resistencia + soporte) / 2))
    if distancia > rango_total * 0.25:
        return True

    return False

# ============================================
# 🎯 SEÑAL FINAL - SOLO DEVUELVE SEÑAL SI TODO CUMPLE
# ============================================

def get_signal(df):
    """
    🛑 REGLAS FINALES ESTRICTAS:
    1. Solo opera si hay tendencia clara (cumple todas las condiciones)
    2. Solo opera si está en zona clave
    3. Solo opera si hay fuerza de tendencia
    4. TODAS las confirmaciones deben cumplirse
    5. Si algo falla: NO DEVUELVE NADA
    6. NUNCA opera en contra de la tendencia
    """
    # Datos suficientes
    if len(df) < 100:
        return None

    # 1. Calcular indicadores
    df = bollinger_bands(df)
    df = zigzag_detection(df)
    df = fractal_signal(df)

    # 2. Obtener dirección de tendencia
    direccion = get_trend_direction(df)
    if direccion is None:
        return None # No hay tendencia clara: NO OPERAR

    # 3. Verificar fuerza de la tendencia
    if not verificar_fuerza_tendencia(df, direccion):
        return None # Tendencia débil: NO OPERAR

    # 4. Verificar que esté en zona clave
    esta_en_zona, tipo_zona = en_zona_clave(df)
    if not esta_en_zona:
        return None # No está en zona: NO OPERAR

    # 5. Verificar reglas de rechazo
    if hay_que_rechazar(df, direccion):
        return None # Algo falló: NO OPERAR

    # 6. VERIFICAR QUE TODAS LAS CONFIRMACIONES CUMPLAN
    # 🛑 SI FALTA ALGUNA: NO HAY SEÑAL
    c1 = confirma_bollinger(df, direccion)
    c2 = confirma_zigzag(df, direccion)
    c3 = confirma_fractal(df, direccion)
    c4 = rechazo_fuerte(df)
    c5 = vela_fuerte(df)

    # 🛑 TODAS DEBEN SER VERDADERAS
    if not (c1 and c2 and c3 and c4 and c5):
        return None

    # 7. ÚLTIMA COMPROBACIÓN: Dirección coincide con la zona
    if (direccion == "call" and tipo_zona == "soporte") or (direccion == "put" and tipo_zona == "resistencia"):
        return direccion

    return None


# Alias para que func
