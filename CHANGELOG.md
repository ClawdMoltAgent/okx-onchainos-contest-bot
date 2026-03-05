# Changelog

## [0.2.0] - 2026-03-05
### Added
- Complete bot pipeline: signal -> risk -> quote/swap -> receipt check -> logging.
- OKX v6 DEX integration for market, quote, swap, approve-transaction.
- Live transaction signing/broadcast on Base via web3.
- Profitability analytics: win rate, realized PnL, avg PnL, max drawdown, Sharpe (per-trade), profit factor, daily PnL.
- GitHub standard templates and CI workflow.
- Contest docs: strategy, flow, submission (CN/EN).

### Fixed
- Corrected approve transaction target contract for ERC20 approval.
- Added strict receipt status check to prevent false-success logging.
- Improved nonce handling for sequential approve/swap flow.

## [0.1.0] - 2026-03-04
### Added
- Initial scaffold for OKX OnchainOS contest bot.
