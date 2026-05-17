import time, os, sys, logging
import pandas as pd
import numpy as np
import requests
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
BASE_AMOUNT = 3500
MAX_TRADES_PER_CANDLE = 2
TIMEFRAME_M1 = 60
TIMEFRAME_M5 = 300

PAIRS = [
    "EURUSD-OTC","GBPUSD-OTC","AUDUSD-OTC","USDCAD-OTC","USDCHF-OTC",
    "EURJPY-OTC","GBPJPY-OTC","AUDJPY-OTC","CADJPY-OTC","CHFJPY-OTC",
    "NZDJPY-OTC","EURAUD-OTC","EURGBP-OTC","EURCHF-OTC",
    "GBPAUD-OTC","GBPCHF-OTC","AUDCAD-OTC","NZDCAD-OTC"
]

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

def connect():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            ok, _ = iq.connect()
            if ok:
                iq.change_balance("PRACTICE")
                send("✅ Bot avanzado conectado")
                return iq
        except:
            pass
        time.sleep(5)

iq = connect()
risk = RiskManager(max_loss_streak=3, cooldown_sec=180)

def get_df(pair, tf, n=120):
    data = iq.get_candles(pair, tf, n, time.time())
    df = pd.DataFrame(data)
    if df.empty:
        return None
    df.rename(columns={"max":"high","min":"low"}, inplace=True)
    return df

def wait_new_candle():
    while True:
        if int(iq.get_server_timestamp()) % 60 == 0:
            break
        time.sleep(0.2)

last_candle = None

while True:
    try:
        wait_new_candle()
        candle = int(iq.get_server_timestamp() // 60)
        if candle == last_candle:
            continue
        last_candle = candle

        # Ranking de mercado
        ranked = []
        for p in PAIRS:
            df1 = get_df(p, TIMEFRAME_M1)
            df5 = get_df(p, TIMEFRAME_M5)
            if df1 is None or df5 is None:
                continue
            s = score_market(df1, df5)
            ranked.append((p, s, df1, df5))

        ranked.sort(key=lambda x: x[1], reverse=True)
        best = ranked[:5]

        trades = 0

        for pair, _, df1, df5 in best:
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
                    risk.register_trade(open_time=time.time())

            if trades >= MAX_TRADES_PER_CANDLE:
                break

        print(f"⏱ Trades ejecutados: {trades}")

    except Exception as e:
        print("Error:", e)
        time.sleep(2)
