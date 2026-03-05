from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean, pstdev
from collections import defaultdict


def _max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    mdd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > mdd:
                mdd = dd
    return mdd * 100.0


def summarize_trades(path: str = "./data/trades.jsonl") -> dict:
    p = Path(path)
    if not p.exists():
        return {
            "exists": False,
            "total_trades": 0,
            "closed_trades": 0,
            "win_rate": 0.0,
            "realized_pnl_usd": 0.0,
            "avg_pnl_per_close": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_per_trade": 0.0,
            "profit_factor": 0.0,
            "daily_pnl": {},
            "equity_curve": [],
        }

    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    closes = [r for r in rows if r.get("event") == "SELL"]
    pnls = [float(r.get("pnl", 0.0)) for r in closes]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]

    equity = 1000.0
    equity_curve = [equity]
    returns = []
    daily_pnl = defaultdict(float)

    for r in closes:
        pnl = float(r.get("pnl", 0.0))
        usd = float(r.get("usd", 0.0))
        ts = str(r.get("ts", ""))
        day = ts[:10] if len(ts) >= 10 else "unknown"

        daily_pnl[day] += pnl
        equity += pnl
        equity_curve.append(equity)
        if usd > 0:
            returns.append(pnl / usd)

    sharpe = 0.0
    if len(returns) >= 2:
        mu = mean(returns)
        sigma = pstdev(returns)
        if sigma > 0:
            sharpe = (mu / sigma) * math.sqrt(len(returns))

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

    return {
        "exists": True,
        "total_trades": len(rows),
        "closed_trades": len(closes),
        "win_rate": (len(wins) / len(closes) * 100.0) if closes else 0.0,
        "realized_pnl_usd": sum(pnls),
        "avg_pnl_per_close": mean(pnls) if pnls else 0.0,
        "max_drawdown_pct": _max_drawdown(equity_curve),
        "sharpe_per_trade": sharpe,
        "profit_factor": profit_factor,
        "daily_pnl": dict(sorted(daily_pnl.items())),
        "equity_curve": equity_curve,
    }


def pretty_print_report(summary: dict) -> str:
    if not summary.get("exists"):
        return "No trades log yet (data/trades.jsonl not found)."

    daily_lines = [f"  {k}: ${v:.4f}" for k, v in summary.get("daily_pnl", {}).items()]
    daily_text = "\n".join(daily_lines) if daily_lines else "  (no closed trades yet)"

    return (
        "\n".join(
            [
                "=== Profitability Validation Report ===",
                f"Total trade events: {summary['total_trades']}",
                f"Closed trades: {summary['closed_trades']}",
                f"Win rate: {summary['win_rate']:.2f}%",
                f"Realized PnL: ${summary['realized_pnl_usd']:.4f}",
                f"Avg PnL per close: ${summary['avg_pnl_per_close']:.4f}",
                f"Max Drawdown: {summary['max_drawdown_pct']:.2f}%",
                f"Sharpe (per-trade): {summary['sharpe_per_trade']:.4f}",
                f"Profit Factor: {summary['profit_factor']:.4f}",
                "Daily PnL:",
                daily_text,
            ]
        )
    )
