import time
import pandas as pd
from estrategia_reversal import get_reversal_signal

# =========================================================
# CONFIGURACIÓN
# =========================================================

ARCHIVO_DATOS = "datos.csv"   # tu archivo de velas
TIEMPO_ESPERA = 5             # segundos entre ejecuciones

# =========================================================
# CARGAR DATOS
# =========================================================

def cargar_datos():
    try:
        df = pd.read_csv(ARCHIVO_DATOS)

        # Asegurar formato correcto
        df = df.rename(columns=str.lower)

        required = ["open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                raise Exception(f"Falta columna: {col}")

        return df

    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return None

# =========================================================
# EJECUTAR ESTRATEGIA
# =========================================================

def analizar_mercado():

    df = cargar_datos()

    if df is None:
        return

    señal = get_reversal_signal(df)

    if señal is None:
        print("⏸️ Sin señal")
        return

    tipo, score, mensaje = señal

    print("===================================")
    print(f"📊 SEÑAL DETECTADA: {tipo.upper()}")
    print(f"🔥 Score: {score}")
    print(f"🧠 Estrategia: {mensaje}")
    print("===================================")

    ejecutar_trade(tipo, score)

# =========================================================
# EJECUCIÓN (SIMULADA)
# =========================================================

def ejecutar_trade(tipo, score):

    # Aquí puedes conectar tu broker real
    # Ej: IQ Option, Binomo, Deriv, etc.

    print(f"🚀 Ejecutando operación: {tipo.upper()}")

    # Simulación
    if tipo == "call":
        print("📈 COMPRA (CALL)")
    elif tipo == "put":
        print("📉 VENTA (PUT)")

# =========================================================
# LOOP PRINCIPAL
# =========================================================

def run_bot():

    print("🤖 BOT INICIADO...\n")

    while True:
        try:
            analizar_mercado()
            time.sleep(TIEMPO_ESPERA)

        except KeyboardInterrupt:
            print("\n🛑 Bot detenido manualmente")
            break

        except Exception as e:
            print(f"💥 Error: {e}")
            time.sleep(5)

# =========================================================
# INICIO
# =========================================================

if __name__ == "__main__":
    run_bot()
