import pandas as pd
import numpy as np

# ==================================================
# 🧠 ESTRATEGIA: ESTRUCTURA + RECHAZO + PATRONES
# 🎯 ACTIVO: EURUSD | 1MIN | REVERSIÓN
# 📏 LÓGICA: Analiza últimas 60 velas, busca zonas
# respetadas, medir mechas/rechazo, detectar secuencias
# ==================================================

# ============================================
# 🏗️ 1. ANALIZAR ESTRUCTURA - DETECTAR ZONAS
# Busca los niveles que el precio HA RESPETADO YA
# en las ultimas N velas (max/min significativos)
# ============================================
def analizar_estructura(df, n_velas=60):
    """
    Devuelve listas de soportes y resistencias claras
    basado en Mínimos y Máximos relevantes de las últimas velas.
    """
    # Trabajamos solo con las N velas más recientes
    data = df.tail(n_velas).copy()
    
    soportes = []
    resistencias = []
    
    # 📏 VENTANA PARA MÁX/MÍN: Buscamos giros locales
    # Un mínimo es punto bajo si los 2 anteriores y 2 siguientes son más altos
    for i in range(3, len(data)-3):
        # DETECTAR SOPORTE (Mínimo Local / VALLE)
        min_local = data['low'].iloc[i]
        if (min_local < data['low'].iloc[i-1] and 
            min_local < data['low'].iloc[i-2] and
            min_local < data['low'].iloc[i+1] and 
            min_local < data['low'].iloc[i+2]):
            soportes.append(round(min_local, 5))

        # DETECTAR RESISTENCIA (Máximo Local / PICO)
        max_local = data['high'].iloc[i]
        if (max_local > data['high'].iloc[i-1] and 
            max_local > data['high'].iloc[i-2] and
            max_local > data['high'].iloc[i+1] and 
            max_local > data['high'].iloc[i+2]):
            resistencias.append(round(max_local, 5))

    # 🧹 LIMPIEZA: Eliminar niveles repetidos o muy cercanos (ruido)
    soportes = sorted(list(set(soportes)))
    resistencias = sorted(list(set(resistencias)))

    # Filtrar: solo niveles donde el precio rebotó al menos 10 pips
    soportes_filtrados = []
    resistencias_filtradas = []
    
    # Simplificamos dejando los 3 niveles más fuertes (los extremos)
    if len(soportes) >= 2:
        soportes_filtrados = [min(soportes), np.median(soportes), max(soportes)]
    if len(resistencias) >= 2:
        resistencias_filtradas = [min(resistencias), np.median(resistencias), max(resistencias)]

    return soportes_filtrados, resistencias_filtradas

# ============================================
# 🧨 2. MEDIR RECHAZO EN ZONAS
# Analiza la VELA ACTUAL: ¿Tiene MECHA larga tocando zona?
# ============================================
def verificar_rechazo(vela, soportes, resistencias, tolerancia_pips=0.0003):
    """
    Comprueba si la vela actual está tocando una zona fuerte
    y tiene una mecha grande indicando rechazo.
    """
    precio_actual_cierre = vela['close']
    precio_bajo = vela['low']
    precio_alto = vela['high']
    cuerpo = abs(vela['open'] - vela['close'])
    
    # Definimos tamaño de mecha mínima para considerar rechazo (>= 1.5x cuerpo)
    MECHA_MINIMA = cuerpo * 1.5 if cuerpo > 0 else 0.0002

    # 🔵 COMPROBAR RECHAZO ARRIBA -> VENDA (PUT)
    # Precio toca Resistencia -> Sube mucho -> Baja rápido (Mecha arriba larga)
    for r in resistencias:
        # ¿El precio ALTO de esta vela ha tocado o superado la zona?
        if abs(precio_alto - r) <= tolerancia_pips:
            # ¿La mecha superior es LARGA? (Se fue arriba, rechazo, volvió abajo)
            mecha_sup = precio_alto - max(vela['open'], vela['close'])
            if mecha_sup >= MECHA_MINIMA:
                # 🎯 CONFIRMACIÓN: El cierre quedó LEJOS de la zona tocada
                if precio_actual_cierre < (r - tolerancia_pips):
                    return True, "bajista", r # Rechazo fuerte -> Ir a PUT

    # 🟢 COMPROBAR RECHAZO ABAJO -> COMPRA (CALL)
    # Precio toca Soporte -> Baja mucho -> Sube rápido (Mecha abajo larga)
    for s in soportes:
        # ¿El precio BAJO de esta vela ha tocado o bajado de la zona?
        if abs(precio_bajo - s) <= tolerancia_pips:
            # ¿La mecha inferior es LARGA? (Se fue abajo, rechazo, volvió arriba)
            mecha_inf = min(vela['open'], vela['close']) - precio_bajo
            if mecha_inf >= MECHA_MINIMA:
                # 🎯 CONFIRMACIÓN: El cierre quedó LEJOS de la zona tocada
                if precio_actual_cierre > (s + tolerancia_pips):
                    return True, "alcista", s # Rechazo fuerte -> Ir a CALL

    return False, None, None

# ============================================
# 🔁 3. DETECTAR PATRONES DE VELAS REPETITIVOS
# Busca secuencias tipo: 🔵🔵🔵🔴 | 🔴🔴🔴🔵
# que se repiten 2 veces, a la 3ª operamos
# ============================================
def detectar_patron(df):
    """
    Analiza las ultimas 10 velas cerradas.
    Busca patron: [3 Verdes, 1 Roja] o [3 Rojas, 1 Verde]
    Si este patron ocurre por 3ra vez, devuelve señal.
    """
    # Tomamos las últimas 10 velas YA CERRADAS
    velas = df.tail(11).copy()
    if len(velas) < 10:
        return False, None

    # 🟩 = 1 (Verde/Alcista), 🟥 = -1 (Roja/Bajista)
    velas['tipo'] = np.where(velas['close'] > velas['open'], 1, -1)
    secuencia = velas['tipo'].tolist()

    contador_patron_alcista = 0 # Patron: [1,1,1,-1] -> 3V 1R
    contador_patron_bajista = 0 # Patron: [-1,-1,-1,1] -> 3R 1V

    # Buscar ocurrencias del patrón mirando hacia atrás
    for i in range(len(secuencia)-4, 0, -1):
        # PATRÓN 1: 3 VERDES + 1 ROJA -> Fin subida, posible bajada
        if secuencia[i] == 1 and secuencia[i+1] == 1 and secuencia[i+2] == 1 and secuencia[i+3] == -1:
            contador_patron_bajista += 1
            
        # PATRÓN 2: 3 ROJAS + 1 VERDE -> Fin bajada, posible subida
        if secuencia[i] == -1 and secuencia[i+1] == -1 and secuencia[i+2] == -1 and secuencia[i+3] == 1:
            contador_patron_alcista += 1

    # ✅ REGLA: Si se ha repetido AL MENOS 2 VECES, y ahora es la 3ª
    # Comprobamos si la ÚLTIMA SECUENCIA (actual) cumple el patrón
    ult4 = secuencia[-4:]

    if ult4 == [1,1,1,-1] and contador_patron_bajista >= 2:
        return True, "bajista" # 🎯 PATRÓN COMPLETO -> VENDER

    if ult4 == [-1,-1,-1,1] and contador_patron_alcista >= 2:
        return True, "alcista" # 🎯 PATRÓN COMPLETO -> COMPRAR

    return False, None
