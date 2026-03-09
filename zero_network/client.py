"""Low-level HTTP client for the Zero Network RPC API.

Provides both synchronous and asynchronous methods for all API endpoints.
Async methods are prefixed with ``a`` (e.g., ``await client.astatus()``).
Synchronous methods use the same name without prefix and spin up a
short-lived httpx client per call so they work outside of async contexts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .constants import DEFAULT_RPC, TESTNET_FAUCET


class ZeroClient:
    """HTTP client for the Zero Network JSON API.

    Args:
        rpc_url: Base URL of the RPC endpoint. Defaults to ``DEFAULT_RPC``.
        faucet_url: Base URL of the testnet faucet. Defaults to ``TESTNET_FAUCET``.
        timeout: Request timeout in seconds. Defaults to 30.
    """

    def __init__(
        self,
        rpc_url: str = DEFAULT_RPC,
        faucet_url: str = TESTNET_FAUCET,
        timeout: float = 30.0,
    ) -> None:
        self.rpc_url = rpc_url.rstrip("/")
        self.faucet_url = faucet_url.rstrip("/")
        self.timeout = timeout
        self._async_client: Optional[httpx.AsyncClient] = None

    # ── Async client lifecycle ──────────────────────────────────────────

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(timeout=self.timeout)
        return self._async_client

    async def aclose(self) -> None:
        """Close the underlying async HTTP client."""
        if self._async_client is not None and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None

    # ── Sync helpers ────────────────────────────────────────────────────

    def _sync_get(self, path: str) -> Any:
        url = f"{self.rpc_url}{path}"
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.get(url)
            resp.raise_for_status()
            return resp.json()

    def _sync_post(self, url: str, json: Any) -> Any:
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.post(url, json=json)
            resp.raise_for_status()
            return resp.json()

    # ── Async helpers ───────────────────────────────────────────────────

    async def _async_get(self, path: str) -> Any:
        url = f"{self.rpc_url}{path}"
        client = self._get_async_client()
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def _async_post(self, url: str, json: Any) -> Any:
        client = self._get_async_client()
        resp = await client.post(url, json=json)
        resp.raise_for_status()
        return resp.json()

    # ── GET /api/status ─────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Get network status (sync)."""
        return self._sync_get("/api/status")

    async def astatus(self) -> Dict[str, Any]:
        """Get network status (async)."""
        return await self._async_get("/api/status")

    # ── GET /api/balance/:pubkey ────────────────────────────────────────

    def balance(self, pubkey: str) -> Dict[str, Any]:
        """Get account balance (sync).

        Args:
            pubkey: Hex-encoded public key.

        Returns:
            Dict with balance information.
        """
        return self._sync_get(f"/api/balance/{pubkey}")

    async def abalance(self, pubkey: str) -> Dict[str, Any]:
        """Get account balance (async)."""
        return await self._async_get(f"/api/balance/{pubkey}")

    # ── GET /api/account/:pubkey ────────────────────────────────────────

    def account(self, pubkey: str) -> Dict[str, Any]:
        """Get full account state: balance, nonce, head (sync).

        Args:
            pubkey: Hex-encoded public key.

        Returns:
            Dict with balance, nonce, and head fields.
        """
        return self._sync_get(f"/api/account/{pubkey}")

    async def aaccount(self, pubkey: str) -> Dict[str, Any]:
        """Get full account state (async)."""
        return await self._async_get(f"/api/account/{pubkey}")

    # ── GET /api/history/:pubkey ────────────────────────────────────────

    def history(self, pubkey: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get transaction history (sync).

        Args:
            pubkey: Hex-encoded public key.
            limit: Maximum number of transactions to return.

        Returns:
            List of transaction dicts.
        """
        return self._sync_get(f"/api/history/{pubkey}?limit={limit}")

    async def ahistory(self, pubkey: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get transaction history (async)."""
        return await self._async_get(f"/api/history/{pubkey}?limit={limit}")

    # ── POST /api/send ──────────────────────────────────────────────────

    def send(
        self,
        from_hex: str,
        to_hex: str,
        amount_units: int,
        nonce: int,
        signature_hex: str,
    ) -> Dict[str, Any]:
        """Submit a signed transaction (sync).

        Args:
            from_hex: Hex-encoded sender public key.
            to_hex: Hex-encoded recipient public key.
            amount_units: Amount in internal units.
            nonce: Sender nonce.
            signature_hex: Hex-encoded truncated signature (28 bytes).

        Returns:
            API response dict.
        """
        payload = {
            "from": from_hex,
            "to": to_hex,
            "amount": amount_units,
            "nonce": nonce,
            "signature": signature_hex,
        }
        return self._sync_post(f"{self.rpc_url}/api/send", payload)

    async def asend(
        self,
        from_hex: str,
        to_hex: str,
        amount_units: int,
        nonce: int,
        signature_hex: str,
    ) -> Dict[str, Any]:
        """Submit a signed transaction (async)."""
        payload = {
            "from": from_hex,
            "to": to_hex,
            "amount": amount_units,
            "nonce": nonce,
            "signature": signature_hex,
        }
        return await self._async_post(f"{self.rpc_url}/api/send", payload)

    # ── POST /faucet ────────────────────────────────────────────────────

    def faucet(self, address: str) -> Dict[str, Any]:
        """Request testnet funds from the faucet (sync).

        Args:
            address: Hex-encoded public key to fund.

        Returns:
            Faucet response dict.
        """
        return self._sync_post(f"{self.faucet_url}/faucet", {"recipient": address})

    async def afaucet(self, address: str) -> Dict[str, Any]:
        """Request testnet funds from the faucet (async)."""
        return await self._async_post(f"{self.faucet_url}/faucet", {"recipient": address})

    # ── POST /api/bridge/in ──────────────────────────────────────────

    def bridge_in(
        self,
        source_chain: str,
        token: str,
        tx_hash: str,
        zero_recipient: str,
    ) -> Dict[str, Any]:
        """Report an L2 deposit to begin bridge-in (minting ZERO) (sync).

        Args:
            source_chain: Source chain name ("base", "arbitrum").
            token: Token symbol ("USDC", "USDT").
            tx_hash: L2 deposit transaction hash.
            zero_recipient: Hex-encoded Zero public key (64 chars).

        Returns:
            Dict with bridge_id, status, z_amount.
        """
        payload = {
            "source_chain": source_chain,
            "token": token,
            "tx_hash": tx_hash,
            "zero_recipient": zero_recipient,
        }
        return self._sync_post(f"{self.rpc_url}/api/bridge/in", payload)

    async def abridge_in(
        self,
        source_chain: str,
        token: str,
        tx_hash: str,
        zero_recipient: str,
    ) -> Dict[str, Any]:
        """Report an L2 deposit to begin bridge-in (minting ZERO) (async)."""
        payload = {
            "source_chain": source_chain,
            "token": token,
            "tx_hash": tx_hash,
            "zero_recipient": zero_recipient,
        }
        return await self._async_post(f"{self.rpc_url}/api/bridge/in", payload)

    # ── POST /api/bridge/out ─────────────────────────────────────────

    def bridge_out(
        self,
        dest_chain: str,
        token: str,
        dest_address: str,
        z_amount: int,
        from_pubkey: str,
        signature: str,
    ) -> Dict[str, Any]:
        """Initiate bridge-out (burn ZERO -> release tokens on L2) (sync).

        Args:
            dest_chain: Destination chain ("base", "arbitrum").
            token: Token to receive ("USDC", "USDT").
            dest_address: L2 recipient address.
            z_amount: Amount in Z units to burn.
            from_pubkey: Hex-encoded sender's Zero public key.
            signature: Hex-encoded Ed25519 signature over burn request.

        Returns:
            Dict with bridge_id, status.
        """
        payload = {
            "dest_chain": dest_chain,
            "token": token,
            "dest_address": dest_address,
            "z_amount": z_amount,
            "from_pubkey": from_pubkey,
            "signature": signature,
        }
        return self._sync_post(f"{self.rpc_url}/api/bridge/out", payload)

    async def abridge_out(
        self,
        dest_chain: str,
        token: str,
        dest_address: str,
        z_amount: int,
        from_pubkey: str,
        signature: str,
    ) -> Dict[str, Any]:
        """Initiate bridge-out (burn ZERO -> release tokens on L2) (async)."""
        payload = {
            "dest_chain": dest_chain,
            "token": token,
            "dest_address": dest_address,
            "z_amount": z_amount,
            "from_pubkey": from_pubkey,
            "signature": signature,
        }
        return await self._async_post(f"{self.rpc_url}/api/bridge/out", payload)

    # ── GET /api/bridge/status/:bridge_id ────────────────────────────

    def bridge_status(self, bridge_id: str) -> Dict[str, Any]:
        """Get status of a bridge operation (sync).

        Args:
            bridge_id: Bridge operation ID.

        Returns:
            Dict with bridge_id, direction, status, source_chain, token,
            z_amount, attestations, required.
        """
        return self._sync_get(f"/api/bridge/status/{bridge_id}")

    async def abridge_status(self, bridge_id: str) -> Dict[str, Any]:
        """Get status of a bridge operation (async)."""
        return await self._async_get(f"/api/bridge/status/{bridge_id}")
