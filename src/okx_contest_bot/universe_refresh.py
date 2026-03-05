from __future__ import annotations

import json
from pathlib import Path

from .config import Config
from .okx_client import OkxDexClient, OkxApiError


USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH = "0x4200000000000000000000000000000000000006"

STABLE_SYMBOL_HINTS = {
    "USDC",
    "USDT",
    "DAI",
    "USDE",
    "USDBC",
    "FDUSD",
    "TUSD",
    "SUSDS",
    "AXLUSDC",
    "GHO",
}


def refresh_base_universe(cfg: Config, out_path: str = "./data/base_token_universe.json", max_tokens: int = 20) -> dict:
    client = OkxDexClient(cfg)
    raw_tokens = client.list_all_tokens()

    scored: list[tuple[float, dict]] = []
    for t in raw_tokens:
        symbol = str(t.get("tokenSymbol", "")).upper()
        addr = str(t.get("tokenContractAddress", ""))
        if not symbol or not addr:
            continue
        if addr.lower() in {USDC.lower()}:
            continue
        if symbol in STABLE_SYMBOL_HINTS or "USD" in symbol:
            continue

        # quality gate: must be quoteable from USDC and from WETH on Base
        score = 0.0
        try:
            q1 = client.get_swap_quote(USDC, addr, str(1_000_000), cfg.slippage_bps)  # 1 USDC
            if int(q1.to_token_amount) > 0:
                score += 1.0
            score -= min(abs(float(q1.price_impact_pct)), 20.0) / 100.0
        except (OkxApiError, ValueError):
            continue

        try:
            q2 = client.get_swap_quote(WETH, addr, str(10**14), cfg.slippage_bps)  # 0.0001 WETH
            if int(q2.to_token_amount) > 0:
                score += 1.0
            score -= min(abs(float(q2.price_impact_pct)), 20.0) / 100.0
        except (OkxApiError, ValueError):
            pass

        # lightweight penalty for suspect symbols
        if any(x in symbol for x in ["INU", "DOG", "MOON"]):
            score -= 0.15

        scored.append(
            (
                score,
                {
                    "symbol": symbol,
                    "address": addr,
                    "chainIndex": cfg.base_chain_index,
                },
            )
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [x[1] for x in scored[:max_tokens]]

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "total_seen": len(raw_tokens),
        "selected": len(selected),
        "out_path": str(p),
        "top_symbols": [x["symbol"] for x in selected[:10]],
    }
