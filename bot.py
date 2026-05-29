import time
import os
import sys
import logging
import threading
from datetime import datetime
import pandas as pd
from iqoptionapi.stable_api import IQ_Option
import telebot

# ===============================================================
# CONFIGURACIÓN
# ===============================================================

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

PAIRS = ["EURUSD-OTC", "EURGBP-OTC", "EURJPY-OTC"]

RUNNING = False
API = None

# ===============================================================
# =============  ESTRATEGIA COMPLETA (PRO_SIGNAL)  ==============
# ===============================================================

def pro_signal(df):
    df = df.copy()

    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]

    bodies = abs(df['open'] - df['close'])
    avg_body = bodies.tail(20).mean()

    support = df['low'].tail(40).min()
    resistance = df['high'].tail(40).max()

    breakout_up = c1['close'] > resistance
    breakout_down = c1['close'] < support

    strong_bull = (c1['close'] > c1['open']) and (abs(c1['close']-c1['open']) > avg_body*1.3)
    strong_bear = (c1['close'] < c1['open']) and (abs(c1['open']-c1['close']) > avg_body*1.3)

    reject_low = (c1['low'] <= support + (avg_body*0.2)) and (c1['close'] > c1['open'])
    reject_high = (c1['high'] >= resistance - (avg_body*0.2)) and (c1['close'] < c1['open'])

    exhaustion_bull = (c1['close'] < c1['open']) and (c2['close'] < c2['open']) and (c3['close'] < c3['open'])
    exhaustion_bear = (c1['close'] > c1['open']) and (c2['close'] > c2['open']) and (c3['close'] > c3['open'])

    if reject_low and strong_bull:
        return "call"
    if breakout_up and strong_bull:
        return "call"
    if exhaustion_bear and reject_low:
        return "call"

    if reject_high and strong_bear:
        return "put"
    if breakout_down and strong_bear:
        return "put"
    if exhaustion_bull and reject_high:
        return "put"

    return None

# ===============================================================
# ======================  BOT PRINCIPAL  ========================
# ===============================================================

def connect():
    global API
    API = IQ_Option(EMAIL, PASSWORD)

    API.connect()
    API.change_balance("PRACTICE")

    if API.check_connect():
        print("🟢 Conectado correctamente a IQ Option")
        bot.send_message(CHAT_ID, "🟢 Bot conectado a IQ Option")
    else:
        print("🔴 Error de conexión, reintentando…")
        bot.send_message(CHAT_ID, "🔴 Error de conexión, reintentando…")
        time.sleep(3)
        connect()

def get_candles(pair):
    candles = API.get_candles(pair, 300, 160, time.time())
    df = pd.DataFrame(candles)
    return df

def place_trade(pair, direction, amount=2):
    try:
        status, _ = API.buy(amount, pair, direction, 5)  # EXPIRACIÓN 5 MINUTOS

        if status:
            msg = f"🟩 Entrada ejecutada\n📌 {pair}\n📊 Dirección: {direction.upper()}\n⏱ Exp: 5 minutos"
            print(msg)
            bot.send_message(CHAT_ID, msg)
        else:
            print("⚠️ Error ejecutando entrada")
            bot.send_message(CHAT_ID, "⚠️ Error ejecutando entrada")

    except:
        print("❌ ERROR al enviar la orden")
        bot.send_message(CHAT_ID, "❌ ERROR al enviar la orden")

def run_bot():
    global RUNNING

    connect()
    bot.send_message(CHAT_ID, "🔵 BOT INICIADO")

    while RUNNING:
        now = datetime.utcnow()
        if now.second == 0:
            for pair in PAIRS:
                df = get_candles(pair)
                signal = pro_signal(df)

                if signal in ["call", "put"]:
                    place_trade(pair, signal)

            time.sleep(2)

        time.sleep(0.5)

    bot.send_message(CHAT_ID, "🔴 BOT DETENIDO")

# ===============================================================
# ======================  COMANDOS TELEGRAM  ====================
# ===============================================================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    global RUNNING

    if RUNNING:
        bot.send_message(CHAT_ID, "⚠️ El bot ya está activo")
        return

    RUNNING = True
    bot.send_message(CHAT_ID, "🟢 Bot iniciado")

    t = threading.Thread(target=run_bot)
    t.start()

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    global RUNNING
    RUNNING = False
    bot.send_message(CHAT_ID, "🛑 Bot detenido")

# ===============================================================
# ========================  INICIAR BOT  ========================
# ===============================================================

print("🤖 Bot de trading listo")
bot.infinity_polling()
