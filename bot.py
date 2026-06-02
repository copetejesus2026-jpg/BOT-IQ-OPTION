import time
import os
import requests
import pandas as pd
import sys
import logging
from datetime import datetime

# IMPORTAMOS LA NUEVA ESTRATEGIA DE ESTRUCTURA
from strategy import analizar_estructura, detectar_patron, verificar_rechazo

from iqoptionapi.stable_api import IQ_Option

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

# ==========================================
# 🔑 CONFIGURACIÓN - EXCLUSIVO EURUSD REAL
# ==========================================
EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ⚙️ PARÁMETROS SEGÚN TU SOLICITUD
ASSET = "EURUSD"               # 🎯 SOLO ESTE ACTIVO - MERCADO REAL
EXPIRATION = 1                  # ⏱️ EXPIRACIÓN 1 MINUTO
BASE_AMOUNT = 2.0               # 💰 MONTO POR OPERACIÓN
TIMEFRAME = 60                  # 🕯️ VELAS DE 1 MINUTO
WINDOW_ANALISIS = 60            # 🔍 ANALIZAR SOLO ÚLTIMAS 60 VELAS

# 🛑 GESTIÓN DE RIESGO
MAX_DAILY_TRADES = 15
MAX_LOSS_STREAK = 2
PAUSE_TIME_AFTER_LOSS = 300     # 5 minutos de pausa si pierdes

# 🚦 VARIABLES GLOBALES
BOT_ACTIVO = True
DAILY_TRADES = 0
CURRENT_DAY = datetime.utcnow().day
LOSS_STREAK = 0
LAST_LOSS_TIME = 0

# ====================================================
#   📱 COMUNICACIÓN TELEGRAM
# ====================================================
def send_telegram(mensaje):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={
                    "chat_id": CHAT_ID,
                    "text": mensaje,
                    "parse_mode": "HTML"
                },
                timeout=5
            )
        except Exception as e:
            print(f"Telegram Error: {e}")

# ====================================================
#   🔄 CONTROL DE DÍA Y CONEXIÓN
# ====================================================
def reiniciar_diario():
    global DAILY_TRADES, CURRENT_DAY, LOSS_STREAK
    hoy = datetime.utcnow().day
    if hoy != CURRENT_DAY:
        DAILY_TRADES = 0
        LOSS_STREAK = 0
        CURRENT_DAY = hoy
        send_telegram("🔄 <b>NUEVO DÍA INICIADO</b> | Contadores reiniciados.")

def conectar_iq():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            conectado, razon = iq.connect()
            if conectado:
                # ⚠️ CAMBIA A "REAL" SI YA USAS DINERO REAL
                iq.change_balance("PRACTICE") 
                saldo = iq.get_balance()
                send_telegram(f"""✅ <b>CONECTADO A IQ OPTION</b>
💹 ACTIVO: {ASSET} (REAL)
📊 MODO: ESTRUCTURA + RECHAZO + PATRONES
💰 SALDO: ${saldo:.2f}""")
                return iq
            else:
                send_telegram("❌ Error conexión: Reintentando...")
        except Exception as e:
            send_telegram(f"❌ FALLÓ CONEXIÓN: {str(e)}")
        time.sleep(5)

# ====================================================
#   📥 OBTENER DATOS DEL MERCADO (TIEMPO REAL)
# ====================================================
def obtener_datos(iq):
    """
    Obtiene EXACTAMENTE las últimas 60 velas cerradas + vela actual en formación
    """
    try:
        # Pedimos 61 velas para tener 60 cerradas + la que se está formando
        datos = iq.get_candles(ASSET, TIMEFRAME, WINDOW_ANALISIS + 1, time.time())
        if not datos:
            return None
        
        df = pd.DataFrame(datos)
        df.rename(columns={"max": "high", "min": "low"}, inplace=True)
        
        # Aseguramos tipos numéricos
        df['open'] = pd.to_numeric(df['open'])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        
        return df
    except Exception as e:
        send_telegram(f"⚠️ Error datos: {e}")
        return None

# ====================================================
#   🧠 BUCLE PRINCIPAL DE EJECUCIÓN
# ====================================================
def main():
    global LOSS_STREAK, LAST_LOSS_TIME, DAILY_TRADES, BOT_ACTIVO
    iq = conectar_iq()
    ultima_vela_procesada = None
    señal_enviada = False

    while True:
        try:
            reiniciar_diario()
            tiempo_servidor = iq.get_server_timestamp()
            segundo = tiempo_servidor % 60
            minuto_actual = int(tiempo_servidor // 60)

            # ======================================
            # 🛑 CONTROLES DE SEGURIDAD
            # ======================================
            if not BOT_ACTIVO:
                time.sleep(1)
                continue
                
            if DAILY_TRADES >= MAX_DAILY_TRADES:
                send_telegram("🛑 <b>LÍMITE DE OPERACIONES ALCANZADO</b>")
                BOT_ACTIVO = False
                continue

            if LOSS_STREAK >= MAX_LOSS_STREAK:
                if time.time() - LAST_LOSS_TIME < PAUSE_TIME_AFTER_LOSS:
                    # En pausa obligatoria
                    time.sleep(1)
                    continue
                else:
                    LOSS_STREAK = 0 # Reactivar tras pausa

            # ======================================
            # 🔍 FASE 1: ANÁLISIS CONTINUO (TIEMPO REAL)
            # Entre segundo 10 y 58: Analizamos como va formándose la vela
            # ======================================
            if 10 <= segundo <= 58:
                df = obtener_datos(iq)
                if df is None or len(df) < WINDOW_ANALISIS:
                    continue

                # 1. Analizar Estructura: Encontrar Soportes y Resistencias RESPETADAS
                soportes, resistencias = analizar_estructura(df, WINDOW_ANALISIS)
                
                # 2. Analizar Vela Actual: ¿Se acerca y RECHAZA esas zonas?
                vela_actual = df.iloc[-1] # La última fila es la vela en vivo
                hay_rechazo, direccion_rechazo, zona_tocada = verificar_rechazo(vela_actual, soportes, resistencias)

                # 3. Detectar Patrón de Velas (3V1R, etc)
                patron_detectado, direccion_patron = detectar_patron(df)

                # 📝 GUARDAMOS ESTADO PARA CUANDO CIERRE LA VELA
                estado_analisis = {
                    "rechazo": hay_rechazo,
                    "direccion": direccion_rechazo,
                    "zona": zona_tocada,
                    "patron_ok": patron_detectado,
                    "dir_patron": direccion_patron,
                    "soportes": soportes,
                    "resistencias": resistencias
                }

            # ======================================
            # ⚡ FASE 2: DECISIÓN EN CIERRE DE VELA
            # EXACTAMENTE al cambio de minuto (59.8s - 0.3s)
            # ======================================
            if 59.7 <= segundo <= 59.99 or 0 <= segundo <= 0.3:
                
                # Evitar procesar la misma vela 2 veces
                if minuto_actual == ultima_vela_procesada:
                    continue
                ultima_vela_procesada = minuto_actual

                # Si no hicimos análisis previo, saltamos
                if 'estado_analisis' not in locals():
                    continue

                ea = estado_analisis # Atajo para leer mejor

                # ==================================================
                # ✅ CONDICIONES DE ENTRADA (TU LÓGICA EXACTA):
                # 1. Hubo RECHAZO claro en zona fuerte
                # 2. Se formó el PATRÓN de velas esperado
                # 3. Dirección coincide (REVERSIÓN)
                # ==================================================
                
                condiciones_cumplidas = False
                direccion_final = None
                mensaje_log = ""

                # CASO 1: RECHAZO EN RESISTENCIA (PRECIO SUBIÓ, CHOCÓ, BAJARÁ -> PUT)
                if ea["rechazo"] and ea["direccion"] == "bajista" and ea["patron_ok"] and ea["dir_patron"] == "bajista":
                    direccion_final = "put"
                    condiciones_cumplidas = True
                    mensaje_log = f"""🔴 <b>SEÑAL DETECTADA: REVERSIÓN BAJISTA</b>
📍 Zona: RESISTENCIA ({ea['zona']:.5f})
📉 Acción: PRECIO RECHAZADO HACIA ABAJO
🎯 Patrón: Confirmado x3
⏱️ Entrada: CIERRE DE VELA"""

                # CASO 2: RECHAZO EN SOPORTE (PRECIO BAJÓ, CHOCÓ, SUBIRÁ -> CALL)
                elif ea["rechazo"] and ea["direccion"] == "alcista" and ea["patron_ok"] and ea["dir_patron"] == "alcista":
                    direccion_final = "call"
                    condiciones_cumplidas = True
                    mensaje_log = f"""🟢 <b>SEÑAL DETECTADA: REVERSIÓN ALCISTA</b>
📍 Zona: SOPORTE ({ea['zona']:.5f})
📈 Acción: PRECIO RECHAZADO HACIA ARRIBA
🎯 Patrón: Confirmado x3
⏱️ Entrada: CIERRE DE VELA"""


                # ======================================
                # 🚀 EJECUTAR ORDEN SI TODO COINCIDE
                # ======================================
                if condiciones_cumplidas and direccion_final and ea["zona"] is not None:
                    send_telegram(mensaje_log)
                    
                    # Ejecutar compra/venta en IQ Option
                    status, trade_id = iq.buy(BASE_AMOUNT, ASSET, direccion_final, EXPIRATION)

                    if status:
                        DAILY_TRADES += 1
                        tipo_op = "🟢 COMPRA (CALL)" if direccion_final == "call" else "🔴 VENTA (PUT)"
                        send_telegram(f"""⚡ <b>OPERACIÓN EJECUTADA</b>
💹 Activo: {ASSET}
📈 Tipo: {tipo_op}
💲 Monto: ${BASE_AMOUNT}
🔄 #Op: {DAILY_TRADES}/{MAX_DAILY_TRADES}""")

                        # ⏳ ESPERAR RESULTADO (65 Segundos)
                        time.sleep(65)
                        resultado = iq.check_win_v4(trade_id)

                        if resultado < 0:
                            LOSS_STREAK += 1
                            LAST_LOSS_TIME = time.time()
                            send_telegram(f"❌ <b>LOSS</b> | Saldo: ${resultado:.2f}\n⚠️ Rachas: {LOSS_STREAK}/{MAX_LOSS_STREAK}")
                        else:
                            LOSS_STREAK = 0
                            send_telegram(f"✅ <b>WIN</b> | Ganancia: +${resultado:.2f}\n_________________________")
                
                # Reset señal para el siguiente ciclo
                del estado_analisis

            time.sleep(0.03) # Alta frecuencia para capturar el cierre exacto

        except Exception as e:
            send_telegram(f"💥 <b>ERROR CRÍTICO:</b> {str(e)}")
            time.sleep(3)

if __name__ == "__main__":
    main()
