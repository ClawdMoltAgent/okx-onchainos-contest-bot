import json

from okx_contest_bot.analytics import summarize_trades
from okx_contest_bot.config import load_config, _parse_candidates
from okx_contest_bot.strategy import MovingAverageStrategy
from okx_contest_bot.risk import RiskManager, RiskState


def test_load_config():
    cfg = load_config()
    assert cfg.base_chain_index == "8453"


def test_strategy_signal_shapes():
    s = MovingAverageStrategy(3, 5, 1, 1)
    prices = [100, 101, 102, 103, 104]
    sig = None
    for p in prices:
        sig = s.on_price(p)
    assert sig is not None
    assert sig.action in {"BUY", "SELL", "HOLD"}


def test_risk_open_limit():
    r = RiskManager(max_daily_loss_usd=20, max_position_usd=40)
    state = RiskState(daily_realized_pnl_usd=0, position_usd=30)
    ok, reason = r.can_open(state, 20)
    assert not ok
    assert reason == "position-limit-hit"


def test_parse_candidates():
    c = _parse_candidates("WETH:0x1,cbBTC:0x2")
    assert len(c) == 2
    assert c[0]["symbol"] == "WETH"


def test_analytics_summary(tmp_path):
    log = tmp_path / "trades.jsonl"
    rows = [
        {"ts": "2026-03-05T09:00:00", "event": "BUY", "usd": 20, "price": 2000},
        {"ts": "2026-03-05T09:10:00", "event": "SELL", "usd": 20, "price": 2010, "pnl": 0.1},
        {"ts": "2026-03-05T09:20:00", "event": "BUY", "usd": 20, "price": 2010},
        {"ts": "2026-03-05T09:30:00", "event": "SELL", "usd": 20, "price": 1990, "pnl": -0.2},
    ]
    with log.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    s = summarize_trades(str(log))
    assert s["exists"] is True
    assert s["closed_trades"] == 2
    assert abs(s["realized_pnl_usd"] - (-0.1)) < 1e-9
