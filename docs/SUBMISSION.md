# OKX OnchainOS Contest Submission / 比赛提交说明

## 1) Project Overview / 项目概述
**EN**: This project is a Base-chain trading bot for the OKX OnchainOS contest. It uses OKX DEX APIs for market data and swap routing, applies a risk-first momentum strategy, and provides reproducible runtime logs and profitability analytics.

**中文**：本项目是面向 OKX OnchainOS 比赛的 Base 链交易机器人。通过 OKX DEX API 获取行情与路由，执行“风控优先”的动量策略，并提供可复现实盘日志与盈利分析。

## 2) Model & Version / 模型与版本
- Runtime: Python 3.11+
- Strategy core: Moving Average momentum (fast/slow windows)
- Execution: OKX v6 DEX endpoints + Base on-chain signed tx

## 3) Strategy Logic / 策略逻辑
**EN**:
- Compute fast/slow moving averages from latest market price stream.
- Signal edge in bps: `(fast - slow) / slow * 10000`.
- Buy/Sell thresholds trigger actions; otherwise hold.
- All actions pass risk checks first (daily loss, max position, per-trade cap).

**中文**：
- 使用行情序列计算快慢均线。
- 信号强度（bps）：`(fast - slow) / slow * 10000`。
- 超过买入/卖出阈值才执行，否则保持观望。
- 所有动作先通过风控（单日亏损、最大仓位、单笔额度）。

## 4) Execution Flow / 执行流程
1. Load config + wallet
2. Pull market price
3. Generate signal
4. Risk gate
5. Build quote/swap tx (and approve when needed)
6. Sign + submit on Base
7. Receipt check (`status=1` required)
8. Persist logs + report metrics

## 5) Risk Controls / 风控规则
- `RISK_MAX_DAILY_LOSS_USD`
- `RISK_MAX_POSITION_USD`
- `PER_TRADE_USD`
- `SLIPPAGE_BPS`
- Reverted tx is always treated as failed execution

## 6) Deliverables / 交付物
- Source code with GitHub CI
- Strategy and flow docs (`docs/STRATEGY.md`, `docs/FLOW.md`)
- Runtime logs (`data/trades.jsonl`)
- Analytics report (`--report`, optional `--report-json`)

## 7) Repro Steps / 复现步骤
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
okx-contest-bot --dry-run
okx-contest-bot --report
```

## 8) Notes / 说明
**EN**: Start with dry-run and low notional live mode before scaling.

**中文**：建议先 dry-run 验证，再小额实盘，稳定后再扩仓。
