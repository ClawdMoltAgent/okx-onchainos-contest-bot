from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class StrategySignal:
    action: str  # BUY | SELL | HOLD
    edge_bps: float


class MovingAverageStrategy:
    def __init__(self, fast_window: int, slow_window: int, buy_threshold_bps: int, sell_threshold_bps: int):
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.buy_threshold_bps = buy_threshold_bps
        self.sell_threshold_bps = sell_threshold_bps
        self.prices: deque[float] = deque(maxlen=slow_window)

    def on_price(self, price: float) -> StrategySignal:
        self.prices.append(price)
        if len(self.prices) < self.slow_window:
            return StrategySignal(action="HOLD", edge_bps=0.0)

        p = list(self.prices)
        fast = sum(p[-self.fast_window:]) / self.fast_window
        slow = sum(p) / self.slow_window
        edge_bps = (fast - slow) / slow * 10000

        if edge_bps >= self.buy_threshold_bps:
            return StrategySignal(action="BUY", edge_bps=edge_bps)
        if edge_bps <= -self.sell_threshold_bps:
            return StrategySignal(action="SELL", edge_bps=edge_bps)
        return StrategySignal(action="HOLD", edge_bps=edge_bps)
