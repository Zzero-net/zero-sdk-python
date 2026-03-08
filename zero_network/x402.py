"""x402 protocol support for the Zero Network.

The x402 protocol enables machine-to-machine micropayments over HTTP.
When a server responds with ``402 Payment Required``, the client
automatically pays the requested amount and retries the request.

Client usage::

    from zero_network import Wallet
    from zero_network.x402 import x402_fetch

    wallet = Wallet.from_env()
    response = x402_fetch("https://api.example.com/data", wallet)
    # If the server returns 402, the SDK pays and retries automatically.

Server usage (FastAPI/Starlette)::

    from zero_network.x402 import x402_gate

    @app.get("/premium")
    @x402_gate(0.05)  # charge 0.05 Z per request
    async def premium_endpoint(request):
        return {"data": "premium content"}
"""

from __future__ import annotations

import functools
import json
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

import httpx

from .constants import MAX_TRANSFER_UNITS, UNITS_PER_Z

if TYPE_CHECKING:
    from .wallet import Wallet


def x402_fetch(
    url: str,
    wallet: "Wallet",
    *,
    method: str = "GET",
    max_price_z: float = 25.0,
    headers: Optional[Dict[str, str]] = None,
    json_body: Any = None,
    timeout: float = 30.0,
    max_retries: int = 1,
) -> httpx.Response:
    """HTTP fetch with automatic x402 payment (sync).

    Makes an HTTP request. If the server responds with 402 and includes
    payment instructions in the response body, automatically sends payment
    and retries the request with a payment proof header.

    The 402 response body is expected to be JSON with at least::

        {
            "address": "<recipient hex pubkey>",
            "amount": <amount in Z as float>,
        }

    After payment, the retry includes the header::

        X-Zero-Payment: <transaction signature hex>

    Args:
        url: The URL to fetch.
        wallet: Wallet to pay from if 402 is received.
        method: HTTP method (GET, POST, etc.).
        max_price_z: Maximum price willing to pay in Z. Defaults to 25.0.
        headers: Additional headers for the request.
        json_body: JSON body for POST/PUT requests.
        timeout: Request timeout in seconds.
        max_retries: Number of payment retries. Defaults to 1.

    Returns:
        The final httpx.Response (either the original if not 402, or the
        retried response after payment).

    Raises:
        ValueError: If the requested payment exceeds max_price_z.
        httpx.HTTPStatusError: If the retried request also fails.
    """
    req_headers = dict(headers or {})

    with httpx.Client(timeout=timeout) as client:
        resp = client.request(method, url, headers=req_headers, json=json_body)

        retries = 0
        while resp.status_code == 402 and retries < max_retries:
            retries += 1
            payment_info = resp.json()
            address = payment_info.get("address")
            amount_z = float(payment_info.get("amount", 0))

            if not address:
                break

            if amount_z > max_price_z:
                raise ValueError(
                    f"Server requests {amount_z} Z but max_price_z is {max_price_z}"
                )

            # Pay the server
            tx_result = wallet.send(address, amount_z)
            signature = tx_result.get("signature", tx_result.get("hash", ""))

            # Retry with payment proof
            req_headers["X-Zero-Payment"] = signature
            resp = client.request(method, url, headers=req_headers, json=json_body)

    return resp


async def ax402_fetch(
    url: str,
    wallet: "Wallet",
    *,
    method: str = "GET",
    max_price_z: float = 25.0,
    headers: Optional[Dict[str, str]] = None,
    json_body: Any = None,
    timeout: float = 30.0,
    max_retries: int = 1,
) -> httpx.Response:
    """HTTP fetch with automatic x402 payment (async).

    Async version of :func:`x402_fetch`. See that function for full docs.
    """
    req_headers = dict(headers or {})

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(method, url, headers=req_headers, json=json_body)

        retries = 0
        while resp.status_code == 402 and retries < max_retries:
            retries += 1
            payment_info = resp.json()
            address = payment_info.get("address")
            amount_z = float(payment_info.get("amount", 0))

            if not address:
                break

            if amount_z > max_price_z:
                raise ValueError(
                    f"Server requests {amount_z} Z but max_price_z is {max_price_z}"
                )

            tx_result = await wallet.asend(address, amount_z)
            signature = tx_result.get("signature", tx_result.get("hash", ""))

            req_headers["X-Zero-Payment"] = signature
            resp = await client.request(method, url, headers=req_headers, json=json_body)

    return resp


def x402_gate(
    amount_z: float,
    *,
    recipient_address: Optional[str] = None,
) -> Callable:
    """Decorator to gate a Starlette/FastAPI endpoint behind x402 payment.

    When a request arrives without a valid ``X-Zero-Payment`` header, the
    endpoint returns a 402 response with payment instructions. The client
    is expected to pay and retry with the payment proof header.

    Usage::

        from zero_network.x402 import x402_gate

        @app.get("/premium")
        @x402_gate(0.05, recipient_address="aabb...")
        async def premium(request):
            return {"data": "paid content"}

    Args:
        amount_z: Price in Z to charge per request.
        recipient_address: Hex-encoded public key to receive payment.
            If not provided, the 402 response omits the address and the
            client must know it out-of-band.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try to find the Request object from args/kwargs
            request = kwargs.get("request") or (args[0] if args else None)

            # Check for payment header
            payment_proof = None
            if hasattr(request, "headers"):
                payment_proof = request.headers.get("x-zero-payment")

            if not payment_proof:
                # Import here to avoid hard dependency on starlette
                try:
                    from starlette.responses import JSONResponse
                except ImportError:
                    raise ImportError(
                        "starlette is required for x402_gate. "
                        "Install it with: pip install zero-network[x402]"
                    )

                body: Dict[str, Any] = {"amount": amount_z}
                if recipient_address:
                    body["address"] = recipient_address

                return JSONResponse(
                    status_code=402,
                    content=body,
                    headers={"X-Zero-Price": str(amount_z)},
                )

            # Payment header present — proceed with the handler.
            # In a production system you would verify the payment on-chain
            # here before serving the content.
            return await func(*args, **kwargs)

        return wrapper

    return decorator
