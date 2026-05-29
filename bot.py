import time
import os
import sys
import logging
import requests
import pandas as pd

try:
    from iqoptionapi.stable_api import IQ_Option
except ImportError:
    print("❌ iqoptionapi no instalado")
    time.sleep(60)
    exit()

from strategy_pa import pro_signal   # ← ARCHIVO 2

# ================= CONFIGURACIÓN =================

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXPIRATION = 5   # ← ENTRADAS A 5 MIN
AMOUNT = 3500

PAIRS = [
    "EURUSD-OTC",
    "EURGBP-OTC",
    "EURJPY-OTC"
]

# ================= TELEGRAM =================

def send(msg):
    if not TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=5
        )
    except:
        pass

# ================= CONEXIÓN =================

def connect_iq():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            status, _ = iq.connect()
            if status:
                iq.change_balance("PRACTICE")
                send("✅ Bot Price Action conectado")
                return iq
        except:
            pass
        time.sleep(5)

iq = connect_iq()

print("🔥 BOT PRICE ACTION — SOLO PA · ESTRUCTURA DEL PRECIO")
send("🔥 BOT PRICE ACTION — SOLO PA · ESTRUCTURA DEL PRECIO")

# ================= OBTENER DATOS =================

def get_data(pair):
    try:
        data = iq.get_candles(pair, 60, 160, time.time())  # ← 160 VELAS
        df = pd.DataFrame(data)
        if df.empty:
            return None
        df.rename(columns={"max": "high", "min": "low"}, inplace=True)
        return df
    except:
        return None

# ================= TRADE =================

def execute(pair, direction):
    try:
        status, _ = iq.buy(AMOUNT, pair, direction, EXPIRATION)

        if status:
            msg = f"🎯 {pair} → {direction.upper()} (5M)"
            print(msg)
            send(msg)
    except:
        pass

# ================= ESPERA DE VELA NUEVA =================

def wait_new_candle():
    while True:
        if int(iq.get_server_timestamp()) % 60 == 0:
            break
        time.sleep(0.2)

# ================= LOOP PRINCIPAL =================

last_candle = None

while True:
    try:
        wait_new_candle()

        candle = int(iq.get_server_timestamp() // 60)

        if candle == last_candle:
            continue

        last_candle = candle

        print("\n⏱ Analizando pares...\n")

        for pair in PAIRS:

            df = get_data(pair)
            if df is None:
                continue

            signal = pro_signal(df)  # ← SOLO PRICE ACTION

            if signal:
                execute(pair, signal)

    except Exception as e:
        print("Error:", e)
        time.sleep(2)
