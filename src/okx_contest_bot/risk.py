from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskState:
    daily_realized_pnl_usd: float = 0.0
    position_usd: float = 0.0


class RiskManager:
    def __init__(self, max_daily_loss_usd: float, max_position_usd: float):
        self.max_daily_loss_usd = max_daily_loss_usd
        self.max_position_usd = max_position_usd

    def can_open(self, state: RiskState, new_position_usd: float) -> tuple[bool, str]:
        if state.daily_realized_pnl_usd <= -self.max_daily_loss_usd:
            return False, "daily-loss-limit-hit"
        if state.position_usd + new_position_usd > self.max_position_usd:
            return False, "position-limit-hit"
        return True, "ok"

    def can_close(self, state: RiskState) -> tuple[bool, str]:
        if state.position_usd <= 0:
            return False, "no-position"
        return True, "ok"
