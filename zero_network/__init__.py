"""Zero Network Python SDK — stablecoin microtransactions for AI agents.

Quick start::

    from zero_network import Wallet

    # Create a new wallet
    wallet = Wallet.create()
    print(wallet.address)

    # Or restore from seed
    wallet = Wallet.from_seed("abcd1234...")

    # Or from environment variable ZERO_KEY
    wallet = Wallet.from_env()

    # Check balance (1 Z = $0.01 USD)
    print(wallet.balance(), "Z")

    # Send funds
    wallet.send("recipient_pubkey_hex", 1.0)  # send 1 Z

For x402 auto-paying HTTP requests::

    from zero_network.x402 import x402_fetch
    response = x402_fetch("https://api.example.com/data", wallet)
"""

from __future__ import annotations

from .client import ZeroClient
from .constants import (
    BRIDGE_OUT_FEE_UNITS,
    DEFAULT_RPC,
    FEE_UNITS,
    MAX_TRANSFER_UNITS,
    TESTNET_FAUCET,
    UNITS_PER_Z,
)
from .transaction import Transfer, build_transfer, parse_transfer, sign_transfer
from .wallet import Wallet

__version__ = "0.2.0"

__all__ = [
    # Core
    "Wallet",
    "ZeroClient",
    # Transaction
    "Transfer",
    "build_transfer",
    "sign_transfer",
    "parse_transfer",
    # Constants
    "UNITS_PER_Z",
    "FEE_UNITS",
    "BRIDGE_OUT_FEE_UNITS",
    "MAX_TRANSFER_UNITS",
    "DEFAULT_RPC",
    "TESTNET_FAUCET",
    # Version
    "__version__",
]


# ── Convenience functions ───────────────────────────────────────────────


def get_balance(address: str, rpc_url: str = DEFAULT_RPC) -> float:
    """Quick balance check without creating a Wallet.

    Args:
        address: Hex-encoded public key.
        rpc_url: RPC endpoint URL.

    Returns:
        Balance in Z as a float.
    """
    client = ZeroClient(rpc_url=rpc_url)
    data = client.balance(address)
    return data.get("balance", 0) / UNITS_PER_Z


def get_account(address: str, rpc_url: str = DEFAULT_RPC) -> dict:
    """Quick account state lookup without creating a Wallet.

    Args:
        address: Hex-encoded public key.
        rpc_url: RPC endpoint URL.

    Returns:
        Dict with balance, nonce, and head fields.
    """
    client = ZeroClient(rpc_url=rpc_url)
    return client.account(address)


def get_status(rpc_url: str = DEFAULT_RPC) -> dict:
    """Quick network status check.

    Args:
        rpc_url: RPC endpoint URL.

    Returns:
        Network status dict.
    """
    client = ZeroClient(rpc_url=rpc_url)
    return client.status()
