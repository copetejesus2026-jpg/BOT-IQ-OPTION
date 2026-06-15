import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import threading
import logging
from datetime import datetime, timezone

from strategy import get_reversal_signal
from iqoptionapi.stable_api import IQ_Option

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ⚙️ CONFIGURACIÓN
EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXPIRATION = 1
BASE_AMOUNT = 600
TIMEFRAME_M1 = 60

# Todos los pares OTC
PARES_TODOS_OTC = [
    "EURUSD-OTC", "GBPUSD-OTC", "EURGBP-OTC", "EURJPY-OTC",
    "AUDUSD-OTC", "USDCAD-OTC", "USDCHF-OTC", "EURCAD-OTC", "GBPCAD-OTC", "AUDJPY-OTC", "CADJPY-OTC",
    "GBPAUD-OTC", "AUDCAD-OTC", "AUDCHF-OTC", "EURAUD-OTC", "GBPCHF-OTC", "EURCHF-OTC"
]

MAX_DAILY_TRADES = 35
MAX_LOSS_STREAK = 5
PAUSE_TIME = 900
MAX_RECONNECT_ATTEMPTS = 20
RECONNECT_DELAY = 1

# Reglas de señal
FUERZA_MINIMA = 78
TOLERANCIA_NIVEL = 0.0020
VENTANA_NIVELES = 6
CONFIRMAR_TENDENCIA = True

# ⚙️ EJECUCIÓN MEJORADA PARA QUE NO FALLE
TIEMPO_ESPERA_EJECUCION = 0.008
REINTENTOS_EJECUCION = 12          # Más intentos
TIEMPO_MINIMO_VALIDO = 59          # Casi todo el minuto
ESPERA_ENTRE_INTENTOS = 0.02
RANGO_ENTRADA_INICIO = 0           # Entrar desde el segundo 0
RANGO_ENTRADA_FIN = 6              # Hasta segundo 6

# Variables globales
DAILY_TRADES = 0
CURRENT_DAY = datetime.now(timezone.utc).day
LOSS_STREAK = 0
LAST_LOSS = 0
LAST_TRADE = None
BOT_RUNNING = False
SEÑAL_PENDIENTE = None
ULTIMA_VELA_EJECUTADA = None

# 📱 FUNCIONES TELEGRAM
def send(msg):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
                timeout=8
            )
        except Exception as e:
            logging.error(f"Telegram: {str(e)}")

def listen_commands():
    global BOT_RUNNING
    last_update_id = 0
    while True:
        try:
            res = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": last_update_id + 1, "timeout": 30},
                timeout=35
            )
            data = res.json()
            if not data.get("ok"):
                time.sleep(2)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if chat_id != str(CHAT_ID):
                    continue

                if text == "/start":
                    if not BOT_RUNNING:
                        BOT_RUNNING = True
                        send("✅ <b>BOT CORREGIDO INICIADO</b>\nEjecución garantizada\nTodos los pares OTC\nVencimiento 1 min")
                    else:
                        send("ℹ️ El bot ya está activo.")
                elif text == "/stop":
                    if BOT_RUNNING:
                        BOT_RUNNING = False
                        send("🛑 <b>BOT DETENIDO</b>")
                    else:
                        send("ℹ️ El bot ya está detenido.")

        except Exception as e:
            logging.error(f"Comandos: {str(e)}")
            time.sleep(1)

# 🔄 REINICIO DIARIO
def reset_day():
    global DAILY_TRADES, CURRENT_DAY, LOSS_STREAK, LAST_TRADE, SEÑAL_PENDIENTE, ULTIMA_VELA_EJECUTADA
    today = datetime.now(timezone.utc).day
    if today != CURRENT_DAY:
        DAILY_TRADES = 0
        LOSS_STREAK = 0
        LAST_TRADE = None
        SEÑAL_PENDIENTE = None
        ULTIMA_VELA_EJECUTADA = None
        CURRENT_DAY = today
        if BOT_RUNNING:
            send("🔄 <b>NUEVO DÍA</b> | Contadores reiniciados.")

# 🔌 CONEXIÓN IQ OPTION
def connect():
    attempts = 0
    while attempts < MAX_RECONNECT_ATTEMPTS:
        try:
            if not EMAIL or not PASSWORD:
                send("❌ ERROR: Credenciales no configuradas.")
                time.sleep(10)
                attempts += 1
                continue

            iq = IQ_Option(EMAIL, PASSWORD)
            ok, reason = iq.connect()
            
            if ok:
                try:
                    iq.change_balance("PRACTICE")
                    balance = iq.get_balance()
                    send(f"✅ <b>CONECTADO</b>\nSaldo: ${balance:.2f}")
                    return iq
                except Exception:
                    send("ℹ️ Cargando datos...")
                    time.sleep(0.3)
            else:
                send(f"❌ Conexión fallida: {reason}")
                
        except Exception as e:
            send(f"❌ Error conexión: {str(e)}")
        
        attempts += 1
        time.sleep(RECONNECT_DELAY)
    
    send("💥 Reintentando en 20 s...")
    time.sleep(20)
    return connect()

# 📥 OBTENER DATOS
def get_df(iq, par, reintentos=3):
    for _ in range(reintentos):
        try:
            if not iq or not iq.check_connect():
                iq = connect()
                if not iq:
                    time.sleep(0.5)
                    continue

            datos = iq.get_candles(par, TIMEFRAME_M1, 40, time.time())
            if not datos or len(datos) < 12:
                time.sleep(0.2)
                continue

            df = pd.DataFrame(datos)
            df.rename(columns={"max": "high", "min": "low"}, inplace=True)
            df[["open", "close", "high", "low", "volume"]] = df[["open", "close", "high", "low", "volume"]].astype(float)
            return df

        except Exception as e:
            logging.error(f"Datos {par}: {str(e)}")
            time.sleep(0.3)
    
    return None

# 🚀 EJECUTAR OPERACIÓN - NUEVA VERSIÓN QUE NO FALLA
def ejecutar_operacion(iq, monto, par, direccion, vencimiento):
    for intento in range(REINTENTOS_EJECUCION + 1):
        try:
            # Reconectar en cada intento
            if not iq.check_connect():
                iq = connect()
                time.sleep(0.02)
            
            tiempo_servidor = iq.get_server_timestamp()
            segundos_restantes = 60 - (tiempo_servidor % 60)
            
            # Solo si hay tiempo suficiente
            if segundos_restantes < 2:
                return False, None
            
            time.sleep(TIEMPO_ESPERA_EJECUCION)
            estado, id_operacion = iq.buy(monto, par, direccion, vencimiento)
            
            if estado and id_operacion > 0:
                send(f"✅ Ejecutado correctamente - Intento {intento+1}")
                return True, id_operacion
            
            if intento < REINTENTOS_EJECUCION:
                time.sleep(ESPERA_ENTRE_INTENTOS)

        except Exception as e:
            logging.error(f"Intento {intento+1}: {str(e)}")
            if intento < REINTENTOS_EJECUCION:
                time.sleep(ESPERA_ENTRE_INTENTOS)
    
    return False, None

# 🧠 BUCLE PRINCIPAL
def main():
    global BOT_RUNNING, LOSS_STREAK, LAST_LOSS, DAILY_TRADES, LAST_TRADE, SEÑAL_PENDIENTE, ULTIMA_VELA_EJECUTADA
    threading.Thread(target=listen_commands, daemon=True).start()

    iq = connect()
    send("ℹ️ <b>SISTEMA LISTO</b>\nEjecución solucionada\nEntrada: segundos 0‑6\nEnvía /start")

    while True:
        try:
            if not BOT_RUNNING:
                time.sleep(0.3)
                continue

            reset_day()

            if not iq or not iq.check_connect():
                iq = connect()
                time.sleep(0.5)
                continue

            if DAILY_TRADES >= MAX_DAILY_TRADES:
                send("ℹ️ Límite diario alcanzado.")
                BOT_RUNNING = False
                time.sleep(300)
                continue

            if LOSS_STREAK >= MAX_LOSS_STREAK:
                restante = int(PAUSE_TIME - (time.time() - LAST_LOSS))
                if restante > 0:
                    send(f"⏸️ Pausa: {restante//60} min por racha de pérdidas")
                    time.sleep(5)
                    continue
                else:
                    LOSS_STREAK = 0
                    LAST_TRADE = None
                    send("✅ Pausa finalizada.")

            tiempo_servidor = iq.get_server_timestamp()
            segundos = tiempo_servidor % 60
            vela_actual = int(tiempo_servidor // 60)

            # Ejecutar señal en rango permitido
            if vela_actual != ULTIMA_VELA_EJECUTADA and RANGO_ENTRADA_INICIO <= segundos <= RANGO_ENTRADA_FIN:
                ULTIMA_VELA_EJECUTADA = vela_actual

                if SEÑAL_PENDIENTE is not None:
                    par, senal, fuerza, tipo = SEÑAL_PENDIENTE
                    SEÑAL_PENDIENTE = None

                    if (par, senal) == LAST_TRADE:
                        send("ℹ️ Señal repetida → se omite")
                        continue
                    LAST_TRADE = (par, senal)

                    send(f"""🚀 <b>EJECUTANDO AHORA</b>
💹 Activo: {par}
📍 Condición: {tipo}
💪 Fuerza: {fuerza}/100
⏱️ Segundo: {segundos:.2f} | Vencimiento: 1 min""")

                    estado, id_operacion = ejecutar_operacion(iq, BASE_AMOUNT, par, senal, EXPIRATION)

                    if estado:
                        DAILY_TRADES += 1
                        send(f"✅ <b>OPERACIÓN ABIERTA</b> | ${BASE_AMOUNT:.2f} | Total: {DAILY_TRADES}/{MAX_DAILY_TRADES}")

                        time.sleep(65)
                        try:
                            resultado = iq.check_win_v4(id_operacion)
                            if resultado is None:
                                send("ℹ️ Resultado pendiente")
                                continue

                            if resultado < 0:
                                LOSS_STREAK += 1
                                LAST_LOSS = time.time()
                                send(f"❌ <b>PERDIDA</b> | -${abs(resultado):.2f}\nRacha: {LOSS_STREAK}/{MAX_LOSS_STREAK}")
                            else:
                                LOSS_STREAK = 0
                                send(f"✅ <b>GANADA</b> | +${resultado:.2f}\n_________________________")

                        except Exception as e:
                            send(f"⚠️ Verificación: {str(e)}")
                    else:
                        send(f"❌ No se pudo ejecutar en {par} tras todos los reintentos")

            # Buscar señales al final de vela
            if 54 <= segundos <= 58:
                mejor_opcion = None
                mayor_fuerza = 0

                for par in PARES_TODOS_OTC:
                    df = get_df(iq, par)
                    if df is None:
                        continue

                    resultado_señal = get_reversal_signal(df, TOLERANCIA_NIVEL, VENTANA_NIVELES, CONFIRMAR_TENDENCIA)
                    if resultado_señal is not None:
                        senal, fuerza, tipo = resultado_señal
                        if fuerza >= FUERZA_MINIMA and fuerza > mayor_fuerza:
                            mayor_fuerza = fuerza
                            mejor_opcion = (par, senal, fuerza, tipo)

                if mejor_opcion is not None:
                    SEÑAL_PENDIENTE = mejor_opcion
                    par, senal, fuerza, tipo = mejor_opcion
                    send(f"""🔍 <b>SEÑAL DETECTADA</b>
💹 Activo: {par}
📍 Nivel: {tipo}
💪 Fuerza: {fuerza}/100
⏳ Ejecución: inicio siguiente vela""")

            time.sleep(0.01)

        except Exception as e:
            send(f"💥 Error: {str(e)} | Reiniciando...")
            logging.exception("Error en bucle principal")
            time.sleep(1)
            try:
                iq = connect()
            except:
                pass

if __name__ == "__main__":
    requeridas = ["IQ_EMAIL", "IQ_PASSWORD", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"]
    faltantes = [var for var in requeridas if not os.getenv(var)]
    if faltantes:
        print(f"❌ Faltan variables: {', '.join(faltantes)}")
        sys.exit(1)
    main()
