"""Initial AgentShield schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260905_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "agent_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("max_transaction_paise", sa.Integer(), nullable=False),
        sa.Column("daily_limit_paise", sa.Integer(), nullable=False),
        sa.Column("verification_threshold_paise", sa.Integer(), nullable=False),
        sa.Column("blocked_categories", sa.JSON(), nullable=False),
        sa.Column("allowed_regions", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("agent_id"),
    )
    op.create_index("ix_agent_policies_agent_id", "agent_policies", ["agent_id"])
    op.create_table(
        "payment_intents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column(
            "agent_id", sa.String(64), sa.ForeignKey("agent_policies.agent_id"), nullable=False
        ),
        sa.Column("merchant_id", sa.String(64), nullable=False),
        sa.Column("merchant_name", sa.String(120), nullable=False),
        sa.Column("merchant_category", sa.String(64), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("device_id", sa.String(128), nullable=False),
        sa.Column("ip_region", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(240), nullable=False),
        sa.Column("initiated_at", sa.DateTime(), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("model_probability", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.Column("policy_violations", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("explanation_source", sa.String(32), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("razorpay_order_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
    )
    for name, columns in (
        ("ix_intents_created_decision", ["created_at", "decision"]),
        ("ix_intents_agent_created", ["agent_id", "created_at"]),
        ("ix_payment_intents_correlation_id", ["correlation_id"]),
        ("ix_payment_intents_merchant_id", ["merchant_id"]),
        ("ix_payment_intents_idempotency_key", ["idempotency_key"]),
        ("ix_payment_intents_razorpay_order_id", ["razorpay_order_id"]),
    ):
        op.create_index(name, "payment_intents", columns)
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "payment_intent_id", sa.String(36), sa.ForeignKey("payment_intents.id"), nullable=False
        ),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(240), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_entity_time", "audit_events", ["payment_intent_id", "created_at"])
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])
    op.create_table(
        "processed_webhooks",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("processed_webhooks")
    op.drop_table("audit_events")
    op.drop_table("payment_intents")
    op.drop_table("agent_policies")
    op.drop_table("users")
