import time
import os
import requests
import pandas as pd
import numpy as np
import sys
import threading
import logging

from datetime import datetime, timezone
from strategy import get_reversal_signal
from iqoptionapi.stable_api import IQ_Option

# =========================================================
# LOGS
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================================
# CONFIG
# =========================================================

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ACCOUNT_TYPE = "PRACTICE"

EXPIRATION = 1
BASE_AMOUNT = 600

TIMEFRAME_M1 = 60

# =========================================================
# PARES OTC
# =========================================================

PARES_TODOS_OTC = [

    "EURUSD-OTC",
    "GBPUSD-OTC",
    "EURGBP-OTC",
    "EURJPY-OTC",
    "AUDUSD-OTC",
    "USDCAD-OTC",
    "USDCHF-OTC",
    "EURCAD-OTC",
    "GBPCAD-OTC",
    "AUDJPY-OTC",
    "CADJPY-OTC",
    "GBPAUD-OTC",
    "AUDCAD-OTC",
    "AUDCHF-OTC",
    "EURAUD-OTC",
    "GBPCHF-OTC",
    "EURCHF-OTC"

]

# =========================================================
# CONTROL
# =========================================================

MAX_DAILY_TRADES = 35

MAX_LOSS_STREAK = 5

PAUSE_TIME = 900

FUERZA_MINIMA = 90

# =========================================================
# VARIABLES
# =========================================================

DAILY_TRADES = 0

CURRENT_DAY = datetime.now(timezone.utc).day

LOSS_STREAK = 0

LAST_LOSS = 0

BOT_RUNNING = False

ULTIMA_VELA_ANALIZADA = None

# =========================================================
# TELEGRAM
# =========================================================

def send(msg):

    if TOKEN and CHAT_ID:

        try:

            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={
                    "chat_id": CHAT_ID,
                    "text": msg,
                    "parse_mode": "HTML"
                },
                timeout=8
            )

        except Exception as e:

            logging.error(str(e))

# =========================================================
# COMANDOS
# =========================================================

def listen_commands():

    global BOT_RUNNING

    last_update_id = 0

    while True:

        try:

            response = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={
                    "offset": last_update_id + 1,
                    "timeout": 30
                },
                timeout=35
            )

            data = response.json()

            for update in data.get("result", []):

                last_update_id = update["update_id"]

                msg = update.get("message", {})

                text = msg.get("text", "").lower().strip()

                chat_id = str(msg.get("chat", {}).get("id", ""))

                if chat_id != str(CHAT_ID):
                    continue

                if text == "/start":

                    BOT_RUNNING = True

                    send(
                        "✅ <b>BOT ACTIVADO</b>\n"
                        "⚡ MODO QUANT\n"
                        "🎯 Entrada inmediata"
                    )

                elif text == "/stop":

                    BOT_RUNNING = False

                    send("🛑 BOT DETENIDO")

        except Exception as e:

            logging.error(str(e))

            time.sleep(1)

# =========================================================
# CONEXIÓN
# =========================================================

def connect():

    while True:

        try:

            iq = IQ_Option(EMAIL, PASSWORD)

            check, reason = iq.connect()

            if check:

                iq.change_balance(ACCOUNT_TYPE)

                balance = iq.get_balance()

                send(
                    f"✅ <b>CONECTADO</b>\n"
                    f"💰 ${balance:.2f}"
                )

                return iq

        except Exception as e:

            send(f"❌ Error conexión: {str(e)}")

        time.sleep(2)

# =========================================================
# DATAFRAME
# =========================================================

def get_df(iq, par):

    try:

        candles = iq.get_candles(
            par,
            TIMEFRAME_M1,
            50,
            time.time()
        )

        if not candles:
            return None

        df = pd.DataFrame(candles)

        df.rename(
            columns={
                "max": "high",
                "min": "low"
            },
            inplace=True
        )

        columnas = [
            "open",
            "close",
            "high",
            "low",
            "volume"
        ]

        df[columnas] = df[columnas].astype(float)

        return df

    except Exception:

        return None

# =========================================================
# EJECUTAR
# =========================================================

def ejecutar_operacion(iq, monto, par, direccion):

    try:

        estado, order_id = iq.buy(
            monto,
            par,
            direccion,
            EXPIRATION
        )

        return estado, order_id

    except Exception:

        return False, None

# =========================================================
# RESULTADO
# =========================================================

def verificar_resultado(iq, order_id):

    global LOSS_STREAK
    global LAST_LOSS

    time.sleep(65)

    try:

        resultado = iq.check_win_v4(order_id)

        if resultado is None:
            return

        # Corregir tuple
        if isinstance(resultado, tuple):

            resultado = resultado[0]

        resultado = float(resultado)

        if resultado > 0:

            LOSS_STREAK = 0

            send(
                f"✅ <b>WIN</b>\n"
                f"💰 +${resultado:.2f}"
            )

        else:

            LOSS_STREAK += 1

            LAST_LOSS = time.time()

            send(
                f"❌ <b>LOSS</b>\n"
                f"💸 -${abs(resultado):.2f}\n"
                f"📉 Racha: {LOSS_STREAK}/{MAX_LOSS_STREAK}"
            )

    except Exception as e:

        send(f"⚠️ Resultado: {str(e)}")

# =========================================================
# MAIN
# =========================================================

def main():

    global BOT_RUNNING
    global DAILY_TRADES
    global LOSS_STREAK
    global LAST_LOSS
    global ULTIMA_VELA_ANALIZADA

    threading.Thread(
        target=listen_commands,
        daemon=True
    ).start()

    iq = connect()

    send("🤖 BOT LISTO")

    while True:

        try:

            if not BOT_RUNNING:

                time.sleep(0.2)

                continue

            # =============================================
            # RECONEXIÓN
            # =============================================

            if not iq.check_connect():

                iq = connect()

            # =============================================
            # PAUSA POR RACHA
            # =============================================

            if LOSS_STREAK >= MAX_LOSS_STREAK:

                restante = int(
                    PAUSE_TIME - (time.time() - LAST_LOSS)
                )

                if restante > 0:

                    time.sleep(5)

                    continue

                else:

                    LOSS_STREAK = 0

            # =============================================
            # TIEMPO SERVIDOR
            # =============================================

            server_time = iq.get_server_timestamp()

            segundos = server_time % 60

            vela_actual = int(server_time // 60)

            # =============================================
            # ANALIZAR SOLO 1 VEZ POR VELA
            # =============================================

            if ULTIMA_VELA_ANALIZADA == vela_actual:

                time.sleep(0.005)

                continue

            ULTIMA_VELA_ANALIZADA = vela_actual

            mejor = None

            mayor_fuerza = 0

            # =============================================
            # BUSCAR MEJOR SEÑAL
            # =============================================

            for par in PARES_TODOS_OTC:

                df = get_df(iq, par)

                if df is None:
                    continue

                resultado = get_reversal_signal(df)

                if resultado is None:
                    continue

                direccion, fuerza, tipo = resultado

                if fuerza >= FUERZA_MINIMA:

                    if fuerza > mayor_fuerza:

                        mayor_fuerza = fuerza

                        mejor = (
                            par,
                            direccion,
                            fuerza,
                            tipo
                        )

            # =============================================
            # EJECUTAR INMEDIATAMENTE
            # =============================================

            if mejor is not None:

                par, direccion, fuerza, tipo = mejor

                send(
                    f"🚀 <b>ENTRADA INMEDIATA</b>\n"
                    f"💹 {par}\n"
                    f"📈 {direccion.upper()}\n"
                    f"💪 Fuerza: {fuerza}/100\n"
                    f"⏱️ {segundos:.2f}s\n"
                    f"📍 {tipo}"
                )

                estado, order_id = ejecutar_operacion(
                    iq,
                    BASE_AMOUNT,
                    par,
                    direccion
                )

                if estado:

                    DAILY_TRADES += 1

                    send(
                        f"✅ <b>OPERACIÓN ABIERTA</b>\n"
                        f"💰 ${BASE_AMOUNT}\n"
                        f"📊 {DAILY_TRADES}/{MAX_DAILY_TRADES}"
                    )

                    threading.Thread(
                        target=verificar_resultado,
                        args=(iq, order_id),
                        daemon=True
                    ).start()

                else:

                    send("❌ Error ejecución")

            time.sleep(0.005)

        except Exception as e:

            logging.exception("MAIN")

            send(f"💥 {str(e)}")

            time.sleep(1)

# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    variables = [

        "IQ_EMAIL",
        "IQ_PASSWORD",
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID"

    ]

    faltantes = [

        x for x in variables
        if not os.getenv(x)

    ]

    if faltantes:

        print("❌ Variables faltantes")

        sys.exit(1)

    main()
