import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import AgentPolicy, AuditEvent, PaymentIntent, User


def seed_demo_data(db: Session, demo_user_password: str | None = None) -> None:
    if demo_user_password and not db.scalar(
        select(User).where(User.email == "analyst@agentshield.dev")
    ):
        db.add(
            User(
                email="analyst@agentshield.dev",
                password_hash=hash_password(demo_user_password),
                role="RISK_ANALYST",
            )
        )
    if not db.scalar(select(AgentPolicy).where(AgentPolicy.agent_id == "agent-shopping-01")):
        db.add(
            AgentPolicy(
                agent_id="agent-shopping-01",
                display_name="Shopping Copilot",
                max_transaction_paise=500_000,
                daily_limit_paise=1_500_000,
                verification_threshold_paise=300_000,
                blocked_categories=["gambling", "restricted_goods", "cash_equivalent"],
                allowed_regions=["IN-KA", "IN-AS", "IN-DL", "IN-MH"],
            )
        )
    db.flush()
    if (db.scalar(select(func.count(PaymentIntent.id))) or 0) == 0:
        now = datetime.now(UTC).replace(tzinfo=None)
        examples = [
            ("Paper & Pine", 125_000, "ALLOW", 11),
            ("Metro Fresh", 84_500, "ALLOW", 8),
            ("Cloudline Travel", 335_000, "VERIFY", 58),
            ("Aria Electronics", 475_000, "VERIFY", 67),
            ("QuickChip Exchange", 890_000, "BLOCK", 94),
            ("Banyan Books", 62_900, "ALLOW", 6),
            ("Northstar Tools", 215_000, "ALLOW", 18),
            ("Unknown Digital", 640_000, "BLOCK", 88),
        ]
        for index, (merchant, amount, decision, score) in enumerate(examples):
            transaction_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"agentshield-demo-{index}"))
            correlation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"agentshield-correlation-{index}"))
            status = {"ALLOW": "APPROVED", "VERIFY": "AWAITING_VERIFICATION", "BLOCK": "BLOCKED"}[
                decision
            ]
            intent = PaymentIntent(
                id=transaction_id,
                correlation_id=correlation_id,
                idempotency_key=f"seed-payment-{index:04d}",
                agent_id="agent-shopping-01",
                merchant_id=f"seed-merchant-{index:03d}",
                merchant_name=merchant,
                merchant_category="cash_equivalent" if decision == "BLOCK" else "retail",
                amount_paise=amount,
                currency="INR",
                device_id="seed-device-known" if decision == "ALLOW" else f"seed-device-{index}",
                ip_region="IN-KA" if decision != "BLOCK" else "IN-DL",
                purpose="Synthetic buildathon demonstration record",
                initiated_at=now - timedelta(days=1, minutes=(8 - index) * 17),
                decision=decision,
                status=status,
                risk_score=score,
                model_probability=score / 100,
                confidence=max(score / 100, 1 - score / 100),
                signals=[
                    {
                        "code": "demo_signal",
                        "label": "Synthetic scenario",
                        "contribution": max(score - 50, 0),
                        "evidence": "Seeded deterministic demo evidence",
                    }
                ],
                policy_violations=["blocked_merchant_category"] if decision == "BLOCK" else [],
                explanation=(
                    f"{decision}: deterministic synthetic scenario for the buildathon demo."
                ),
                explanation_source="deterministic",
                model_version="seeded-demo-v1",
                created_at=now - timedelta(days=1, minutes=(8 - index) * 17),
            )
            db.add(intent)
            db.add(
                AuditEvent(
                    payment_intent_id=transaction_id,
                    correlation_id=correlation_id,
                    actor="demo-seeder",
                    action="demo.seeded",
                    status=decision,
                    reason="Reproducible synthetic demonstration record",
                    event_metadata={"synthetic": True},
                )
            )
    db.commit()
