import time
import os
import sys
import logging
from datetime import datetime
import pandas as pd
from iqoptionapi.stable_api import IQ_Option

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")

PAIRS = ["EURUSD-OTC", "EURGBP-OTC", "EURJPY-OTC"]

# ===============================================================
# =============  ARCHIVO COMPLETO CON LA ESTRATEGIA  ============
# ===============================================================

def pro_signal(df):
    df = df.copy()

    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]
    c4 = df.iloc[-4]
    c5 = df.iloc[-5]

    bodies = abs(df['open'] - df['close'])
    avg_body = bodies.tail(20).mean()

    wicks_up = abs(df['high'] - df[['open', 'close']].max(axis=1))
    wicks_down = abs(df[['open', 'close']].min(axis=1) - df['low'])

    support = df['low'].tail(40).min()
    resistance = df['high'].tail(40).max()

    last_dir = "bull" if c1['close'] > c1['open'] else "bear"

    breakout_up = c1['close'] > resistance
    breakout_down = c1['close'] < support

    strong_bull = (
        (c1['close'] > c1['open']) and
        (abs(c1['close'] - c1['open']) > avg_body * 1.3) and
        (c2['close'] > c2['open'])
    )

    strong_bear = (
        (c1['close'] < c1['open']) and
        (abs(c1['open'] - c1['close']) > avg_body * 1.3) and
        (c2['close'] < c2['open'])
    )

    reject_low = (c1['close'] > c1['open']) and (c1['low'] <= support + (avg_body * 0.2))
    reject_high = (c1['close'] < c1['open']) and (c1['high'] >= resistance - (avg_body * 0.2))

    exhaustion_bull = (
        (c1['close'] < c1['open']) and
        (c2['close'] < c2['open']) and
        (c3['close'] < c3['open'])
    )

    exhaustion_bear = (
        (c1['close'] > c1['open']) and
        (c2['close'] > c2['open']) and
        (c3['close'] > c3['open'])
    )

    # ===================
    # Señales finales
    # ===================

    if reject_low and strong_bull:
        return "call"

    if breakout_up and strong_bull:
        return "call"

    if exhaustion_bear and reject_low:
        return "call"

    if reject_high and strong_bear:
        return "put"

    if breakout_down and strong_bear:
        return "put"

    if exhaustion_bull and reject_high:
        return "put"

    return None


# ===============================================================
# ======================  BOT PRINCIPAL  ========================
# ===============================================================

def connect():
    global API
    API = IQ_Option(EMAIL, PASSWORD)

    API.connect()
    API.change_balance("PRACTICE")

    if API.check_connect():
        print("🟢 Conectado correctamente")
    else:
        print("🔴 Error de conexión, reintentando…")
        time.sleep(3)
        connect()

def get_candles(pair):
    candles = API.get_candles(pair, 300, 160, time.time())
    df = pd.DataFrame(candles)
    df['time'] = pd.to_datetime(df['from'], unit='s')
    df['mid'] = (df['open'] + df['close']) / 2
    return df

def place_trade(pair, direction, amount=2):
    try:
        status, _ = API.buy(amount, pair, direction, 5)
        if status:
            print(f"🟩 Entrada ejecutada: {pair} {direction}")
        else:
            print("⚠️ Error ejecutando entrada")
    except:
        print("❌ ERROR al enviar la orden")

def start():
    connect()
    print("\n🔵 BOT INICIADO\n")

    while True:
        now = datetime.utcnow()
        sec = now.second

        if sec == 0:
            for pair in PAIRS:
                df = get_candles(pair)
                signal = pro_signal(df)

                if signal in ["call", "put"]:
                    place_trade(pair, signal)

            time.sleep(2)

        time.sleep(0.5)

start()
