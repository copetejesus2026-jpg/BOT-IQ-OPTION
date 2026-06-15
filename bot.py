import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import threading
import logging
from datetime import datetime, timezone
from iqoptionapi.stable_api import IQ_Option

logging.basicConfig(level=logging.INFO)

# =========================================================
# 🔥 ESTRATEGIA INTEGRADA (SIN IMPORT)
# =========================================================

def body(c):
    return abs(c["close"] - c["open"])

def range_c(c):
    return c["high"] - c["low"]

def bullish(c):
    return c["close"] > c["open"]

def bearish(c):
    return c["close"] < c["open"]

def get_reversal_signal(df, *args):

    if len(df) < 40:
        return None

    df = df.copy()

    df['ema5'] = df['close'].ewm(span=5).mean()
    df['ema8'] = df['close'].ewm(span=8).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(5).mean()
    avg_loss = loss.rolling(5).mean().replace(0, 0.001)

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    c1 = df.iloc[-1]
    c2 = df.iloc[-2]

    fuerza = body(c1) / range_c(c1)

    if fuerza < 0.75:
        return None

    rsi = c1["rsi"]

    if bullish(c1) and rsi > 65:
        return None

    if bearish(c1) and rsi < 35:
        return None

    tendencia_alcista = df['ema5'].iloc[-1] > df['ema8'].iloc[-1] > df['ema21'].iloc[-1]
    tendencia_bajista = df['ema5'].iloc[-1] < df['ema8'].iloc[-1] < df['ema21'].iloc[-1]

    if tendencia_alcista and bullish(c1) and c1["close"] > c2["close"]:
        return ("call", 95, "FUERZA EXTREMA")

    if tendencia_bajista and bearish(c1) and c1["close"] < c2["close"]:
        return ("put", 95, "FUERZA EXTREMA")

    return None

# =========================================================
# CONFIG
# =========================================================

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PARES = ["EURUSD-OTC", "GBPUSD-OTC"]

# =========================================================
# TELEGRAM
# =========================================================

def send(msg):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg}
            )
        except:
            pass

# =========================================================
# CONEXIÓN
# =========================================================

def connect():
    iq = IQ_Option(EMAIL, PASSWORD)
    iq.connect()
    iq.change_balance("PRACTICE")
    return iq

# =========================================================
# DATOS
# =========================================================

def get_df(iq, par):
    data = iq.get_candles(par, 60, 50, time.time())
    df = pd.DataFrame(data)
    df.rename(columns={"max": "high", "min": "low"}, inplace=True)
    return df

# =========================================================
# MAIN
# =========================================================

def main():
    iq = connect()
    send("✅ BOT SIN ERRORES (Railway OK)")

    while True:
        try:
            for par in PARES:

                df = get_df(iq, par)

                señal = get_reversal_signal(df)

                if señal:
                    tipo, fuerza, _ = señal

                    send(f"🚀 {par} {tipo} {fuerza}")

                    iq.buy(100, par, tipo, 1)

                    time.sleep(60)

            time.sleep(1)

        except Exception as e:
            send(f"💥 Error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()
