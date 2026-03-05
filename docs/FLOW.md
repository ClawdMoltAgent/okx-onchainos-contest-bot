# Trading Flow

## Runtime pipeline

```text
Config -> Signal -> Risk -> Quote -> Approve(if needed) -> Swap -> Receipt Check -> Log/Report
```

## Details
- Config
  - Load env + fallback secrets
  - Resolve wallet address and RPC
- Signal
  - Consume latest market price
  - Compute MA edge and action
- Risk
  - Reject if max loss / max position violated
- Quote & Tx Build
  - OKX v6 `/dex/aggregator/quote` and `/dex/aggregator/swap`
  - For ERC20 source token, build approve tx first
- Submit
  - Sign with local key
  - sendRawTransaction
  - wait_for_transaction_receipt
- Validation
  - success only if `receipt.status == 1`
- Persistence
  - `data/trades.jsonl`
  - `data/runtime_state.json`
  - analytics report via `--report`

## Failure handling
- API error: skip cycle, retry next poll
- Revert: mark failure in logs, do not count as fill
- Nonce/rate-limit: backoff and retry next cycle
