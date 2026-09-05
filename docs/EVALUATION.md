# Track 02 evaluation methodology

## Claim boundary

All data is synthetic and reproducible. Results demonstrate a rigorous detector/evaluation workflow; they do not claim performance on Razorpay customer transactions.

## Dataset

- 10,000 temporally ordered synthetic agent-payment records
- Fixed random seed: 42
- Time-based 70% train / 15% validation / 15% held-out test
- Features: amount deviation, velocity, device novelty, merchant novelty, unusual time, region mismatch, category risk, and mandate utilization
- Controlled drift in the final 15% simulates modest future behavior change

## Model selection

Logistic regression provides an interpretable baseline. Histogram gradient boosting captures interactions and nonlinear thresholds. Isolation Forest is an unsupervised anomaly comparison. Model selection uses validation PR-AUC; the held-out test is used only for final reporting.

## Metrics

- Precision, recall, F1
- PR-AUC and ROC-AUC
- False-positive rate and count
- False-negative count and payment exposure
- Estimated false-positive review cost: ₹150 per legitimate payment escalated
- Illustrative false-negative loss severity: 10% of missed anomalous payment value

Run:

```bash
make benchmark
```

## Held-out results

Generated on 2026-09-05 by `app.ml.benchmark` against 1,500 untouched future records:

| Metric | Result |
|---|---:|
| Selected model | Logistic regression |
| Operating threshold | 0.80 |
| Precision | **94.78%** |
| Recall | **85.83%** |
| F1 | **90.08%** |
| PR-AUC | **90.18%** |
| ROC-AUC | **94.80%** |
| False-positive rate | **0.44%** (6 / 1,373 legitimate) |
| False positives | 6 |
| False negatives | 18 |
| Estimated false-positive cost | **₹900** |
| Estimated missed-anomaly exposure | **₹48,741.55** |
| Estimated operating cost | **₹5,774.15** |

The complete threshold comparison and confusion matrices are in `benchmark-results.json`.

## Limitations

Synthetic labels encode assumptions and may overstate separability. Cost values are illustrative, not merchant-calibrated. Real deployment requires backtesting against consented historical data, bias review, drift monitoring, challenger models, and threshold approval by risk operations.
