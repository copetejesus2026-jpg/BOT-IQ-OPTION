import time
import os
import requests
import pandas as pd
import sys
import logging

from iqoptionapi.stable_api import IQ_Option
from strategy import get_signal
from risk import RiskManager

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXPIRATION = 5
BASE_AMOUNT = 470

TIMEFRAME_M5 = 300

BOT_ACTIVE = True
LAST_UPDATE_ID = None

LOSS_STREAK = 0
MAX_LOSSES = 3
COOLDOWN_TIME = 300
STOP_UNTIL = 0

PAIR = "EURUSD"

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
    global BOT_ACTIVE, LAST_UPDATE_ID, LOSS_STREAK

    if not TOKEN:
        return

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        params = {"timeout": 1}

        if LAST_UPDATE_ID:
            params["offset"] = LAST_UPDATE_ID

        res = requests.get(url, params=params, timeout=3).json()

        for upd in res.get("result", []):
            LAST_UPDATE_ID = upd["update_id"] + 1
            text = upd.get("message", {}).get("text", "").lower()

            if text == "/stop":
                BOT_ACTIVE = False
                send("⛔ BOT DETENIDO")

            elif text == "/start":
                BOT_ACTIVE = True
                LOSS_STREAK = 0
                send("✅ BOT ACTIVADO")

    except:
        pass


# ================= CONEXIÓN =================
def connect():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            status, _ = iq.connect()

            if status:
                iq.change_balance("PRACTICE")
                send("🔥 BOT CONTINUACIÓN ACTIVO")
                return iq
        except:
            pass

        time.sleep(3)


# ================= DATA =================
def get_df(iq):
    try:
        data = iq.get_candles(PAIR, TIMEFRAME_M5, 120, time.time())
        df = pd.DataFrame(data)

        if df.empty:
            return None

        df.rename(columns={"max": "high", "min": "low"}, inplace=True)
        return df

    except:
        return None


# ================= MAIN =================
def main():
    global LOSS_STREAK, STOP_UNTIL

    iq = connect()
    risk = RiskManager()

    last_candle = None

    while True:
        try:
            check_telegram()

            now = time.time()

            if now < STOP_UNTIL:
                time.sleep(1)
                continue

            if not BOT_ACTIVE:
                time.sleep(1)
                continue

            server_time = iq.get_server_timestamp()
            candle = int(server_time // 300)

            if candle == last_candle:
                time.sleep(1)
                continue

            last_candle = candle

            df = get_df(iq)

            if df is None:
                continue

            signal = get_signal(df, df)

            if signal and risk.can_trade():

                status, trade_id = iq.buy(BASE_AMOUNT, PAIR, signal, EXPIRATION)

                if status:
                    send(f"⚡ EURUSD {signal.upper()}")

                    time.sleep(EXPIRATION * 60 + 2)
                    result = iq.check_win_v4(trade_id)

                    if result < 0:
                        LOSS_STREAK += 1
                        send(f"❌ LOSS ({LOSS_STREAK})")

                        if LOSS_STREAK >= MAX_LOSSES:
                            STOP_UNTIL = time.time() + COOLDOWN_TIME
                            LOSS_STREAK = 0
                            send("🛑 PAUSA POR RACHA")

                    else:
                        LOSS_STREAK = 0
                        send("✅ WIN")

            time.sleep(1)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)


if __name__ == "__main__":
    main()
