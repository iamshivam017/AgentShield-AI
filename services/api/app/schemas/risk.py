from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import Decision, TransactionStatus


class PaymentIntentCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    agent_id: str = Field(min_length=3, max_length=64)
    merchant_id: str = Field(min_length=3, max_length=64)
    merchant_name: str = Field(min_length=2, max_length=120)
    merchant_category: str = Field(min_length=2, max_length=64)
    amount_paise: int = Field(gt=0, le=100_000_000)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    device_id: str = Field(min_length=3, max_length=128)
    ip_region: str = Field(min_length=2, max_length=64)
    purpose: str = Field(min_length=3, max_length=240)
    initiated_at: datetime

    @field_validator("merchant_name", "purpose")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise ValueError("control characters are not permitted")
        return value.strip()


class RiskSignal(BaseModel):
    code: str
    label: str
    contribution: int = Field(ge=-100, le=100)
    evidence: str


class RiskDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: UUID
    correlation_id: UUID
    decision: Decision
    status: TransactionStatus
    risk_score: int = Field(ge=0, le=100)
    model_probability: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    signals: list[RiskSignal]
    policy_violations: list[str]
    explanation: str
    explanation_source: str
    model_version: str
    created_at: datetime


class VerificationRequest(BaseModel):
    action: str = Field(pattern=r"^(APPROVE|BLOCK)$")
    reason: str = Field(min_length=3, max_length=240)


class TransactionListItem(BaseModel):
    transaction_id: UUID
    merchant_name: str
    amount_paise: int
    decision: Decision
    status: TransactionStatus
    risk_score: int
    created_at: datetime


class DashboardSummary(BaseModel):
    total: int
    allowed: int
    verify: int
    blocked: int
    amount_screened_paise: int
    amount_blocked_paise: int
    avg_risk_score: float
    decisions_by_hour: list[dict[str, Any]]
