import time
import os
import requests
import pandas as pd
from iqoptionapi.stable_api import IQ_Option
from strategy import get_reversal_signal

# ==============================
# CONFIGURACIÓN
# ==============================

EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")

RIESGO_POR_TRADE = 0.02  # 2% del balance
EXPIRACION = 1

PARES = ["EURUSD-OTC", "GBPUSD-OTC"]

# ==============================
# TELEGRAM
# ==============================

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send(msg):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg}
            )
        except:
            pass

# ==============================
# CONEXIÓN
# ==============================

def connect():
    iq = IQ_Option(EMAIL, PASSWORD)
    iq.connect()
    iq.change_balance("PRACTICE")
    return iq

# ==============================
# DATOS
# ==============================

def get_df(iq, par):
    data = iq.get_candles(par, 60, 50, time.time())
    df = pd.DataFrame(data)
    df.rename(columns={"max": "high", "min": "low"}, inplace=True)
    return df

# ==============================
# CALCULAR MONTO DINÁMICO
# ==============================

def calcular_monto(iq):
    balance = iq.get_balance()
    monto = balance * RIESGO_POR_TRADE
    return round(monto, 2)

# ==============================
# MAIN
# ==============================

def main():
    iq = connect()
    send("🤖 BOT PROFESIONAL ACTIVADO")

    ultima_vela = None

    while True:
        try:
            tiempo = iq.get_server_timestamp()
            segundos = int(tiempo % 60)
            vela = int(tiempo // 60)

            # SOLO EN SEGUNDO 0-2
            if 0 <= segundos <= 2 and vela != ultima_vela:
                ultima_vela = vela

                for par in PARES:

                    df = get_df(iq, par)
                    señal = get_reversal_signal(df)

                    if señal:
                        tipo, fuerza, motivo = señal

                        monto = calcular_monto(iq)

                        send(f"""🚀 ENTRADA PRO
Par: {par}
Tipo: {tipo}
Fuerza: {fuerza}
Monto: ${monto}""")

                        iq.buy(monto, par, tipo, EXPIRACION)

                        time.sleep(60)

            time.sleep(0.5)

        except Exception as e:
            send(f"💥 Error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()
