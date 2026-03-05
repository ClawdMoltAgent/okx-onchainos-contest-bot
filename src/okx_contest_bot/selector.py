from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import json

from .okx_client import OkxDexClient


@dataclass
class TokenCandidate:
    symbol: str
    address: str


@dataclass
class SelectedToken:
    symbol: str
    address: str
    price: float
    edge_bps: float


class TokenSelector:
    def __init__(
        self,
        client: OkxDexClient,
        candidates: list[TokenCandidate] | list[dict[str, str]],
        fast_window: int,
        slow_window: int,
        min_edge_bps: float,
        state_path: str = "./data/selected_token.json",
    ):
        self.client = client
        self.candidates = [
            c if isinstance(c, TokenCandidate) else TokenCandidate(symbol=c["symbol"], address=c["address"])
            for c in candidates
        ]
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.min_edge_bps = min_edge_bps
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.series: dict[str, deque[float]] = {c.address: deque(maxlen=slow_window) for c in self.candidates}

    def _edge(self, prices: list[float]) -> float:
        if len(prices) < self.slow_window:
            return 0.0
        fast = sum(prices[-self.fast_window :]) / self.fast_window
        slow = sum(prices) / self.slow_window
        return (fast - slow) / slow * 10000 if slow > 0 else 0.0

    def select(self) -> SelectedToken | None:
        best: SelectedToken | None = None

        for c in self.candidates:
            p = self.client.get_price(c.address)
            s = self.series[c.address]
            s.append(p)
            edge = self._edge(list(s))

            if best is None or edge > best.edge_bps:
                best = SelectedToken(symbol=c.symbol, address=c.address, price=p, edge_bps=edge)

        if best is None:
            return None

        if best.edge_bps < self.min_edge_bps:
            # if no strong momentum, keep best anyway but label through edge.
            pass

        self.state_path.write_text(
            json.dumps(
                {
                    "symbol": best.symbol,
                    "address": best.address,
                    "price": best.price,
                    "edge_bps": best.edge_bps,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return best
