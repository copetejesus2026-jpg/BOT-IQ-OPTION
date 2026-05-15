import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import logging

# ================= FIX IQ =================
try:
    from iqoptionapi.stable_api import IQ_Option
except ImportError:
    print("❌ iqoptionapi no está instalado")
    time.sleep(60)
    exit()

# ================= CONFIG =================

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TIMEFRAME = 60
EXPIRATION = 2
BASE_AMOUNT = 2000
MAX_LOSS_STREAK = 3

PAIRS = [
    "EURUSD-OTC",
    "GBPUSD-OTC",
    "EURJPY-OTC",
    "USDCHF-OTC",
    "AUDCAD-OTC"
]

# ================= VALIDACIONES =================

if not EMAIL or not PASSWORD:
    print("❌ Faltan credenciales IQ Option")
    time.sleep(60)
    exit()

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

# ================= CONEXIÓN IQ (MEJORADA) =================

def connect_iq():
    while True:
        try:
            print("🔌 Conectando a IQ Option...")

            iq = IQ_Option(EMAIL, PASSWORD)
            status, reason = iq.connect()

            if status:
                print("✅ Conectado a IQ Option")
                send("✅ Conectado a IQ Option")
                iq.change_balance("PRACTICE")
                return iq

            else:
                print("❌ Error conexión:", reason)
                send(f"❌ Error IQ: {reason}")

        except Exception as e:
            print("❌ Excepción:", e)

        print("🔁 Reintentando en 10 segundos...")
        time.sleep(10)

# ================= INICIAR =================

iq = connect_iq()

print("🔥 BOT ACTIVO")
send("🔥 BOT ACTIVO")

# ================= INDICADORES =================

def indicators(df):
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift()),
            abs(df["low"] - df["close"].shift())
        )
    )

    df["atr"] = df["tr"].rolling(14).mean()
    return df

# ================= DATOS =================

def get_candles(pair, tf):
    try:
        data = iq.get_candles(pair, tf, 100, time.time())
        df = pd.DataFrame(data)

        if df.empty:
            return None

        df.rename(columns={"max": "high", "min": "low"}, inplace=True)
        return indicators(df)

    except:
        return None

# ================= ESTRATEGIA =================

def sniper_pro(df_m1, df_m5):
    try:
        last = df_m1.iloc[-1]
        prev = df_m1.iloc[-2]

        trend_up = df_m5.iloc[-1]["ema20"] > df_m5.iloc[-1]["ema50"]
        trend_down = df_m5.iloc[-1]["ema20"] < df_m5.iloc[-1]["ema50"]

        if last["atr"] < df_m1["atr"].mean():
            return None

        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]

        if range_ == 0:
            return None

        strength = body / range_

        if (
            prev["close"] > prev["open"] and
            last["close"] < last["open"] and
            strength > 0.7 and
            last["close"] < prev["low"] and
            trend_down
        ):
            return "put"

        if (
            prev["close"] < prev["open"] and
            last["close"] > last["open"] and
            strength > 0.7 and
            last["close"] > prev["high"] and
            trend_up
        ):
            return "call"

        return None

    except:
        return None

# ================= TRADE =================

trade_open = False
last_trade_time = 0
last_trade_candle = None

def trade(pair, direction):
    global trade_open, last_trade_time

    try:
        status, _ = iq.buy(BASE_AMOUNT, pair, direction, EXPIRATION)

        if status:
            trade_open = True
            last_trade_time = time.time()

            msg = f"🎯 {pair} {direction.upper()}"
            print(msg)
            send(msg)

    except Exception as e:
        print("Error trade:", e)

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

# ================= LOOP =================

while True:
    try:
        check_result()

        if trade_open:
            time.sleep(1)
            continue

        server_time = int(iq.get_server_timestamp())
        current_candle = server_time // 60

        if last_trade_candle == current_candle:
            time.sleep(1)
            continue

        for pair in PAIRS:

            df_m1 = get_candles(pair, 60)
            df_m5 = get_candles(pair, 300)

            if df_m1 is None or df_m5 is None:
                continue

            signal = sniper_pro(df_m1, df_m5)

            if signal:
                trade(pair, signal)
                last_trade_candle = current_candle
                break

        time.sleep(1)

    except Exception as e:
        print("Error loop:", e)
        time.sleep(2)
