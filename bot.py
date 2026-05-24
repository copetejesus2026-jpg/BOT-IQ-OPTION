import time
import os
import requests
import pandas as pd
import sys
import logging
from datetime import datetime

from iqoptionapi.stable_api import IQ_Option
from strategy import get_signal, score_market
from risk import RiskManager

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXPIRATION = 2
BASE_AMOUNT = 20000

TIMEFRAME_M1 = 60
TIMEFRAME_M5 = 300
TIMEFRAME_M15 = 900

PAIRS = [
    "EURUSD-OTC","GBPUSD-OTC","USDCHF-OTC","EURGBP-OTC","EURJPY-OTC",
    "GBPJPY-OTC","AUDUSD-OTC","USDCAD-OTC","NZDUSD-OTC",
    "EURCAD-OTC","GBPCAD-OTC","AUDJPY-OTC","CADJPY-OTC","CHFJPY-OTC"
]

def send(msg):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg},
                timeout=3
            )
        except:
            pass

def connect():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            status, _ = iq.connect()
            if status:
                iq.change_balance("PRACTICE")
                send("🔥 BOT SNIPER ACTIVO")
                return iq
        except:
            pass
        time.sleep(3)

def get_df(iq, pair, tf):
    try:
        data = iq.get_candles(pair, tf, 120, time.time())
        df = pd.DataFrame(data)
        if df.empty:
            return None
        df.rename(columns={"max": "high", "min": "low"}, inplace=True)
        return df
    except:
        return None

def main():
    iq = connect()
    risk = RiskManager()

    last_candle = None
    signal = None

    while True:
        try:
            server_time = iq.get_server_timestamp()
            sec = server_time % 60

            # 🔍 ANALISIS
            if 45 <= sec <= 58:
                signal = None
                best_score = 0

                for pair in PAIRS:
                    df1 = get_df(iq, pair, TIMEFRAME_M1)
                    df5 = get_df(iq, pair, TIMEFRAME_M5)
                    df15 = get_df(iq, pair, TIMEFRAME_M15)

                    if df1 is None or df5 is None or df15 is None:
                        continue

                    score = score_market(df1, df5, df15)

                    if score < 6:
                        continue

                    s = get_signal(df1, df5, df15)

                    if s and score > best_score:
                        best_score = score
                        signal = (pair, s)

            # 🎯 ENTRADA
            if sec >= 59.5 or sec <= 0.3:
                candle = int(server_time // 60)

                if candle == last_candle:
                    continue

                last_candle = candle

                if not signal:
                    continue

                pair, direction = signal

                if not risk.can_trade():
                    continue

                status, trade_id = iq.buy(BASE_AMOUNT, pair, direction, EXPIRATION)

                if status:
                    send(f"🎯 {pair} {direction.upper()}")

                    risk.register_trade()

                    time.sleep(180)
                    result = iq.check_win_v4(trade_id)

                    if result > 0:
                        send("✅ WIN")
                    else:
                        send("❌ LOSS")

            time.sleep(0.05)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
