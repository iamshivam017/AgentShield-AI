from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FEATURE_NAMES = [
    "amount_ratio",
    "amount_zscore",
    "velocity_10m",
    "new_device",
    "new_merchant",
    "unusual_hour",
    "region_mismatch",
    "category_risk",
    "limit_utilization",
]


@dataclass(frozen=True)
class Dataset:
    x: NDArray[np.float64]
    y: NDArray[np.int64]
    amounts_paise: NDArray[np.int64]
    timestamps: NDArray[np.int64]


def generate_synthetic_dataset(size: int = 10_000, seed: int = 42) -> Dataset:
    """Generate labeled, temporally ordered agent-payment data.

    Labels are produced from latent risk plus noise, rather than copied from the policy
    thresholds used by the application. This keeps the benchmark honest while remaining
    reproducible and explicitly synthetic.
    """
    rng = np.random.default_rng(seed)
    timestamps = np.arange(size, dtype=np.int64)
    amount_ratio = np.clip(rng.lognormal(0.0, 0.38, size), 0.05, 15)
    amount_zscore = np.maximum(0, (amount_ratio - 1) * rng.uniform(0.8, 1.8, size))
    velocity = np.clip(rng.poisson(0.8, size), 0, 15)
    new_device = rng.binomial(1, 0.06, size)
    new_merchant = rng.binomial(1, 0.14, size)
    unusual_hour = rng.binomial(1, 0.08, size)
    region_mismatch = rng.binomial(1, 0.03, size)
    category_risk = rng.binomial(1, 0.01, size)
    limit_utilization = np.clip(amount_ratio * rng.uniform(0.18, 0.65, size), 0.01, 6)

    # Inject a known anomaly class using correlated behavioral changes. The target
    # is not copied from an application policy threshold: each anomalous record has
    # a varied combination and no single feature is sufficient.
    labels = rng.binomial(1, 0.085, size).astype(np.int64)
    anomalous = labels == 1
    count = int(anomalous.sum())
    amount_ratio[anomalous] *= rng.uniform(1.6, 4.8, count)
    amount_zscore[anomalous] = np.maximum(
        amount_zscore[anomalous], (amount_ratio[anomalous] - 1) * rng.uniform(0.9, 1.7, count)
    )
    velocity[anomalous] += rng.binomial(6, 0.55, count)
    new_device[anomalous] = np.maximum(new_device[anomalous], rng.binomial(1, 0.62, count))
    new_merchant[anomalous] = np.maximum(new_merchant[anomalous], rng.binomial(1, 0.57, count))
    unusual_hour[anomalous] = np.maximum(unusual_hour[anomalous], rng.binomial(1, 0.30, count))
    region_mismatch[anomalous] = np.maximum(
        region_mismatch[anomalous], rng.binomial(1, 0.32, count)
    )
    category_risk[anomalous] = np.maximum(category_risk[anomalous], rng.binomial(1, 0.18, count))
    limit_utilization[anomalous] *= rng.uniform(1.15, 2.8, count)

    # Add 1% ambiguous labels and moderate behavioral drift in the held-out future
    # window so the evaluation is not perfectly separable.
    flip = rng.random(size) < 0.01
    labels[flip] = 1 - labels[flip]
    drift = timestamps > int(size * 0.85)
    new_device[drift] = np.maximum(new_device[drift], rng.binomial(1, 0.04, drift.sum()))
    velocity[drift] += rng.binomial(2, 0.08, drift.sum())
    base_amounts = rng.lognormal(np.log(150_000), 0.7, size)
    amounts = np.clip(base_amounts * amount_ratio, 5_000, 10_000_000).astype(np.int64)
    x = np.column_stack(
        [
            amount_ratio,
            amount_zscore,
            velocity,
            new_device,
            new_merchant,
            unusual_hour,
            region_mismatch,
            category_risk,
            limit_utilization,
        ]
    ).astype(np.float64)
    return Dataset(x=x, y=labels, amounts_paise=amounts, timestamps=timestamps)


def temporal_split(dataset: Dataset) -> tuple[Dataset, Dataset, Dataset]:
    train_end = int(len(dataset.y) * 0.70)
    validation_end = int(len(dataset.y) * 0.85)

    def subset(start: int, end: int) -> Dataset:
        return Dataset(
            x=dataset.x[start:end],
            y=dataset.y[start:end],
            amounts_paise=dataset.amounts_paise[start:end],
            timestamps=dataset.timestamps[start:end],
        )

    return (
        subset(0, train_end),
        subset(train_end, validation_end),
        subset(validation_end, len(dataset.y)),
    )
