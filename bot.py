import time
import os
import requests
import pandas as pd
import sys
import logging
import numpy as np
from datetime import datetime

from iqoptionapi.stable_api import IQ_Option

logging.getLogger().setLevel(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

# ==========================================
# 🔑 CONFIGURACIÓN DE CUENTA Y TELEGRAM
# ==========================================
EMAIL = os.getenv("IQ_EMAIL")
PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ⚙️ PARÁMETROS DE OPERACIÓN
EXPIRATION = 1                  # 1 Minuto (NO CAMBIAR)
BASE_AMOUNT = 3.33              # Monto por operación
TIMEFRAME_M1 = 60               # 1 Minuto
TIMEFRAME_M5 = 300              # 5 Minutos (filtro tendencia)

# 📋 ACTIVOS OTC (MERCADO EXACTO)
PAIRS = [
    "EURUSD-OTC", "GBPUSD-OTC", "USDCHF-OTC", 
    "EURGBP-OTC", "EURJPY-OTC", "AUDUSD-OTC"
]

# 🛑 CONTROL DE RIESGO Y SEGURIDAD
MAX_DAILY_TRADES = 15           # Máx 15 ops/día (Calidad > Cantidad)
MAX_LOSS_STREAK = 1             # Para tras 1 pérdida
PAUSE_TIME = 300                # Pausa 5 min tras pérdida
MIN_CANDLE_BODY_PERCENT = 0.70  # 70% del rango = Vela FUERTE

# 🚦 VARIABLE GLOBAL PRINCIPAL (DECLARADA AQUÍ ARRIBA)
# ✅ SOLUCIÓN 1: Variable declarada en el nivel más alto del código
BOT_RUNNING = False             # <-- POR DEFECTO: DETENIDO
LAST_UPDATE_ID = 0              # Para evitar leer mensajes repetidos

# ==================================================
# 🚀 ESTRATEGIA PRO - VERSIÓN: BLOQUEO ESTRICTO
# ✅ SOLO SEÑALES CON VELA ANTERIOR DE CONFIRMACIÓN
# ✅ BLOQUEADO SI NO HAY CONFIRMACIÓN
# ==================================================

# ---------------- INDICADORES ----------------
def bollinger_bands(df, window=20, std_dev=2.1):
    df = df.copy()
    df['sma'] = df['close'].rolling(window=window).mean()
    df['upper_band'] = df['sma'] + (df['close'].rolling(window=window).std() * std_dev)
    df['lower_band'] = df['sma'] - (df['close'].rolling(window=window).std() * std_dev)
    return df

def zigzag_detection(df, pips_threshold=0.0008):
    df = df.copy()
    df['zigzag'] = 0
    last_swing_high = None
    last_swing_low = None
    for i in range(3, len(df)-2):
        if (df['high'].iloc[i] > df['high'].iloc[i-1] and df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and df['high'].iloc[i] > df['high'].iloc[i+2]):
            if last_swing_high is None or (df['high'].iloc[i] - last_swing_high) > pips_threshold:
                df.loc[df.index[i], 'zigzag'] = 1; last_swing_high = df['high'].iloc[i]
        if (df['low'].iloc[i] < df['low'].iloc[i-1] and df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and df['low'].iloc[i] < df['low'].iloc[i+2]):
            if last_swing_low is None or (last_swing_low - df['low'].iloc[i]) > pips_threshold:
                df.loc[df.index[i], 'zigzag'] = -1; last_swing_low = df['low'].iloc[i]
    return df

def fractal_signal(df):
    df = df.copy()
    df['fractal_up'], df['fractal_down'] = False, False
    if len(df) < 5: return df
    for i in range(2, len(df)-2):
        if (df['high'].iloc[i] > df['high'].iloc[i-2] and df['high'].iloc[i] > df['high'].iloc[i-1] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and df['high'].iloc[i] > df['high'].iloc[i+2]):
            df.loc[df.index[i], 'fractal_up'] = True
        if (df['low'].iloc[i] < df['low'].iloc[i-2] and df['low'].iloc[i] < df['low'].iloc[i-1] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and df['low'].iloc[i] < df['low'].iloc[i+2]):
            df.loc[df.index[i], 'fractal_down'] = True
    return df

# ---------------- ✅ VERIFICACIÓN CLAVE: VELA ANTERIOR DE CONFIRMACIÓN ----------------
def vela_anterior_confirma_tendencia(df, direccion):
    if len(df) < 2: return False
    vela_anterior = df.iloc[-2]
    vela_actual = df.iloc[-1]
    cuerpo_ant = abs(vela_anterior['close'] - vela_anterior['open'])
    rango_ant = vela_anterior['high'] - vela_anterior['low']
    if rango_ant == 0: return False
    es_fuerte = (cuerpo_ant / rango_ant) >= MIN_CANDLE_BODY_PERCENT
    if direccion == "call":
        direccion_ok = (vela_anterior['close'] > vela_anterior['open']) and (vela_anterior['close'] > vela_anterior['high'].shift(1).iloc[-2])
        continuacion = vela_actual['low'] > vela_anterior['open']
    else:
        direccion_ok = (vela_anterior['close'] < vela_anterior['open']) and (vela_anterior['close'] < vela_anterior['low'].shift(1).iloc[-2])
        continuacion = vela_actual['high'] < vela_anterior['open']
    return es_fuerte and direccion_ok and continuacion

# ---------------- ANÁLISIS DE TENDENCIA ----------------
def get_trend_direction(df):
    cierre = df['close'].values
    minimos = df['low'].values
    maximos = df['high'].values
    alcista = (cierre[-1] > cierre[-2] > cierre[-3] > cierre[-4] and cierre[-1] > maximos[-3] and all(cierre[i] > cierre[i-1] for i in range(-1, -5, -1)))
    bajista = (cierre[-1] < cierre[-2] < cierre[-3] < cierre[-4] and cierre[-1] < minimos[-3] and all(cierre[i] < cierre[i-1] for i in range(-1, -5, -1)))
    if alcista: return "call"
    if bajista: return "put"
    return None

def zona_clave(df):
    ultimo = df.iloc[-1]
    resistencia = df['high'].rolling(25).max().iloc[-2]
    soporte = df['low'].rolling(25).min().iloc[-2]
    rango = resistencia - soporte
    if rango == 0: return False, None
    umbral = rango * 0.01
    if abs(ultimo['close'] - resistencia) < umbral: return True, "resistencia"
    if abs(ultimo['close'] - soporte) < umbral: return True, "soporte"
    return False, None

def confirmaciones(df, direccion):
    ultimo = df.iloc[-1]
    boll_ok = False
    if direccion == "call" and ultimo['low'] <= ultimo['lower_band'] * 1.001: boll_ok = True
    if direccion == "put" and ultimo['high'] >= ultimo['upper_band'] * 0.999: boll_ok = True
    zig_ok = False
    if direccion == "call" and df['zigzag'].iloc[-10:].isin([-1]).any(): zig_ok = True
    if direccion == "put" and df['zigzag'].iloc[-10:].isin([1]).any(): zig_ok = True
    frac_ok = False
    if direccion == "call" and df['fractal_down'].iloc[-6:].any(): frac_ok = True
    if direccion == "put" and df['fractal_up'].iloc[-6:).any(): frac_ok = True
    return boll_ok and zig_ok and frac_ok

# ---------------- 🎯 SEÑAL FINAL ----------------
def get_signal(df1, df5):
    if len(df1) < 80: return None
    df1 = bollinger_bands(df1)
    df1 = zigzag_detection(df1)
    df1 = fractal_signal(df1)
    direccion = get_trend_direction(df1)
    if direccion is None: return None
    zona_ok, tipo_zona = zona_clave(df1)
    if not zona_ok: return None
    if not vela_anterior_confirma_tendencia(df1, direccion): return None
    if not confirmaciones(df1, direccion): return None
    if (direccion == "call" and tipo_zona == "soporte") or (direccion == "put" and tipo_zona == "resistencia"):
        return direccion
    return None

def score_market(df1, df5):
    vela = df1.iloc[-1]
    cuerpo = abs(vela['open'] - vela['close'])
    rango = vela['high'] - vela['low']
    if rango == 0: return 0
    calidad = (cuerpo / rango) * 100
    if calidad >= 70: return 9
    if calidad >= 50: return 6
    return 3

# ==================================================
# 🤖 GESTIÓN DEL BOT - CONEXIÓN, COMANDOS Y EJECUCIÓN
# ==================================================

class RiskManager:
    def __init__(self):
        self.daily = 0
        self.max_daily = MAX_DAILY_TRADES
    def can_trade(self):
        return self.daily < self.max_daily
    def register_trade(self):
        self.daily += 1

DAILY_TRADES = 0
CURRENT_DAY = datetime.utcnow().day
LOSS_STREAK = 0
LAST_LOSS = 0

# ---------------- 🆕 FUNCIÓN COMANDOS TELEGRAM - CORREGIDA 100% ----------------
def check_telegram_commands():
    """
    ✅ SOLUCIÓN 2: Declaración GLOBAL explícita al PRINCIPIO de la función
    """
    global BOT_RUNNING, LAST_UPDATE_ID  # <--- ¡¡¡OBLIGATORIO Y AL INICIO!!!
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=5"
        response = requests.get(url, timeout=10).json()
        if not response.get("ok"): return
        updates = response.get("result", [])
        for update in updates:
            LAST_UPDATE_ID = update['update_id']
            if "message" in update and "text" in update["message"]:
                text = update["message"]["text"].strip().lower()
                chat_id = str(update["message"]["chat"]["id"])
                if chat_id != str(CHAT_ID): continue

                # 🟢 COMANDO START
                if text == "/start":
                    BOT_RUNNING = True  # <--- Modificamos variable global
                    send("🟢 <b>BOT INICIADO</b>\n✅ Operando: Solo confirmación vela anterior\n✅ Solo a favor de tendencia")
                # 🔴 COMANDO STOP
                elif text == "/stop":
                    BOT_RUNNING = False # <--- Modificamos variable global
                    send("🔴 <b>BOT DETENIDO</b>\n⏸️ En pausa. Usa /start para activar.")
    except Exception as e:
        print(f"Error comandos: {e}")


def send(msg):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True},
                timeout=5
            )
        except: pass

def reset_day():
    global DAILY_TRADES, CURRENT_DAY, LOSS_STREAK
    if datetime.utcnow().day != CURRENT_DAY:
        DAILY_TRADES = 0
        CURRENT_DAY = datetime.utcnow().day
        LOSS_STREAK = 0
        # ✅ Accedemos a global BOT_RUNNING
        if BOT_RUNNING:
            send("🔄 <b>NUEVO DÍA</b> | Contadores reiniciados.")

def connect():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            status, _ = iq.connect()
            if status:
                iq.change_balance("PRACTICE") # Cambiar a "REAL" si usas dinero real
                send("✅ <b>BOT CONECTADO</b>\nEscribe /start para EMPEZAR.")
                return iq
        except Exception as e:
            send(f"❌ Error Conexión: {str(e)}")
        time.sleep(5)

def get_df(iq, pair, tf):
    try:
        data = iq.get_candles(pair, tf, 120, time.time())
        df = pd.DataFrame(data)
        if df.empty: return None
        df.rename(columns={"max": "high", "min": "low"}, inplace=True)
        df['open'] = pd.to_numeric(df['open'])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        return df
    except: return None

def candle_quality(df):
    last = df.iloc[-1]
    body = abs(last['open'] - last['close'])
    wick_up = last['high'] - max(last['open'], last['close'])
    wick_down = min(last['open'], last['close']) - last['low']
    if wick_up > body * 1.2: return False
    if wick_down > body * 1.2: return False
    if body < ((last['high'] - last['low']) * 0.3): return False
    return True


def main():
    global LOSS_STREAK, LAST_LOSS, DAILY_TRADES, BOT_RUNNING # <--- ✅ Global aquí también
    iq = connect()
    risk = RiskManager()
    last_candle = None
    signal = None

    while True:
        try:
            # Leer comandos SIEMPRE primero
            check_telegram_commands()
            reset_day()

            # ✅ SOLUCIÓN 3: Acceso claro a variable global
            if not BOT_RUNNING:
                time.sleep(1)
                continue

            # 🔒 LÍMITES DE SEGURIDAD
            if DAILY_TRADES >= MAX_DAILY_TRADES:
                send("⛔ <b>LÍMITE DIARIO ALCANZADO</b>")
                BOT_RUNNING = False # <--- Modificamos global
                time.sleep(10)
                continue
            if LOSS_STREAK >= MAX_LOSS_STREAK:
                if time.time() - LAST_LOSS < PAUSE_TIME:
                    time.sleep(1)
                    continue
                else:
                    LOSS_STREAK = 0

            server_time = iq.get_server_timestamp()
            sec = server_time % 60

            # 🕒 ANÁLISIS
            if 45 <= sec <= 58:
                best_score = 0
                best_pair = None
                best_signal = None
                for pair in PAIRS:
                    df1 = get_df(iq, pair, TIMEFRAME_M1)
                    df5 = get_df(iq, pair, TIMEFRAME_M5)
                    if df1 is None or df5 is None: continue
                    if not candle_quality(df1): continue
                    score = score_market(df1, df5)
                    if score < 5: continue
                    s = get_signal(df1, df5)
                    if s and score > best_score:
                        best_score = score
                        best_pair = pair
                        best_signal = s
                signal = (best_pair, best_signal) if best_pair else None

            # ⚡ EJECUCIÓN
            if 59.4 <= sec <= 59.98 or 0 <= sec <= 0.25:
                candle = int(server_time // 60)
                if candle == last_candle: continue
                last_candle = candle
                if not signal: continue

                pair, direction = signal
                # NO INVERTIR SEÑAL
                if not risk.can_trade(): continue

                status, trade_id = iq.buy(BASE_AMOUNT, pair, direction, EXPIRATION)
                if status:
                    DAILY_TRADES += 1
                    tipo = "🟢 <b>COMPRA / CALL</b>" if direction == "call" else "🔴 <b>VENTA / PUT</b>"
                    send(f"🚀 {pair} | {tipo} | ${BASE_AMOUNT} | {DAILY_TRADES}/{MAX_DAILY_TRADES}")
                    risk.register_trade()
                    time.sleep(65)
                    result = iq.check_win_v4(trade_id)
                    if result < 0:
                        LOSS_STREAK += 1
                        LAST_LOSS = time.time()
                        send(f"❌ LOSS | ${result:.2f} | Pausa {PAUSE_TIME//60}min")
                    else:
                        LOSS_STREAK = 0
                        send(f"✅ WIN | +${result:.2f}")
                signal = None

            time.sleep(0.1)

        except Exception as e:
            send(f"💥 <b>ERROR:</b> {str(e)}")
            time.sleep(3)

if __name__ == "__main__":
    main()
