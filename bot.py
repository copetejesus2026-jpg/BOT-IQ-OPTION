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
EXPIRATION = 1   # 🔥 mejor para sniper
BASE_AMOUNT = 10000

PAIRS = [
    "EURUSD-OTC",
    "GBPUSD-OTC",
    "USDZAR-OTC",
    "AUDUSD-OTC",
    "USDCAD-OTC",
    "USDCHF-OTC",
    "EURJPY-OTC",
    "GBPJPY-OTC"
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
            print("🔌 Conectando...")
            iq = IQ_Option(EMAIL, PASSWORD)
            status, reason = iq.connect()

            if status:
                print("✅ Conectado")
                send("✅ Bot conectado")
                iq.change_balance("PRACTICE")
                return iq
            else:
                print("❌", reason)

        except Exception as e:
            print("❌ Error:", e)

        time.sleep(5)

iq = connect_iq()

print("🔥 BOT SNIPER ACTIVO")
send("🔥 BOT SNIPER ACTIVO")

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

def get_data(pair):
    try:
        m1 = iq.get_candles(pair, 60, 100, time.time())
        m5 = iq.get_candles(pair, 300, 100, time.time())

        df1 = pd.DataFrame(m1)
        df5 = pd.DataFrame(m5)

        if df1.empty or df5.empty:
            return None, None

        df1.rename(columns={"max": "high", "min": "low"}, inplace=True)
        df5.rename(columns={"max": "high", "min": "low"}, inplace=True)

        return indicators(df1), indicators(df5)

    except:
        return None, None

# ================= ESTRATEGIA SNIPER =================

def sniper(df1, df5):
    try:
        last = df1.iloc[-1]
        prev = df1.iloc[-2]

        trend_up = df5.iloc[-1]["ema20"] > df5.iloc[-1]["ema50"]
        trend_down = df5.iloc[-1]["ema20"] < df5.iloc[-1]["ema50"]

        if last["atr"] < df1["atr"].mean():
            return None

        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]

        if range_ == 0:
            return None

        strength = body / range_

        # 🔴 PUT
        if (
            prev["close"] > prev["open"] and
            last["close"] < last["open"] and
            strength > 0.7 and
            last["close"] < prev["low"] and
            trend_down
        ):
            return "put"

        # 🟢 CALL
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

def execute_trade(pair, direction):
    try:
        status, _ = iq.buy(BASE_AMOUNT, pair, direction, EXPIRATION)

        if status:
            msg = f"🎯 {pair} {direction.upper()}"
            print(msg)
            send(msg)

    except Exception as e:
        print("Error trade:", e)

# ================= ESPERAR APERTURA EXACTA =================

def wait_new_candle():
    while True:
        server_time = iq.get_server_timestamp()
        if int(server_time) % 60 == 0:
            break
        time.sleep(0.2)

# ================= LOOP PRINCIPAL =================

last_candle = None

while True:
    try:
        wait_new_candle()

        current_candle = int(iq.get_server_timestamp() // 60)

        if current_candle == last_candle:
            continue

        last_candle = current_candle

        signals = []

        # 🔥 ANALIZA TODOS LOS PARES RÁPIDO
        for pair in PAIRS:
            df1, df5 = get_data(pair)

            if df1 is None:
                continue

            signal = sniper(df1, df5)

            if signal:
                signals.append((pair, signal))

        # 🔥 EJECUTA TODAS LAS SEÑALES (MULTIPAR)
        for pair, signal in signals:
            execute_trade(pair, signal)

        print(f"⏱ Nueva vela | señales: {len(signals)}")

    except Exception as e:
        print("Error:", e)
        time.sleep(2)
