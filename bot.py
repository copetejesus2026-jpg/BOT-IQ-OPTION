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
EXPIRATION = 1                  # 1 Minuto
BASE_AMOUNT = 3.33              # Monto por operación
TIMEFRAME_M1 = 60               # 1 Minuto
TIMEFRAME_M5 = 300              # 5 Minutos

# 📋 ACTIVOS OTC
PAIRS = [
    "EURUSD-OTC", "GBPUSD-OTC", "USDCHF-OTC", 
    "EURGBP-OTC", "EURJPY-OTC", "AUDUSD-OTC"
]

# 🛑 CONTROL DE RIESGO
MAX_DAILY_TRADES = 15           # Máx operaciones/día
MAX_LOSS_STREAK = 1             # Detener tras 1 pérdida
PAUSE_TIME = 300                # Pausa 5min tras pérdida
MIN_CANDLE_BODY_PERCENT = 0.70  # 70% cuerpo = Vela fuerte

# ==========================================
# 🚦 VARIABLE GLOBAL (SOLUCIÓN PRINCIPAL)
# ==========================================
BOT_RUNNING = False             # ESTADO INICIAL: DETENIDO
LAST_UPDATE_ID = 0              # Control de mensajes Telegram
DAILY_TRADES = 0
CURRENT_DAY = datetime.utcnow().day
LOSS_STREAK = 0
LAST_LOSS = 0


# ==================================================
# 🚀 ESTRATEGIA PRO - CONFIRMACIÓN VELA ANTERIOR
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
        if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
            df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and 
            df['high'].iloc[i] > df['high'].iloc[i+2]):
            if last_swing_high is None or (df['high'].iloc[i] - last_swing_high) > pips_threshold:
                df.loc[df.index[i], 'zigzag'] = 1
                last_swing_high = df['high'].iloc[i]
                
        if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
            df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and 
            df['low'].iloc[i] < df['low'].iloc[i+2]):
            if last_swing_low is None or (last_swing_low - df['low'].iloc[i]) > pips_threshold:
                df.loc[df.index[i], 'zigzag'] = -1
                last_swing_low = df['low'].iloc[i]
    return df

def fractal_signal(df):
    df = df.copy()
    df['fractal_up'], df['fractal_down'] = False, False
    if len(df) < 5: 
        return df
    for i in range(2, len(df)-2):
        if (df['high'].iloc[i] > df['high'].iloc[i-2] and 
            df['high'].iloc[i] > df['high'].iloc[i-1] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and 
            df['high'].iloc[i] > df['high'].iloc[i+2]):
            df.loc[df.index[i], 'fractal_up'] = True
            
        if (df['low'].iloc[i] < df['low'].iloc[i-2] and 
            df['low'].iloc[i] < df['low'].iloc[i-1] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and 
            df['low'].iloc[i] < df['low'].iloc[i+2]):
            df.loc[df.index[i], 'fractal_down'] = True
    return df

# ---------------- ✅ REGLA PRINCIPAL: VELA ANTERIOR ----------------
def vela_anterior_confirma_tendencia(df, direccion):
    if len(df) < 2: 
        return False
    
    vela_anterior = df.iloc[-2]
    vela_actual = df.iloc[-1]

    cuerpo_ant = abs(vela_anterior['close'] - vela_anterior['open'])
    rango_ant = vela_anterior['high'] - vela_anterior['low']

    if rango_ant == 0: 
        return False

    es_fuerte = (cuerpo_ant / rango_ant) >= MIN_CANDLE_BODY_PERCENT

    if direccion == "call":
        direccion_ok = (vela_anterior['close'] > vela_anterior['open']) and \
                       (vela_anterior['close'] > vela_anterior['high'].shift(1).iloc[-2])
        continuacion = vela_actual['low'] > vela_anterior['open']

    else:
        direccion_ok = (vela_anterior['close'] < vela_anterior['open']) and \
                       (vela_anterior['close'] < vela_anterior['low'].shift(1).iloc[-2])
        continuacion = vela_actual['high'] < vela_anterior['open']

    return es_fuerte and direccion_ok and continuacion

# ---------------- ANÁLISIS DE TENDENCIA ----------------
def get_trend_direction(df):
    cierre = df['close'].values
    minimos = df['low'].values
    maximos = df['high'].values

    alcista = (
        cierre[-1] > cierre[-2] > cierre[-3] > cierre[-4] and
        cierre[-1] > maximos[-3] and
        all(cierre[i] > cierre[i-1] for i in range(-1, -5, -1))
    )
    bajista = (
        cierre[-1] < cierre[-2] < cierre[-3] < cierre[-4] and
        cierre[-1] < minimos[-3] and
        all(cierre[i] < cierre[i-1] for i in range(-1, -5, -1))
    )

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
    if direccion == "call" and ultimo['low'] <= ultimo['lower_band'] * 1.001:
        boll_ok = True
    if direccion == "put" and ultimo['high'] >= ultimo['upper_band'] * 0.999:
        boll_ok = True

    zig_ok = False
    if direccion == "call" and df['zigzag'].iloc[-10:].isin([-1]).any():
        zig_ok = True
    if direccion == "put" and df['zigzag'].iloc[-10:].isin([1]).any():
        zig_ok = True

    frac_ok = False
    if direccion == "call" and df['fractal_down'].iloc[-6:].any():
        frac_ok = True
    if direccion == "put" and df['fractal_up'].iloc[-6:].any():
        frac_ok = True

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

    if not vela_anterior_confirma_tendencia(df1, direccion):
        return None

    if not confirmaciones(df1, direccion): return None

    if (direccion == "call" and tipo_zona == "soporte") or \
       (direccion == "put" and tipo_zona == "resistencia"):
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
# 🤖 GESTIÓN DEL BOT - COMANDOS /START /STOP
# ==================================================

class RiskManager:
    def __init__(self):
        self.daily = 0
        self.max_daily = MAX_DAILY_TRADES
    def can_trade(self):
        return self.daily < self.max_daily
    def register_trade(self):
        self.daily += 1

# ---------------- 🆕 COMANDOS TELEGRAM (CORREGIDOS) ----------------
def check_telegram_commands():
    """
    ✅ AQUÍ ESTÁ LA SOLUCIÓN: Declaramos GLOBAL al PRINCIPIO
    """
    global BOT_RUNNING, LAST_UPDATE_ID  # ← ¡¡¡ESTA LÍNEA ES LA CLAVE!!!
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=2"
        res = requests.get(url, timeout=5).json()
        
        if not res.get("ok"): 
            return

        for update in res.get("result", []):
            LAST_UPDATE_ID = update['update_id']
            
            if "message" not in update or "text" not in update["message"]:
                continue
                
            text = update["message"]["text"].strip().lower()
            chat_id = str(update["message"]["chat"]["id"])

            if chat_id != str(CHAT_ID):
                continue

            if text == "/start":
                BOT_RUNNING = True
                send("🟢 <b>BOT INICIADO ✅</b>\n🔐 Modo: ESTRICTO\n📊 Condición: Solo con confirmación de vela anterior")
            
            elif text == "/stop":
                BOT_RUNNING = False
                send("🔴 <b>BOT DETENIDO ⏹️</b>\nUsa /start para reactivar.")

    except Exception as e:
        print(f"Error comandos: {e}")


def send(msg):
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
                timeout=5
            )
        except: pass

def reset_day():
    """
    ✅ También declaramos GLOBAL aquí
    """
    global DAILY_TRADES, CURRENT_DAY, LOSS_STREAK, BOT_RUNNING  # ← GLOBAL
    if datetime.utcnow().day != CURRENT_DAY:
        DAILY_TRADES = 0
        CURRENT_DAY = datetime.utcnow().day
        LOSS_STREAK = 0
        if BOT_RUNNING:
            send("🔄 <b>NUEVO DÍA 🌅</b>")

def connect():
    while True:
        try:
            iq = IQ_Option(EMAIL, PASSWORD)
            status, _ = iq.connect()
            if status:
                iq.change_balance("PRACTICE")
                send("✅ <b>CONECTADO</b>\nEscribe /start para empezar.")
                return iq
        except Exception as e:
            send(f"❌ Error: {str(e)}")
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
    
    if wick_up > body * 
