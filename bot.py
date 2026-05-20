import time
import os
import requests
import pandas as pd
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
BASE_AMOUNT = 4750
MAX_TRADES_PER_CANDLE = 1

TIMEFRAME_M1 = 60
TIMEFRAME_M5 = 300

# 🔥 SOLO LOS MEJORES
PAIRS = ["EURUSD-OTC", "GBPUSD-OTC"]

LOSS_STREAK = 0
MAX_LOSS_STREAK = 3
PAUSE_AFTER_LOSS = 180
LAST_LOSS_TIME = 0

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
                send("🔥 BOT PRO ACTIVO")
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
    global LOSS_STREAK, LAST_LOSS_TIME

    iq = connect()
    risk = RiskManager()

    last_candle = None
    cached_signal = None

    while True:
        try:
            # 🔥 PAUSA SI PIERDE MUCHO
            if LOSS_STREAK >= MAX_LOSS_STREAK:
                if time.time() - LAST_LOSS_TIME < PAUSE_AFTER_LOSS:
                    continue
                else:
                    LOSS_STREAK = 0

            server_time = iq.get_server_timestamp()
            sec = server_time % 60

            # 🔍 ANALISIS
            if 40 <= sec <= 55:
                cached_signal = None

                for pair in PAIRS:
                    df1 = get_df(iq, pair, TIMEFRAME_M1)
                    df5 = get_df(iq, pair, TIMEFRAME_M5)

                    if df1 is None or df5 is None:
                        continue

                    score = score_market(df1, df5)

                    if score < 4:
                        continue

                    signal = get_signal(df1, df5)

                    if signal:
                        cached_signal = (pair, signal)
                        break

            # 🎯 ENTRADA
            if sec >= 59.5 or sec <= 0.3:
                candle = int(server_time // 60)

                if candle == last_candle:
                    continue

                last_candle = candle

                if not cached_signal:
                    continue

                pair, signal = cached_signal

                if not risk.can_trade():
                    continue

                status, trade_id = iq.buy(BASE_AMOUNT, pair, signal, EXPIRATION)

                if status:
                    send(f"⚡ {pair} {signal.upper()}")
                    risk.register_trade()

                    time.sleep(65)
                    result = iq.check_win_v4(trade_id)

                    if result < 0:
                        LOSS_STREAK += 1
                        LAST_LOSS_TIME = time.time()
                        send(f"❌ LOSS {LOSS_STREAK}")
                    else:
                        LOSS_STREAK = 0
                        send("✅ WIN")

            time.sleep(0.05)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
