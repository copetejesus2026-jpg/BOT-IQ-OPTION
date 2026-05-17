import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import logging

# ================= IQ =================
try:
    from iqoptionapi.stable_api import IQ_Option
except ImportError:
    print("❌ iqoptionapi no instalado")
    time.sleep(60)
    exit()

# ================= CONFIG =================

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXPIRATION = 1
BASE_AMOUNT = 3500
MAX_TRADES_PER_CANDLE = 2

PAIRS = [
    "EURUSD-OTC","GBPUSD-OTC","AUDUSD-OTC","USDCAD-OTC","USDCHF-OTC",
    "EURJPY-OTC","GBPJPY-OTC","AUDJPY-OTC","CADJPY-OTC","CHFJPY-OTC",
    "NZDJPY-OTC","EURAUD-OTC","EURGBP-OTC","EURCHF-OTC",
    "GBPAUD-OTC","GBPCHF-OTC","AUDCAD-OTC","NZDCAD-OTC"
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
                send("✅ Bot sin EMA conectado")
                return iq
        except:
            pass
        time.sleep(5)

iq = connect_iq()

print("🔥 BOT PRICE ACTION ACTIVO")
send("🔥 BOT PRICE ACTION ACTIVO")

# ================= INDICADORES =================

def indicators(df):
    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # ATR
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

def get_data(pair):
    try:
        data = iq.get_candles(pair, 60, 100, time.time())
        df = pd.DataFrame(data)

        if df.empty:
            return None

        df.rename(columns={"max": "high", "min": "low"}, inplace=True)

        return indicators(df)
    except:
        return None

# ================= ESTRATEGIA SIN EMA =================

def price_action_signal(df):
    try:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        # volatilidad
        if last["atr"] < df["atr"].mean():
            return None

        # fuerza de vela
        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]

        if range_ == 0:
            return None

        strength = body / range_

        if strength < 0.6:
            return None

        # ================= CALL =================
        if (
            last["close"] > prev["high"] and
            prev["close"] > prev2["close"] and
            last["rsi"] < 65
        ):
            return "call"

        # ================= PUT =================
        if (
            last["close"] < prev["low"] and
            prev["close"] < prev2["close"] and
            last["rsi"] > 35
        ):
            return "put"

        return None

    except:
        return None

# ================= TRADE =================

def execute_trade(pair, direction):
    try:
        status, _ = iq.buy(BASE_AMOUNT, pair, direction, EXPIRATION)

        if status:
            msg = f"🎯 {pair} {direction.upper()}"
            print(msg)
            send(msg)

    except:
        pass

# ================= TIMING =================

def wait_new_candle():
    while True:
        if int(iq.get_server_timestamp()) % 60 == 0:
            break
        time.sleep(0.2)

# ================= LOOP =================

last_candle = None

while True:
    try:
        wait_new_candle()

        candle = int(iq.get_server_timestamp() // 60)

        if candle == last_candle:
            continue

        last_candle = candle
        trades = 0

        for pair in PAIRS:

            df = get_data(pair)

            if df is None:
                continue

            signal = price_action_signal(df)

            if signal:
                execute_trade(pair, signal)
                trades += 1

            if trades >= MAX_TRADES_PER_CANDLE:
                break

        print(f"⏱ Trades ejecutados: {trades}")

    except Exception as e:
        print("Error:", e)
        time.sleep(2)
