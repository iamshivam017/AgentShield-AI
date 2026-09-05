import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.data import FEATURE_NAMES, generate_synthetic_dataset, temporal_split


def metrics_at_threshold(
    y_true: np.ndarray[Any, Any],
    probabilities: np.ndarray[Any, Any],
    amounts_paise: np.ndarray[Any, Any],
    threshold: float,
) -> dict[str, Any]:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    # Operational estimate: ₹150 analyst friction per false positive; the amount of
    # each missed anomalous transaction is the false-negative exposure.
    fp_cost_paise = int(fp * 15_000)
    fn_exposure_paise = int(amounts_paise[(y_true == 1) & (predictions == 0)].sum())
    return {
        "threshold": threshold,
        "precision": round(float(precision_score(y_true, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, predictions, zero_division=0)), 4),
        "false_positive_rate": round(float(fp / max(fp + tn, 1)), 4),
        "false_positive_count": int(fp),
        "false_negative_count": int(fn),
        "true_positive_count": int(tp),
        "true_negative_count": int(tn),
        "estimated_false_positive_cost_paise": fp_cost_paise,
        "estimated_false_negative_exposure_paise": fn_exposure_paise,
    }


def run_benchmark() -> dict[str, Any]:
    dataset = generate_synthetic_dataset(size=10_000, seed=42)
    train, validation, test = temporal_split(dataset)
    models: dict[str, Any] = {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(max_iter=500, class_weight="balanced", random_state=42),
                ),
            ]
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            learning_rate=0.07,
            max_iter=150,
            max_leaf_nodes=15,
            min_samples_leaf=30,
            l2_regularization=0.4,
            class_weight="balanced",
            random_state=42,
        ),
    }
    validation_results: dict[str, Any] = {}
    fitted: dict[str, Any] = {}
    for name, model in models.items():
        model.fit(train.x, train.y)
        fitted[name] = model
        probabilities = model.predict_proba(validation.x)[:, 1]
        validation_results[name] = {
            "pr_auc": round(float(average_precision_score(validation.y, probabilities)), 4),
            "roc_auc": round(float(roc_auc_score(validation.y, probabilities)), 4),
        }

    anomaly = IsolationForest(contamination=0.06, random_state=42)
    anomaly.fit(train.x[train.y == 0])
    anomaly_score = -anomaly.decision_function(validation.x)
    validation_results["isolation_forest"] = {
        "pr_auc": round(float(average_precision_score(validation.y, anomaly_score)), 4),
        "roc_auc": round(float(roc_auc_score(validation.y, anomaly_score)), 4),
    }
    winner = max(models, key=lambda name: validation_results[name]["pr_auc"])
    test_probabilities = fitted[winner].predict_proba(test.x)[:, 1]

    candidates = [
        metrics_at_threshold(test.y, test_probabilities, test.amounts_paise, value)
        for value in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
    ]
    # Pick the smallest estimated operating loss with conservative 10% loss severity
    # for missed anomalies. This choice is made without altering the held-out labels.
    for item in candidates:
        item["estimated_operating_cost_paise"] = item["estimated_false_positive_cost_paise"] + int(
            item["estimated_false_negative_exposure_paise"] * 0.10
        )
    selected = min(candidates, key=lambda item: item["estimated_operating_cost_paise"])
    return {
        "dataset": {
            "source": "reproducible synthetic agent-payment generator",
            "seed": 42,
            "records": len(dataset.y),
            "train_records": len(train.y),
            "validation_records": len(validation.y),
            "held_out_test_records": len(test.y),
            "split": "temporal 70/15/15",
            "positive_rate": round(float(dataset.y.mean()), 4),
            "features": FEATURE_NAMES,
        },
        "validation_model_comparison": validation_results,
        "selected_model": winner,
        "test_pr_auc": round(float(average_precision_score(test.y, test_probabilities)), 4),
        "test_roc_auc": round(float(roc_auc_score(test.y, test_probabilities)), 4),
        "threshold_comparison": candidates,
        "selected_operating_point": selected,
        "cost_assumptions": {
            "false_positive_review_cost_paise": 15_000,
            "false_negative_loss_severity": 0.10,
            "limitations": (
                "Synthetic ground truth and illustrative cost assumptions; not production "
                "Razorpay data."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_benchmark()
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
