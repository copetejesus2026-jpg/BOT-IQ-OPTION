import time
import os
import logging
import requests
import pandas as pd
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option

from strategy import StrategyPRO

logging.getLogger().setLevel(logging.CRITICAL)

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXPIRATION = 5
AMOUNT = 15000

M1 = 60
M5 = 300

PAIRS = [
    "EURUSD-OTC", "GBPUSD-OTC", "USDCHF-OTC", "EURGBP-OTC", "EURJPY-OTC",
    "GBPJPY-OTC", "AUDUSD-OTC", "USDCAD-OTC",
    "EURCAD-OTC", "GBPCAD-OTC", "AUDJPY-OTC", "CADJPY-OTC", "CHFJPY-OTC"
]

# ------------------------------------------------------------
#   ENVIAR MENSAJES A TELEGRAM
# ------------------------------------------------------------
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


# ------------------------------------------------------------
#   CONEXIÓN
# ------------------------------------------------------------
def connect():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            status, _ = iq.connect()
            if status:
                iq.change_balance("PRACTICE")
                send("🔥 BOT PRO INICIADO")
                return iq
        except:
            pass
        time.sleep(2)


# ------------------------------------------------------------
#   OBTENER DATOS
# ------------------------------------------------------------
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


# ------------------------------------------------------------
#   FILTRO DE VELAS MANIPULADAS
# ------------------------------------------------------------
def candle_ok(df):
    last = df.iloc[-1]

    body = abs(last["close"] - last["open"])
    total = last["high"] - last["low"]

    if total == 0:
        return False

    wick_up = last["high"] - max(last["close"], last["open"])
    wick_down = min(last["close"], last["open"]) - last["low"]

    if wick_up > body * 1.8 or wick_down > body * 1.8:
        return False

    if body < total * 0.25:
        return False

    return True


# ------------------------------------------------------------
#   ALGORITMO PRINCIPAL
# ------------------------------------------------------------
def main():
    iq = connect()
    strat = StrategyPRO()

    last_candle = None
    best_signal = None

    while True:
        try:
            server = iq.get_server_timestamp()
            sec = server % 60

            # Buscar señal entre 45s y 58s
            if 45 <= sec <= 58:

                best_score = 0
                best_pair = None
                final_signal = None

                for pair in PAIRS:

                    df1 = get_df(iq, pair, M1)
                    df5 = get_df(iq, pair, M5)
                    if df1 is None or df5 is None:
                        continue

                    if not candle_ok(df1):
                        continue

                    score = strat.score_market(df1, df5)
                    signal = strat.get_signal(df1, df5)

                    if signal and score > best_score:
                        best_score = score
                        best_pair = pair
                        final_signal = signal

                if best_pair:
                    best_signal = (best_pair, final_signal)

            # Ejecutar operación
            if 59.5 <= sec or sec <= 0.2:
                candle = int(server // 60)

                if candle == last_candle:
                    continue
                last_candle = candle

                if not best_signal:
                    continue

                pair, direction = best_signal

                op = "call" if direction == "call" else "put"

                status, trade_id = iq.buy(AMOUNT, pair, op, EXPIRATION)

                if status:
                    send(f"⚡ OPERACIÓN: {pair} → {op.upper()}")
                    time.sleep(70)
                    result = iq.check_win_v4(trade_id)

                    if result > 0:
                        send("✅ WIN")
                    else:
                        send("❌ LOSS")

            time.sleep(0.05)

        except Exception as e:
            print("Error:", e)
            time.sleep(1)


if __name__ == "__main__":
    main()
