import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import DbSession, require_roles
from app.db.models import AuditEvent, PaymentIntent
from app.domain.enums import Role

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    correlation_id: uuid.UUID
    actor: str
    action: str
    status: str
    reason: str
    event_metadata: dict[str, object]
    created_at: datetime


@router.get("/{transaction_id}", response_model=list[AuditEventResponse])
def transaction_audit(
    transaction_id: uuid.UUID,
    db: DbSession,
    _: object = Depends(require_roles(Role.ADMIN, Role.RISK_ANALYST, Role.OPERATOR, Role.VIEWER)),
) -> list[AuditEventResponse]:
    if not db.get(PaymentIntent, str(transaction_id)):
        raise HTTPException(status_code=404, detail="Transaction not found")
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.payment_intent_id == str(transaction_id))
        .order_by(AuditEvent.created_at)
    ).all()
    return [
        AuditEventResponse(
            id=uuid.UUID(event.id),
            correlation_id=uuid.UUID(event.correlation_id),
            actor=event.actor,
            action=event.action,
            status=event.status,
            reason=event.reason,
            event_metadata=event.event_metadata,
            created_at=event.created_at.replace(tzinfo=UTC),
        )
        for event in events
    ]
