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

EXPIRATION = 3
BASE_AMOUNT = 7000

TIMEFRAME_M1 = 60
TIMEFRAME_M5 = 300
TIMEFRAME_M15 = 900

PAIRS = [
    "EURUSD-OTC","GBPUSD-OTC","USDCHF-OTC","EURGBP-OTC","EURJPY-OTC",
    "GBPJPY-OTC","USDJPY-OTC","AUDUSD-OTC","USDCAD-OTC","NZDUSD-OTC",
    "EURCAD-OTC","GBPCAD-OTC","AUDJPY-OTC","CADJPY-OTC","CHFJPY-OTC"
]

BOT_RUNNING = True
LAST_UPDATE_ID = None

# ================= TELEGRAM =================

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

def check_telegram():
    global BOT_RUNNING, LAST_UPDATE_ID

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        params = {"offset": LAST_UPDATE_ID}
        res = requests.get(url, params=params).json()

        for update in res.get("result", []):
            LAST_UPDATE_ID = update["update_id"] + 1

            if "message" in update:
                text = update["message"].get("text", "").lower()
                chat = str(update["message"]["chat"]["id"])

                if chat != str(CHAT_ID):
                    continue

                if text == "/stop":
                    BOT_RUNNING = False
                    send("🛑 BOT DETENIDO")

                elif text == "/start":
                    BOT_RUNNING = True
                    send("🚀 BOT ACTIVADO")

    except:
        pass

# ================= IQ =================

def connect():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            status, _ = iq.connect()
            if status:
                iq.change_balance("PRACTICE")
                send("🔥 BOT ACTIVO")
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

# ================= MAIN =================

def main():
    global BOT_RUNNING

    iq = connect()
    risk = RiskManager()

    last_candle = None
    signal = None

    while True:
        try:
            check_telegram()

            if not BOT_RUNNING:
                time.sleep(1)
                continue

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
                    # 🔥 MENSAJE PRO
                    tipo = "COMPRA" if direction == "call" else "VENTA"
                    send(f"🎯 {pair} {tipo} 3 MINUTOS")

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
