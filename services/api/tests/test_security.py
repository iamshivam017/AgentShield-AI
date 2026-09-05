import hashlib
import hmac

import pytest

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    verify_razorpay_signature,
)


def test_password_round_trip_and_rejects_wrong_password() -> None:
    encoded = hash_password("correct horse battery staple", salt=b"0123456789abcdef")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)


def test_jwt_round_trip() -> None:
    secret = "j" * 40
    token = create_access_token("user-1", "ADMIN", secret, 5)
    payload = decode_access_token(token, secret)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "ADMIN"


def test_razorpay_signature() -> None:
    body = b'{"event":"payment.captured"}'
    webhook_secret = "w" * 40
    signature = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_razorpay_signature(body, signature, webhook_secret)
    assert not verify_razorpay_signature(body, "invalid", webhook_secret)


def test_cors_origins_accept_comma_separated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://one.example, https://two.example")
    settings = Settings(jwt_secret="j" * 40)
    assert settings.cors_origin_list == ["https://one.example", "https://two.example"]
