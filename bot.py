import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import logging

from iqoptionapi.stable_api import IQ_Option
from strategy import get_signal, score_market
from risk import RiskManager

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXPIRATION = 1
BASE_AMOUNT = 3700
MAX_TRADES_PER_CANDLE = 2

TIMEFRAME_M1 = 60
TIMEFRAME_M5 = 300

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
def connect():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            status, reason = iq.connect()

            if status:
                iq.change_balance("PRACTICE")
                print("✅ Conectado")
                send("✅ Bot conectado")
                return iq
            else:
                print("❌ Error:", reason)

        except Exception as e:
            print("❌ Excepción:", e)

        time.sleep(5)

# ================= DATOS =================
def get_df(iq, pair, timeframe, n=120):
    try:
        data = iq.get_candles(pair, timeframe, n, time.time())
        df = pd.DataFrame(data)

        if df.empty:
            return None

        df.rename(columns={"max": "high", "min": "low"}, inplace=True)
        return df

    except:
        return None

# ================= TIMING =================
def wait_new_candle(iq):
    while True:
        if int(iq.get_server_timestamp()) % 60 == 0:
            break
        time.sleep(0.2)

# ================= MAIN =================
def main():
    iq = connect()
    risk = RiskManager()

    last_candle = None

    print("🔥 BOT ACTIVO")

    while True:
        try:
            wait_new_candle(iq)

            candle = int(iq.get_server_timestamp() // 60)

            if candle == last_candle:
                continue

            last_candle = candle

            ranked = []

            # 🔥 Ranking mercado
            for pair in PAIRS:
                df1 = get_df(iq, pair, TIMEFRAME_M1)
                df5 = get_df(iq, pair, TIMEFRAME_M5)

                if df1 is None or df5 is None:
                    continue

                score = score_market(df1, df5)
                ranked.append((pair, score, df1, df5))

            ranked.sort(key=lambda x: x[1], reverse=True)
            best_pairs = ranked[:5]

            trades = 0

            for pair, _, df1, df5 in best_pairs:

                if not risk.can_trade():
                    break

                signal = get_signal(df1, df5)

                if signal:
                    status, _ = iq.buy(BASE_AMOUNT, pair, signal, EXPIRATION)

                    if status:
                        msg = f"🎯 {pair} {signal.upper()}"
                        print(msg)
                        send(msg)
                        trades += 1
                        risk.register_trade()

                if trades >= MAX_TRADES_PER_CANDLE:
                    break

            print(f"⏱ Trades: {trades}")

        except Exception as e:
            print("❌ Error loop:", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
