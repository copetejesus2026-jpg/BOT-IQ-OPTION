import time
import os
import requests
import pandas as pd
import logging
from iqoptionapi.stable_api import IQ_Option

from strategy import get_reversal_signal

# ==============================
# CONFIG LOGS
# ==============================
logging.basicConfig(level=logging.INFO)

# ==============================
# CONFIGURACIÓN
# ==============================
EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")

BASE_AMOUNT = 600
EXPIRATION = 1
TIMEFRAME = 60

# ENTRADA SNIPER (APERTURA)
ENTRY_START = 0
ENTRY_END = 2

MIN_FORCE = 98

PARES = [
    "EURUSD-OTC",
    "GBPUSD-OTC",
    "USDJPY-OTC",
    "EURJPY-OTC",
    "GBPJPY-OTC"
]

# ==============================
# VARIABLES
# ==============================
iq = None
SEÑAL = None
ULTIMA_VELA = None

# ==============================
# CONEXIÓN
# ==============================
def connect():
    global iq
    iq = IQ_Option(EMAIL, PASSWORD)
    iq.connect()

    if iq.check_connect():
        iq.change_balance("PRACTICE")
        print("✅ Conectado correctamente")
    else:
        print("❌ Error conexión")
        exit()

# ==============================
# DATAFRAME
# ==============================
def get_df(par):
    candles = iq.get_candles(par, TIMEFRAME, 50, time.time())
    df = pd.DataFrame(candles)

    df.rename(columns={
        "max": "high",
        "min": "low"
    }, inplace=True)

    return df

# ==============================
# EJECUTAR OPERACIÓN
# ==============================
def ejecutar(par, direccion):
    estado, id_op = iq.buy(BASE_AMOUNT, par, direccion, EXPIRATION)

    if estado:
        print(f"✅ OPERACIÓN: {direccion.upper()} {par}")
    else:
        print("❌ Error ejecución")

# ==============================
# LOOP PRINCIPAL
# ==============================
def run():
    global SEÑAL, ULTIMA_VELA

    connect()

    while True:
        try:
            server_time = iq.get_server_timestamp()
            segundos = server_time % 60
            vela = int(server_time // 60)

            # =========================
            # BUSCAR SEÑALES
            # =========================
            if 55 <= segundos <= 58:
                mejor = None

                for par in PARES:
                    df = get_df(par)

                    resultado = get_reversal_signal(df)

                    if resultado:
                        direccion, fuerza, tipo = resultado

                        if fuerza >= MIN_FORCE:
                            mejor = (par, direccion, fuerza, tipo)

                if mejor:
                    SEÑAL = mejor
                    print(f"🔍 Señal detectada {mejor}")

            # =========================
            # EJECUTAR SNIPER INVERTIDO
            # =========================
            if (
                SEÑAL
                and ENTRY_START <= segundos <= ENTRY_END
                and vela != ULTIMA_VELA
            ):
                ULTIMA_VELA = vela

                par, direccion, fuerza, tipo = SEÑAL
                SEÑAL = None

                # 🔁 INVERTIR SIEMPRE
                direccion = "put" if direccion == "call" else "call"

                print(f"🚀 SNIPER INVERTIDO | {par} | {direccion} | Fuerza: {fuerza}")

                ejecutar(par, direccion)

            time.sleep(0.2)

        except Exception as e:
            print(f"💥 Error: {e}")
            time.sleep(2)
            connect()

# ==============================
# START
# ==============================
if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("❌ Faltan credenciales")
    else:
        run()
