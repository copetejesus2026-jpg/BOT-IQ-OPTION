import pandas as pd


class StrategyPRO:

    def __init__(self):
        pass

    # -------------------------------------------
    # DETERMINAR DIRECCIÓN DE PRECIO (M1 Y M5)
    # -------------------------------------------
    def get_direction(self, df: pd.DataFrame):
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Cuerpo de vela
        body = abs(last["close"] - last["open"])
        total = last["high"] - last["low"]

        # Rechazos
        wick_up = last["high"] - max(last["open"], last["close"])
        wick_down = min(last["open"], last["close"]) - last["low"]

        # Filtro de vela basura
        if total == 0 or body < total * 0.25:
            return None

        # Vela alcista fuerte
        if last["close"] > last["open"] and wick_down > body * 0.3:
            return "call"

        # Vela bajista fuerte
        if last["close"] < last["open"] and wick_up > body * 0.3:
            return "put"

        return None

    # -------------------------------------------
    # PUNTUACIÓN DEL MERCADO
    # -------------------------------------------
    def score_market(self, df_m1: pd.DataFrame, df_m5: pd.DataFrame):
        last1 = df_m1.iloc[-1]
        last5 = df_m5.iloc[-1]

        # Rango mínimo para evitar consolidación
        range1 = last1["high"] - last1["low"]
        range5 = last5["high"] - last5["low"]

        if range1 == 0 or range5 == 0:
            return 0

        score = 0

        # Rango amplio → buen movimiento
        if range1 > (range5 / 4):
            score += 3

        # Cuerpo dominante → intención institucional
        body = abs(last1["close"] - last1["open"])
        if body > range1 * 0.65:
            score += 3

        # Tendencia M5 confirma microdirección M1
        if (last1["close"] > last1["open"] and last5["close"] > last5["open"]):
            score += 3
        if (last1["close"] < last1["open"] and last5["close"] < last5["open"]):
            score += 3

        return score

    # -------------------------------------------
    # GENERAR SEÑAL FINAL
    # -------------------------------------------
    def get_signal(self, df_m1: pd.DataFrame, df_m5: pd.DataFrame):
        dir_m1 = self.get_direction(df_m1)
        dir_m5 = self.get_direction(df_m5)

        if not dir_m1 or not dir_m5:
            return None

        # Solo operar si M1 y M5 coinciden
        if dir_m1 == dir_m5:
            return dir_m1

        return None
