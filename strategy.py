import pandas as pd


class StrategyPRO:

    def __init__(self):
        pass

    # ======================================================
    #   LECTURA AVANZADA DE VELA (M1)
    # ======================================================
    def read_candle(self, c):
        body = abs(c["close"] - c["open"])
        range_total = c["high"] - c["low"]

        if range_total == 0:
            return None

        wick_up = c["high"] - max(c["open"], c["close"])
        wick_down = min(c["open"], c["close"]) - c["low"]

        strong_bull = (c["close"] > c["open"]) and body > range_total * 0.45
        strong_bear = (c["open"] > c["close"]) and body > range_total * 0.45

        rejection_low = wick_down > body * 0.35
        rejection_high = wick_up > body * 0.35

        return {
            "body": body,
            "range": range_total,
            "wick_up": wick_up,
            "wick_down": wick_down,
            "strong_bull": strong_bull,
            "strong_bear": strong_bear,
            "rejection_low": rejection_low,
            "rejection_high": rejection_high
        }

    # ======================================================
    #   TENDENCIA M5 → DIRECCIÓN GLOBAL
    # ======================================================
    def trend_m5(self, df):
        last = df.iloc[-1]
        prev = df.iloc[-4]

        if last["close"] > prev["close"]:
            return "call"

        if last["close"] < prev["close"]:
            return "put"

        return None

    # ======================================================
    #   ESTRUCTURA M1 → ZONA ÓPTIMA DE ENTRADA
    # ======================================================
    def structure_m1(self, df):
        c1 = self.read_candle(df.iloc[-1])
        c2 = self.read_candle(df.iloc[-2])
        c3 = self.read_candle(df.iloc[-3])

        if not c1 or not c2 or not c3:
            return None

        # ----------------------------------------------------------
        # ENTRADAS INVERTIDAS (tal como pediste)
        # ----------------------------------------------------------

        # =====================================
        #     ANTES ERA CALL → AHORA PUT
        # =====================================
        if (
            c1["strong_bull"] and 
            c2["rejection_low"] and 
            c1["wick_up"] < c1["wick_down"]
        ):
            return "put"

        # =====================================
        #     ANTES ERA CALL → AHORA PUT
        # =====================================
        if (
            c1["strong_bull"] and c2["strong_bull"] and c3["rejection_low"]
        ):
            return "put"

        # =====================================
        #     ANTES ERA PUT → AHORA CALL
        # =====================================
        if (
            c1["strong_bear"] and 
            c2["rejection_high"] and 
            c1["wick_down"] < c1["wick_up"]
        ):
            return "call"

        # =====================================
        #     ANTES ERA PUT → AHORA CALL
        # =====================================
        if (
            c1["strong_bear"] and c2["strong_bear"] and c3["rejection_high"]
        ):
            return "call"

        return None

    # ======================================================
    #   SEÑAL FINAL (INVIERTE ENTRADAS)
    # ======================================================
    def get_signal(self, df_m1: pd.DataFrame, df_m5: pd.DataFrame):

        trend = self.trend_m5(df_m5)
        structure = self.structure_m1(df_m1)

        if not trend or not structure:
            return None

        # ❗ ENTRADAS INVERTIDAS:  
        # Si estructura dice CALL → damos PUT  
        # Si estructura dice PUT → damos CALL  

        if structure == "call":
            return "put"

        if structure == "put":
            return "call"

        return None
