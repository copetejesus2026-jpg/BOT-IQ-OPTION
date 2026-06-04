import time
import os
import requests
import pandas as pd
import sys
import logging
from datetime import datetime

# IMPORTAMOS LA ESTRATEGIA
from strategy import analizar_estructura, detectar_patron, verificar_rechazo

from iqoptionapi.stable_api import IQ_Option

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

# ==========================================
# 🔑 CONFIGURACIÓN
# ==========================================
EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ⚙️ PARÁMETROS
ASSET = "EURUSD"               # Activo
EXPIRATION = 1                  # Expiración 1 minuto
BASE_AMOUNT = 2.0               # Monto por operación
TIMEFRAME = 60                  # Velas de 1 minuto
WINDOW_ANALISIS = 60            # Últimas 60 velas

# 🛑 GESTIÓN DE RIESGO
MAX_DAILY_TRADES = 15
MAX_LOSS_STREAK = 2
PAUSE_TIME_AFTER_LOSS = 300     # 5 minutos de pausa

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
            if not EMAIL or not PASSWORD:
                send_telegram("❌ ERROR: Faltan credenciales IQ_EMAIL o IQ_PASSWORD")
                time.sleep(10)
                continue

            iq = IQ_Option(EMAIL, PASSWORD)
            conectado, razon = iq.connect()
            if conectado:
                iq.change_balance("PRACTICE")
                saldo = iq.get_balance()
                send_telegram(f"""✅ <b>CONECTADO A IQ OPTION</b>
💹 ACTIVO: {ASSET}
📊 MODO: ESTRUCTURA + RECHAZO + PATRONES
💰 SALDO: ${saldo:.2f}""")
                return iq
            else:
                send_telegram(f"❌ Error conexión: {razon} | Reintentando...")
        except Exception as e:
            send_telegram(f"❌ FALLÓ CONEXIÓN: {str(e)}")
        time.sleep(5)

# ====================================================
#   📥 OBTENER DATOS DEL MERCADO
# ====================================================
def obtener_datos(iq):
    try:
        datos = iq.get_candles(ASSET, TIMEFRAME, WINDOW_ANALISIS + 1, time.time())
        if not datos:
            return None
        
        df = pd.DataFrame(datos)
        df.rename(columns={"max": "high", "min": "low"}, inplace=True)
        
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        
        if df.isnull().any().any():
            return None
        
        return df
    except Exception as e:
        send_telegram(f"⚠️ Error datos: {e}")
        return None

# ====================================================
#   🧠 BUCLE PRINCIPAL
# ====================================================
def main():
    global LOSS_STREAK, LAST_LOSS_TIME, DAILY_TRADES, BOT_ACTIVO
    iq = conectar_iq()
    ultima_vela_procesada = None

    while True:
        try:
            reiniciar_diario()
            tiempo_servidor = iq.get_server_timestamp()
            segundo = tiempo_servidor % 60
            minuto_actual = int(tiempo_servidor // 60)

            # 🛑 CONTROLES DE SEGURIDAD
            if not BOT_ACTIVO:
                time.sleep(1)
                continue
                
            if DAILY_TRADES >= MAX_DAILY_TRADES:
                send_telegram("🛑 <b>LÍMITE DE OPERACIONES ALCANZADO</b>")
                BOT_ACTIVO = False
                continue

            if LOSS_STREAK >= MAX_LOSS_STREAK:
                tiempo_pausa = time.time() - LAST_LOSS_TIME
                if tiempo_pausa < PAUSE_TIME_AFTER_LOSS:
                    time.sleep(1)
                    continue
                else:
                    LOSS_STREAK = 0

            # 🔍 FASE 1: ANÁLISIS
            estado_analisis = None
            if 10 <= segundo <= 58:
                df = obtener_datos(iq)
                if df is None or len(df) < WINDOW_ANALISIS:
                    continue

                soportes, resistencias = analizar_estructura(df, WINDOW_ANALISIS)
                vela_actual = df.iloc[-1]
                hay_rechazo, direccion_rechazo, zona_tocada = verificar_rechazo(vela_actual, soportes, resistencias)
                patron_detectado, direccion_patron = detectar_patron(df)

                estado_analisis = {
                    "rechazo": hay_rechazo,
                    "direccion": direccion_rechazo,
                    "zona": zona_tocada,
                    "patron_ok": patron_detectado,
                    "dir_patron": direccion_patron
                }

            # ⚡ FASE 2: DECISIÓN EN CIERRE
            if 59.7 <= segundo <= 59.99 or 0 <= segundo <= 0.3:
                if minuto_actual == ultima_vela_procesada:
                    continue
                ultima_vela_procesada = minuto_actual

                if not estado_analisis:
                    continue

                ea = estado_analisis
                condiciones_cumplidas = False
                direccion_final = None
                mensaje_log = ""

                # Caso bajista
                if ea["rechazo"] and ea["direccion"] == "bajista" and ea["patron_ok"] and ea["dir_patron"] == "bajista":
                    direccion_final = "put"
                    condiciones_cumplidas = True
                    mensaje_log = f"""🔴 <b>SEÑAL: REVERSIÓN BAJISTA</b>
📍 Resistencia: {ea['zona']:.5f}
📉 Rechazo confirmado
⏱️ Entrada al cierre"""

                # Caso alcista
                elif ea["rechazo"] and ea["direccion"] == "alcista" and ea["patron_ok"] and ea["dir_patron"] == "alcista":
                    direccion_final = "call"
                    condiciones_cumplidas = True
                    mensaje_log = f"""🟢 <b>SEÑAL: REVERSIÓN ALCISTA</b>
📍 Soporte: {ea['zona']:.5f}
📈 Rechazo confirmado
⏱️ Entrada al cierre"""

                # Ejecutar operación
                if condiciones_cumplidas and direccion_final and ea["zona"] is not None:
                    send_telegram(mensaje_log)
                    status, trade_id = iq.buy(BASE_AMOUNT, ASSET, direccion_final, EXPIRATION)

                    if status:
                        DAILY_TRADES += 1
                        tipo_op = "🟢 COMPRA (CALL)" if direccion_final == "call" else "🔴 VENTA (PUT)"
                        send_telegram(f"""⚡ <b>OPERACIÓN EJECUTADA</b>
💹 Activo: {ASSET}
📈 Tipo: {tipo_op}
💲 Monto: ${BASE_AMOUNT}
🔄 #Op: {DAILY_TRADES}/{MAX_DAILY_TRADES}""")

                        time.sleep(65)
                        resultado = iq.check_win_v4(trade_id)

                        if resultado < 0:
                            LOSS_STREAK += 1
                            LAST_LOSS_TIME = time.time()
                            send_telegram(f"❌ <b>LOSS</b> | Pérdida: ${abs(resultado):.2f}\n⚠️ Rachas: {LOSS_STREAK}/{MAX_LOSS_STREAK}")
                        else:
                            LOSS_STREAK = 0
                            send_telegram(f"✅ <b>WIN</b> | Ganancia: +${resultado:.2f}\n_________________________")

            time.sleep(0.03)

        except Exception as e:
            send_telegram(f"💥 <b>ERROR CRÍTICO:</b> {str(e)}")
            time.sleep(3)

if __name__ == "__main__":
    main()
