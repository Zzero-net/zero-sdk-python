"""Transaction building and parsing for the Zero Network.

Transaction format (136 bytes total):
    from_pubkey[32] + to_pubkey[32] + amount[4] + nonce[4] + signature[64]

The Ed25519 signature covers the first 72 bytes (from + to + amount + nonce).
The full 64-byte signature is appended, matching the wire format required by
the Zero Network validators.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

from nacl.signing import SigningKey, VerifyKey

from .constants import TX_SIZE


@dataclass(frozen=True)
class Transfer:
    """Parsed transfer transaction."""

    from_pubkey: bytes
    to_pubkey: bytes
    amount_units: int
    nonce: int
    signature: bytes

    @property
    def from_hex(self) -> str:
        return self.from_pubkey.hex()

    @property
    def to_hex(self) -> str:
        return self.to_pubkey.hex()


def build_transfer(
    from_pubkey: bytes,
    to_pubkey: bytes,
    amount_units: int,
    nonce: int,
) -> bytes:
    """Build an unsigned transfer transaction (72 bytes, no signature yet).

    Args:
        from_pubkey: 32-byte sender public key.
        to_pubkey: 32-byte recipient public key.
        amount_units: Amount in internal units (1 Z = 100 units).
        nonce: Sender's current nonce (sequence number).

    Returns:
        72-byte unsigned transaction payload.

    Raises:
        ValueError: If any argument is invalid.
    """
    if len(from_pubkey) != 32:
        raise ValueError(f"from_pubkey must be 32 bytes, got {len(from_pubkey)}")
    if len(to_pubkey) != 32:
        raise ValueError(f"to_pubkey must be 32 bytes, got {len(to_pubkey)}")
    if amount_units < 0 or amount_units > 0xFFFFFFFF:
        raise ValueError(f"amount_units out of u32 range: {amount_units}")
    if nonce < 0 or nonce > 0xFFFFFFFF:
        raise ValueError(f"nonce out of u32 range: {nonce}")

    return from_pubkey + to_pubkey + struct.pack("<I", amount_units) + struct.pack("<I", nonce)


def sign_transfer(unsigned_tx: bytes, signing_key: SigningKey) -> bytes:
    """Sign an unsigned transaction and return the complete 136-byte tx.

    The Ed25519 signature is computed over the 72-byte unsigned payload.
    The full 64-byte signature is appended.

    Args:
        unsigned_tx: 72-byte unsigned transaction from build_transfer().
        signing_key: Ed25519 signing key (nacl.signing.SigningKey).

    Returns:
        136-byte signed transaction ready for submission.

    Raises:
        ValueError: If unsigned_tx is not 72 bytes.
    """
    if len(unsigned_tx) != 72:
        raise ValueError(f"unsigned_tx must be 72 bytes, got {len(unsigned_tx)}")

    signed = signing_key.sign(unsigned_tx)
    # signed.signature is the full 64-byte Ed25519 signature
    return unsigned_tx + signed.signature


def parse_transfer(tx_bytes: bytes) -> Transfer:
    """Parse a signed transaction into its components.

    Accepts 136-byte (full signature) or 100-byte (legacy) format.

    Args:
        tx_bytes: Signed transaction bytes.

    Returns:
        Transfer dataclass with parsed fields.

    Raises:
        ValueError: If tx_bytes is not 136 or 100 bytes.
    """
    LEGACY_TX_SIZE = 100
    if len(tx_bytes) != TX_SIZE and len(tx_bytes) != LEGACY_TX_SIZE:
        raise ValueError(
            f"tx_bytes must be {TX_SIZE} or {LEGACY_TX_SIZE} bytes, got {len(tx_bytes)}"
        )

    from_pubkey = tx_bytes[0:32]
    to_pubkey = tx_bytes[32:64]
    amount_units = struct.unpack("<I", tx_bytes[64:68])[0]
    nonce = struct.unpack("<I", tx_bytes[68:72])[0]
    signature = tx_bytes[72:]

    return Transfer(
        from_pubkey=from_pubkey,
        to_pubkey=to_pubkey,
        amount_units=amount_units,
        nonce=nonce,
        signature=signature,
    )
