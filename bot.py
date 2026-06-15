import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import threading
import logging
from datetime import datetime, timezone

# ✅ IMPORT CORREGIDO
from estrategia_reversal import get_reversal_signal

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

PARES_TODOS_OTC = [
    "EURUSD-OTC", "GBPUSD-OTC", "EURGBP-OTC", "EURJPY-OTC",
    "AUDUSD-OTC", "USDCAD-OTC", "USDCHF-OTC", "EURCAD-OTC",
    "GBPCAD-OTC", "AUDJPY-OTC", "CADJPY-OTC",
    "GBPAUD-OTC", "AUDCAD-OTC", "AUDCHF-OTC",
    "EURAUD-OTC", "GBPCHF-OTC", "EURCHF-OTC"
]

MAX_DAILY_TRADES = 12
MAX_LOSS_STREAK = 2
PAUSE_TIME = 900
MAX_RECONNECT_ATTEMPTS = 20
RECONNECT_DELAY = 3

FUERZA_MINIMA = 70
TOLERANCIA_NIVEL = 0.0020
VENTANA_NIVELES = 6
CONFIRMAR_TENDENCIA = True

TIEMPO_ESPERA_EJECUCION = 0.008
REINTENTOS_EJECUCION = 12
TIEMPO_MINIMO_VALIDO = 59
ESPERA_ENTRE_INTENTOS = 0.02
RANGO_ENTRADA_INICIO = 0
RANGO_ENTRADA_FIN = 6

DAILY_TRADES = 0
CURRENT_DAY = datetime.now(timezone.utc).day
LOSS_STREAK = 0
LAST_LOSS = 0
LAST_TRADE = None
BOT_RUNNING = False
SEÑAL_PENDIENTE = None
ULTIMA_VELA_EJECUTADA = None

# 📱 TELEGRAM
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

            for update in data.get("result", []):
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if chat_id != str(CHAT_ID):
                    continue

                if text == "/start":
                    BOT_RUNNING = True
                    send("✅ BOT INICIADO")
                elif text == "/stop":
                    BOT_RUNNING = False
                    send("🛑 BOT DETENIDO")

        except Exception as e:
            logging.error(f"Comandos: {str(e)}")
            time.sleep(1)

# 🔄 RESET DIARIO
def reset_day():
    global DAILY_TRADES, CURRENT_DAY, LOSS_STREAK
    today = datetime.now(timezone.utc).day
    if today != CURRENT_DAY:
        DAILY_TRADES = 0
        LOSS_STREAK = 0
        CURRENT_DAY = today

# 🔌 CONEXIÓN
def connect():
    iq = IQ_Option(EMAIL, PASSWORD)
    iq.connect()
    iq.change_balance("PRACTICE")
    return iq

# 📥 DATOS
def get_df(iq, par):
    datos = iq.get_candles(par, TIMEFRAME_M1, 40, time.time())
    df = pd.DataFrame(datos)
    df.rename(columns={"max": "high", "min": "low"}, inplace=True)
    return df

# 🚀 EJECUCIÓN
def ejecutar(iq, par, tipo):
    estado, id_op = iq.buy(BASE_AMOUNT, par, tipo, EXPIRATION)
    return estado, id_op

# 🧠 LOOP
def main():
    global BOT_RUNNING

    threading.Thread(target=listen_commands, daemon=True).start()
    iq = connect()

    while True:
        try:
            if not BOT_RUNNING:
                time.sleep(1)
                continue

            reset_day()

            for par in PARES_TODOS_OTC:
                df = get_df(iq, par)

                señal = get_reversal_signal(
                    df,
                    TOLERANCIA_NIVEL,
                    VENTANA_NIVELES,
                    CONFIRMAR_TENDENCIA
                )

                if señal:
                    tipo, fuerza, msg = señal

                    if fuerza >= FUERZA_MINIMA:
                        send(f"🚀 {par} | {tipo} | {fuerza}")

                        estado, _ = ejecutar(iq, par, tipo)

                        if estado:
                            send("✅ OPERACIÓN EJECUTADA")
                        else:
                            send("❌ ERROR EJECUCIÓN")

                        time.sleep(60)

            time.sleep(1)

        except Exception as e:
            send(f"💥 Error: {str(e)}")
            time.sleep(5)

# ▶️ INICIO
if __name__ == "__main__":
    main()
