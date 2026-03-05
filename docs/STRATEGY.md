# Strategy Spec (OKX OnchainOS Contest)

## Scope
- Chain: Base (8453)
- Pair (default): USDC / WETH
- Mode: event-loop, low notional, strict risk-first

## Signal Logic (v1)
- Price source: OKX DEX market price endpoint
- Indicators:
  - Fast MA: `FAST_WINDOW` (default 5)
  - Slow MA: `SLOW_WINDOW` (default 12)
- Signal edge:
  - `edge_bps = (fast - slow) / slow * 10000`
- Actions:
  - BUY when `edge_bps >= BUY_THRESHOLD_BPS`
  - SELL when `edge_bps <= -SELL_THRESHOLD_BPS`
  - else HOLD

## Execution Logic
1. Pull price
2. Update MA signal
3. Risk gate
4. Build quote/swap tx via OKX v6 aggregator
5. Submit tx on Base
6. Wait receipt (`status=1` required)
7. Persist runtime + trade log

## Risk Controls
- Max daily loss: `RISK_MAX_DAILY_LOSS_USD`
- Max position: `RISK_MAX_POSITION_USD`
- Per trade notional: `PER_TRADE_USD`
- Slippage: `SLIPPAGE_BPS`
- Hard rule: reverted tx is failure, not counted as filled

## Improvement Roadmap (v2)
- Multi-token ranking + top-N rotation
- Volatility filter (ATR/realized vol)
- Time-window filter (avoid thin-liquidity periods)
- Dynamic position sizing by realized volatility
- Forced close / max holding time
