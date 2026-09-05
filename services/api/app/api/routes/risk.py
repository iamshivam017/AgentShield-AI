import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import AppSettings, DbSession, require_roles
from app.db.models import AgentPolicy, AuditEvent, PaymentIntent
from app.domain.enums import Decision, Role, TransactionStatus
from app.domain.explanation import create_explanation
from app.domain.features import BehavioralContext, extract_features
from app.domain.policy import evaluate_policy
from app.domain.razorpay import RazorpayService, RazorpayUnavailableError
from app.ml.model import MODEL_VERSION, get_risk_model
from app.schemas.risk import (
    DashboardSummary,
    PaymentIntentCreate,
    RiskDecisionResponse,
    TransactionListItem,
    VerificationRequest,
)

router = APIRouter(tags=["risk"])


def serialize_response(intent: PaymentIntent) -> RiskDecisionResponse:
    return RiskDecisionResponse(
        transaction_id=uuid.UUID(intent.id),
        correlation_id=uuid.UUID(intent.correlation_id),
        decision=Decision(intent.decision),
        status=TransactionStatus(intent.status),
        risk_score=intent.risk_score,
        model_probability=intent.model_probability,
        confidence=intent.confidence,
        signals=intent.signals,
        policy_violations=intent.policy_violations,
        explanation=intent.explanation,
        explanation_source=intent.explanation_source,
        model_version=intent.model_version,
        created_at=intent.created_at.replace(tzinfo=UTC),
    )


@router.post("/risk/evaluate", response_model=RiskDecisionResponse)
async def evaluate_payment(
    payload: PaymentIntentCreate,
    db: DbSession,
    settings: AppSettings,
    _: object = Depends(require_roles(Role.ADMIN, Role.RISK_ANALYST, Role.OPERATOR)),
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> RiskDecisionResponse:
    if idempotency_header and idempotency_header != payload.idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency key mismatch")
    existing = db.scalar(
        select(PaymentIntent).where(PaymentIntent.idempotency_key == payload.idempotency_key)
    )
    if existing:
        return serialize_response(existing)

    policy = db.scalar(select(AgentPolicy).where(AgentPolicy.agent_id == payload.agent_id))
    if policy is None:
        raise HTTPException(status_code=404, detail="Agent policy not found")
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
    prior = list(
        db.scalars(
            select(PaymentIntent)
            .where(PaymentIntent.agent_id == payload.agent_id, PaymentIntent.created_at >= since)
            .order_by(PaymentIntent.created_at.desc())
            .limit(100)
        )
    )
    known_merchants = {item.merchant_id for item in prior}
    known_devices = {item.device_id for item in prior}
    average = int(sum(item.amount_paise for item in prior) / len(prior)) if prior else 145_000
    daily_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    daily_spend = sum(
        item.amount_paise
        for item in prior
        if item.created_at >= daily_start and item.status not in {TransactionStatus.BLOCKED.value}
    )
    context = BehavioralContext(
        average_amount_paise=average,
        amount_std_paise=max(int(average * 0.55), 1),
        recent_transaction_count=sum(
            1
            for item in prior
            if item.created_at >= datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10)
        ),
        daily_spend_paise=daily_spend,
        device_seen_before=not prior or payload.device_id in known_devices,
        merchant_seen_before=not prior or payload.merchant_id in known_merchants,
    )
    features, signals = extract_features(
        payload,
        context,
        max_transaction_paise=policy.max_transaction_paise,
        allowed_regions=policy.allowed_regions,
    )
    probability, confidence = get_risk_model().predict(features)
    risk_score = round(probability * 100)
    policy_result = evaluate_policy(
        payload, policy, daily_spend_paise=daily_spend, risk_score=risk_score
    )
    signals.extend(policy_result.signals)
    explanation = await create_explanation(
        settings, policy_result.decision, risk_score, signals, policy_result.violations
    )
    transaction_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    tx_status = {
        Decision.ALLOW: TransactionStatus.APPROVED,
        Decision.VERIFY: TransactionStatus.AWAITING_VERIFICATION,
        Decision.BLOCK: TransactionStatus.BLOCKED,
    }[policy_result.decision]
    intent = PaymentIntent(
        id=transaction_id,
        correlation_id=correlation_id,
        **payload.model_dump(exclude={"initiated_at"}),
        initiated_at=payload.initiated_at.replace(tzinfo=None),
        decision=policy_result.decision.value,
        status=tx_status.value,
        risk_score=risk_score,
        model_probability=probability,
        confidence=confidence,
        signals=[signal.model_dump() for signal in signals],
        policy_violations=policy_result.violations,
        explanation=explanation.text,
        explanation_source=explanation.source,
        model_version=MODEL_VERSION,
    )
    db.add(intent)
    for action, event_status, reason in (
        ("payment.requested", "RECEIVED", "Agent submitted a payment intent"),
        ("risk.scored", "COMPLETED", f"Model score {risk_score}/100"),
        ("policy.evaluated", policy_result.decision.value, explanation.text[:240]),
    ):
        db.add(
            AuditEvent(
                payment_intent_id=transaction_id,
                correlation_id=correlation_id,
                actor=payload.agent_id,
                action=action,
                status=event_status,
                reason=reason,
                event_metadata={"model_version": MODEL_VERSION},
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        replay = db.scalar(
            select(PaymentIntent).where(PaymentIntent.idempotency_key == payload.idempotency_key)
        )
        if replay:
            return serialize_response(replay)
        raise
    db.refresh(intent)
    return serialize_response(intent)


@router.get("/transactions", response_model=list[TransactionListItem])
def list_transactions(
    db: DbSession,
    _: object = Depends(require_roles(Role.ADMIN, Role.RISK_ANALYST, Role.OPERATOR, Role.VIEWER)),
    decision: Decision | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TransactionListItem]:
    query = select(PaymentIntent).order_by(PaymentIntent.created_at.desc()).limit(limit)
    if decision:
        query = query.where(PaymentIntent.decision == decision.value)
    items = db.scalars(query).all()
    return [
        TransactionListItem(
            transaction_id=uuid.UUID(item.id),
            merchant_name=item.merchant_name,
            amount_paise=item.amount_paise,
            decision=Decision(item.decision),
            status=TransactionStatus(item.status),
            risk_score=item.risk_score,
            created_at=item.created_at.replace(tzinfo=UTC),
        )
        for item in items
    ]


@router.get("/transactions/{transaction_id}", response_model=RiskDecisionResponse)
def get_transaction(
    transaction_id: uuid.UUID,
    db: DbSession,
    _: object = Depends(require_roles(Role.ADMIN, Role.RISK_ANALYST, Role.OPERATOR, Role.VIEWER)),
) -> RiskDecisionResponse:
    intent = db.get(PaymentIntent, str(transaction_id))
    if not intent:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return serialize_response(intent)


@router.post("/transactions/{transaction_id}/verify", response_model=RiskDecisionResponse)
def verify_transaction(
    transaction_id: uuid.UUID,
    payload: VerificationRequest,
    db: DbSession,
    user: object = Depends(require_roles(Role.ADMIN, Role.RISK_ANALYST)),
) -> RiskDecisionResponse:
    intent = db.get(PaymentIntent, str(transaction_id))
    if not intent:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if intent.status != TransactionStatus.AWAITING_VERIFICATION.value:
        raise HTTPException(status_code=409, detail="Transaction is not awaiting verification")
    if payload.action == "APPROVE":
        next_status = TransactionStatus.APPROVED.value
        next_decision = intent.decision
    else:
        next_status = TransactionStatus.BLOCKED.value
        next_decision = Decision.BLOCK.value
    result = db.execute(
        update(PaymentIntent)
        .where(
            PaymentIntent.id == str(transaction_id),
            PaymentIntent.status == TransactionStatus.AWAITING_VERIFICATION.value,
        )
        .values(status=next_status, decision=next_decision)
    )
    if getattr(result, "rowcount", 0) != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="Verification was already resolved")
    db.add(
        AuditEvent(
            payment_intent_id=intent.id,
            correlation_id=intent.correlation_id,
            actor=f"user:{getattr(user, 'id', 'unknown')}",
            action="verification.resolved",
            status=payload.action,
            reason=payload.reason,
            event_metadata={},
        )
    )
    db.commit()
    resolved = db.get(PaymentIntent, str(transaction_id))
    if resolved is None:
        raise HTTPException(status_code=500, detail="Verification state unavailable")
    return serialize_response(resolved)


@router.post("/transactions/{transaction_id}/execute")
async def execute_transaction(
    transaction_id: uuid.UUID,
    db: DbSession,
    settings: AppSettings,
    _: object = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
) -> dict[str, str | int]:
    intent = db.get(PaymentIntent, str(transaction_id))
    if not intent:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if intent.razorpay_order_id:
        return {
            "order_id": intent.razorpay_order_id,
            "status": intent.status,
            "amount": intent.amount_paise,
        }
    if intent.status != TransactionStatus.APPROVED.value:
        raise HTTPException(status_code=409, detail="Risk decision does not permit execution")
    claimed = db.execute(
        update(PaymentIntent)
        .where(
            PaymentIntent.id == str(transaction_id),
            PaymentIntent.status == TransactionStatus.APPROVED.value,
            PaymentIntent.razorpay_order_id.is_(None),
        )
        .values(status=TransactionStatus.PAYMENT_PENDING.value)
    )
    if getattr(claimed, "rowcount", 0) != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="Payment execution is already in progress")
    db.add(
        AuditEvent(
            payment_intent_id=intent.id,
            correlation_id=intent.correlation_id,
            actor="razorpay-adapter",
            action="payment.create_started",
            status="PENDING",
            reason="Risk-approved test order creation started",
            event_metadata={},
        )
    )
    db.commit()
    try:
        order = await RazorpayService(settings).create_order(
            amount_paise=intent.amount_paise,
            currency=intent.currency,
            receipt=intent.id,
            idempotency_key=intent.idempotency_key,
        )
    except RazorpayUnavailableError as exc:
        intent.status = TransactionStatus.PAYMENT_FAILED.value
        db.add(
            AuditEvent(
                payment_intent_id=intent.id,
                correlation_id=intent.correlation_id,
                actor="razorpay-adapter",
                action="payment.create_failed",
                status="FAILED_SAFE",
                reason=str(exc),
                event_metadata={},
            )
        )
        db.commit()
        raise HTTPException(
            status_code=503, detail="Payment provider unavailable; no charge was attempted"
        ) from exc
    intent.razorpay_order_id = order.id
    intent.status = TransactionStatus.PAYMENT_CREATED.value
    db.add(
        AuditEvent(
            payment_intent_id=intent.id,
            correlation_id=intent.correlation_id,
            actor="razorpay-adapter",
            action="payment.order_created",
            status=order.status,
            reason="Risk-approved Razorpay test order created",
            event_metadata={"order_id": order.id},
        )
    )
    db.commit()
    return {"order_id": order.id, "status": order.status, "amount": order.amount}


@router.get("/metrics/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: DbSession,
    _: object = Depends(require_roles(Role.ADMIN, Role.RISK_ANALYST, Role.OPERATOR, Role.VIEWER)),
) -> DashboardSummary:
    total, allowed, verify, blocked, amount, blocked_amount, average = db.execute(
        select(
            func.count(PaymentIntent.id),
            func.sum(case((PaymentIntent.decision == Decision.ALLOW.value, 1), else_=0)),
            func.sum(case((PaymentIntent.decision == Decision.VERIFY.value, 1), else_=0)),
            func.sum(case((PaymentIntent.decision == Decision.BLOCK.value, 1), else_=0)),
            func.coalesce(func.sum(PaymentIntent.amount_paise), 0),
            func.coalesce(
                func.sum(
                    case(
                        (
                            PaymentIntent.decision == Decision.BLOCK.value,
                            PaymentIntent.amount_paise,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(func.avg(PaymentIntent.risk_score), 0),
        )
    ).one()
    return DashboardSummary(
        total=total or 0,
        allowed=allowed or 0,
        verify=verify or 0,
        blocked=blocked or 0,
        amount_screened_paise=amount or 0,
        amount_blocked_paise=blocked_amount or 0,
        avg_risk_score=round(float(average or 0), 1),
        decisions_by_hour=[],
    )
