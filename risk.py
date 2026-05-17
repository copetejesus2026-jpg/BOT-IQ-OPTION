import time

class RiskManager:
    def __init__(self, max_loss_streak=3, cooldown_sec=180):
        self.loss_streak = 0
        self.max_loss_streak = max_loss_streak
        self.cooldown_sec = cooldown_sec
        self.last_trade_time = 0

    def can_trade(self):
        # cooldown por tiempo
        if time.time() - self.last_trade_time < 5:
            return False
        # cooldown por racha
        if self.loss_streak >= self.max_loss_streak:
            if time.time() - self.last_trade_time < self.cooldown_sec:
                return False
            else:
                self.loss_streak = 0
        return True

    def register_trade(self, open_time):
        self.last_trade_time = open_time

    # (opcional) integrar lectura de resultado para actualizar racha
    def register_result(self, win: bool):
        if win:
            self.loss_streak = 0
        else:
            self.loss_streak += 1
