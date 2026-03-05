from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import time

from web3 import Web3

from .config import Config, load_state_path
from .okx_client import OkxDexClient, OkxApiError
from .risk import RiskManager, RiskState
from .strategy import MovingAverageStrategy


USDC_DECIMALS = 6


def _to_wei(amount: float, decimals: int) -> str:
    return str(int(amount * (10**decimals)))


@dataclass
class RuntimeState:
    ts: str
    price: float
    action: str
    edge_bps: float
    position_usd: float
    daily_realized_pnl_usd: float


class TradingEngine:
    def __init__(self, cfg: Config, dry_run: bool):
        self.cfg = cfg
        self.dry_run = dry_run
        self.client = OkxDexClient(cfg)
        self.strategy = MovingAverageStrategy(
            fast_window=cfg.fast_window,
            slow_window=cfg.slow_window,
            buy_threshold_bps=cfg.buy_threshold_bps,
            sell_threshold_bps=cfg.sell_threshold_bps,
        )
        self.risk_mgr = RiskManager(cfg.risk_max_daily_loss_usd, cfg.risk_max_position_usd)
        self.risk_state = RiskState()
        self.state_path = load_state_path()
        self.trades_path = Path("./data/trades.jsonl")
        self.trades_path.parent.mkdir(parents=True, exist_ok=True)
        self._entry_price: float | None = None
        self.w3 = Web3(Web3.HTTPProvider(cfg.base_rpc_url))

    def _save_runtime(self, s: RuntimeState) -> None:
        payload = asdict(s)
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_trade_event(self, event: dict) -> None:
        self.trades_path.open("a", encoding="utf-8").write(json.dumps(event, ensure_ascii=False) + "\n")

    def _submit_evm_tx(self, tx: dict, nonce: int | None = None) -> str:
        if not self.cfg.evm_private_key or not self.cfg.evm_address:
            raise RuntimeError("EVM_PRIVATE_KEY / EVM_ADDRESS required for live mode")

        from_addr = Web3.to_checksum_address(self.cfg.evm_address)
        chain_id = int(self.cfg.base_chain_index)
        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(from_addr, "pending")

        gas = int(tx.get("gas") or tx.get("gasLimit") or 250000)
        value = int(tx.get("value", "0"))

        tx_obj = {
            "chainId": chain_id,
            "nonce": nonce,
            "to": Web3.to_checksum_address(tx["to"]),
            "data": tx["data"],
            "value": value,
            "gas": gas,
        }

        if tx.get("maxFeePerGas") and tx.get("maxPriorityFeePerGas"):
            tx_obj["maxFeePerGas"] = int(tx["maxFeePerGas"])
            tx_obj["maxPriorityFeePerGas"] = int(tx["maxPriorityFeePerGas"])
        elif tx.get("gasPrice"):
            tx_obj["gasPrice"] = int(tx["gasPrice"])
        else:
            tx_obj["gasPrice"] = int(self.w3.eth.gas_price)

        signed = self.w3.eth.account.sign_transaction(tx_obj, private_key=self.cfg.evm_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def _wait_success(self, tx_hash: str, timeout_sec: int = 120) -> None:
        h = tx_hash if tx_hash.startswith("0x") else f"0x{tx_hash}"
        receipt = self.w3.eth.wait_for_transaction_receipt(h, timeout=timeout_sec, poll_latency=1)
        if int(receipt.status) != 1:
            raise RuntimeError(f"tx reverted: {tx_hash}")

    def _buy(self, price: float) -> str:
        ok, reason = self.risk_mgr.can_open(self.risk_state, self.cfg.per_trade_usd)
        if not ok:
            return f"SKIP BUY ({reason})"

        amount_wei = _to_wei(self.cfg.per_trade_usd, USDC_DECIMALS)
        quote = self.client.get_swap_quote(
            from_token_address=self.cfg.quote_token_address,
            to_token_address=self.cfg.trade_token_address,
            amount_wei=amount_wei,
            slippage_bps=self.cfg.slippage_bps,
        )

        tx_hash = "dry-run"
        approve_tx_hash = ""
        if not self.dry_run:
            base_nonce = self.w3.eth.get_transaction_count(Web3.to_checksum_address(self.cfg.evm_address), "pending")
            approve_tx = self.client.build_approve_transaction(token_contract_address=self.cfg.quote_token_address, approve_amount_wei=amount_wei)
            approve_tx_hash = self._submit_evm_tx(approve_tx, nonce=base_nonce)
            self._wait_success(approve_tx_hash)
            swap_tx = self.client.build_swap_transaction(
                from_token_address=self.cfg.quote_token_address,
                to_token_address=self.cfg.trade_token_address,
                amount_wei=amount_wei,
                slippage_bps=self.cfg.slippage_bps,
            )
            tx_hash = self._submit_evm_tx(swap_tx, nonce=base_nonce + 1)
            self._wait_success(tx_hash)

        self.risk_state.position_usd += self.cfg.per_trade_usd
        self._entry_price = price

        self._append_trade_event(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "event": "BUY",
                "mode": "DRY" if self.dry_run else "LIVE",
                "price": price,
                "usd": self.cfg.per_trade_usd,
                "to_amount": quote.to_token_amount,
                "approve_tx_hash": approve_tx_hash,
                "tx_hash": tx_hash,
            }
        )
        if self.dry_run:
            return f"DRY BUY usd={self.cfg.per_trade_usd:.2f} quote_to={quote.to_token_amount}"
        return f"LIVE BUY approve={approve_tx_hash} swap={tx_hash}"

    def _sell(self, price: float) -> str:
        ok, reason = self.risk_mgr.can_close(self.risk_state)
        if not ok:
            return f"SKIP SELL ({reason})"

        close_usd = min(self.cfg.per_trade_usd, self.risk_state.position_usd)
        amount_wei = _to_wei(close_usd, USDC_DECIMALS)

        quote = self.client.get_swap_quote(
            from_token_address=self.cfg.trade_token_address,
            to_token_address=self.cfg.quote_token_address,
            amount_wei=amount_wei,
            slippage_bps=self.cfg.slippage_bps,
        )

        pnl = 0.0
        if self._entry_price and self._entry_price > 0:
            pnl = close_usd * ((price - self._entry_price) / self._entry_price)
        self.risk_state.daily_realized_pnl_usd += pnl
        self.risk_state.position_usd -= close_usd

        tx_hash = "dry-run"
        approve_tx_hash = ""
        if not self.dry_run:
            base_nonce = self.w3.eth.get_transaction_count(Web3.to_checksum_address(self.cfg.evm_address), "pending")
            approve_tx = self.client.build_approve_transaction(token_contract_address=self.cfg.trade_token_address, approve_amount_wei=amount_wei)
            approve_tx_hash = self._submit_evm_tx(approve_tx, nonce=base_nonce)
            self._wait_success(approve_tx_hash)
            swap_tx = self.client.build_swap_transaction(
                from_token_address=self.cfg.trade_token_address,
                to_token_address=self.cfg.quote_token_address,
                amount_wei=amount_wei,
                slippage_bps=self.cfg.slippage_bps,
            )
            tx_hash = self._submit_evm_tx(swap_tx, nonce=base_nonce + 1)
            self._wait_success(tx_hash)

        self._append_trade_event(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "event": "SELL",
                "mode": "DRY" if self.dry_run else "LIVE",
                "price": price,
                "usd": close_usd,
                "to_amount": quote.to_token_amount,
                "pnl": pnl,
                "approve_tx_hash": approve_tx_hash,
                "tx_hash": tx_hash,
            }
        )
        if self.dry_run:
            return f"DRY SELL usd={close_usd:.2f} quote_to={quote.to_token_amount} pnl={pnl:.2f}"
        return f"LIVE SELL approve={approve_tx_hash} swap={tx_hash} pnl={pnl:.2f}"

    def run(self) -> None:
        cycle = 0
        while True:
            cycle += 1
            try:
                price = self.client.get_price(self.cfg.trade_token_address)
                signal = self.strategy.on_price(price)

                if signal.action == "BUY":
                    result = self._buy(price)
                elif signal.action == "SELL":
                    result = self._sell(price)
                else:
                    result = "HOLD"

                runtime = RuntimeState(
                    ts=datetime.now().isoformat(timespec="seconds"),
                    price=price,
                    action=result,
                    edge_bps=signal.edge_bps,
                    position_usd=self.risk_state.position_usd,
                    daily_realized_pnl_usd=self.risk_state.daily_realized_pnl_usd,
                )
                self._save_runtime(runtime)

                print(
                    f"[{runtime.ts}] price={runtime.price:.6f} edge={runtime.edge_bps:.1f}bps "
                    f"action={runtime.action} pos=${runtime.position_usd:.2f} "
                    f"dailyPnL=${runtime.daily_realized_pnl_usd:.2f}"
                )
            except OkxApiError as e:
                print(f"[{datetime.now().isoformat(timespec='seconds')}] api-error: {e}")
            except Exception as e:
                print(f"[{datetime.now().isoformat(timespec='seconds')}] fatal: {e}")

            if self.cfg.max_cycles > 0 and cycle >= self.cfg.max_cycles:
                print(f"max-cycles reached ({self.cfg.max_cycles}), exit")
                return
            time.sleep(self.cfg.poll_interval_sec)
