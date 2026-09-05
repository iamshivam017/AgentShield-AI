import base64
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings


class RazorpayUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class RazorpayOrder:
    id: str
    amount: int
    currency: str
    status: str


class RazorpayService:
    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings = settings
        self.transport = transport

    async def create_order(
        self, *, amount_paise: int, currency: str, receipt: str, idempotency_key: str
    ) -> RazorpayOrder:
        if not self.settings.razorpay_test_mode:
            raise RazorpayUnavailableError("Live mode is intentionally disabled")
        if not self.settings.razorpay_key_id or not self.settings.razorpay_key_secret:
            # A deterministic test-mode stand-in keeps the end-to-end demo operational
            # without pretending an external Razorpay call succeeded.
            return RazorpayOrder(
                id=f"order_demo_{idempotency_key[-12:]}",
                amount=amount_paise,
                currency=currency,
                status="demo_created",
            )
        credentials = base64.b64encode(
            f"{self.settings.razorpay_key_id}:{self.settings.razorpay_key_secret}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt[:40],
            "notes": {"agentshield_idempotency_key": idempotency_key[:128]},
        }
        try:
            async with httpx.AsyncClient(timeout=8.0, transport=self.transport) as client:
                response = await client.post(
                    "https://api.razorpay.com/v1/orders", headers=headers, json=payload
                )
                response.raise_for_status()
                body = response.json()
                return RazorpayOrder(
                    id=str(body["id"]),
                    amount=int(body["amount"]),
                    currency=str(body["currency"]),
                    status=str(body["status"]),
                )
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise RazorpayUnavailableError(
                "Razorpay test-mode order creation failed safely"
            ) from exc
