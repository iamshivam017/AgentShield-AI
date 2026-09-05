import httpx
import pytest

from app.core.config import Settings
from app.domain.razorpay import RazorpayService, RazorpayUnavailableError


@pytest.mark.anyio
async def test_razorpay_order_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/orders"
        assert request.headers["authorization"].startswith("Basic ")
        body = __import__("json").loads(request.content)
        assert body["amount"] == 875_000
        assert body["currency"] == "INR"
        return httpx.Response(
            200,
            json={
                "id": "order_test_123",
                "amount": 875_000,
                "currency": "INR",
                "status": "created",
            },
        )

    settings = Settings(
        environment="test",
        jwt_secret="j" * 40,
        razorpay_key_id="rzp_test_public",
        razorpay_key_secret="s" * 24,
    )
    order = await RazorpayService(settings, httpx.MockTransport(handler)).create_order(
        amount_paise=875_000,
        currency="INR",
        receipt="intent-123",
        idempotency_key="intent-test-123",
    )
    assert order.id == "order_test_123"


@pytest.mark.anyio
async def test_razorpay_failure_is_safe() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    settings = Settings(
        environment="test",
        jwt_secret="j" * 40,
        razorpay_key_id="rzp_test_public",
        razorpay_key_secret="s" * 24,
    )
    with pytest.raises(RazorpayUnavailableError, match="failed safely"):
        await RazorpayService(settings, httpx.MockTransport(handler)).create_order(
            amount_paise=100_000,
            currency="INR",
            receipt="intent-123",
            idempotency_key="intent-test-123",
        )
