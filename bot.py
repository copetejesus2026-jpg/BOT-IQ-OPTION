import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import logging

# ================= FIX IQ =================

try:
    from iqoptionapi.stable_api import IQ_Option
except ImportError:
    print("❌ iqoptionapi no está instalado")
    time.sleep(60)
    exit()

# ================= CONFIG =================

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TIMEFRAME = 60
EXPIRATION = 4
BASE_AMOUNT = 10000
MAX_LOSS_STREAK = 3

PAIRS = [
    "EURUSD-OTC",
    "GBPUSD-OTC",
    "EURJPY-OTC",
    "USDCHF-OTC",
    "AUDCAD-OTC"
]

# ================= VALIDACIONES =================

if not EMAIL or not PASSWORD:
    print("❌ Faltan credenciales IQ Option")
    time.sleep(60)
    exit()

# ================= TELEGRAM =================

def send(msg):
    if not TOKEN or not CHAT_ID:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=5
        )
    except:
        pass

# ================= CONEXIÓN IQ =================

def connect_iq():

    while True:

        try:
            print("🔌 Conectando a IQ Option...")

            iq = IQ_Option(EMAIL, PASSWORD)
            status, reason = iq.connect()

            if status:

                print("✅ Conectado a IQ Option")
                send("✅ Conectado a IQ Option")

                iq.change_balance("PRACTICE")

                return iq

            else:
                print("❌ Error conexión:", reason)
                send(f"❌ Error IQ: {reason}")

        except Exception as e:
            print("❌ Excepción:", e)

        print("🔁 Reintentando en 10 segundos...")
        time.sleep(10)

# ================= INICIAR =================

iq = connect_iq()

print("🔥 BOT ACTIVO")
send("🔥 BOT ACTIVO")

# ================= INDICADORES =================

def indicators(df):

    # EMA
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    # RSI
    delta = df["close"].diff()

    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, abs(delta), 0)

    avg_gain = pd.Series(gain).rolling(14).mean()
    avg_loss = pd.Series(loss).rolling(14).mean()

    rs = avg_gain / avg_loss

    df["rsi"] = 100 - (100 / (1 + rs))

    # ATR
    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift()),
            abs(df["low"] - df["close"].shift())
        )
    )

    df["atr"] = df["tr"].rolling(14).mean()

    return df

# ================= DATOS =================

def get_candles(pair, tf):

    try:

        data = iq.get_candles(pair, tf, 250, time.time())

        df = pd.DataFrame(data)

        if df.empty:
            return None

        df.rename(columns={
            "max": "high",
            "min": "low"
        }, inplace=True)

        return indicators(df)

    except:
        return None

# ================= SOPORTE / RESISTENCIA =================

def support_resistance(df):

    recent = df.tail(30)

    support = recent["low"].min()
    resistance = recent["high"].max()

    return support, resistance

# ================= RECHAZO DE VELA =================

def candle_rejection(candle):

    body = abs(candle["close"] - candle["open"])

    upper_wick = candle["high"] - max(candle["close"], candle["open"])
    lower_wick = min(candle["close"], candle["open"]) - candle["low"]

    total = candle["high"] - candle["low"]

    if total == 0:
        return None

    # rechazo alcista
    if lower_wick > body * 2:
        return "bullish"

    # rechazo bajista
    if upper_wick > body * 2:
        return "bearish"

    return None

# ================= FILTRO TENDENCIA =================

def trend_filter(df_m5):

    last = df_m5.iloc[-1]

    bullish = (
        last["ema20"] > last["ema50"] > last["ema200"]
    )

    bearish = (
        last["ema20"] < last["ema50"] < last["ema200"]
    )

    if bullish:
        return "up"

    if bearish:
        return "down"

    return None

# ================= ESTRATEGIA MEJORADA =================

def sniper_pro(df_m1, df_m5):

    try:

        last = df_m1.iloc[-1]
        prev = df_m1.iloc[-2]

        trend = trend_filter(df_m5)

        if trend is None:
            return None

        # ================= VOLATILIDAD =================

        current_atr = last["atr"]
        avg_atr = df_m1["atr"].tail(20).mean()

        if current_atr < avg_atr:
            return None

        # ================= SOPORTE Y RESISTENCIA =================

        support, resistance = support_resistance(df_m5)

        price = last["close"]

        near_support = abs(price - support) <= current_atr * 0.5
        near_resistance = abs(price - resistance) <= current_atr * 0.5

        # ================= RECHAZO =================

        rejection = candle_rejection(last)

        # ================= FUERZA VELA =================

        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]

        if range_ == 0:
            return None

        strength = body / range_

        # ================= COMPRA =================

        bullish_breakout = (
            last["close"] > prev["high"]
        )

        bullish_conditions = [

            trend == "up",
            near_support,
            rejection == "bullish",
            last["rsi"] > 50,
            strength > 0.5,
            bullish_breakout
        ]

        if all(bullish_conditions):
            return "call"

        # ================= VENTA =================

        bearish_breakout = (
            last["close"] < prev["low"]
        )

        bearish_conditions = [

            trend == "down",
            near_resistance,
            rejection == "bearish",
            last["rsi"] < 50,
            strength > 0.5,
            bearish_breakout
        ]

        if all(bearish_conditions):
            return "put"

        return None

    except:
        return None

# ================= CONTROL OPERACIONES =================

trade_open = False
last_trade_time = 0
last_trade_candle = None
loss_streak = 0

# ================= TRADE =================

def trade(pair, direction):

    global trade_open
    global last_trade_time

    try:

        status, trade_id = iq.buy(
            BASE_AMOUNT,
            pair,
            direction,
            EXPIRATION
        )

        if status:

            trade_open = True
            last_trade_time = time.time()

            msg = f"🎯 ENTRADA\n\n📊 {pair}\n📈 {direction.upper()}\n💰 ${BASE_AMOUNT}"

            print(msg)
            send(msg)

        else:
            print("❌ Error ejecutando trade")

    except Exception as e:
        print("Error trade:", e)

# ================= RESULTADOS =================

def check_result():

    global trade_open
    global loss_streak

    try:

        if not trade_open:
            return

        if time.time() - last_trade_time < 65:
            return

        trade_open = False

    except:
        trade_open = False

# ================= VERIFICAR CONEXIÓN =================

def reconnect():

    global iq

    try:

        if not iq.check_connect():

            print("🔄 Reconectando...")

            send("🔄 Reconectando IQ Option...")

            iq = connect_iq()

    except:
        iq = connect_iq()

# ================= LOOP PRINCIPAL =================

while True:

    try:

        reconnect()

        check_result()

        if trade_open:
            time.sleep(1)
            continue

        server_time = int(iq.get_server_timestamp())

        current_candle = server_time // 60

        # evitar múltiples entradas misma vela
        if last_trade_candle == current_candle:
            time.sleep(1)
            continue

        for pair in PAIRS:

            print(f"🔍 Analizando {pair}")

            # ================= DATOS =================

            df_m1 = get_candles(pair, 60)
            df_m5 = get_candles(pair, 300)

            if df_m1 is None or df_m5 is None:
                continue

            # ================= ESTRATEGIA =================

            signal = sniper_pro(df_m1, df_m5)

            # ================= ENTRADA =================

            if signal:

                trade(pair, signal)

                last_trade_candle = current_candle

                break

        time.sleep(1)

    except Exception as e:

        print("❌ Error loop:", e)

        time.sleep(2)
