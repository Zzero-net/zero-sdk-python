"""High-level Wallet for the Zero Network.

Wraps key management, transaction building, signing, and RPC submission
into a single convenient interface. All network methods have both sync
and async variants (async prefixed with ``a``).

Example (sync)::

    from zero_network import Wallet

    w = Wallet.create()
    print(w.address)
    w.faucet()                        # get testnet funds
    print(w.balance())                # check balance
    w.send("deadbeef..." , 1.0)       # send 1 Z

Example (async)::

    w = Wallet.create()
    await w.afaucet()
    print(await w.abalance())
    await w.asend("deadbeef...", 1.0)
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional

from nacl.signing import SigningKey

from .client import ZeroClient
from .constants import (
    DEFAULT_RPC,
    FEE_UNITS,
    MAX_TRANSFER_UNITS,
    TESTNET_FAUCET,
    UNITS_PER_Z,
)
from .transaction import build_transfer, sign_transfer


class Wallet:
    """Zero Network wallet — manages a single Ed25519 keypair.

    Use the class methods to create or restore a wallet:

    - ``Wallet.create()`` — fresh random keypair
    - ``Wallet.from_seed(hex)`` — restore from a 32-byte seed (hex string)
    - ``Wallet.from_env()`` — restore from the ``ZERO_KEY`` environment variable

    Args:
        signing_key: A ``nacl.signing.SigningKey`` instance.
        rpc_url: RPC endpoint URL. Defaults to ``DEFAULT_RPC``.
        faucet_url: Testnet faucet URL. Defaults to ``TESTNET_FAUCET``.
    """

    def __init__(
        self,
        signing_key: SigningKey,
        rpc_url: str = DEFAULT_RPC,
        faucet_url: str = TESTNET_FAUCET,
    ) -> None:
        self._signing_key = signing_key
        self._verify_key = signing_key.verify_key
        self._client = ZeroClient(rpc_url=rpc_url, faucet_url=faucet_url)

    # ── Constructors ────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        rpc_url: str = DEFAULT_RPC,
        faucet_url: str = TESTNET_FAUCET,
    ) -> "Wallet":
        """Generate a new random Ed25519 keypair.

        Returns:
            A new Wallet instance.
        """
        return cls(SigningKey.generate(), rpc_url=rpc_url, faucet_url=faucet_url)

    @classmethod
    def from_seed(
        cls,
        seed_hex: str,
        rpc_url: str = DEFAULT_RPC,
        faucet_url: str = TESTNET_FAUCET,
    ) -> "Wallet":
        """Restore a wallet from a 32-byte hex-encoded seed.

        Args:
            seed_hex: 64-character hex string (32 bytes).

        Returns:
            Wallet restored from the given seed.

        Raises:
            ValueError: If seed_hex is not a valid 32-byte hex string.
        """
        seed_bytes = bytes.fromhex(seed_hex)
        if len(seed_bytes) != 32:
            raise ValueError(f"Seed must be 32 bytes, got {len(seed_bytes)}")
        return cls(SigningKey(seed_bytes), rpc_url=rpc_url, faucet_url=faucet_url)

    @classmethod
    def from_env(
        cls,
        env_var: str = "ZERO_KEY",
        rpc_url: str = DEFAULT_RPC,
        faucet_url: str = TESTNET_FAUCET,
    ) -> "Wallet":
        """Restore a wallet from an environment variable.

        Args:
            env_var: Name of the environment variable containing the hex seed.
                Defaults to ``ZERO_KEY``.

        Returns:
            Wallet restored from the environment variable.

        Raises:
            EnvironmentError: If the environment variable is not set.
        """
        seed_hex = os.environ.get(env_var)
        if not seed_hex:
            raise EnvironmentError(
                f"Environment variable {env_var} is not set. "
                "Set it to your 64-character hex seed."
            )
        return cls.from_seed(seed_hex, rpc_url=rpc_url, faucet_url=faucet_url)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def address(self) -> str:
        """Hex-encoded public key (64 characters)."""
        return bytes(self._verify_key).hex()

    @property
    def public_key_bytes(self) -> bytes:
        """Raw 32-byte public key."""
        return bytes(self._verify_key)

    @property
    def seed_hex(self) -> str:
        """Hex-encoded 32-byte seed for backup/restore.

        Keep this secret! Anyone with the seed can spend your funds.
        """
        return bytes(self._signing_key).hex()[:64]

    # ── Internal helpers ────────────────────────────────────────────────

    def _z_to_units(self, amount_z: float) -> int:
        """Convert Z amount to internal units, rounding to nearest int."""
        units = round(amount_z * UNITS_PER_Z)
        if units <= 0:
            raise ValueError(f"Amount must be positive, got {amount_z} Z")
        if units > MAX_TRANSFER_UNITS:
            raise ValueError(
                f"Amount {amount_z} Z exceeds max transfer of "
                f"{MAX_TRANSFER_UNITS / UNITS_PER_Z} Z"
            )
        return units

    def _build_and_sign(self, to_hex: str, amount_units: int, nonce: int) -> dict:
        """Build, sign a transfer and return the JSON-ready payload."""
        to_bytes = bytes.fromhex(to_hex)
        if len(to_bytes) != 32:
            raise ValueError(f"Recipient address must be 32 bytes (64 hex chars), got {len(to_bytes)}")

        unsigned = build_transfer(
            from_pubkey=self.public_key_bytes,
            to_pubkey=to_bytes,
            amount_units=amount_units,
            nonce=nonce,
        )
        signed = sign_transfer(unsigned, self._signing_key)
        sig_hex = signed[72:100].hex()

        return {
            "from_hex": self.address,
            "to_hex": to_hex,
            "amount_units": amount_units,
            "nonce": nonce,
            "signature_hex": sig_hex,
        }

    # ── Sync network methods ───────────────────────────────────────────

    def balance(self) -> float:
        """Query current balance in Z (sync).

        Returns:
            Balance as a float in Z (e.g. 1.5 means 1.50 Z = $0.015).
        """
        data = self._client.balance(self.address)
        units = data.get("balance", 0)
        return units / UNITS_PER_Z

    def account(self) -> Dict[str, Any]:
        """Get full account state (sync).

        Returns:
            Dict with ``balance`` (units), ``nonce``, and ``head`` fields.
        """
        return self._client.account(self.address)

    def history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transaction history (sync).

        Args:
            limit: Maximum number of transactions to return.

        Returns:
            List of transaction dicts.
        """
        return self._client.history(self.address, limit=limit)

    def send(self, to: str, amount_z: float) -> Dict[str, Any]:
        """Send Z to another address (sync).

        Automatically fetches the current nonce, builds the transaction,
        signs it, and submits it to the network.

        Args:
            to: Recipient's hex-encoded public key (64 characters).
            amount_z: Amount to send in Z (e.g., 0.5 for 0.50 Z).

        Returns:
            API response dict from the network.

        Raises:
            ValueError: If amount is invalid or address is malformed.
        """
        amount_units = self._z_to_units(amount_z)

        # Fetch current nonce
        acct = self._client.account(self.address)
        nonce = acct.get("nonce", 0)

        payload = self._build_and_sign(to, amount_units, nonce)
        return self._client.send(**payload)

    def faucet(self) -> Dict[str, Any]:
        """Request testnet funds from the faucet (sync).

        Returns:
            Faucet response dict.
        """
        return self._client.faucet(self.address)

    # ── Async network methods ──────────────────────────────────────────

    async def abalance(self) -> float:
        """Query current balance in Z (async)."""
        data = await self._client.abalance(self.address)
        units = data.get("balance", 0)
        return units / UNITS_PER_Z

    async def aaccount(self) -> Dict[str, Any]:
        """Get full account state (async)."""
        return await self._client.aaccount(self.address)

    async def ahistory(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transaction history (async)."""
        return await self._client.ahistory(self.address, limit=limit)

    async def asend(self, to: str, amount_z: float) -> Dict[str, Any]:
        """Send Z to another address (async).

        Automatically fetches the current nonce, builds the transaction,
        signs it, and submits it to the network.

        Args:
            to: Recipient's hex-encoded public key (64 characters).
            amount_z: Amount to send in Z (e.g., 0.5 for 0.50 Z).

        Returns:
            API response dict from the network.
        """
        amount_units = self._z_to_units(amount_z)

        acct = await self._client.aaccount(self.address)
        nonce = acct.get("nonce", 0)

        payload = self._build_and_sign(to, amount_units, nonce)
        return await self._client.asend(**payload)

    async def afaucet(self) -> Dict[str, Any]:
        """Request testnet funds from the faucet (async)."""
        return await self._client.afaucet(self.address)

    async def aclose(self) -> None:
        """Close the underlying async HTTP client."""
        await self._client.aclose()

    # ── Dunder methods ──────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"Wallet(address={self.address!r})"

    def __str__(self) -> str:
        return self.address
