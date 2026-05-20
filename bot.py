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
MAX_TRADES_PER_CANDLE = 2

TIMEFRAME_M1 = 60
TIMEFRAME_M5 = 300

BOT_ACTIVE = True
LAST_UPDATE_ID = None

PAIR_COOLDOWN = {}

PAIRS = [
    "EURUSD-OTC","GBPUSD-OTC","USDCHF-OTC","AUDUSD-OTC",
    "USDCAD-OTC","EURGBP-OTC","EURJPY-OTC","EURAUD-OTC",
    "EURCHF-OTC","EURNZD-OTC","GBPJPY-OTC","GBPCHF-OTC"
]

# ================= TELEGRAM =================
def send(msg):
    if not TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=3
        )
    except:
        pass


def check_telegram_commands():
    global BOT_ACTIVE, LAST_UPDATE_ID

    if not TOKEN:
        return

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        params = {"timeout": 1}

        if LAST_UPDATE_ID:
            params["offset"] = LAST_UPDATE_ID

        res = requests.get(url, params=params, timeout=3).json()

        for update in res.get("result", []):
            LAST_UPDATE_ID = update["update_id"] + 1

            message = update.get("message", {})
            text = message.get("text", "")

            if not text:
                continue

            text = text.lower()

            if text == "/stop":
                BOT_ACTIVE = False
                send("⛔ BOT DETENIDO")

            elif text == "/start":
                BOT_ACTIVE = True
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
                send("🔥 BOT PRO ACTIVO")
                return iq
        except:
            pass

        time.sleep(3)


# ================= DATOS =================
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
    iq = connect()
    risk = RiskManager()

    last_candle = None
    cached_signals = []

    while True:
        try:
            check_telegram_commands()

            if not BOT_ACTIVE:
                time.sleep(1)
                continue

            server_time = iq.get_server_timestamp()
            sec = server_time % 60

            # ================= ANALISIS =================
            if 45 <= sec <= 55:
                cached_signals.clear()
                ranked = []

                for pair in PAIRS:
                    df1 = get_df(iq, pair, TIMEFRAME_M1)
                    df5 = get_df(iq, pair, TIMEFRAME_M5)

                    if df1 is None or df5 is None:
                        continue

                    score = score_market(df1, df5)
                    ranked.append((pair, score, df1, df5))

                ranked.sort(key=lambda x: x[1], reverse=True)
                best = ranked[:3]

                for pair, _, df1, df5 in best:

                    last_trade = PAIR_COOLDOWN.get(pair, 0)
                    if time.time() - last_trade < 120:
                        continue

                    signal = get_signal(df1, df5)

                    if signal:
                        cached_signals.append((pair, signal))

            # ================= ENTRADA =================
            if sec >= 59.5 or sec <= 0.3:
                candle = int(server_time // 60)

                if candle == last_candle:
                    continue

                last_candle = candle
                trades = 0

                for pair, signal in cached_signals:

                    if not risk.can_trade():
                        break

                    status, _ = iq.buy(BASE_AMOUNT, pair, signal, EXPIRATION)

                    if status:
                        send(f"⚡ {pair} {signal.upper()}")
                        PAIR_COOLDOWN[pair] = time.time()
                        trades += 1
                        risk.register_trade()

                    if trades >= MAX_TRADES_PER_CANDLE:
                        break

                print(f"Trades: {trades}")

            time.sleep(0.05)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)


if __name__ == "__main__":
    main()
