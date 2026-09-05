import hashlib
import json

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AppSettings, DbSession
from app.core.security import verify_razorpay_signature
from app.db.models import AuditEvent, PaymentIntent, ProcessedWebhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay", status_code=status.HTTP_202_ACCEPTED)
async def razorpay_webhook(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
) -> dict[str, str]:
    if not settings.razorpay_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook verification is not configured")
    body = await request.body()
    if not signature or not verify_razorpay_signature(
        body, signature, settings.razorpay_webhook_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(body)
        event_type = str(payload["event"])
        entity = payload["payload"]["payment"]["entity"]
        event_id = str(payload.get("id") or f"{event_type}:{entity['id']}")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Malformed webhook payload") from exc
    if db.scalar(select(ProcessedWebhook).where(ProcessedWebhook.event_id == event_id)):
        return {"status": "duplicate_ignored"}
    db.add(
        ProcessedWebhook(
            event_id=event_id, event_type=event_type, payload_hash=hashlib.sha256(body).hexdigest()
        )
    )
    order_id = entity.get("order_id")
    intent = (
        db.scalar(select(PaymentIntent).where(PaymentIntent.razorpay_order_id == order_id))
        if order_id
        else None
    )
    if intent:
        db.add(
            AuditEvent(
                payment_intent_id=intent.id,
                correlation_id=intent.correlation_id,
                actor="razorpay-webhook",
                action=event_type,
                status=str(entity.get("status", "received")),
                reason="Verified Razorpay webhook processed",
                event_metadata={"payment_id": entity.get("id")},
            )
        )
    try:
        db.commit()
    except IntegrityError:
        # A concurrent delivery may win the unique event-id insert after our
        # initial read. Roll back every side effect from this duplicate.
        db.rollback()
        return {"status": "duplicate_ignored"}
    return {"status": "accepted"}
