from dataclasses import dataclass
from datetime import UTC

from app.schemas.risk import PaymentIntentCreate, RiskSignal


@dataclass(frozen=True)
class BehavioralContext:
    average_amount_paise: int = 145_000
    amount_std_paise: int = 80_000
    recent_transaction_count: int = 1
    daily_spend_paise: int = 120_000
    device_seen_before: bool = True
    merchant_seen_before: bool = True


@dataclass(frozen=True)
class FeatureVector:
    amount_ratio: float
    amount_zscore: float
    velocity_10m: int
    new_device: int
    new_merchant: int
    unusual_hour: int
    region_mismatch: int
    category_risk: float
    limit_utilization: float

    def as_list(self) -> list[float]:
        return [
            self.amount_ratio,
            self.amount_zscore,
            float(self.velocity_10m),
            float(self.new_device),
            float(self.new_merchant),
            float(self.unusual_hour),
            float(self.region_mismatch),
            self.category_risk,
            self.limit_utilization,
        ]


HIGH_RISK_CATEGORIES = {"gambling", "restricted_goods", "cash_equivalent"}


def extract_features(
    intent: PaymentIntentCreate,
    context: BehavioralContext,
    *,
    max_transaction_paise: int,
    allowed_regions: list[str],
) -> tuple[FeatureVector, list[RiskSignal]]:
    std = max(context.amount_std_paise, 1)
    amount_ratio = intent.amount_paise / max(context.average_amount_paise, 1)
    amount_zscore = max(0.0, (intent.amount_paise - context.average_amount_paise) / std)
    initiated = intent.initiated_at
    if initiated.tzinfo is None:
        initiated = initiated.replace(tzinfo=UTC)
    unusual_hour = int(initiated.hour < 6 or initiated.hour >= 23)
    region_mismatch = int(bool(allowed_regions) and intent.ip_region not in allowed_regions)
    category_risk = 1.0 if intent.merchant_category.lower() in HIGH_RISK_CATEGORIES else 0.0
    vector = FeatureVector(
        amount_ratio=min(amount_ratio, 20.0),
        amount_zscore=min(amount_zscore, 20.0),
        velocity_10m=min(context.recent_transaction_count, 20),
        new_device=int(not context.device_seen_before),
        new_merchant=int(not context.merchant_seen_before),
        unusual_hour=unusual_hour,
        region_mismatch=region_mismatch,
        category_risk=category_risk,
        limit_utilization=intent.amount_paise / max(max_transaction_paise, 1),
    )
    signals: list[RiskSignal] = []
    if vector.amount_ratio >= 3:
        signals.append(
            RiskSignal(
                code="amount_anomaly",
                label="Amount anomaly",
                contribution=21,
                evidence=f"{vector.amount_ratio:.1f}× historical average",
            )
        )
    if vector.new_device:
        signals.append(
            RiskSignal(
                code="new_device",
                label="New device",
                contribution=18,
                evidence="Device has no trusted payment history",
            )
        )
    if vector.new_merchant:
        signals.append(
            RiskSignal(
                code="new_merchant",
                label="New merchant",
                contribution=12,
                evidence="First payment to this merchant",
            )
        )
    if vector.velocity_10m >= 4:
        signals.append(
            RiskSignal(
                code="high_velocity",
                label="Unusual velocity",
                contribution=14,
                evidence=f"{vector.velocity_10m} attempts in 10 minutes",
            )
        )
    if vector.unusual_hour:
        signals.append(
            RiskSignal(
                code="unusual_hour",
                label="Unusual time",
                contribution=8,
                evidence="Initiated outside normal hours",
            )
        )
    if vector.region_mismatch:
        signals.append(
            RiskSignal(
                code="region_mismatch",
                label="Region mismatch",
                contribution=15,
                evidence=f"{intent.ip_region} is outside delegated regions",
            )
        )
    if context.merchant_seen_before:
        signals.append(
            RiskSignal(
                code="known_merchant",
                label="Known merchant",
                contribution=-10,
                evidence="Merchant has prior successful history",
            )
        )
    return vector, signals
