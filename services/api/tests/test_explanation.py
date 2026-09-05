import pytest

from app.core.config import Settings
from app.domain.enums import Decision
from app.domain.explanation import create_explanation
from app.schemas.risk import RiskSignal


@pytest.mark.anyio
async def test_deterministic_explanation_needs_no_provider() -> None:
    settings = Settings(
        environment="test",
        jwt_secret="j" * 40,
        llm_provider="deterministic",
    )
    result = await create_explanation(
        settings,
        Decision.VERIFY,
        77,
        [
            RiskSignal(
                code="new_device",
                label="New device",
                contribution=18,
                evidence="Device has no trusted history",
            )
        ],
        ["amount_above_agent_limit"],
    )
    assert result.source == "deterministic"
    assert "amount above agent limit" in result.text
