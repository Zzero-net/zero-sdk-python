"""Network constants for the Zero Network."""

# 1 Z = 100 units internally
UNITS_PER_Z: int = 100

# Flat transaction fee: 0.01 Z = 1 unit
FEE_UNITS: int = 1

# Maximum transfer: 25 Z = 2500 units
MAX_TRANSFER_UNITS: int = 2500

# Account creation cost: 1.00 Z = 100 units (deducted on first receive)
ACCOUNT_CREATION_UNITS: int = 100

# Transaction size in bytes: from[32] + to[32] + amount[4] + nonce[4] + signature[28]
TX_SIZE: int = 100

# Default RPC endpoint
DEFAULT_RPC: str = "https://rpc.zzero.net"

# Testnet faucet endpoint
TESTNET_FAUCET: str = "http://157.180.56.48:8093"
