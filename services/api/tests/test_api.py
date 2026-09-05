import hashlib
import hmac
import json
from datetime import UTC, datetime

from conftest import TEST_WEBHOOK_SECRET
from fastapi.testclient import TestClient


def intent_payload(key: str, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "idempotency_key": key,
        "agent_id": "agent-shopping-01",
        "merchant_id": "merchant-known",
        "merchant_name": "Paper & Pine",
        "merchant_category": "retail",
        "amount_paise": 125_000,
        "currency": "INR",
        "device_id": "device-known",
        "ip_region": "IN-KA",
        "purpose": "Office supplies",
        "initiated_at": datetime(2026, 9, 5, 10, tzinfo=UTC).isoformat(),
    }
    values.update(overrides)
    return values


def test_auth_is_required(client: TestClient) -> None:
    assert client.get("/api/v1/transactions").status_code == 401


def test_invalid_login_is_generic(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@agentshield.dev", "password": "not-the-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_evaluate_replay_and_dashboard(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = intent_payload("low-risk-0001")
    response = client.post("/api/v1/risk/evaluate", json=payload, headers=auth_headers)
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["decision"] == "ALLOW"
    replay = client.post("/api/v1/risk/evaluate", json=payload, headers=auth_headers)
    assert replay.json()["transaction_id"] == first["transaction_id"]
    summary = client.get("/api/v1/metrics/summary", headers=auth_headers).json()
    assert summary["total"] == 9


def test_idempotency_header_must_match(client: TestClient, auth_headers: dict[str, str]) -> None:
    headers = {**auth_headers, "Idempotency-Key": "different-key"}
    response = client.post(
        "/api/v1/risk/evaluate", json=intent_payload("payload-key-0001"), headers=headers
    )
    assert response.status_code == 400


def test_verify_then_execute_demo_order(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/risk/evaluate",
        json=intent_payload("verify-risk-0001", amount_paise=450_000),
        headers=auth_headers,
    )
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "VERIFY"
    verified = client.post(
        f"/api/v1/transactions/{result['transaction_id']}/verify",
        json={"action": "APPROVE", "reason": "User confirmed the intended purchase"},
        headers=auth_headers,
    )
    assert verified.status_code == 200
    executed = client.post(
        f"/api/v1/transactions/{result['transaction_id']}/execute", headers=auth_headers
    )
    assert executed.status_code == 200
    assert executed.json()["order_id"].startswith("order_demo_")


def test_hard_block_cannot_execute(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/risk/evaluate",
        json=intent_payload("blocked-risk-001", merchant_category="gambling"),
        headers=auth_headers,
    )
    result = response.json()
    assert result["decision"] == "BLOCK"
    executed = client.post(
        f"/api/v1/transactions/{result['transaction_id']}/execute", headers=auth_headers
    )
    assert executed.status_code == 409


def test_verify_is_single_use(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/risk/evaluate",
        json=intent_payload("single-use-verify", amount_paise=450_000),
        headers=auth_headers,
    )
    transaction_id = response.json()["transaction_id"]
    payload = {"action": "APPROVE", "reason": "User confirmed purchase"}
    assert (
        client.post(
            f"/api/v1/transactions/{transaction_id}/verify", json=payload, headers=auth_headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/transactions/{transaction_id}/verify", json=payload, headers=auth_headers
        ).status_code
        == 409
    )


def test_webhook_rejects_invalid_and_deduplicates(client: TestClient) -> None:
    payload = {
        "id": "evt_1",
        "event": "payment.captured",
        "payload": {
            "payment": {"entity": {"id": "pay_1", "order_id": "missing", "status": "captured"}}
        },
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    assert (
        client.post(
            "/api/v1/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": "bad", "Content-Type": "application/json"},
        ).status_code
        == 401
    )
    signature = hmac.new(TEST_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    headers = {"X-Razorpay-Signature": signature, "Content-Type": "application/json"}
    assert (
        client.post("/api/v1/webhooks/razorpay", content=body, headers=headers).json()["status"]
        == "accepted"
    )
    assert (
        client.post("/api/v1/webhooks/razorpay", content=body, headers=headers).json()["status"]
        == "duplicate_ignored"
    )
