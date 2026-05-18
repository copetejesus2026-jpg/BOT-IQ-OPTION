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
BASE_AMOUNT = 3590
MAX_TRADES_PER_CANDLE = 2

TIMEFRAME_M1 = 60
TIMEFRAME_M5 = 300

BOT_ACTIVE = True
LAST_UPDATE_ID = None

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
        params = {"timeout": 1, "offset": LAST_UPDATE_ID}
        res = requests.get(url, params=params, timeout=3).json()

        if not res.get("result"):
            return

        for update in res["result"]:
            LAST_UPDATE_ID = update["update_id"] + 1

            message = update.get("message", {})
            text = message.get("text", "")

            if not text:
                continue

            if text.lower() == "/stop":
                BOT_ACTIVE = False
                send("⛔ BOT DETENIDO")

            elif text.lower() == "/start":
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
                print("✅ Conectado")
                send("🔥 BOT CONTRARIAN ACTIVO")
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

# ================= PREDICTIVO INVERTIDO =================
def pre_signal(df1, df5):
    try:
        last = df1.iloc[-1]
        prev = df1.iloc[-2]

        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]

        if range_ == 0:
            return None

        strength = body / range_

        m5_up = df5["close"].iloc[-1] > df5["close"].iloc[-3]
        m5_down = df5["close"].iloc[-1] < df5["close"].iloc[-3]

        # 🔁 INVERTIDO

        # rompe arriba → PUT
        if last["close"] > prev["high"] and strength > 0.6 and m5_up:
            return "put"

        # rompe abajo → CALL
        if last["close"] < prev["low"] and strength > 0.6 and m5_down:
            return "call"

        return None

    except:
        return None

# ================= MAIN =================
def main():
    iq = connect()
    risk = RiskManager()

    last_candle = None
    cached_signals = []

    print("🔥 BOT CONTRARIAN SNIPER")

    while True:
        try:
            check_telegram_commands()

            if not BOT_ACTIVE:
                time.sleep(1)
                continue

            server_time = iq.get_server_timestamp()
            sec = server_time % 60

            # ANALIZA ANTES DE CIERRE
            if 50 <= sec <= 58:
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
                best = ranked[:5]

                for pair, _, df1, df5 in best:
                    signal = pre_signal(df1, df5)
                    if signal:
                        cached_signals.append((pair, signal))

            # ENTRADA
            if sec >= 59.7 or sec <= 0.2:
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
                        msg = f"⚡ CONTRARIAN {pair} {signal.upper()}"
                        print(msg)
                        send(msg)
                        trades += 1
                        risk.register_trade()

                    if trades >= MAX_TRADES_PER_CANDLE:
                        break

                print(f"🚀 Trades: {trades}")

            time.sleep(0.05)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
