import time
import os
import requests
import pandas as pd
import sys
import logging
from datetime import datetime

from iqoptionapi.stable_api import IQ_Option
from strategy import get_signal

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")

EXPIRATION = 1
BASE_AMOUNT = 15000

TIMEFRAME_M1 = 60
TIMEFRAME_M5 = 300

MAX_TRADES_DAY = 4
MAX_LOSS_STREAK = 2

DAILY_TRADES = 0
LOSS_STREAK = 0
CURRENT_DAY = datetime.now().day

PAIRS = ["EURUSD-OTC","GBPUSD-OTC","USDCHF-OTC"]

# ================= CONEXION =================

def connect():
    while True:
        iq = IQ_Option(EMAIL, PASSWORD)
        status, _ = iq.connect()

        if status:
            iq.change_balance("PRACTICE")
            return iq

        time.sleep(3)

# ================= DATA =================

def get_df(iq, pair, tf):
    data = iq.get_candles(pair, tf, 120, time.time())
    df = pd.DataFrame(data)

    if df.empty:
        return None

    df.rename(columns={"max": "high", "min": "low"}, inplace=True)
    return df

# ================= MAIN =================

def main():
    global DAILY_TRADES, LOSS_STREAK, CURRENT_DAY

    iq = connect()

    while True:
        try:
            # reset diario
            if datetime.now().day != CURRENT_DAY:
                DAILY_TRADES = 0
                LOSS_STREAK = 0
                CURRENT_DAY = datetime.now().day

            if DAILY_TRADES >= MAX_TRADES_DAY:
                time.sleep(10)
                continue

            if LOSS_STREAK >= MAX_LOSS_STREAK:
                print("⛔ STOP POR RACHA PERDEDORA")
                time.sleep(30)
                continue

            for pair in PAIRS:

                df1 = get_df(iq, pair, TIMEFRAME_M1)
                df5 = get_df(iq, pair, TIMEFRAME_M5)

                if df1 is None or df5 is None:
                    continue

                signal = get_signal(df1, df5)

                if signal:

                    status, trade_id = iq.buy(BASE_AMOUNT, pair, signal, EXPIRATION)

                    if status:
                        DAILY_TRADES += 1
                        print(f"TRADE {pair} {signal}")

                        time.sleep(65)

                        result = iq.check_win_v3(trade_id)

                        if result < 0:
                            LOSS_STREAK += 1
                        else:
                            LOSS_STREAK = 0

            time.sleep(1)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
