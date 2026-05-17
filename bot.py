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

EXPIRATION = 1
BASE_AMOUNT = 3579
MAX_TRADES_PER_CANDLE = 2   # 🔥 más precisión

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
                send("✅ Bot SMART conectado")
                return iq
        except:
            pass
        time.sleep(5)

iq = connect_iq()

print("🔥 BOT SMART ACTIVO")
send("🔥 BOT SMART ACTIVO")

# ================= INDICADORES =================

def indicators(df):
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

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

# ================= FILTRO MERCADO =================

def market_score(df1, df5):
    try:
        atr = df1["atr"].iloc[-1]
        atr_avg = df1["atr"].mean()

        ema_diff = abs(df5["ema20"].iloc[-1] - df5["ema50"].iloc[-1])

        # score = volatilidad + tendencia
        score = (atr / atr_avg) + (ema_diff * 10000)

        return score
    except:
        return 0

# ================= ESTRATEGIA =================

def sniper(df1, df5):
    try:
        last = df1.iloc[-1]
        prev = df1.iloc[-2]

        trend_up = df5.iloc[-1]["ema20"] > df5.iloc[-1]["ema50"]
        trend_down = df5.iloc[-1]["ema20"] < df5.iloc[-1]["ema50"]

        # ❌ evitar mercado lateral
        if abs(df5["ema20"].iloc[-1] - df5["ema50"].iloc[-1]) < 0.00005:
            return None

        # volatilidad
        if last["atr"] < df1["atr"].mean():
            return None

        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]

        if range_ == 0:
            return None

        strength = body / range_

        if strength < 0.6:
            return None

        # CALL
        if (
            trend_up and
            last["rsi"] < 70 and
            last["close"] > prev["high"]
        ):
            return "call"

        # PUT
        if (
            trend_down and
            last["rsi"] > 30 and
            last["close"] < prev["low"]
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

        ranked_pairs = []

        # 🔥 evaluar mercado
        for pair in PAIRS:
            df1, df5 = get_data(pair)

            if df1 is None:
                continue

            score = market_score(df1, df5)
            ranked_pairs.append((pair, score, df1, df5))

        # 🔥 elegir mejores pares
        ranked_pairs.sort(key=lambda x: x[1], reverse=True)
        best_pairs = ranked_pairs[:5]

        trades = 0

        for pair, _, df1, df5 in best_pairs:

            signal = sniper(df1, df5)

            if signal:
                execute_trade(pair, signal)
                trades += 1

            if trades >= MAX_TRADES_PER_CANDLE:
                break

        print(f"🔥 Mejores pares analizados: {len(best_pairs)} | Trades: {trades}")

    except Exception as e:
        print("Error:", e)
        time.sleep(2)
