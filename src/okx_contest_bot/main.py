import argparse
import json
from pathlib import Path

from .analytics import pretty_print_report, summarize_trades
from .config import load_config
from .engine import TradingEngine



def main() -> None:
    parser = argparse.ArgumentParser(description="OKX OnchainOS contest bot")
    parser.add_argument("--dry-run", action="store_true", help="simulate only, no on-chain submit")
    parser.add_argument("--live", action="store_true", help="enable live transaction building")
    parser.add_argument("--report", action="store_true", help="print profitability report from trade logs")
    parser.add_argument("--report-json", default="", help="optional output json path, e.g. ./data/report.json")
    args = parser.parse_args()

    if args.report:
        summary = summarize_trades("./data/trades.jsonl")
        print(pretty_print_report(summary))
        if args.report_json:
            p = Path(args.report_json)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"saved report json -> {p}")
        return

    if args.dry_run and args.live:
        raise SystemExit("Use either --dry-run or --live, not both")

    cfg = load_config()
    dry_run = True if not args.live else False
    if args.dry_run:
        dry_run = True

    print("OKX contest bot starting")
    print(f"mode={'DRY' if dry_run else 'LIVE'} chain={cfg.base_chain_index} pair={cfg.quote_token_symbol}/{cfg.trade_token_symbol}")
    print(
        f"risk(maxDailyLoss=${cfg.risk_max_daily_loss_usd}, maxPosition=${cfg.risk_max_position_usd}, perTrade=${cfg.per_trade_usd})"
    )

    engine = TradingEngine(cfg=cfg, dry_run=dry_run)
    engine.run()


if __name__ == "__main__":
    main()
