from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.deps import DbSession, require_roles
from app.db.models import AgentPolicy
from app.domain.enums import Role

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    display_name: str
    max_transaction_paise: int
    daily_limit_paise: int
    verification_threshold_paise: int
    blocked_categories: list[str]
    allowed_regions: list[str]
    is_active: bool


class PolicyUpdate(BaseModel):
    max_transaction_paise: int = Field(gt=0, le=100_000_000)
    daily_limit_paise: int = Field(gt=0, le=1_000_000_000)
    verification_threshold_paise: int = Field(gt=0, le=100_000_000)
    blocked_categories: list[str] = Field(max_length=50)
    allowed_regions: list[str] = Field(max_length=100)
    is_active: bool = True


@router.get("/{agent_id}", response_model=PolicyResponse)
def get_policy(
    agent_id: str,
    db: DbSession,
    _: object = Depends(require_roles(Role.ADMIN, Role.RISK_ANALYST, Role.OPERATOR, Role.VIEWER)),
) -> AgentPolicy:
    policy = db.scalar(select(AgentPolicy).where(AgentPolicy.agent_id == agent_id))
    if not policy:
        raise HTTPException(status_code=404, detail="Agent policy not found")
    return policy


@router.put("/{agent_id}", response_model=PolicyResponse)
def update_policy(
    agent_id: str,
    payload: PolicyUpdate,
    db: DbSession,
    _: object = Depends(require_roles(Role.ADMIN, Role.RISK_ANALYST)),
) -> AgentPolicy:
    if payload.verification_threshold_paise > payload.max_transaction_paise:
        raise HTTPException(
            status_code=422, detail="Verification threshold cannot exceed the transaction limit"
        )
    if payload.max_transaction_paise > payload.daily_limit_paise:
        raise HTTPException(
            status_code=422, detail="Transaction limit cannot exceed the daily limit"
        )
    policy = db.scalar(select(AgentPolicy).where(AgentPolicy.agent_id == agent_id))
    if not policy:
        raise HTTPException(status_code=404, detail="Agent policy not found")
    for key, value in payload.model_dump().items():
        setattr(policy, key, value)
    db.commit()
    db.refresh(policy)
    return policy
