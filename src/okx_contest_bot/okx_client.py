from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any
import urllib.parse

import requests

from .config import Config


class OkxApiError(RuntimeError):
    pass


@dataclass
class QuoteResult:
    from_token_amount: str
    to_token_amount: str
    price_impact_pct: float
    raw: dict[str, Any]


class OkxDexClient:
    def __init__(self, cfg: Config, timeout_sec: int = 15):
        self.cfg = cfg
        self.base_url = cfg.okx_api_base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        message = f"{timestamp}{method.upper()}{request_path}{body}"
        mac = hmac.new(self.cfg.okx_secret_key.encode(), message.encode(), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode()

    def _base_headers(self, method: str, request_path: str, body: str = "") -> dict[str, str]:
        ts = self._timestamp()
        sign = self._sign(ts, method, request_path, body)
        h = {
            "OK-ACCESS-KEY": self.cfg.okx_api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self.cfg.okx_passphrase,
            "Content-Type": "application/json",
        }
        if self.cfg.okx_project_id:
            h["OK-ACCESS-PROJECT"] = self.cfg.okx_project_id
        return h

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        request_path = f"{path}?{query}" if query else path
        r = requests.get(
            f"{self.base_url}{path}",
            params=params,
            headers=self._base_headers("GET", request_path),
            timeout=self.timeout_sec,
        )
        data = r.json()
        if r.status_code >= 400:
            raise OkxApiError(f"HTTP {r.status_code}: {data}")
        if str(data.get("code", "0")) not in ("0", ""):
            raise OkxApiError(f"OKX error: {data}")
        return data

    def _post(self, path: str, payload: Any) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"))
        r = requests.post(
            f"{self.base_url}{path}",
            data=body,
            headers=self._base_headers("POST", path, body),
            timeout=self.timeout_sec,
        )
        data = r.json()
        if r.status_code >= 400:
            raise OkxApiError(f"HTTP {r.status_code}: {data}")
        if str(data.get("code", "0")) not in ("0", ""):
            raise OkxApiError(f"OKX error: {data}")
        return data

    def get_price(self, token_address: str) -> float:
        data = self._post(
            "/api/v6/dex/market/price",
            [{"chainIndex": self.cfg.base_chain_index, "tokenContractAddress": token_address}],
        )
        items = data.get("data", [])
        if not items:
            raise OkxApiError(f"No price data returned: {data}")
        price = items[0].get("price") or items[0].get("tokenPrice")
        if price is None:
            raise OkxApiError(f"Price missing in response: {data}")
        return float(price)

    def get_swap_quote(self, from_token_address: str, to_token_address: str, amount_wei: str, slippage_bps: int) -> QuoteResult:
        data = self._get(
            "/api/v6/dex/aggregator/quote",
            {
                "chainIndex": self.cfg.base_chain_index,
                "fromTokenAddress": from_token_address,
                "toTokenAddress": to_token_address,
                "amount": amount_wei,
                "slippagePercent": slippage_bps / 10000,
                "userWalletAddress": self.cfg.evm_address,
            },
        )
        items = data.get("data", [])
        if not items:
            raise OkxApiError(f"No quote data returned: {data}")
        item = items[0]
        rr = item.get("routerResult", item)
        return QuoteResult(
            from_token_amount=str(rr.get("fromTokenAmount", amount_wei)),
            to_token_amount=str(rr.get("toTokenAmount", "0")),
            price_impact_pct=float(rr.get("priceImpactPercent", rr.get("priceImpactPercentage", 0.0))),
            raw=item,
        )

    def build_swap_transaction(self, from_token_address: str, to_token_address: str, amount_wei: str, slippage_bps: int) -> dict[str, Any]:
        data = self._get(
            "/api/v6/dex/aggregator/swap",
            {
                "chainIndex": self.cfg.base_chain_index,
                "fromTokenAddress": from_token_address,
                "toTokenAddress": to_token_address,
                "amount": amount_wei,
                "slippagePercent": slippage_bps / 10000,
                "userWalletAddress": self.cfg.evm_address,
            },
        )
        items = data.get("data", [])
        if not items:
            raise OkxApiError(f"No swap tx data returned: {data}")
        return items[0].get("tx", {})

    def build_approve_transaction(self, token_contract_address: str, approve_amount_wei: str) -> dict[str, Any]:
        data = self._get(
            "/api/v6/dex/aggregator/approve-transaction",
            {
                "chainIndex": self.cfg.base_chain_index,
                "tokenContractAddress": token_contract_address,
                "approveAmount": approve_amount_wei,
            },
        )
        items = data.get("data", [])
        if not items:
            raise OkxApiError(f"No approve tx data returned: {data}")
        x = items[0]
        return {
            # approve() is called on token contract; dexContractAddress is spender argument encoded in data
            "to": token_contract_address,
            "data": x.get("data"),
            "gas": x.get("gasLimit"),
            "gasPrice": x.get("gasPrice"),
            "value": "0",
        }

    def list_all_tokens(self) -> list[dict[str, Any]]:
        data = self._get("/api/v6/dex/aggregator/all-tokens", {"chainIndex": self.cfg.base_chain_index})
        return data.get("data", [])
