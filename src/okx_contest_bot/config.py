from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    okx_api_key: str
    okx_secret_key: str
    okx_passphrase: str
    okx_project_id: str
    evm_private_key: str
    evm_address: str
    base_chain_index: str = "8453"

    risk_max_daily_loss_usd: float = 20.0
    risk_max_position_usd: float = 40.0
    slippage_bps: int = 50
    poll_interval_sec: int = 30
    max_cycles: int = 0

    quote_token_symbol: str = "USDC"
    quote_token_address: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    trade_token_symbol: str = "WETH"
    trade_token_address: str = "0x4200000000000000000000000000000000000006"
    per_trade_usd: float = 20.0

    # Auto token selector
    token_candidates: list[dict[str, str]] | None = None
    selector_min_edge_bps: float = 1.0

    fast_window: int = 5
    slow_window: int = 12
    buy_threshold_bps: int = 10
    sell_threshold_bps: int = 10

    okx_api_base_url: str = "https://web3.okx.com"
    base_rpc_url: str = "https://mainnet.base.org"


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    return float(v) if v not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return int(v) if v not in (None, "") else default


def _parse_candidates(raw: str) -> list[dict[str, str]]:
    # format: SYMBOL:0xaddr,SYMBOL2:0xaddr2
    out: list[dict[str, str]] = []
    for part in raw.split(","):
        s = part.strip()
        if not s or ":" not in s:
            continue
        sym, addr = s.split(":", 1)
        out.append({"symbol": sym.strip().upper(), "address": addr.strip()})
    return out


def _load_base_universe(path: str, base_chain_index: str) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        arr = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[dict[str, str]] = []
    for x in arr:
        if str(x.get("chainIndex", "")) != str(base_chain_index):
            continue
        sym = str(x.get("symbol", "")).strip().upper()
        addr = str(x.get("address", "")).strip()
        if sym and addr:
            out.append({"symbol": sym, "address": addr})
    return out


def _load_fallback_okx_secrets() -> dict[str, str]:
    p = Path("/Users/mini4/.openclaw/workspace/data/okx/.env.json")
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _normalize_private_key(v: str) -> str:
    vv = v.strip()
    if vv.startswith("0x"):
        vv = vv[2:]
    if len(vv) == 64:
        return "0x" + vv
    return v


def load_config() -> Config:
    load_dotenv()
    fallback = _load_fallback_okx_secrets()

    okx_api_key = os.getenv("OKX_API_KEY", "") or fallback.get("OKX_API_KEY", "")
    okx_secret_key = os.getenv("OKX_SECRET_KEY", "") or fallback.get("OKX_SECRET_KEY", "")
    okx_passphrase = os.getenv("OKX_PASSPHRASE", "") or fallback.get("OKX_PASSPHRASE", "")

    raw_priv = os.getenv("EVM_PRIVATE_KEY", "") or fallback.get("EVM_PRIVATE_KEY", "") or fallback.get("address", "")
    evm_private_key = _normalize_private_key(raw_priv) if raw_priv else ""

    evm_address = os.getenv("EVM_ADDRESS", "") or fallback.get("EVM_ADDRESS", "")
    if not evm_address and evm_private_key:
        try:
            from eth_account import Account

            evm_address = Account.from_key(evm_private_key).address
        except Exception:
            evm_address = ""

    raw_candidates = os.getenv(
        "TOKEN_CANDIDATES",
        "WETH:0x4200000000000000000000000000000000000006,cbBTC:0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf,AERO:0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    )
    universe_path = os.getenv("TOKEN_UNIVERSE_PATH", "./data/base_token_universe.json")
    candidates = _load_base_universe(universe_path, os.getenv("BASE_CHAIN_INDEX", "8453")) or _parse_candidates(raw_candidates)

    cfg = Config(
        okx_api_key=okx_api_key,
        okx_secret_key=okx_secret_key,
        okx_passphrase=okx_passphrase,
        okx_project_id=os.getenv("OKX_PROJECT_ID", "") or fallback.get("OKX_PROJECT_ID", ""),
        evm_private_key=evm_private_key,
        evm_address=evm_address,
        base_chain_index=os.getenv("BASE_CHAIN_INDEX", "8453"),
        risk_max_daily_loss_usd=_env_float("RISK_MAX_DAILY_LOSS_USD", 20.0),
        risk_max_position_usd=_env_float("RISK_MAX_POSITION_USD", 40.0),
        slippage_bps=_env_int("SLIPPAGE_BPS", 50),
        poll_interval_sec=_env_int("POLL_INTERVAL_SEC", 30),
        max_cycles=_env_int("MAX_CYCLES", 0),
        quote_token_symbol=os.getenv("QUOTE_TOKEN_SYMBOL", "USDC"),
        quote_token_address=os.getenv("QUOTE_TOKEN_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
        trade_token_symbol=os.getenv("TRADE_TOKEN_SYMBOL", "WETH"),
        trade_token_address=os.getenv("TRADE_TOKEN_ADDRESS", "0x4200000000000000000000000000000000000006"),
        per_trade_usd=_env_float("PER_TRADE_USD", 20.0),
        token_candidates=candidates,
        selector_min_edge_bps=_env_float("SELECTOR_MIN_EDGE_BPS", 1.0),
        fast_window=_env_int("FAST_WINDOW", 5),
        slow_window=_env_int("SLOW_WINDOW", 12),
        buy_threshold_bps=_env_int("BUY_THRESHOLD_BPS", 10),
        sell_threshold_bps=_env_int("SELL_THRESHOLD_BPS", 10),
        okx_api_base_url=os.getenv("OKX_API_BASE_URL", "https://web3.okx.com"),
        base_rpc_url=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
    )

    if cfg.fast_window <= 0 or cfg.slow_window <= 0 or cfg.fast_window >= cfg.slow_window:
        raise ValueError("FAST_WINDOW must be >0 and < SLOW_WINDOW")
    return cfg


def load_state_path() -> Path:
    p = os.getenv("BOT_STATE_PATH", "./data/runtime_state.json")
    path = Path(p)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_json_tokens_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
