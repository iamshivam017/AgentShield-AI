# Synthetic data

No customer or Razorpay transaction data is stored in this repository. The benchmark dataset is generated in memory by `services/api/app/ml/data.py` using seed `42`, controlled multi-signal anomaly injection, a 1% ambiguity rate, and modest drift in the future test window.

Recreate all 10,000 records and metrics with:

```bash
make benchmark
```

Generated model binaries are intentionally excluded from Git. A production training pipeline should version consented data, schemas, feature definitions, and signed artifacts in a dedicated registry.
