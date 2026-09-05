from datetime import UTC, datetime

from app.db.models import AgentPolicy
from app.domain.enums import Decision
from app.domain.features import BehavioralContext, extract_features
from app.domain.policy import evaluate_policy
from app.schemas.risk import PaymentIntentCreate


def make_intent(**overrides: object) -> PaymentIntentCreate:
    values: dict[str, object] = {
        "idempotency_key": "test-intent-001",
        "agent_id": "agent-shopping-01",
        "merchant_id": "merchant-1",
        "merchant_name": "Reliable Store",
        "merchant_category": "retail",
        "amount_paise": 100_000,
        "device_id": "device-known",
        "ip_region": "IN-KA",
        "purpose": "Purchase office supplies",
        "initiated_at": datetime(2026, 9, 5, 10, tzinfo=UTC),
    }
    values.update(overrides)
    return PaymentIntentCreate.model_validate(values)


def make_policy() -> AgentPolicy:
    return AgentPolicy(
        agent_id="agent-shopping-01",
        display_name="Shopping Copilot",
        max_transaction_paise=500_000,
        daily_limit_paise=1_500_000,
        verification_threshold_paise=300_000,
        blocked_categories=["gambling"],
        allowed_regions=["IN-KA"],
    )


def test_normal_intent_is_allowed() -> None:
    result = evaluate_policy(make_intent(), make_policy(), daily_spend_paise=0, risk_score=10)
    assert result.decision == Decision.ALLOW
    assert result.violations == []


def test_agent_limit_requires_verification() -> None:
    result = evaluate_policy(
        make_intent(amount_paise=600_000), make_policy(), daily_spend_paise=0, risk_score=20
    )
    assert result.decision == Decision.VERIFY
    assert "amount_above_agent_limit" in result.violations


def test_blocked_category_is_hard_block() -> None:
    result = evaluate_policy(
        make_intent(merchant_category="gambling"), make_policy(), daily_spend_paise=0, risk_score=5
    )
    assert result.decision == Decision.BLOCK


def test_feature_engine_explains_anomalies() -> None:
    vector, signals = extract_features(
        make_intent(amount_paise=900_000, device_id="new", ip_region="IN-DL"),
        BehavioralContext(
            device_seen_before=False, merchant_seen_before=False, recent_transaction_count=5
        ),
        max_transaction_paise=500_000,
        allowed_regions=["IN-KA"],
    )
    assert vector.amount_ratio > 3
    assert {signal.code for signal in signals} >= {
        "amount_anomaly",
        "new_device",
        "new_merchant",
        "high_velocity",
        "region_mismatch",
    }
