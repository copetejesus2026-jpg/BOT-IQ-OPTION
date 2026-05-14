import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import logging

from iqoptionapi.stable_api import IQ_Option
from estrategia import add_indicators, sniper_pro

# =========================================================
# BOT IA SNIPER PRO DEMO - IQ OPTION
# =========================================================

# ================= CONFIG =================

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TIMEFRAME = 60
EXPIRATION = 1

# 🔥 IMPORTE DEMO
BASE_AMOUNT = 10

MAX_LOSS_STREAK = 3

PAIRS = [
    "EURUSD-OTC",
    "GBPUSD-OTC",
    "EURJPY-OTC",
    "USDCHF-OTC",
    "AUDCAD-OTC"
]

# ================= ESTADO =================

trade_open = False
last_trade_time = 0
last_trade_candle = None

loss_streak = 0

bot_active = True
last_update_id = None

# ================= TELEGRAM =================

def send(msg):

    try:

        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=5
        )

    except:
        pass


def check_commands():

    global bot_active
    global last_update_id

    try:

        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={
                "timeout": 1,
                "offset": last_update_id
            },
            timeout=5
        ).json()

        for result in response.get("result", []):

            last_update_id = result["update_id"] + 1

            if "message" not in result:
                continue

            text = result["message"].get("text", "").lower()

            # ================= STOP =================

            if text == "/stop":

                bot_active = False

                print("⛔ BOT DETENIDO")
                send("⛔ BOT DETENIDO")

            # ================= START =================

            elif text == "/start":

                bot_active = True

                print("✅ BOT ACTIVADO")
                send("✅ BOT ACTIVADO")

    except:
        pass

# ================= IQ OPTION =================

iq = IQ_Option(EMAIL, PASSWORD)

iq.connect()

if not iq.check_connect():

    print("❌ ERROR CONECTANDO IQ OPTION")
    exit()

# 🔥 CUENTA DEMO
iq.change_balance("PRACTICE")

print("🔥 BOT IA SNIPER PRO DEMO ACTIVO")
send("🔥 BOT IA SNIPER PRO DEMO ACTIVO")

# ================= DATOS =================

def get_candles(pair, tf):

    try:

        data = iq.get_candles(
            pair,
            tf,
            100,
            time.time()
        )

        df = pd.DataFrame(data)

        df.rename(
            columns={
                "max": "high",
                "min": "low"
            },
            inplace=True
        )

        return add_indicators(df)

    except:
        return None

# ================= TRADE =================

def trade(pair, direction):

    global trade_open
    global last_trade_time

    try:

        status, trade_id = iq.buy(
            BASE_AMOUNT,
            pair,
            direction,
            EXPIRATION
        )

        if status:

            trade_open = True
            last_trade_time = time.time()

            msg = (
                f"🎯 ENTRADA DEMO\n\n"
                f"PAR: {pair}\n"
                f"DIRECCIÓN: {direction.upper()}\n"
                f"IMPORTE: ${BASE_AMOUNT}\n"
                f"EXPIRACIÓN: {EXPIRATION}m"
            )

            print(msg)
            send(msg)

    except Exception as e:

        print("ERROR TRADE:", e)

# ================= RESULTADO =================

def check_result():

    global trade_open

    try:

        if not trade_open:
            return

        if time.time() - last_trade_time < 65:
            return

        trade_open = False

    except:

        trade_open = False

# ================= LOOP PRINCIPAL =================

while True:

    try:

        check_commands()

        # ================= BOT DETENIDO =================

        if not bot_active:

            time.sleep(1)
            continue

        # ================= RESULTADO =================

        check_result()

        # ================= OPERACIÓN ABIERTA =================

        if trade_open:

            time.sleep(1)
            continue

        server_time = int(iq.get_server_timestamp())

        current_candle = server_time // 60

        # evitar múltiples entradas
        if last_trade_candle == current_candle:

            time.sleep(1)
            continue

        # entrar últimos segundos
        if server_time % 60 < 57:

            time.sleep(0.2)
            continue

        # ================= ANALISIS =================

        for pair in PAIRS:

            df_m1 = get_candles(pair, 60)
            df_m5 = get_candles(pair, 300)

            if df_m1 is None or df_m5 is None:
                continue

            signal = sniper_pro(df_m1, df_m5)

            if signal:

                # protección pérdidas
                if loss_streak >= MAX_LOSS_STREAK:

                    send("🛑 STOP POR RACHAS")

                    time.sleep(120)

                    loss_streak = 0

                    break

                trade(pair, signal)

                last_trade_candle = current_candle

                break

        time.sleep(1)

    except Exception as e:

        print("ERROR LOOP:", e)

        time.sleep(1)
