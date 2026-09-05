from functools import lru_cache

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.domain.features import FeatureVector
from app.ml.data import generate_synthetic_dataset, temporal_split

MODEL_VERSION = "logreg-calibrated-synthetic-v1"


class RiskModel:
    def __init__(self) -> None:
        dataset = generate_synthetic_dataset(size=6_000, seed=42)
        train, _, _ = temporal_split(dataset)
        estimator = LogisticRegression(
            max_iter=500,
            class_weight="balanced",
            random_state=42,
        )
        self.pipeline = Pipeline([("scale", StandardScaler()), ("model", estimator)])
        self.model = CalibratedClassifierCV(self.pipeline, method="sigmoid", cv=3)
        self.model.fit(train.x, train.y)

    def predict(self, features: FeatureVector) -> tuple[float, float]:
        sample = np.asarray([features.as_list()], dtype=np.float64)
        probability = float(self.model.predict_proba(sample)[0, 1])
        confidence = float(max(probability, 1 - probability))
        return probability, confidence


@lru_cache
def get_risk_model() -> RiskModel:
    return RiskModel()
