# zero-network

Python SDK for the [Zero Network](https://zzero.net) — stablecoin microtransactions for AI agents.

**1 Z = $0.01 USD** | Ed25519 signatures | 100-byte transactions | x402 support

## Install

```bash
pip install zero-network
```

For x402 server-side gating (requires Starlette/FastAPI):

```bash
pip install zero-network[x402]
```

## Quick Start

```python
from zero_network import Wallet

# Create a new wallet
wallet = Wallet.create()
print(wallet.address)      # hex-encoded public key
print(wallet.seed_hex)     # save this! needed to restore

# Restore from seed
wallet = Wallet.from_seed("your_64char_hex_seed")

# Or from ZERO_KEY environment variable
wallet = Wallet.from_env()

# Request testnet funds
wallet.faucet()

# Check balance
print(wallet.balance(), "Z")

# Send 0.50 Z to another address
wallet.send("recipient_pubkey_hex_64chars", 0.5)

# Transaction history
for tx in wallet.history(limit=5):
    print(tx)
```

## Async Usage

All wallet methods have async variants prefixed with `a`:

```python
import asyncio
from zero_network import Wallet

async def main():
    wallet = Wallet.create()
    await wallet.afaucet()
    balance = await wallet.abalance()
    print(f"{balance} Z")
    await wallet.asend("recipient_pubkey_hex", 1.0)
    await wallet.aclose()

asyncio.run(main())
```

## x402 Auto-Paying Client

Fetch paywalled resources with automatic micropayment:

```python
from zero_network import Wallet
from zero_network.x402 import x402_fetch

wallet = Wallet.from_env()
response = x402_fetch("https://api.example.com/premium", wallet, max_price_z=0.10)
print(response.json())
```

If the server returns `402 Payment Required` with a JSON body containing `{"address": "...", "amount": 0.05}`, the SDK pays automatically and retries.

## x402 Server-Side Gating

Gate FastAPI/Starlette endpoints behind a paywall:

```python
from fastapi import FastAPI, Request
from zero_network.x402 import x402_gate

app = FastAPI()

@app.get("/premium")
@x402_gate(0.05, recipient_address="your_pubkey_hex")
async def premium(request: Request):
    return {"data": "premium content"}
```

## Low-Level Client

```python
from zero_network import ZeroClient

client = ZeroClient()
print(client.status())
print(client.balance("pubkey_hex"))
print(client.account("pubkey_hex"))
```

## API Reference

### Wallet

| Method | Description |
|--------|-------------|
| `Wallet.create()` | Generate new Ed25519 keypair |
| `Wallet.from_seed(hex)` | Restore from 32-byte hex seed |
| `Wallet.from_env(var="ZERO_KEY")` | Restore from environment variable |
| `wallet.address` | Hex-encoded public key |
| `wallet.seed_hex` | Hex-encoded seed (keep secret!) |
| `wallet.balance()` / `abalance()` | Query balance in Z |
| `wallet.send(to, amount_z)` / `asend()` | Send Z (auto nonce + sign) |
| `wallet.account()` / `aaccount()` | Full account state |
| `wallet.history(limit)` / `ahistory()` | Transaction history |
| `wallet.faucet()` / `afaucet()` | Request testnet funds |

### ZeroClient

| Method | Description |
|--------|-------------|
| `client.status()` / `astatus()` | Network status |
| `client.balance(pubkey)` / `abalance()` | Account balance |
| `client.account(pubkey)` / `aaccount()` | Account state |
| `client.history(pubkey, limit)` / `ahistory()` | Transaction history |
| `client.send(...)` / `asend()` | Submit signed transaction |
| `client.faucet(address)` / `afaucet()` | Request testnet funds |

### Transaction Helpers

| Function | Description |
|----------|-------------|
| `build_transfer(from_pub, to_pub, amount, nonce)` | Build unsigned 72-byte tx |
| `sign_transfer(unsigned_tx, signing_key)` | Sign and return 100-byte tx |
| `parse_transfer(tx_bytes)` | Parse 100-byte tx into Transfer |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `UNITS_PER_Z` | 100 | Internal units per 1 Z |
| `FEE_UNITS` | 1 | Flat transfer fee (0.01 Z) |
| `BRIDGE_OUT_FEE_UNITS` | 50 | Bridge-out fee (0.5 Z) |
| `MAX_TRANSFER_UNITS` | 2500 | Max transfer (25 Z) |
| `DEFAULT_RPC` | `https://rpc.zzero.net` | Default RPC endpoint |
| `TESTNET_FAUCET` | `http://157.180.56.48:8093` | Testnet faucet |

## Network Details

- **Denomination**: 1 Z = $0.01 USD = 100 internal units
- **Transfer fee**: 0.01 Z (1 unit) flat per transaction
- **Bridge-out fee**: 0.5 Z (50 units) per withdrawal
- **Max transfer**: 25 Z (2500 units)
- **Account creation**: 1.00 Z deducted on first receive
- **Signatures**: Ed25519 (compatible with tweetnacl/dalek)
- **Hashing**: BLAKE3
- **Transaction size**: 100 bytes

## License

MIT
