from dataclasses import dataclass

from app.db.models import AgentPolicy
from app.domain.enums import Decision
from app.schemas.risk import PaymentIntentCreate, RiskSignal


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    violations: list[str]
    signals: list[RiskSignal]


def evaluate_policy(
    intent: PaymentIntentCreate,
    policy: AgentPolicy,
    *,
    daily_spend_paise: int,
    risk_score: int,
) -> PolicyResult:
    violations: list[str] = []
    signals: list[RiskSignal] = []
    category = intent.merchant_category.lower()

    # SQLAlchemy applies column defaults at insert time, so transient policy
    # objects can expose ``None`` here. Only an explicit false disables an agent.
    if policy.is_active is False:
        violations.append("agent_disabled")
    if category in set(policy.blocked_categories):
        violations.append("blocked_merchant_category")
    if intent.amount_paise > policy.max_transaction_paise:
        violations.append("amount_above_agent_limit")
        signals.append(
            RiskSignal(
                code="agent_limit_exceeded",
                label="Agent limit exceeded",
                contribution=30,
                evidence=(
                    f"₹{intent.amount_paise / 100:,.0f} exceeds "
                    f"₹{policy.max_transaction_paise / 100:,.0f} mandate"
                ),
            )
        )
    if daily_spend_paise + intent.amount_paise > policy.daily_limit_paise:
        violations.append("daily_limit_exceeded")
    if policy.allowed_regions and intent.ip_region not in policy.allowed_regions:
        violations.append("region_outside_mandate")

    hard_blocks = {"agent_disabled", "blocked_merchant_category", "daily_limit_exceeded"}
    if hard_blocks.intersection(violations) or risk_score >= 85:
        decision = Decision.BLOCK
    elif (
        violations or intent.amount_paise >= policy.verification_threshold_paise or risk_score >= 55
    ):
        decision = Decision.VERIFY
    else:
        decision = Decision.ALLOW
    return PolicyResult(decision=decision, violations=violations, signals=signals)
