import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./agentshield-test.db"
TEST_JWT_SECRET = "j" * 40
TEST_WEBHOOK_SECRET = "w" * 40
TEST_DEMO_PASSWORD = "p" * 20
os.environ["JWT_SECRET"] = TEST_JWT_SECRET
os.environ["RAZORPAY_WEBHOOK_SECRET"] = TEST_WEBHOOK_SECRET
os.environ["DEMO_USER_PASSWORD"] = TEST_DEMO_PASSWORD

from app.db.base import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo-admin@agentshield.dev", "password": TEST_DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
